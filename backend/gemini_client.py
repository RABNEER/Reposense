import os
import httpx
import json
import re
from pathlib import Path
from dotenv import load_dotenv

env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
GEMINI_MODEL = "gemini-2.5-flash"


class GeminiClient:
    def __init__(self, api_key: str = None):
        self.api_key = api_key or GEMINI_API_KEY
        self.available = bool(self.api_key)

    def _slim_context(self, repo_context: dict) -> dict:
        slim = {
            'repo_name': repo_context.get('repo_name', ''),
            'owner': repo_context.get('owner', ''),
            'metadata': {
                'description': repo_context.get('metadata', {}).get('description', ''),
                'language': repo_context.get('metadata', {}).get('language', ''),
                'stars': repo_context.get('metadata', {}).get('stars', 0),
                'topics': repo_context.get('metadata', {}).get('topics', [])
            },
            'file_tree': [f['path'] for f in
                          repo_context.get('file_tree', [])[:60]],
            'key_files': {}
        }

        for path, content in list(
            repo_context.get('key_files', {}).items()
        )[:4]:
            slim['key_files'][path] = content[:300]

        return slim

    async def _call(self, prompt: str, system: str = None) -> str:
        if not self.api_key:
            raise Exception("GEMINI_API_KEY not set")

        full_prompt = prompt + "\n\nIMPORTANT: Respond with valid JSON only. No markdown fences. No explanation. Just the JSON object."

        messages = []
        if system:
            messages.append({
                "role": "user",
                "parts": [{"text": f"System: {system}\n\n{full_prompt}"}]
            })
        else:
            messages.append({
                "role": "user",
                "parts": [{"text": full_prompt}]
            })

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{GEMINI_BASE_URL}/models/{GEMINI_MODEL}:generateContent",
                params={"key": self.api_key},
                json={
                    "contents": messages,
                    "generationConfig": {
                        "temperature": 0.1,
                        "maxOutputTokens": 8192
                    }
                }
            )

            if response.status_code != 200:
                raise Exception(f"Gemini API error: {response.text}")

            data = response.json()
            return data["candidates"][0]["content"]["parts"][0]["text"]

    def parse_json_response(self, raw: str) -> dict:
        import re
        import json
        
        if not raw:
            raise Exception("Empty response from Gemini")
        
        cleaned = raw.strip()

        # Remove markdown fences if present
        cleaned = re.sub(r'^```json\s*\n?', '', cleaned)
        cleaned = re.sub(r'^```\s*\n?', '', cleaned)
        cleaned = re.sub(r'\n?```\s*$', '', cleaned)
        cleaned = cleaned.strip()

        # Try direct parse
        try:
            result = json.loads(cleaned)
            # If result is a string (double-encoded JSON), parse again
            if isinstance(result, str):
                result = json.loads(result)
            # Must be a dict
            if isinstance(result, dict):
                return result
            # If it's a list, wrap it
            if isinstance(result, list):
                return {"items": result}
        except json.JSONDecodeError:
            pass

        # Try to extract JSON object from text
        try:
            start = cleaned.index('{')
            # Find matching closing brace
            depth = 0
            end = start
            for i, char in enumerate(cleaned[start:], start):
                if char == '{':
                    depth += 1
                elif char == '}':
                    depth -= 1
                    if depth == 0:
                        end = i + 1
                        break
            
            candidate = cleaned[start:end]
            result = json.loads(candidate)
            if isinstance(result, dict):
                return result
        except (ValueError, json.JSONDecodeError):
            pass

        # Last resort: try to fix truncated JSON
        try:
            start = cleaned.index('{')
            candidate = cleaned[start:]
            open_braces = candidate.count('{') - candidate.count('}')
            open_brackets = candidate.count('[') - candidate.count(']')
            # Close open strings first
            if candidate.count('"') % 2 != 0:
                candidate += '"'
            candidate += ']' * max(0, open_brackets)
            candidate += '}' * max(0, open_braces)
            result = json.loads(candidate)
            if isinstance(result, dict):
                return result
        except (ValueError, json.JSONDecodeError):
            pass
        
        raise Exception(
            f"Cannot parse Gemini response as dict. "
            f"Got: {type(cleaned).__name__}. "
            f"Content: {cleaned[:200]}"
        )

    async def analyze(self, repo_context: dict) -> dict:
        slim = self._slim_context(repo_context)
        try:
            from backend.prompts import build_analysis_prompt, SYSTEM_PROMPT
        except ImportError:
            from prompts import build_analysis_prompt, SYSTEM_PROMPT
        prompt = build_analysis_prompt(slim)
        raw = await self._call(prompt, SYSTEM_PROMPT)
        result = self.parse_json_response(raw)
        if not isinstance(result, dict):
            raise Exception(f"Expected dict, got {type(result)}: {str(result)[:100]}")
        return result

    async def find_issue(self, repo_context: dict) -> dict:
        slim = self._slim_context(repo_context)
        try:
            from backend.prompts import build_issue_prompt, SYSTEM_PROMPT
        except ImportError:
            from prompts import build_issue_prompt, SYSTEM_PROMPT
        prompt = build_issue_prompt(slim)
        raw = await self._call(prompt, SYSTEM_PROMPT)
        result = self.parse_json_response(raw)
        if not isinstance(result, dict):
            raise Exception(f"Expected dict, got {type(result)}: {str(result)[:100]}")
        return result

    async def plan_solution(self, repo_context: dict, issue: dict) -> dict:
        slim = self._slim_context(repo_context)
        try:
            from backend.prompts import build_plan_prompt, SYSTEM_PROMPT
        except ImportError:
            from prompts import build_plan_prompt, SYSTEM_PROMPT
        prompt = build_plan_prompt(slim, issue)
        raw = await self._call(prompt, SYSTEM_PROMPT)
        result = self.parse_json_response(raw)
        if not isinstance(result, dict):
            raise Exception(f"Expected dict, got {type(result)}: {str(result)[:100]}")
        return result

    async def generate_code(self, repo_context: dict, issue: dict, plan: dict) -> dict:
        slim = self._slim_context(repo_context)
        try:
            from backend.prompts import build_code_prompt, SYSTEM_PROMPT
        except ImportError:
            from prompts import build_code_prompt, SYSTEM_PROMPT
        prompt = build_code_prompt(slim, issue, plan)
        raw = await self._call(prompt, SYSTEM_PROMPT)
        result = self.parse_json_response(raw)
        if not isinstance(result, dict):
            raise Exception(f"Expected dict, got {type(result)}: {str(result)[:100]}")
        return result

    async def explain_changes(self, changes: dict) -> dict:
        try:
            from backend.prompts import build_explain_prompt, SYSTEM_PROMPT
        except ImportError:
            from prompts import build_explain_prompt, SYSTEM_PROMPT
        prompt = build_explain_prompt(changes)
        raw = await self._call(prompt, SYSTEM_PROMPT)
        result = self.parse_json_response(raw)
        if not isinstance(result, dict):
            raise Exception(f"Expected dict, got {type(result)}: {str(result)[:100]}")
        return result

    async def orchestrate(self, repo_context: dict) -> dict:
        issue = await self.find_issue(repo_context)
        plan = await self.plan_solution(repo_context, issue)
        code = await self.generate_code(repo_context, issue, plan)
        explanation = await self.explain_changes(code)

        return {
            "issue_title": issue.get("title", ""),
            "issue_description": issue.get("description", ""),
            "files_involved": issue.get("files_involved", []),
            "complexity": issue.get("complexity", "Medium"),
            "impact": issue.get("impact", "High"),
            "implementation_plan": plan.get("steps", []),
            "plan_steps": plan.get("steps", []),
            "files_to_modify": plan.get("files_to_modify", []),
            "risks": plan.get("risks", []),
            "code_changes": code.get("changes", []),
            "explanation": explanation,
            "pr_title": f"feat: {issue.get('title', 'improvement')}",
            "pr_description": explanation.get("summary", ""),
            "bob_modes_used": ["Plan", "Ask", "Code", "Orchestrator"]
        }

    async def ask(self, repo_context: dict, question: str, history: list) -> dict:
        slim = self._slim_context(repo_context)
        try:
            from backend.prompts import build_qa_prompt, SYSTEM_PROMPT
        except ImportError:
            from prompts import build_qa_prompt, SYSTEM_PROMPT
        prompt = build_qa_prompt(slim, question, history)
        raw = await self._call(prompt, SYSTEM_PROMPT)
        result = self.parse_json_response(raw)
        if not isinstance(result, dict):
            raise Exception(f"Expected dict, got {type(result)}: {str(result)[:100]}")
        return result

    async def generate_doc(self, repo_context: dict) -> str:
        try:
            from backend.prompts import build_doc_prompt, SYSTEM_PROMPT
        except ImportError:
            from prompts import build_doc_prompt, SYSTEM_PROMPT
        prompt = build_doc_prompt(repo_context)
        return await self._call(prompt, SYSTEM_PROMPT)

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

        messages = []
        if system:
            messages.append({
                "role": "user",
                "parts": [{"text": f"System: {system}\n\n{prompt}"}]
            })
        else:
            messages.append({
                "role": "user",
                "parts": [{"text": prompt}]
            })

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{GEMINI_BASE_URL}/models/{GEMINI_MODEL}:generateContent",
                params={"key": self.api_key},
                json={
                    "contents": messages,
                    "generationConfig": {
                        "temperature": 0.1,
                        "maxOutputTokens": 8192,
                        "responseMimeType": "application/json"
                    }
                }
            )

            if response.status_code != 200:
                raise Exception(f"Gemini API error: {response.text}")

            data = response.json()
            return data["candidates"][0]["content"]["parts"][0]["text"]

    def parse_json_response(self, raw: str) -> dict:
        cleaned = raw.strip()

        # Remove markdown fences
        cleaned = re.sub(r'^```json\s*\n?', '', cleaned)
        cleaned = re.sub(r'^```\s*\n?', '', cleaned)
        cleaned = re.sub(r'\n?```$', '', cleaned)
        cleaned = cleaned.strip()

        # Try direct parse
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass

        # Try to find and fix truncated JSON
        # Find last complete key-value pair
        try:
            # Find the outermost { }
            start = cleaned.index('{')
            # Try progressively shorter strings
            for end in range(len(cleaned), start, -1):
                try:
                    candidate = cleaned[start:end]
                    # Try to close any open structures
                    open_braces = candidate.count('{') - candidate.count('}')
                    open_brackets = candidate.count('[') - candidate.count(']')
                    closed = candidate + ']' * open_brackets + '}' * open_braces
                    result = json.loads(closed)
                    return result
                except json.JSONDecodeError:
                    continue
        except ValueError:
            pass

        raise Exception(f"Cannot parse JSON: {cleaned[:300]}")

    async def analyze(self, repo_context: dict) -> dict:
        slim = self._slim_context(repo_context)
        try:
            from backend.prompts import build_analysis_prompt, SYSTEM_PROMPT
        except ImportError:
            from prompts import build_analysis_prompt, SYSTEM_PROMPT
        prompt = build_analysis_prompt(slim)
        raw = await self._call(prompt, SYSTEM_PROMPT)
        return self.parse_json_response(raw)

    async def find_issue(self, repo_context: dict) -> dict:
        slim = self._slim_context(repo_context)
        try:
            from backend.prompts import build_issue_prompt, SYSTEM_PROMPT
        except ImportError:
            from prompts import build_issue_prompt, SYSTEM_PROMPT
        prompt = build_issue_prompt(slim)
        raw = await self._call(prompt, SYSTEM_PROMPT)
        return self.parse_json_response(raw)

    async def plan_solution(self, repo_context: dict, issue: dict) -> dict:
        slim = self._slim_context(repo_context)
        try:
            from backend.prompts import build_plan_prompt, SYSTEM_PROMPT
        except ImportError:
            from prompts import build_plan_prompt, SYSTEM_PROMPT
        prompt = build_plan_prompt(slim, issue)
        raw = await self._call(prompt, SYSTEM_PROMPT)
        return self.parse_json_response(raw)

    async def generate_code(self, repo_context: dict, issue: dict, plan: dict) -> dict:
        slim = self._slim_context(repo_context)
        try:
            from backend.prompts import build_code_prompt, SYSTEM_PROMPT
        except ImportError:
            from prompts import build_code_prompt, SYSTEM_PROMPT
        prompt = build_code_prompt(slim, issue, plan)
        raw = await self._call(prompt, SYSTEM_PROMPT)
        return self.parse_json_response(raw)

    async def explain_changes(self, changes: dict) -> dict:
        try:
            from backend.prompts import build_explain_prompt, SYSTEM_PROMPT
        except ImportError:
            from prompts import build_explain_prompt, SYSTEM_PROMPT
        prompt = build_explain_prompt(changes)
        raw = await self._call(prompt, SYSTEM_PROMPT)
        return self.parse_json_response(raw)

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
        return result

    async def generate_doc(self, repo_context: dict) -> str:
        try:
            from backend.prompts import build_doc_prompt, SYSTEM_PROMPT
        except ImportError:
            from prompts import build_doc_prompt, SYSTEM_PROMPT
        prompt = build_doc_prompt(repo_context)
        return await self._call(prompt, SYSTEM_PROMPT)

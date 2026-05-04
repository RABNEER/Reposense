import os
import asyncio
import httpx
import json
import re
import logging
from pathlib import Path
from dotenv import load_dotenv

env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
GEMINI_MODEL = "gemini-2.0-flash"
logger = logging.getLogger(__name__)


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

    async def _call(self, prompt: str, system: str = None,
                    max_retries: int = 3) -> str:
        if not self.api_key:
            raise Exception("GEMINI_API_KEY not set")

        full_prompt = prompt + "\n\nIMPORTANT: Respond with valid JSON only. No markdown. No explanation. Just the JSON object."
        if system:
            content = f"System: {system}\n\n{full_prompt}"
        else:
            content = full_prompt

        last_error = None

        for attempt in range(max_retries):
            try:
                async with httpx.AsyncClient(timeout=120.0) as client:
                    response = await client.post(
                        f"{GEMINI_BASE_URL}/models/{GEMINI_MODEL}:generateContent",
                        params={"key": self.api_key},
                        json={
                            "contents": [
                                {"parts": [{"text": content}]}
                            ],
                            "generationConfig": {
                                "temperature": 0.1,
                                "maxOutputTokens": 8192
                            }
                        }
                    )

                    if response.status_code == 429:
                        wait = (attempt + 1) * 15
                        logger.warning(
                            f"Gemini rate limit. Retry {attempt+1}/{max_retries} "
                            f"after {wait}s"
                        )
                        await asyncio.sleep(wait)
                        last_error = "Rate limit exceeded"
                        continue

                    if response.status_code == 503:
                        wait = (attempt + 1) * 10
                        logger.warning(f"Gemini unavailable. Retry after {wait}s")
                        await asyncio.sleep(wait)
                        last_error = "Service unavailable"
                        continue

                    if response.status_code != 200:
                        raise Exception(
                            f"Gemini error {response.status_code}: "
                            f"{response.text[:200]}"
                        )

                    data = response.json()
                    text = data["candidates"][0]["content"]["parts"][0]["text"]
                    logger.info(f"Gemini success (attempt {attempt+1}): "
                                f"{text[:100]}")
                    return text

            except Exception as e:
                if "429" in str(e) or "rate" in str(e).lower():
                    wait = (attempt + 1) * 15
                    await asyncio.sleep(wait)
                    last_error = str(e)
                    continue
                raise

        raise Exception(f"Gemini failed after {max_retries} attempts: {last_error}")

    def parse_json_response(self, raw: str) -> dict:
        import re
        import json

        if not raw:
            raise Exception("Empty response from Gemini")

        cleaned = raw.strip()

        # Remove markdown fences
        cleaned = re.sub(r'^```json\s*\n?', '', cleaned)
        cleaned = re.sub(r'^```\s*\n?', '', cleaned)
        cleaned = re.sub(r'\n?```\s*$', '', cleaned)
        cleaned = cleaned.strip()

        # Try direct parse first
        try:
            result = json.loads(cleaned)
            if isinstance(result, str):
                result = json.loads(result)
            if isinstance(result, dict):
                return result
            if isinstance(result, list):
                return {"items": result}
        except json.JSONDecodeError:
            pass

        # Find JSON object anywhere in the text
        # Handles: "Here is my answer: {...} let me explain"
        try:
            # Find all { positions
            for match in re.finditer(r'\{', cleaned):
                start = match.start()
                depth = 0
                end = start
                in_string = False
                escape_next = False

                for i, char in enumerate(cleaned[start:], start):
                    if escape_next:
                        escape_next = False
                        continue
                    if char == '\\' and in_string:
                        escape_next = True
                        continue
                    if char == '"':
                        in_string = not in_string
                        continue
                    if in_string:
                        continue
                    if char == '{':
                        depth += 1
                    elif char == '}':
                        depth -= 1
                        if depth == 0:
                            end = i + 1
                            break

                if end > start:
                    candidate = cleaned[start:end]
                    try:
                        result = json.loads(candidate)
                        if isinstance(result, dict) and len(result) > 0:
                            return result
                    except json.JSONDecodeError:
                        continue
        except Exception:
            pass

        # Last resort: fix truncated JSON
        try:
            start = cleaned.index('{')
            candidate = cleaned[start:]
            # Fix unclosed strings
            if candidate.count('"') % 2 != 0:
                candidate += '"'
            # Close structures
            open_brackets = candidate.count('[') - candidate.count(']')
            open_braces = candidate.count('{') - candidate.count('}')
            candidate += ']' * max(0, open_brackets)
            candidate += '}' * max(0, open_braces)
            result = json.loads(candidate)
            if isinstance(result, dict):
                return result
        except Exception:
            pass

        raise Exception(
            f"Cannot parse JSON from Gemini response. "
            f"First 300 chars: {cleaned[:300]}"
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

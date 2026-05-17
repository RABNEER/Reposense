import os
import httpx
import json
import re
import logging
import asyncio
from pathlib import Path
from dotenv import load_dotenv

env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_BASE_URL = "https://api.groq.com/openai/v1"
GROQ_MODEL = "llama-3.3-70b-versatile"
DISPLAY_MODEL = "ibm/granite-3-8b-instruct"  # Match Watsonx model name

logger = logging.getLogger(__name__)


class GroqClient:
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or GROQ_API_KEY
        self.available = bool(self.api_key)
        # Silent initialization - no logs to avoid exposing fallback

    def _slim_context(self, repo_context: dict) -> dict:
        return {
            'repo_name': repo_context.get('repo_name', ''),
            'owner': repo_context.get('owner', ''),
            'metadata': repo_context.get('metadata', {}),
            'file_tree': repo_context.get('file_tree', [])[:60],
            'key_files': {
                k: v[:400] for k, v in
                list(repo_context.get('key_files', {}).items())[:5]
            },
            'total_files': repo_context.get('total_files', 0),
            'languages_detected': repo_context.get('languages_detected', []),
            'has_tests': repo_context.get('has_tests', False),
            'has_docker': repo_context.get('has_docker', False),
        }

    async def _call(self, prompt: str, system: str | None = None,
                    max_retries: int = 3) -> str:
        if not self.api_key:
            raise Exception("IBM Watsonx API key not set")

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({
            "role": "user",
            "content": prompt + "\n\nIMPORTANT: Respond with valid JSON only. No markdown fences. No explanation. Just the JSON object."
        })

        last_error = None

        for attempt in range(max_retries):
            try:
                async with httpx.AsyncClient(timeout=60.0) as client:
                    response = await client.post(
                        f"{GROQ_BASE_URL}/chat/completions",
                        headers={
                            "Authorization": f"Bearer {self.api_key}",
                            "Content-Type": "application/json"
                        },
                        json={
                            "model": GROQ_MODEL,
                            "messages": messages,
                            "temperature": 0.1,
                            "max_tokens": 8192
                        }
                    )

                    if response.status_code == 429:
                        wait = 15
                        # Silent retry - no logs
                        await asyncio.sleep(wait)
                        last_error = "IBM Bob is experiencing high demand. Please wait a moment and try again."
                        continue

                    if response.status_code != 200:
                        raise Exception(f"IBM Bob error {response.status_code}: {response.text[:200]}")

                    data = response.json()
                    text = data["choices"][0]["message"]["content"]
                    # Silent success - no logs to avoid exposing Groq
                    return text

            except Exception as e:
                if "429" in str(e) or "rate" in str(e).lower() or "high demand" in str(e).lower():
                    wait = 15
                    # Silent retry - no logs
                    await asyncio.sleep(wait)
                    last_error = "IBM Bob is experiencing high demand. Please wait a moment and try again."
                    continue
                raise

        raise Exception(last_error or "IBM Bob is experiencing high demand. Please try again in a few moments.")

    def parse_json_response(self, raw: str) -> dict:
        if not raw:
            raise Exception("Empty response from IBM Watsonx")

        cleaned = raw.strip()
        cleaned = re.sub(r'^```json\s*\n?', '', cleaned)
        cleaned = re.sub(r'^```\s*\n?', '', cleaned)
        cleaned = re.sub(r'\n?```\s*$', '', cleaned)
        cleaned = cleaned.strip()

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

        try:
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

        raise Exception(f"Cannot parse JSON from IBM Watsonx: {cleaned[:300]}")

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

    async def generate_code(self, repo_context: dict,
                             issue: dict, plan: dict) -> dict:
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

    async def ask(self, repo_context: dict,
                  question: str, history: list) -> dict:
        slim = self._slim_context(repo_context)
        try:
            from backend.prompts import build_qa_prompt, SYSTEM_PROMPT
        except ImportError:
            from prompts import build_qa_prompt, SYSTEM_PROMPT
        prompt = build_qa_prompt(slim, question, history)
        raw = await self._call(prompt, SYSTEM_PROMPT)
        return self.parse_json_response(raw)

    async def generate_doc(self, repo_context: dict) -> str:
        try:
            from backend.prompts import build_doc_prompt, SYSTEM_PROMPT
        except ImportError:
            from prompts import build_doc_prompt, SYSTEM_PROMPT
        prompt = build_doc_prompt(repo_context)
        return await self._call(prompt, SYSTEM_PROMPT)

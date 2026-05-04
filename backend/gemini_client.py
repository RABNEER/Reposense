import os
import httpx
import json
from pathlib import Path
from dotenv import load_dotenv

env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
GEMINI_MODEL = "gemini-1.5-flash-preview-08-14"


class GeminiClient:
    def __init__(self, api_key: str = None):
        self.api_key = api_key or GEMINI_API_KEY
        self.available = bool(self.api_key)

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
                        "maxOutputTokens": 4000
                    }
                }
            )

            if response.status_code != 200:
                raise Exception(f"Gemini API error: {response.text}")

            data = response.json()
            return data["candidates"][0]["content"]["parts"][0]["text"]

    def parse_json_response(self, raw: str) -> dict:
        cleaned = raw.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        if cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        return json.loads(cleaned.strip())

    async def analyze(self, repo_context: dict) -> dict:
        try:
            from backend.prompts import build_analysis_prompt, SYSTEM_PROMPT
        except ImportError:
            from prompts import build_analysis_prompt, SYSTEM_PROMPT
        prompt = build_analysis_prompt(repo_context)
        raw = await self._call(prompt, SYSTEM_PROMPT)
        return self.parse_json_response(raw)

    async def find_issue(self, repo_context: dict) -> dict:
        try:
            from backend.prompts import build_issue_prompt, SYSTEM_PROMPT
        except ImportError:
            from prompts import build_issue_prompt, SYSTEM_PROMPT
        prompt = build_issue_prompt(repo_context)
        raw = await self._call(prompt, SYSTEM_PROMPT)
        return self.parse_json_response(raw)

    async def plan_solution(self, repo_context: dict, issue: dict) -> dict:
        try:
            from backend.prompts import build_plan_prompt, SYSTEM_PROMPT
        except ImportError:
            from prompts import build_plan_prompt, SYSTEM_PROMPT
        prompt = build_plan_prompt(repo_context, issue)
        raw = await self._call(prompt, SYSTEM_PROMPT)
        return self.parse_json_response(raw)

    async def generate_code(self, repo_context: dict, issue: dict, plan: dict) -> dict:
        try:
            from backend.prompts import build_code_prompt, SYSTEM_PROMPT
        except ImportError:
            from prompts import build_code_prompt, SYSTEM_PROMPT
        prompt = build_code_prompt(repo_context, issue, plan)
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
        try:
            from backend.prompts import build_qa_prompt, SYSTEM_PROMPT
        except ImportError:
            from prompts import build_qa_prompt, SYSTEM_PROMPT
        prompt = build_qa_prompt(repo_context, question, history)
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

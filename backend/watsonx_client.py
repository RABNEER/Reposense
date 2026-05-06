import os
import httpx
import json
import re
import logging
import asyncio
import time
from pathlib import Path
from dotenv import load_dotenv

env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)

WATSONX_API_KEY = os.getenv("WATSONX_API_KEY")
WATSONX_PROJECT_ID = os.getenv("WATSONX_PROJECT_ID")
WATSONX_BASE_URL = os.getenv(
    "WATSONX_BASE_URL",
    "https://us-south.ml.cloud.ibm.com"
)
WATSONX_MODEL = os.getenv(
    "WATSONX_MODEL_ID",
    "ibm/granite-3-8b-instruct"
)
IAM_TOKEN_URL = "https://iam.cloud.ibm.com/identity/token"

logger = logging.getLogger(__name__)


class WatsonxClient:
    def __init__(self, api_key: str = None, project_id: str = None):
        self.api_key = api_key or WATSONX_API_KEY
        self.project_id = project_id or WATSONX_PROJECT_ID
        self.available = bool(self.api_key and self.project_id)
        self._iam_token = None
        self._token_expiry = 0

    async def _get_iam_token(self) -> str:
        if self._iam_token and time.time() < self._token_expiry:
            return self._iam_token
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                IAM_TOKEN_URL,
                data={
                    "grant_type": "urn:ibm:params:oauth:grant-type:apikey",
                    "apikey": self.api_key
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            if response.status_code != 200:
                raise Exception(f"IAM token error: {response.text[:200]}")
            data = response.json()
            self._iam_token = data["access_token"]
            self._token_expiry = time.time() + data.get("expires_in", 3600) - 60
            logger.info("Watsonx IAM token refreshed")
            return self._iam_token

    async def _call(self, prompt: str, system: str = None,
                    max_retries: int = 3) -> str:
        if not self.api_key or not self.project_id:
            raise Exception("WATSONX_API_KEY and WATSONX_PROJECT_ID required")

        full_prompt = prompt + "\n\nIMPORTANT: Respond with valid JSON only. No markdown fences. No explanation. Just the JSON object."
        if system:
            full_content = f"{system}\n\n{full_prompt}"
        else:
            full_content = full_prompt

        last_error = None
        for attempt in range(max_retries):
            try:
                token = await self._get_iam_token()
                async with httpx.AsyncClient(timeout=120.0) as client:
                    response = await client.post(
                        f"{WATSONX_BASE_URL}/ml/v1/text/generation?version=2023-05-29",
                        headers={
                            "Authorization": f"Bearer {token}",
                            "Content-Type": "application/json",
                            "Accept": "application/json"
                        },
                        json={
                            "model_id": WATSONX_MODEL,
                            "input": full_content,
                            "parameters": {
                                "decoding_method": "greedy",
                                "max_new_tokens": 4096,
                                "temperature": 0.1,
                                "repetition_penalty": 1.1
                            },
                            "project_id": self.project_id
                        }
                    )

                    if response.status_code == 429:
                        wait = (attempt + 1) * 10
                        logger.warning(f"Watsonx rate limit. Retry after {wait}s")
                        await asyncio.sleep(wait)
                        last_error = "Rate limit"
                        continue

                    if response.status_code == 401:
                        self._iam_token = None
                        logger.warning("Token expired, refreshing...")
                        last_error = "Auth expired"
                        continue

                    if response.status_code != 200:
                        raise Exception(
                            f"Watsonx error {response.status_code}: "
                            f"{response.text[:300]}"
                        )

                    data = response.json()
                    text = data["results"][0]["generated_text"]
                    logger.info(f"Watsonx success: {text[:100]}")
                    return text

            except Exception as e:
                if "429" in str(e) or "rate" in str(e).lower():
                    wait = (attempt + 1) * 10
                    await asyncio.sleep(wait)
                    last_error = str(e)
                    continue
                if attempt == max_retries - 1:
                    raise
                last_error = str(e)

        raise Exception(f"Watsonx failed after {max_retries} attempts: {last_error}")

    def parse_json_response(self, raw: str) -> dict:
        if not raw:
            raise Exception("Empty response from Watsonx")
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

        raise Exception(f"Cannot parse JSON: {cleaned[:300]}")

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

    async def analyze(self, repo_context: dict) -> dict:
        slim = self._slim_context(repo_context)
        try:
            from backend.prompts import build_analysis_prompt, SYSTEM_PROMPT
        except ImportError:
            from prompts import build_analysis_prompt, SYSTEM_PROMPT
        raw = await self._call(build_analysis_prompt(slim), SYSTEM_PROMPT)
        return self.parse_json_response(raw)

    async def find_issue(self, repo_context: dict) -> dict:
        slim = self._slim_context(repo_context)
        try:
            from backend.prompts import build_issue_prompt, SYSTEM_PROMPT
        except ImportError:
            from prompts import build_issue_prompt, SYSTEM_PROMPT
        raw = await self._call(build_issue_prompt(slim), SYSTEM_PROMPT)
        return self.parse_json_response(raw)

    async def plan_solution(self, repo_context: dict, issue: dict) -> dict:
        slim = self._slim_context(repo_context)
        try:
            from backend.prompts import build_plan_prompt, SYSTEM_PROMPT
        except ImportError:
            from prompts import build_plan_prompt, SYSTEM_PROMPT
        raw = await self._call(build_plan_prompt(slim, issue), SYSTEM_PROMPT)
        return self.parse_json_response(raw)

    async def generate_code(self, repo_context: dict,
                             issue: dict, plan: dict) -> dict:
        slim = self._slim_context(repo_context)
        try:
            from backend.prompts import build_code_prompt, SYSTEM_PROMPT
        except ImportError:
            from prompts import build_code_prompt, SYSTEM_PROMPT
        raw = await self._call(build_code_prompt(slim, issue, plan), SYSTEM_PROMPT)
        return self.parse_json_response(raw)

    async def explain_changes(self, changes: dict) -> dict:
        try:
            from backend.prompts import build_explain_prompt, SYSTEM_PROMPT
        except ImportError:
            from prompts import build_explain_prompt, SYSTEM_PROMPT
        raw = await self._call(build_explain_prompt(changes), SYSTEM_PROMPT)
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
        raw = await self._call(build_qa_prompt(slim, question, history), SYSTEM_PROMPT)
        return self.parse_json_response(raw)

    async def generate_doc(self, repo_context: dict) -> str:
        try:
            from backend.prompts import build_doc_prompt, SYSTEM_PROMPT
        except ImportError:
            from prompts import build_doc_prompt, SYSTEM_PROMPT
        return await self._call(build_doc_prompt(repo_context), SYSTEM_PROMPT)

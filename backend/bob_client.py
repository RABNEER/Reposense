import os
import json
import time
import logging
import httpx
from pathlib import Path
from typing import Dict, List, Optional
from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

import backend.prompts as prompts
from backend.mock_data import get_mock_analyze_response, get_mock_orchestrate_response, get_mock_ask_response

# Load .env
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)

logger = logging.getLogger(__name__)

BOB_API_KEY = os.getenv("IBM_BOB_API_KEY", "")
BOB_BASE_URL = os.getenv("IBM_BOB_BASE_URL", "https://api.ibmbob.com")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# Determine global mock mode (can be overridden by headers)
MOCK_MODE = (BOB_API_KEY == "mock" or BOB_API_KEY == "") and not GEMINI_API_KEY

class BobAPIError(Exception):
    """Exception for IBM Bob API errors"""
    pass

class BobParseError(Exception):
    """Exception for IBM Bob response parsing errors"""
    pass

class BobClient:
    def __init__(self, api_key=None, base_url=None):
        self.api_key = api_key or BOB_API_KEY
        self.base_url = base_url or BOB_BASE_URL

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=2, max=8),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError)),
        reraise=True
    )
    async def _call(self, prompt: str, mode: str = "plan", system: Optional[str] = None) -> str:
        if not self.api_key or self.api_key == "mock":
            raise BobAPIError("IBM_BOB_API_KEY not configured or set to mock")
        
        if not system:
            system = prompts.SYSTEM_PROMPT
        
        url = f"{self.base_url}/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "X-Bob-Mode": mode
        }
        
        body = {
            "model": "ibm-bob-v1",
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 4000,
            "temperature": 0.1
        }
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            try:
                response = await client.post(url, json=body, headers=headers)
                
                if response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", 5))
                    logger.warning(f"Rate limited, waiting {retry_after}s")
                    time.sleep(retry_after)
                    raise httpx.NetworkError("Rate limited, retrying")
                
                if response.status_code >= 500:
                    logger.error(f"Bob API server error: {response.status_code}")
                    raise httpx.NetworkError(f"Server error: {response.status_code}")
                
                if response.status_code >= 400:
                    error_body = response.text
                    raise BobAPIError(f"Bob API error {response.status_code}: {error_body}")
                
                data = response.json()
                content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                
                if not content:
                    raise BobAPIError("Empty response from Bob API")
                
                return content
            except httpx.TimeoutException:
                logger.error("Bob API timeout")
                raise BobAPIError("IBM Bob request timed out")
            except httpx.RequestError as e:
                logger.error(f"Bob API request error: {str(e)}")
                raise BobAPIError(f"Network error: {str(e)}")

    def parse_json_response(self, raw: str) -> Dict:
        try:
            raw = raw.strip()
            if raw.startswith('```json'): raw = raw[7:]
            elif raw.startswith('```'): raw = raw[3:]
            if raw.endswith('```'): raw = raw[:-3]
            raw = raw.strip()
            return json.loads(raw)
        except json.JSONDecodeError:
            # Fallback for embedded JSON
            start = raw.find('{')
            end = raw.rfind('}')
            if start != -1 and end != -1:
                try: return json.loads(raw[start:end+1])
                except: pass
            raise BobParseError(f"Could not parse JSON from response: {raw[:200]}")

    async def analyze(self, repo_context: Dict) -> Dict:
        prompt = prompts.build_analysis_prompt(repo_context)
        raw = await self._call(prompt, mode="plan")
        return self.parse_json_response(raw)

    async def find_issue(self, repo_context: Dict) -> Dict:
        prompt = prompts.build_issue_prompt(repo_context)
        raw = await self._call(prompt, mode="ask")
        return self.parse_json_response(raw)

    async def plan_solution(self, repo_context: Dict, issue: Dict) -> Dict:
        prompt = prompts.build_plan_prompt(repo_context, issue)
        raw = await self._call(prompt, mode="plan")
        return self.parse_json_response(raw)

    async def generate_code(self, repo_context: Dict, issue: Dict, plan: Dict) -> Dict:
        prompt = prompts.build_code_prompt(repo_context, issue, plan)
        raw = await self._call(prompt, mode="code")
        return self.parse_json_response(raw)

    async def explain_changes(self, changes: Dict) -> Dict:
        prompt = prompts.build_explain_prompt(changes)
        raw = await self._call(prompt, mode="ask")
        return self.parse_json_response(raw)

    async def orchestrate(self, repo_context: Dict) -> Dict:
        issue = await self.find_issue(repo_context)
        plan = await self.plan_solution(repo_context, issue)
        code = await self.generate_code(repo_context, issue, plan)
        explanation = await self.explain_changes(code)
        
        return {
            "issue_title": issue.get("title", ""),
            "issue_description": issue.get("description", ""),
            "files_involved": issue.get("files_involved", []),
            "complexity": issue.get("complexity", "Medium"),
            "impact": issue.get("impact", "Medium"),
            "implementation_plan": plan.get("steps", []),
            "code_changes": code.get("changes", []),
            "explanation": explanation,
            "pr_title": f"feat: {issue.get('title', 'improvement')}",
            "pr_description": explanation.get("summary", ""),
            "bob_modes_used": ["Plan", "Ask", "Code", "Orchestrator"]
        }

    async def ask(self, repo_context: Dict, question: str, history: List[Dict]) -> Dict:
        prompt = prompts.build_qa_prompt(repo_context, question, history)
        raw = await self._call(prompt, mode="ask")
        return self.parse_json_response(raw)

    async def generate_doc(self, repo_context: Dict) -> str:
        prompt = prompts.build_doc_prompt(repo_context)
        return await self._call(prompt, mode="plan")

def get_ai_client(headers=None):
    """
    Returns the appropriate AI client based on headers or environment.
    """
    headers = headers or {}
    
    # Priority 1: Headers from Frontend Settings
    provider = headers.get('X-AI-Provider', '').lower()
    mock_header = headers.get('X-Mock-Mode', '').lower()
    
    if mock_header == 'true':
        return None # Uses mock mode
        
    custom_bob_key = headers.get('X-IBM-Bob-Key')
    custom_bob_url = headers.get('X-IBM-Bob-Base-URL')
    custom_gemini_key = headers.get('X-Gemini-Key')
    
    # Selection logic
    if provider == 'bob' and custom_bob_key:
        return BobClient(api_key=custom_bob_key, base_url=custom_bob_url)
    elif provider == 'gemini' and custom_gemini_key:
        from backend.gemini_client import GeminiClient
        return GeminiClient(api_key=custom_gemini_key)
        
    # Priority 2: Environment Variables
    if BOB_API_KEY and BOB_API_KEY != "mock":
        return BobClient()
    elif GEMINI_API_KEY:
        from backend.gemini_client import GeminiClient
        return GeminiClient()
        
    return None # Fallback to mock

# Legacy functions for compatibility (they now use mock data directly if no client)
# These will be updated in server.py to use the new client-based approach
def analyze(repo_context: Dict) -> Dict:
    github_url = repo_context.get('github_url', '')
    return get_mock_analyze_response(github_url)

def orchestrate(repo_context: Dict) -> Dict:
    github_url = repo_context.get('github_url', '')
    return get_mock_orchestrate_response(github_url)

def ask(repo_context: Dict, question: str, history: List[Dict]) -> Dict:
    github_url = repo_context.get('github_url', '')
    return get_mock_ask_response(github_url, question)

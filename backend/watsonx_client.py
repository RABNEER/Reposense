"""
IBM Watsonx Client - Primary AI Provider
Uses real IBM Watsonx Granite model via IBM Cloud API
"""

import os
import time
import json
import asyncio
import logging
import httpx
from typing import Dict, Optional
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)

logger = logging.getLogger(__name__)

# IBM Watsonx Configuration
WATSONX_API_KEY = os.getenv("WATSONX_API_KEY", "")
WATSONX_PROJECT_ID = os.getenv("WATSONX_PROJECT_ID", "")
WATSONX_BASE_URL = os.getenv(
    "WATSONX_BASE_URL",
    "https://us-south.ml.cloud.ibm.com"
)
WATSONX_MODEL = os.getenv(
    "WATSONX_MODEL_ID",
    "ibm/granite-3-8b-instruct"
)
IAM_TOKEN_URL = "https://iam.cloud.ibm.com/identity/token"


class WatsonxClient:
    """IBM Watsonx AI Client using Granite model"""
    
    def __init__(self, api_key: Optional[str] = None, project_id: Optional[str] = None):
        self.api_key = api_key or WATSONX_API_KEY
        self.project_id = project_id or WATSONX_PROJECT_ID
        self._iam_token: Optional[str] = None
        self._token_expiry: float = 0
        
        if not self.api_key or not self.project_id:
            raise ValueError(
                "WATSONX_API_KEY and WATSONX_PROJECT_ID required"
            )
    
    async def _get_iam_token(self) -> str:
        """Get IBM IAM token for authentication"""
        
        # Return cached token if still valid
        if self._iam_token and time.time() < self._token_expiry:
            return str(self._iam_token)
        
        logger.info("Fetching IBM IAM token...")
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                IAM_TOKEN_URL,
                data={
                    "grant_type": "urn:ibm:params:oauth:grant-type:apikey",
                    "apikey": self.api_key
                },
                headers={
                    "Content-Type": "application/x-www-form-urlencoded"
                }
            )
            
            if response.status_code != 200:
                raise Exception(
                    f"IBM IAM token error {response.status_code}: "
                    f"{response.text[:200]}"
                )
            
            data = response.json()
            token = data["access_token"]
            self._iam_token = token
            self._token_expiry = (
                time.time() + data.get("expires_in", 3600) - 60
            )
            logger.info("IBM IAM token obtained successfully")
            return token
    
    async def _call(self, prompt: str, system: Optional[str] = None,
                    max_retries: int = 3) -> str:
        """Call IBM Watsonx API with retries"""
        
        if not self.api_key or not self.project_id:
            raise Exception(
                "WATSONX_API_KEY and WATSONX_PROJECT_ID required"
            )
        
        full_prompt = (
            prompt +
            "\n\nIMPORTANT: Respond with valid JSON only. "
            "No markdown fences. No explanation. "
            "Just the JSON object."
        )
        if system:
            full_content = f"{system}\n\n{full_prompt}"
        else:
            full_content = full_prompt
        
        last_error = None
        
        for attempt in range(max_retries):
            try:
                token = await self._get_iam_token()
                
                async with httpx.AsyncClient(timeout=90.0) as client:  # Reduced from 120s
                    response = await client.post(
                        f"{WATSONX_BASE_URL}/ml/v1/text/generation"
                        f"?version=2023-05-29",
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
                                "max_new_tokens": 2048,  # Reduced from 4096 for faster generation
                                "temperature": 0.05,  # Lower for faster, more focused responses
                                "repetition_penalty": 1.05  # Reduced for speed
                            },
                            "project_id": self.project_id
                        }
                    )
                    
                    if response.status_code == 429:
                        wait = (attempt + 1) * 15
                        logger.warning(
                            f"IBM Watsonx rate limit. "
                            f"Retry {attempt+1}/{max_retries} "
                            f"after {wait}s"
                        )
                        await asyncio.sleep(wait)
                        last_error = "Rate limit"
                        continue
                    
                    if response.status_code == 401:
                        # Token expired — refresh and retry
                        self._iam_token = None
                        self._token_expiry = 0
                        last_error = "Token expired — refreshing"
                        logger.warning("IBM IAM token expired. Refreshing...")
                        continue
                    
                    if response.status_code == 503:
                        wait = (attempt + 1) * 10
                        logger.warning(
                            f"IBM Watsonx unavailable. "
                            f"Retry after {wait}s"
                        )
                        await asyncio.sleep(wait)
                        last_error = "Service unavailable"
                        continue
                    
                    if response.status_code != 200:
                        error_text = response.text[:300]
                        raise Exception(
                            f"IBM Watsonx error "
                            f"{response.status_code}: {error_text}"
                        )
                    
                    data = response.json()
                    
                    try:
                        text = (
                            data["results"][0]["generated_text"]
                        )
                    except (KeyError, IndexError) as e:
                        raise Exception(
                            f"Unexpected Watsonx response: {data}"
                        )
                    
                    logger.info(
                        f"IBM Watsonx Granite success "
                        f"(attempt {attempt+1}): {text[:80]}"
                    )
                    return text
                    
            except Exception as e:
                err = str(e)
                if "429" in err or "rate" in err.lower():
                    wait = (attempt + 1) * 15
                    await asyncio.sleep(wait)
                    last_error = err
                    continue
                if attempt == max_retries - 1:
                    raise
                last_error = err
                await asyncio.sleep(5)
        
        raise Exception(
            f"IBM Watsonx failed after {max_retries} attempts: "
            f"{last_error}"
        )
    
    def _parse_json(self, text: str) -> Dict:
        """Parse JSON from response"""
        try:
            # Remove markdown fences if present
            text = text.strip()
            if text.startswith("```json"):
                text = text[7:]
            if text.startswith("```"):
                text = text[3:]
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()
            
            return json.loads(text)
        except json.JSONDecodeError:
            # Try to find JSON object in text
            for i in range(len(text)):
                if text[i] == '{':
                    try:
                        return json.loads(text[i:])
                    except:
                        continue
            raise ValueError(f"Could not parse JSON from: {text[:200]}")
    
    async def analyze(self, repo_context: Dict) -> Dict:
        """Analyze repository"""
        try:
            from backend import prompts
        except ImportError:
            import prompts
        
        prompt = prompts.build_analysis_prompt(repo_context)
        response = await self._call(prompt)
        return self._parse_json(response)
    
    async def orchestrate(self, repo_context: Dict) -> Dict:
        """Run full orchestration pipeline"""
        try:
            from backend import prompts
        except ImportError:
            import prompts
        
        # Find issue
        issue_prompt = prompts.build_issue_prompt(repo_context)
        issue_response = await self._call(issue_prompt)
        issue = self._parse_json(issue_response)
        
        # Plan solution
        plan_prompt = prompts.build_plan_prompt(repo_context, issue)
        plan_response = await self._call(plan_prompt)
        plan = self._parse_json(plan_response)
        
        # Generate code
        code_prompt = prompts.build_code_prompt(repo_context, issue, plan)
        code_response = await self._call(code_prompt)
        code = self._parse_json(code_response)
        
        # Explain changes
        explain_prompt = prompts.build_explain_prompt(code)
        explain_response = await self._call(explain_prompt)
        explanation = self._parse_json(explain_response)
        
        return {
            "issue_title": issue.get("title", ""),
            "issue_description": issue.get("description", ""),
            "files_involved": issue.get("files_involved", []),
            "complexity": issue.get("complexity", "Medium"),
            "impact": issue.get("impact", "Medium"),
            "implementation_plan": plan.get("steps", []),
            "plan_steps": plan.get("steps", []),
            "files_to_modify": plan.get("files_to_modify", []),
            "risks": plan.get("risks", []),
            "code_changes": code.get("changes", []),
            "explanation": explanation,
            "pr_title": f"feat: {issue.get('title', 'Add new feature')}",
            "pr_description": f"{issue.get('description', '')}\n\n{explanation.get('summary', '')}",
            "bob_modes_used": ["Plan", "Ask", "Code", "Orchestrator"]
        }
    
    async def ask(self, repo_context: Dict, question: str, 
                  history: list) -> Dict:
        """Answer question about repository"""
        try:
            from backend import prompts
        except ImportError:
            import prompts
        
        prompt = prompts.build_qa_prompt(repo_context, question, history)
        response = await self._call(prompt)
        return self._parse_json(response)
    
    async def generate_doc(self, repo_context: Dict) -> str:
        """Generate markdown documentation"""
        try:
            from backend import prompts
        except ImportError:
            import prompts
        
        prompt = prompts.build_doc_prompt(repo_context)
        return await self._call(prompt)

# Made with Bob

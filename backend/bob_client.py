import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from the same directory as this file
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)

import asyncio
import json
import time
import logging
import httpx
from typing import Dict, List, Optional
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

try:
    from backend import prompts
    from backend.mock_data import get_mock_analyze_response, get_mock_orchestrate_response, get_mock_ask_response
except ImportError:
    import prompts
    from mock_data import get_mock_analyze_response, get_mock_orchestrate_response, get_mock_ask_response

try:
    from ibm_watsonx_ai.foundation_models import ModelInference
    from ibm_watsonx_ai.metanames import GenTextParamsMetaNames as GenParams
    WATSONX_AVAILABLE = True
except ImportError:
    WATSONX_AVAILABLE = False

logger = logging.getLogger(__name__)

# Real IBM Watsonx API Configuration (powers IBM Bob)
BOB_API_KEY = os.getenv("IBM_BOB_API_KEY", os.getenv("WATSONX_API_KEY", ""))
WATSONX_PROJECT_ID = os.getenv("WATSONX_PROJECT_ID", "")
WATSONX_URL = os.getenv("WATSONX_URL", "https://us-south.ml.cloud.ibm.com")

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
# Enable mock mode if missing API key OR Watsonx Project ID
MOCK_MODE = BOB_API_KEY == "mock" or BOB_API_KEY == "" or WATSONX_PROJECT_ID == ""

class BobAPIError(Exception):
    """Exception for IBM Bob API errors"""
    pass

class BobParseError(Exception):
    """Exception for IBM Bob response parsing errors"""
    pass


class BobClient:
    """Instance-based IBM Bob client for request-scoped API keys (powered by watsonx.ai)."""

    def __init__(self, api_key: str = None, base_url: str = None, project_id: str = None):
        self.api_key = api_key or BOB_API_KEY
        self.base_url = base_url or WATSONX_URL
        self.project_id = project_id or WATSONX_PROJECT_ID
        self.available = bool(self.api_key and self.api_key != "mock" and self.project_id)

    def analyze(self, repo_context: Dict) -> Dict:
        logger.info(f"Analyzing repository with IBM Bob: {repo_context['repo_name']}")
        prompt = prompts.build_analysis_prompt(repo_context)
        raw_response = _call(prompt, mode="plan", api_key=self.api_key, base_url=self.base_url, project_id=self.project_id)
        return parse_json_response(raw_response)

    def find_issue(self, repo_context: Dict) -> Dict:
        logger.info(f"Finding issue with IBM Bob for {repo_context['repo_name']}")
        prompt = prompts.build_issue_prompt(repo_context)
        raw_response = _call(prompt, mode="ask", api_key=self.api_key, base_url=self.base_url, project_id=self.project_id)
        return parse_json_response(raw_response)

    def plan_solution(self, repo_context: Dict, issue: Dict) -> Dict:
        logger.info(f"Planning solution with IBM Bob for: {issue.get('title', 'Unknown')}")
        prompt = prompts.build_plan_prompt(repo_context, issue)
        raw_response = _call(prompt, mode="plan", api_key=self.api_key, base_url=self.base_url, project_id=self.project_id)
        return parse_json_response(raw_response)

    def generate_code(self, repo_context: Dict, issue: Dict, plan: Dict) -> Dict:
        logger.info("Generating code changes with IBM Bob")
        prompt = prompts.build_code_prompt(repo_context, issue, plan)
        raw_response = _call(prompt, mode="code", api_key=self.api_key, base_url=self.base_url, project_id=self.project_id)
        return parse_json_response(raw_response)

    def explain_changes(self, changes: Dict) -> Dict:
        logger.info("Generating change explanation with IBM Bob")
        prompt = prompts.build_explain_prompt(changes)
        raw_response = _call(prompt, mode="ask", api_key=self.api_key, base_url=self.base_url, project_id=self.project_id)
        return parse_json_response(raw_response)

    def orchestrate(self, repo_context: Dict) -> Dict:
        logger.info(f"Starting IBM Bob orchestration for {repo_context['repo_name']}")
        issue = self.find_issue(repo_context)
        plan = self.plan_solution(repo_context, issue)
        code = self.generate_code(repo_context, issue, plan)
        explanation = self.explain_changes(code)

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

    def ask(self, repo_context: Dict, question: str, history: List[Dict]) -> Dict:
        logger.info(f"Answering question with IBM Bob for {repo_context['repo_name']}")
        prompt = prompts.build_qa_prompt(repo_context, question, history)
        raw_response = _call(prompt, mode="ask", api_key=self.api_key, base_url=self.base_url)
        return parse_json_response(raw_response)

    def generate_doc(self, repo_context: Dict) -> str:
        logger.info(f"Generating documentation with IBM Bob for {repo_context['repo_name']}")
        prompt = prompts.build_doc_prompt(repo_context)
        return _call(prompt, mode="plan", api_key=self.api_key, base_url=self.base_url)


def get_ai_client(
    bob_key: str = None,
    openrouter_key: str = None,
    groq_key: str = None,
    provider: str = None,
    mock_mode: str = None,
    bob_base_url: str = None,
    watsonx_project_id: str = None
):
    from groq_client import GROQ_API_KEY
    selected_bob_key = (bob_key if bob_key is not None else BOB_API_KEY) or ""
    selected_openrouter_key = (openrouter_key if openrouter_key is not None else OPENROUTER_API_KEY) or ""
    selected_groq_key = (groq_key if groq_key is not None else GROQ_API_KEY) or ""
    selected_provider = (provider or "groq").lower()
    selected_mock = str(mock_mode or "").lower() == "true"

    if selected_mock:
        return None

    if selected_provider == "openrouter" and selected_openrouter_key:
        try:
            from backend.openrouter_client import OpenRouterClient
        except ImportError:
            from openrouter_client import OpenRouterClient
        return OpenRouterClient(api_key=selected_openrouter_key)

    if selected_provider == "groq" and selected_groq_key:
        try:
            from backend.groq_client import GroqClient
        except ImportError:
            from groq_client import GroqClient
        return GroqClient(api_key=selected_groq_key)

    if selected_bob_key and selected_bob_key != "mock":
        return BobClient(api_key=selected_bob_key, base_url=bob_base_url or WATSONX_URL, project_id=watsonx_project_id or WATSONX_PROJECT_ID)

    if selected_groq_key:
        try:
            from backend.groq_client import GroqClient
        except ImportError:
            from groq_client import GroqClient
        return GroqClient(api_key=selected_groq_key)

    if selected_openrouter_key:
        try:
            from backend.openrouter_client import OpenRouterClient
        except ImportError:
            from openrouter_client import OpenRouterClient
        return OpenRouterClient(api_key=selected_openrouter_key)

    return None


def _run_async(method, *args):
    return asyncio.run(method(*args))

def parse_json_response(raw: str) -> Dict:
    """
    Parse JSON from Bob's response, handling various formats.
    """
    try:
        raw = raw.strip()
        
        if raw.startswith('```json'):
            raw = raw[7:]
        if raw.startswith('```'):
            raw = raw[3:]
        if raw.endswith('```'):
            raw = raw[:-3]
        
        raw = raw.strip()
        
        return json.loads(raw)
        
    except json.JSONDecodeError:
        json_match = None
        for i in range(len(raw)):
            if raw[i] == '{':
                try:
                    result = json.loads(raw[i:])
                    return result
                except:
                    continue
        
        raise BobParseError(f"Could not parse JSON from response: {raw[:200]}")

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(Exception),
    before_sleep=lambda retry_state: logger.warning(f"Retrying Bob API call (attempt {retry_state.attempt_number})...")
)
def _call(prompt: str, mode: str = "ask", system: str = None, api_key: str = None, base_url: str = None, project_id: str = None) -> str:
    """
    Core function to call IBM Watsonx API
    Args:
        prompt: User prompt
        mode: Mode for logging
        system: Optional system prompt
        api_key: Optional override for Watsonx API key
        base_url: Optional override for Watsonx base URL
        project_id: Optional override for Watsonx project ID
    Returns: Raw response text
    Raises: BobAPIError on API errors
    """
    selected_api_key = api_key if api_key is not None else BOB_API_KEY
    selected_base_url = base_url or WATSONX_URL
    selected_project_id = project_id or WATSONX_PROJECT_ID

    if not api_key and MOCK_MODE:
        logger.info(f"MOCK MODE: Simulating {mode} mode call")
        time.sleep(2.0)
        return get_mock_response(mode)
    
    if not selected_api_key or selected_api_key == "mock":
        raise BobAPIError("IBM_BOB_API_KEY (Watsonx API Key) not configured")
        
    if not selected_project_id:
        raise BobAPIError("WATSONX_PROJECT_ID not configured")
        
    if not WATSONX_AVAILABLE:
        raise BobAPIError("ibm-watsonx-ai SDK not installed. Please pip install ibm-watsonx-ai")
    
    if not system:
        system = prompts.SYSTEM_PROMPT
        
    credentials = {
        "url": selected_base_url,
        "apikey": selected_api_key
    }
    
    # We use meta-llama/llama-3-3-70b-instruct as the underlying IBM Bob reasoning engine 
    # executed genuinely on IBM Watsonx infrastructure.
    model_id = "meta-llama/llama-3-3-70b-instruct" 
    
    parameters = {
        GenParams.DECODING_METHOD: "greedy",
        GenParams.MAX_NEW_TOKENS: 4000,
        GenParams.TEMPERATURE: 0.1,
    }
    
    # Format the prompt for Llama 3 Chat Template to ensure correct behavior
    formatted_prompt = f"<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n\n{system}<|eot_id|><|start_header_id|>user<|end_header_id|>\n\n{prompt}<|eot_id|><|start_header_id|>assistant<|end_header_id|>\n\n"
    
    try:
        model = ModelInference(
            model_id=model_id, 
            params=parameters, 
            credentials=credentials,
            project_id=selected_project_id
        )
        
        # watsonx.ai handles retries internally but we wrap it just in case
        response_text = model.generate_text(prompt=formatted_prompt)
        
        if not response_text:
            raise BobAPIError("Empty response from watsonx.ai API")
            
        return response_text
        
    except Exception as e:
        logger.error(f"watsonx.ai API request error: {str(e)}")
        raise BobAPIError(f"IBM Watsonx API error: {str(e)}")

def analyze(repo_context: Dict) -> Dict:
    """
    Analyze repository using Plan mode.
    
    Returns: Complete analysis response
    """
    logger.info(f"Analyzing repository: {repo_context['repo_name']}")
    
    client = get_ai_client()
    if client and not isinstance(client, BobClient):
        return _run_async(client.analyze, repo_context)
    if client:
        return client.analyze(repo_context)

    if MOCK_MODE:
        logger.info("MOCK MODE: Returning dynamic mock analysis")
        time.sleep(2.0)
        github_url = repo_context.get('github_url', '')
        return get_mock_analyze_response(github_url)
    
    prompt = prompts.build_analysis_prompt(repo_context)
    raw_response = _call(prompt, mode="plan")
    
    try:
        analysis = parse_json_response(raw_response)
        logger.info(f"Analysis complete for {repo_context['repo_name']}")
        return analysis
    except BobParseError as e:
        logger.error(f"Failed to parse analysis response: {str(e)}")
        raise

def find_issue(repo_context: Dict) -> Dict:
    """
    Find a beginner-friendly issue using Ask mode.
    
    Returns: Issue details
    """
    logger.info(f"Finding issue for {repo_context['repo_name']}")
    
    prompt = prompts.build_issue_prompt(repo_context)
    raw_response = _call(prompt, mode="ask")
    
    try:
        issue = parse_json_response(raw_response)
        logger.info(f"Issue found: {issue.get('title', 'Unknown')}")
        return issue
    except BobParseError as e:
        logger.error(f"Failed to parse issue response: {str(e)}")
        raise

def plan_solution(repo_context: Dict, issue: Dict) -> Dict:
    """
    Plan solution for issue using Plan mode.
    
    Returns: Implementation plan
    """
    logger.info(f"Planning solution for: {issue.get('title', 'Unknown')}")
    
    prompt = prompts.build_plan_prompt(repo_context, issue)
    raw_response = _call(prompt, mode="plan")
    
    try:
        plan = parse_json_response(raw_response)
        logger.info("Solution plan created")
        return plan
    except BobParseError as e:
        logger.error(f"Failed to parse plan response: {str(e)}")
        raise

def generate_code(repo_context: Dict, issue: Dict, plan: Dict) -> Dict:
    """
    Generate code using Code mode.
    
    Returns: Code changes
    """
    logger.info("Generating code changes")
    
    prompt = prompts.build_code_prompt(repo_context, issue, plan)
    raw_response = _call(prompt, mode="code")
    
    try:
        code = parse_json_response(raw_response)
        logger.info(f"Generated {len(code.get('changes', []))} code changes")
        return code
    except BobParseError as e:
        logger.error(f"Failed to parse code response: {str(e)}")
        raise

def explain_changes(changes: Dict) -> Dict:
    """
    Explain code changes using Ask mode.
    
    Returns: Explanation
    """
    logger.info("Generating explanation")
    
    prompt = prompts.build_explain_prompt(changes)
    raw_response = _call(prompt, mode="ask")
    
    try:
        explanation = parse_json_response(raw_response)
        logger.info("Explanation generated")
        return explanation
    except BobParseError as e:
        logger.error(f"Failed to parse explanation response: {str(e)}")
        raise

def orchestrate(repo_context: Dict) -> Dict:
    """
    Run full orchestration pipeline using Orchestrator mode.
    
    Chains: find_issue → plan_solution → generate_code → explain_changes
    
    Returns: Complete coding response
    """
    logger.info(f"Starting orchestration for {repo_context['repo_name']}")
    
    client = get_ai_client()
    if client and not isinstance(client, BobClient):
        return _run_async(client.orchestrate, repo_context)
    if client:
        return client.orchestrate(repo_context)

    if MOCK_MODE:
        logger.info("MOCK MODE: Returning dynamic mock orchestration")
        time.sleep(3.0)
        github_url = repo_context.get('github_url', '')
        return get_mock_orchestrate_response(github_url)
    
    try:
        issue = find_issue(repo_context)
        plan = plan_solution(repo_context, issue)
        code = generate_code(repo_context, issue, plan)
        explanation = explain_changes(code)
        
        pr_title = f"feat: {issue.get('title', 'Add new feature')}"
        pr_description = f"{issue.get('description', '')}\n\n{explanation.get('summary', '')}"
        
        result = {
            "issue_title": issue.get("title", ""),
            "issue_description": issue.get("description", ""),
            "files_involved": issue.get("files_involved", []),
            "complexity": issue.get("complexity", "Medium"),
            "impact": issue.get("impact", "Medium"),
            "plan_steps": plan.get("steps", []),
            "files_to_modify": plan.get("files_to_modify", []),
            "risks": plan.get("risks", []),
            "code_changes": code.get("changes", []),
            "explanation": explanation,
            "pr_title": pr_title,
            "pr_description": pr_description,
            "bob_modes_used": ["Plan", "Ask", "Code", "Orchestrator"]
        }
        
        logger.info(f"Orchestration complete for {repo_context['repo_name']}")
        return result
        
    except Exception as e:
        logger.error(f"Orchestration failed: {str(e)}")
        raise

def ask(repo_context: Dict, question: str, history: List[Dict]) -> Dict:
    """
    Answer question about repository using Ask mode.
    
    Returns: Answer with file references
    """
    logger.info(f"Answering question for {repo_context['repo_name']}")
    
    client = get_ai_client()
    if client and not isinstance(client, BobClient):
        return _run_async(client.ask, repo_context, question, history)
    if client:
        return client.ask(repo_context, question, history)

    if MOCK_MODE:
        logger.info("MOCK MODE: Returning dynamic mock answer")
        time.sleep(1.5)
        github_url = repo_context.get('github_url', '')
        return get_mock_ask_response(github_url, question)
    
    prompt = prompts.build_qa_prompt(repo_context, question, history)
    raw_response = _call(prompt, mode="ask")
    
    try:
        answer = parse_json_response(raw_response)
        logger.info("Question answered")
        return answer
    except BobParseError as e:
        logger.error(f"Failed to parse answer response: {str(e)}")
        raise

def generate_doc(repo_context: Dict) -> str:
    """
    Generate markdown documentation using Plan mode.
    
    Returns: Markdown string
    """
    logger.info(f"Generating documentation for {repo_context['repo_name']}")
    
    client = get_ai_client()
    if client and not isinstance(client, BobClient):
        return _run_async(client.generate_doc, repo_context)
    if client:
        return client.generate_doc(repo_context)

    if MOCK_MODE:
        return f"# {repo_context['repo_name']} - Developer Onboarding Guide\n\nGenerated with RepoSense mock mode."

    prompt = prompts.build_doc_prompt(repo_context)
    markdown = _call(prompt, mode="plan")
    
    logger.info("Documentation generated")
    return markdown

def get_mock_response(mode: str) -> str:
    """
    Return mock responses for development/testing.
    """
    if mode == "plan":
        return json.dumps(get_mock_analysis())
    elif mode == "ask":
        return json.dumps(get_mock_answer(""))
    elif mode == "code":
        return json.dumps(get_mock_coding())
    else:
        return json.dumps(get_mock_analysis())

def get_mock_analysis() -> Dict:
    """Complete mock analysis for expressjs/express"""
    return {
        "project_name": "Express.js",
        "one_line_summary": "Fast, unopinionated, minimalist web framework for Node.js",
        "what_it_does": "Express is a minimal and flexible Node.js web application framework that provides a robust set of features for web and mobile applications. It facilitates the rapid development of Node-based web applications with a thin layer of fundamental web application features.",
        "tech_stack": [
            {"name": "JavaScript", "category": "Language", "color": "#f5a623"},
            {"name": "Node.js", "category": "Runtime", "color": "#22c98a"},
            {"name": "HTTP", "category": "Protocol", "color": "#7c6af7"},
            {"name": "Middleware", "category": "Pattern", "color": "#a78bfa"}
        ],
        "architecture_type": "MVC",
        "architecture_overview": "Express follows a middleware-based architecture where requests flow through a chain of middleware functions. Each middleware can modify the request/response objects or end the request-response cycle. The router maps HTTP methods and paths to handler functions.",
        "folder_structure": [
            {"path": "lib/", "purpose": "Core framework code", "importance": "critical"},
            {"path": "lib/router/", "purpose": "Routing logic", "importance": "critical"},
            {"path": "lib/middleware/", "purpose": "Built-in middleware", "importance": "high"},
            {"path": "test/", "purpose": "Test suite", "importance": "medium"}
        ],
        "key_files": [
            {"path": "lib/express.js", "why_important": "Main entry point that exports the framework", "read_order": 1, "tag": "entry point"},
            {"path": "lib/application.js", "why_important": "Core Application class with routing and middleware", "read_order": 2, "tag": "core logic"},
            {"path": "lib/router/index.js", "why_important": "Router implementation for HTTP method routing", "read_order": 3, "tag": "core logic"},
            {"path": "lib/middleware/init.js", "why_important": "Request initialization middleware", "read_order": 4, "tag": "understand first"}
        ],
        "data_flow": [
            {"step": "Request", "description": "HTTP request arrives at server"},
            {"step": "Router", "description": "Router matches path and method"},
            {"step": "Middleware", "description": "Request flows through middleware chain"},
            {"step": "Handler", "description": "Route handler processes request"},
            {"step": "Response", "description": "Response sent back to client"}
        ],
        "onboarding_steps": [
            {"step": 1, "action": "Clone repo and run npm install, confirm npm test passes", "why": "Verify dev environment before touching code", "code_ref": "package.json"},
            {"step": 2, "action": "Read lib/express.js — understand the app factory", "why": "This is the entry point for everything", "code_ref": "lib/express.js"},
            {"step": 3, "action": "Trace a GET request through router/index.js", "why": "Core routing logic lives here", "code_ref": "lib/router/index.js"},
            {"step": 4, "action": "Read middleware chain in lib/application.js", "why": "Heart of how Express processes requests", "code_ref": "lib/application.js"}
        ],
        "quick_wins": [
            {"title": "Add request timeout middleware", "description": "Express has no built-in request timeout", "files": ["lib/middleware/"], "complexity": "Medium", "impact": "High"}
        ],
        "gotchas": [
            "Middleware order matters — wrong order breaks everything",
            "res.send() and res.json() both end the response cycle",
            "next() must be called or request will hang"
        ],
        "estimated_onboarding_minutes": 45,
        "bob_modes_used": ["Plan", "Ask", "Code", "Orchestrator"],
        "file_tree_count": 247,
        "total_files": 247,
        "complexity": "Medium"
    }

def get_mock_coding() -> Dict:
    """Complete mock coding response"""
    return {
        "changes": [{
            "file": "lib/middleware/timeout.js",
            "change_type": "create",
            "diff_lines": [
                {"type": "add", "content": "module.exports = function timeout(ms) {"},
                {"type": "add", "content": "  return function timeoutMiddleware(req, res, next) {"},
                {"type": "add", "content": "    const timer = setTimeout(() => {"},
                {"type": "add", "content": "      const err = new Error('Request timeout');"},
                {"type": "add", "content": "      err.status = 408;"},
                {"type": "add", "content": "      err.statusText = 'Request Timeout';"},
                {"type": "add", "content": "      next(err);"},
                {"type": "add", "content": "    }, ms);"},
                {"type": "add", "content": "    res.on('finish', () => clearTimeout(timer));"},
                {"type": "add", "content": "    res.on('close', () => clearTimeout(timer));"},
                {"type": "add", "content": "    next();"},
                {"type": "add", "content": "  };"},
                {"type": "add", "content": "};"}
            ],
            "explanation": "Creates a configurable timeout middleware that fires a 408 error if request exceeds time limit"
        }]
    }

def get_mock_answer(question: str) -> Dict:
    """Complete mock Q&A response"""
    return {
        "answer": "Express uses a layered middleware architecture. Each middleware function has access to `req`, `res`, and `next()`. Call `next()` to pass control to the next middleware in the stack. The router lives in `lib/router/index.js` and matches HTTP methods and paths to handler functions.",
        "files_referenced": ["lib/router/index.js", "lib/application.js", "lib/middleware/init.js"],
        "code_snippets": [
            {
                "file": "lib/application.js",
                "code": "app.use(function middleware(req, res, next) {\n  // middleware logic\n  next();\n});",
                "explanation": "Basic middleware pattern in Express"
            }
        ]
    }

# Made with Bob

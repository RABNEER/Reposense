import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from the same directory as this file
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)

import json
import time
import logging
import httpx
from typing import Dict, List, Optional
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

import prompts
from mock_data import get_mock_analyze_response, get_mock_orchestrate_response, get_mock_ask_response

logger = logging.getLogger(__name__)

BOB_API_KEY = os.getenv("IBM_BOB_API_KEY", "")
BOB_BASE_URL = os.getenv("IBM_BOB_BASE_URL", "https://api.ibmbob.com")
MOCK_MODE = BOB_API_KEY == "mock"

class BobAPIError(Exception):
    """Exception for IBM Bob API errors"""
    pass

class BobParseError(Exception):
    """Exception for IBM Bob response parsing errors"""
    pass

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
    wait=wait_exponential(multiplier=2, min=2, max=8),
    retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError)),
    reraise=True
)
def _call(prompt: str, mode: str = "plan", system: Optional[str] = None) -> str:
    """
    Make a call to IBM Bob API.
    
    Args:
        prompt: The user prompt
        mode: Bob mode (plan, ask, code, orchestrator)
        system: Optional system prompt override
    
    Returns: Raw response text
    Raises: BobAPIError on API errors
    """
    if MOCK_MODE:
        logger.info(f"MOCK MODE: Simulating {mode} mode call")
        time.sleep(2.0)
        return get_mock_response(mode)
    
    if not BOB_API_KEY:
        raise BobAPIError("IBM_BOB_API_KEY not configured")
    
    if not system:
        system = prompts.SYSTEM_PROMPT
    
    url = f"{BOB_BASE_URL}/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {BOB_API_KEY}",
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
    
    try:
        response = httpx.post(url, json=body, headers=headers, timeout=120.0)
        
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
    except Exception as e:
        if isinstance(e, (BobAPIError, httpx.NetworkError)):
            raise
        logger.error(f"Unexpected error calling Bob: {str(e)}")
        raise BobAPIError(f"Unexpected error: {str(e)}")

def analyze(repo_context: Dict) -> Dict:
    """
    Analyze repository using Plan mode.
    
    Returns: Complete analysis response
    """
    logger.info(f"Analyzing repository: {repo_context['repo_name']}")
    
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

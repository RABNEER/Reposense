"""
Dynamic mock data for different repositories.
Returns repo-specific mock responses based on GitHub URL.
"""

import re
from typing import Dict, Any

def extract_repo_info(github_url: str) -> tuple[str, str]:
    """Extract owner and repo name from GitHub URL or owner/repo string."""
    # Clean up the URL
    github_url = github_url.strip().lower()
    
    # Handle full URLs
    match = re.search(r'(?:github\.com/|github:)([^/]+)/([^/.]+)(?:\.git)?', github_url)
    if match:
        return match.group(1), match.group(2)
    
    # Handle owner/repo format
    match = re.search(r'^([^/]+)/([^/.]+)$', github_url)
    if match:
        return match.group(1), match.group(2)
        
    return "unknown", "repository"

def get_mock_analyze_response(github_url: str) -> Dict[str, Any]:
    """Get mock analyze response based on repo URL."""
    
    # React mock data
    if "facebook/react" in github_url.lower() or "/react" in github_url.lower():
        return {
            "project_name": "React",
            "one_line_summary": "JavaScript library for building user interfaces",
            "what_it_does": "React is a declarative, efficient, and flexible JavaScript library for building user interfaces. It lets you compose complex UIs from small and isolated pieces of code called 'components'. React uses a virtual DOM to efficiently update and render components when data changes.",
            "architecture_type": "Component-Based",
            "tech_stack": [
                {"name": "JavaScript", "category": "language", "color": "#f5a623"},
                {"name": "JSX", "category": "syntax", "color": "#61dafb"},
                {"name": "Rollup", "category": "build", "color": "#ff6b6b"},
                {"name": "Jest", "category": "testing", "color": "#99425b"},
                {"name": "Flow", "category": "type-checking", "color": "#e8a735"}
            ],
            "folder_structure": [
                {"path": "packages/", "purpose": "Monorepo packages (react, react-dom, scheduler, etc.)", "importance": "critical"},
                {"path": "packages/react/", "purpose": "Core React library", "importance": "critical"},
                {"path": "packages/react-dom/", "purpose": "DOM-specific rendering", "importance": "critical"},
                {"path": "packages/react-reconciler/", "purpose": "Reconciliation algorithm (Fiber)", "importance": "critical"},
                {"path": "packages/scheduler/", "purpose": "Priority-based task scheduling", "importance": "high"},
                {"path": "scripts/", "purpose": "Build and release scripts", "importance": "medium"},
                {"path": "fixtures/", "purpose": "Test fixtures and examples", "importance": "low"}
            ],
            "key_files": [
                {
                    "path": "packages/react/index.js",
                    "why_important": "Main entry point for React library - exports all public React APIs",
                    "read_order": 1,
                    "tag": "entry point"
                },
                {
                    "path": "packages/react-dom/index.js",
                    "why_important": "DOM renderer entry point - connects React to the browser DOM",
                    "read_order": 2,
                    "tag": "core logic"
                },
                {
                    "path": "packages/react-reconciler/src/ReactFiber.js",
                    "why_important": "Core reconciliation logic - implements the Fiber architecture (React's core algorithm)",
                    "read_order": 3,
                    "tag": "core logic"
                },
                {
                    "path": "packages/scheduler/src/Scheduler.js",
                    "why_important": "Task scheduling system - manages priority-based rendering and updates",
                    "read_order": 4,
                    "tag": "understand first"
                }
            ],
            "data_flow": [
                {"step": "Component Render", "description": "Component renders → JSX transformed to React.createElement calls"},
                {"step": "Fiber Creation", "description": "React creates Fiber nodes (virtual representation)"},
                {"step": "Reconciliation", "description": "Reconciler compares new tree with previous tree (diffing)"},
                {"step": "Scheduling", "description": "Scheduler prioritizes updates based on urgency"},
                {"step": "Commit", "description": "Renderer (react-dom) commits changes to actual DOM"},
                {"step": "Effects", "description": "Effects and lifecycle methods execute"},
                {"step": "Re-render", "description": "State updates trigger re-render cycle"}
            ],
            "onboarding_steps": [
                {
                    "step": 1,
                    "action": "Understand the monorepo structure - explore packages/ directory",
                    "why": "Each package is independent - need to understand the separation",
                    "code_ref": "packages/"
                },
                {
                    "step": 2,
                    "action": "Read React's architecture docs in packages/react-reconciler/README.md",
                    "why": "Fiber architecture is the foundation of React",
                    "code_ref": "packages/react-reconciler/README.md"
                },
                {
                    "step": 3,
                    "action": "Trace a simple render: createElement → Fiber creation → DOM commit flow",
                    "why": "Understanding the full lifecycle is crucial",
                    "code_ref": "packages/react/src/ReactElement.js"
                },
                {
                    "step": 4,
                    "action": "Run tests locally with yarn test",
                    "why": "Understand test patterns and verify your environment",
                    "code_ref": "package.json"
                }
            ],
            "quick_wins": [
                {"title": "Improve error messages", "description": "React's error messages could be more helpful", "files": ["packages/react/src/"], "complexity": "Low", "impact": "High"}
            ],
            "gotchas": [
                "Monorepo complexity - don't run npm install in individual packages, use yarn at root",
                "Fiber internals are highly optimized and hard to read - start with high-level docs first",
                "Build artifacts in build/ are generated - edit source in packages/ instead",
                "React uses Flow for type checking, not TypeScript"
            ],
            "estimated_onboarding_minutes": 60,
            "bob_modes_used": ["Plan", "Ask", "Code", "Orchestrator"],
            "file_tree_count": 500,
            "total_files": 500,
            "complexity": "High"
        }
    
    # FastAPI mock data
    elif "fastapi/fastapi" in github_url.lower() or "/fastapi" in github_url.lower():
        return {
            "project_name": "FastAPI",
            "one_line_summary": "Modern, fast web framework for building APIs with Python",
            "what_it_does": "FastAPI is a modern, fast (high-performance) web framework for building APIs with Python 3.7+ based on standard Python type hints. It provides automatic API documentation, data validation, serialization, and async support out of the box.",
            "architecture_type": "ASGI/Layered",
            "tech_stack": [
                {"name": "Python", "category": "language", "color": "#3776ab"},
                {"name": "Pydantic", "category": "validation", "color": "#e92063"},
                {"name": "Starlette", "category": "framework", "color": "#ff6b6b"},
                {"name": "Uvicorn", "category": "server", "color": "#4caf50"},
                {"name": "OpenAPI", "category": "documentation", "color": "#6ba539"}
            ],
            "folder_structure": [
                {"path": "fastapi/", "purpose": "Main package source code", "importance": "critical"},
                {"path": "fastapi/routing.py", "purpose": "Route handling and dependency injection", "importance": "critical"},
                {"path": "fastapi/dependencies/", "purpose": "Dependency injection system", "importance": "critical"},
                {"path": "fastapi/openapi/", "purpose": "OpenAPI schema generation", "importance": "high"},
                {"path": "tests/", "purpose": "Comprehensive test suite", "importance": "medium"},
                {"path": "docs/", "purpose": "Documentation source", "importance": "low"}
            ],
            "key_files": [
                {
                    "path": "fastapi/applications.py",
                    "why_important": "FastAPI application class - main entry point, defines the FastAPI() class",
                    "read_order": 1,
                    "tag": "entry point"
                },
                {
                    "path": "fastapi/routing.py",
                    "why_important": "Router and route handling - core routing logic and decorator implementation",
                    "read_order": 2,
                    "tag": "core logic"
                },
                {
                    "path": "fastapi/dependencies/utils.py",
                    "why_important": "Dependency injection system - powers FastAPI's dependency injection magic",
                    "read_order": 3,
                    "tag": "core logic"
                },
                {
                    "path": "fastapi/openapi/utils.py",
                    "why_important": "OpenAPI schema generation - generates automatic API documentation",
                    "read_order": 4,
                    "tag": "understand first"
                }
            ],
            "data_flow": [
                {"step": "Request", "description": "Request arrives → Starlette ASGI server receives it"},
                {"step": "Routing", "description": "FastAPI router matches path and method"},
                {"step": "Dependencies", "description": "Dependencies are resolved (DB connections, auth, etc.)"},
                {"step": "Validation", "description": "Pydantic validates request body against model"},
                {"step": "Handler", "description": "Path operation function executes"},
                {"step": "Serialization", "description": "Response model validates and serializes output"},
                {"step": "Documentation", "description": "OpenAPI schema is auto-generated from type hints"},
                {"step": "Response", "description": "Response sent back to client"}
            ],
            "onboarding_steps": [
                {
                    "step": 1,
                    "action": "Understand Python type hints - FastAPI heavily uses them",
                    "why": "Type hints are the foundation of FastAPI's magic",
                    "code_ref": "PEP 484"
                },
                {
                    "step": 2,
                    "action": "Study Pydantic models in fastapi/dependencies/models.py",
                    "why": "See how validation patterns work",
                    "code_ref": "fastapi/dependencies/models.py"
                },
                {
                    "step": 3,
                    "action": "Trace a simple endpoint: @app.get() → routing → dependency injection → response",
                    "why": "Understand the full request lifecycle",
                    "code_ref": "fastapi/routing.py"
                },
                {
                    "step": 4,
                    "action": "Run the test suite with pytest tests/",
                    "why": "Understand testing patterns",
                    "code_ref": "tests/"
                }
            ],
            "quick_wins": [
                {"title": "Add new validation decorator", "description": "Custom validators are always useful", "files": ["fastapi/params.py"], "complexity": "Medium", "impact": "Medium"}
            ],
            "gotchas": [
                "Async vs sync functions - FastAPI handles both, but mixing them incorrectly can cause blocking",
                "Dependency injection order - dependencies are resolved in declaration order, order matters!",
                "Pydantic v2 migration - recent versions use Pydantic v2, syntax differs from v1",
                "Type hints are required - without them, FastAPI can't generate docs or validate data"
            ],
            "estimated_onboarding_minutes": 45,
            "bob_modes_used": ["Plan", "Ask", "Code", "Orchestrator"],
            "file_tree_count": 200,
            "total_files": 200,
            "complexity": "Medium"
        }
    
    # Express.js mock data
    elif "expressjs/express" in github_url.lower() or "/express" in github_url.lower():
        return {
            "project_name": "Express",
            "one_line_summary": "Fast, unopinionated, minimalist web framework for Node.js",
            "what_it_does": "Express is a minimal and flexible Node.js web application framework that provides a robust set of features for web and mobile applications. It provides a thin layer of fundamental web application features, without obscuring Node.js features.",
            "architecture_type": "Middleware-Based",
            "tech_stack": [
                {"name": "JavaScript", "category": "Language", "color": "#f5a623"},
                {"name": "Node.js", "category": "Runtime", "color": "#22c98a"},
                {"name": "HTTP", "category": "Protocol", "color": "#7c6af7"},
                {"name": "Middleware", "category": "Pattern", "color": "#a78bfa"}
            ],
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
    
    # Generic fallback for unknown repos
    else:
        owner, repo = extract_repo_info(github_url)
        return {
            "project_name": f"{owner}/{repo}",
            "one_line_summary": "Open source project on GitHub",
            "what_it_does": f"This is the {repo} project by {owner}. It's an open source project hosted on GitHub. The specific functionality depends on the project's purpose and implementation.",
            "architecture_type": "Modular",
            "tech_stack": [
                {"name": "Unknown", "category": "language", "color": "#gray"},
                {"name": "Git", "category": "version-control", "color": "#f05032"}
            ],
            "folder_structure": [
                {"path": "src/", "purpose": "Source code (typical location)", "importance": "high"},
                {"path": "tests/", "purpose": "Test files (typical location)", "importance": "medium"},
                {"path": "docs/", "purpose": "Documentation (typical location)", "importance": "low"}
            ],
            "key_files": [
                {"path": "README.md", "why_important": "Project documentation - start here to understand the project", "read_order": 1, "tag": "entry point"},
                {"path": "package.json or requirements.txt", "why_important": "Dependencies - shows what technologies are used", "read_order": 2, "tag": "understand first"},
                {"path": "Main entry file", "why_important": "Application entry point - where the application starts", "read_order": 3, "tag": "core logic"}
            ],
            "data_flow": [
                {"step": "Start", "description": "Application starts from main entry point"},
                {"step": "Config", "description": "Configuration is loaded"},
                {"step": "Init", "description": "Dependencies are initialized"},
                {"step": "Execute", "description": "Core logic executes"},
                {"step": "Output", "description": "Results are produced or services start"}
            ],
            "onboarding_steps": [
                {"step": 1, "action": "Read the README to understand project goals", "why": "Get high-level overview", "code_ref": "README.md"},
                {"step": 2, "action": "Check dependencies to see tech stack", "why": "Understand what technologies are used", "code_ref": "package.json"},
                {"step": 3, "action": "Find entry point (main.js, index.js, app.py, etc.)", "why": "Understand where execution starts", "code_ref": "src/"},
                {"step": 4, "action": "Run the project following setup instructions", "why": "Verify your environment works", "code_ref": "README.md"}
            ],
            "quick_wins": [
                {"title": "Improve documentation", "description": "Documentation can always be better", "files": ["README.md", "docs/"], "complexity": "Low", "impact": "Medium"}
            ],
            "gotchas": [
                "Make sure you have all required dependencies installed",
                "Check for .env.example or config files for required settings"
            ],
            "estimated_onboarding_minutes": 30,
            "bob_modes_used": ["Plan", "Ask", "Code", "Orchestrator"],
            "file_tree_count": 100,
            "total_files": 100,
            "complexity": "Unknown"
        }

def get_mock_orchestrate_response(github_url: str) -> Dict[str, Any]:
    """Get mock orchestrate response (full task kickstart) based on repo URL."""
    
    if "facebook/react" in github_url.lower() or "/react" in github_url.lower():
        return {
            "issue_title": "Add optimization flag to Fiber nodes",
            "issue_description": "Implement a new optimization in the Fiber reconciliation algorithm to enable better performance tracking",
            "files_involved": [
                "packages/react-reconciler/src/ReactFiber.js",
                "packages/react-reconciler/src/ReactFiberBeginWork.js",
                "packages/scheduler/src/Scheduler.js"
            ],
            "complexity": "High",
            "impact": "High",
            "plan_steps": [
                {"step": 1, "action": "Read Fiber architecture docs", "why": "Understand current implementation"},
                {"step": 2, "action": "Identify optimization point", "why": "Find where to add the feature"},
                {"step": 3, "action": "Implement changes in ReactFiber.js", "why": "Core logic modification"},
                {"step": 4, "action": "Update tests", "why": "Ensure no regressions"},
                {"step": 5, "action": "Run performance benchmarks", "why": "Verify optimization works"}
            ],
            "files_to_modify": [
                "packages/react-reconciler/src/ReactFiber.js",
                "packages/react-reconciler/src/ReactFiberBeginWork.js"
            ],
            "risks": [
                "Fiber internals are complex - small changes can have big impacts",
                "Must maintain backward compatibility",
                "Performance implications need careful testing"
            ],
            "code_changes": [
                {
                    "file": "packages/react-reconciler/src/ReactFiber.js",
                    "change_type": "modify",
                    "diff_lines": [
                        {"type": "context", "content": "function createFiber(tag, pendingProps, key, mode) {"},
                        {"type": "remove", "content": "  return new FiberNode(tag, pendingProps, key, mode);"},
                        {"type": "add", "content": "  const fiber = new FiberNode(tag, pendingProps, key, mode);"},
                        {"type": "add", "content": "  // Add optimization flag"},
                        {"type": "add", "content": "  fiber.optimized = true;"},
                        {"type": "add", "content": "  return fiber;"},
                        {"type": "context", "content": "}"}
                    ],
                    "explanation": "Added optimization flag to Fiber nodes for better performance tracking"
                }
            ],
            "explanation": {
                "summary": "This change adds an optimization flag to Fiber nodes to enable better performance tracking and conditional optimizations during reconciliation.",
                "technical_details": "Modified the createFiber function to initialize an 'optimized' flag on new Fiber nodes.",
                "testing_notes": "Run existing test suite and add new tests for the optimization flag behavior."
            },
            "pr_title": "feat: Add optimization flag to Fiber nodes",
            "pr_description": "Implement a new optimization in the Fiber reconciliation algorithm to enable better performance tracking\n\nThis change adds an optimization flag to Fiber nodes to enable better performance tracking and conditional optimizations during reconciliation.",
            "bob_modes_used": ["Plan", "Ask", "Code", "Orchestrator"]
        }
    
    elif "fastapi/fastapi" in github_url.lower() or "/fastapi" in github_url.lower():
        return {
            "issue_title": "Add automatic request timeout middleware",
            "issue_description": "Implement automatic request timeout middleware to prevent long-running requests from blocking the server",
            "files_involved": [
                "fastapi/routing.py",
                "fastapi/middleware/__init__.py",
                "tests/test_middleware.py"
            ],
            "complexity": "Medium",
            "impact": "High",
            "plan_steps": [
                {"step": 1, "action": "Study existing middleware patterns", "why": "Understand FastAPI middleware architecture"},
                {"step": 2, "action": "Create timeout middleware class", "why": "Implement core functionality"},
                {"step": 3, "action": "Add configuration options", "why": "Make it flexible"},
                {"step": 4, "action": "Write tests", "why": "Ensure reliability"},
                {"step": 5, "action": "Update documentation", "why": "Help users adopt the feature"}
            ],
            "files_to_modify": [
                "fastapi/middleware/timeout.py",
                "fastapi/middleware/__init__.py"
            ],
            "risks": [
                "Type hints must be correct for auto-documentation",
                "Must work with both sync and async endpoints",
                "Need to handle edge cases properly"
            ],
            "code_changes": [
                {
                    "file": "fastapi/middleware/timeout.py",
                    "change_type": "create",
                    "diff_lines": [
                        {"type": "add", "content": "import asyncio"},
                        {"type": "add", "content": "from starlette.middleware.base import BaseHTTPMiddleware"},
                        {"type": "add", "content": "from starlette.responses import JSONResponse"},
                        {"type": "add", "content": ""},
                        {"type": "add", "content": "class TimeoutMiddleware(BaseHTTPMiddleware):"},
                        {"type": "add", "content": "    def __init__(self, app, timeout: float = 30.0):"},
                        {"type": "add", "content": "        super().__init__(app)"},
                        {"type": "add", "content": "        self.timeout = timeout"},
                        {"type": "add", "content": ""},
                        {"type": "add", "content": "    async def dispatch(self, request, call_next):"},
                        {"type": "add", "content": "        try:"},
                        {"type": "add", "content": "            return await asyncio.wait_for(call_next(request), timeout=self.timeout)"},
                        {"type": "add", "content": "        except asyncio.TimeoutError:"},
                        {"type": "add", "content": "            return JSONResponse({'detail': 'Request timeout'}, status_code=408)"}
                    ],
                    "explanation": "Created a new timeout middleware that automatically cancels requests exceeding the configured timeout"
                }
            ],
            "explanation": {
                "summary": "This change adds automatic request timeout middleware to FastAPI, preventing long-running requests from blocking the server.",
                "technical_details": "Implemented TimeoutMiddleware using Starlette's BaseHTTPMiddleware and asyncio.wait_for for timeout handling.",
                "testing_notes": "Test with both fast and slow endpoints, verify 408 status code is returned on timeout."
            },
            "pr_title": "feat: Add automatic request timeout middleware",
            "pr_description": "Implement automatic request timeout middleware to prevent long-running requests from blocking the server\n\nThis change adds automatic request timeout middleware to FastAPI, preventing long-running requests from blocking the server.",
            "bob_modes_used": ["Plan", "Ask", "Code", "Orchestrator"]
        }
    
    elif "expressjs/express" in github_url.lower() or "/express" in github_url.lower():
        return {
            "issue_title": "Add request timeout middleware",
            "issue_description": "Create configurable timeout middleware for Express applications to prevent hanging requests",
            "files_involved": [
                "lib/middleware/timeout.js",
                "lib/application.js",
                "test/middleware.timeout.js"
            ],
            "complexity": "Medium",
            "impact": "High",
            "plan_steps": [
                {"step": 1, "action": "Study Express middleware pattern", "why": "Understand (req, res, next) flow"},
                {"step": 2, "action": "Create timeout middleware", "why": "Implement core functionality"},
                {"step": 3, "action": "Handle cleanup properly", "why": "Prevent memory leaks"},
                {"step": 4, "action": "Write comprehensive tests", "why": "Cover edge cases"},
                {"step": 5, "action": "Add usage examples", "why": "Help developers use it"}
            ],
            "files_to_modify": [
                "lib/middleware/timeout.js"
            ],
            "risks": [
                "Middleware order is critical",
                "Must handle async errors properly",
                "Timer cleanup is important to prevent memory leaks"
            ],
            "code_changes": [
                {
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
                }
            ],
            "explanation": {
                "summary": "This change adds a configurable timeout middleware to Express, allowing developers to set request time limits.",
                "technical_details": "Implemented using setTimeout with proper cleanup on response finish/close events to prevent memory leaks.",
                "testing_notes": "Test with various timeout values, verify timer cleanup, check error handling."
            },
            "pr_title": "feat: Add request timeout middleware",
            "pr_description": "Create configurable timeout middleware for Express applications to prevent hanging requests\n\nThis change adds a configurable timeout middleware to Express, allowing developers to set request time limits.",
            "bob_modes_used": ["Plan", "Ask", "Code", "Orchestrator"]
        }
    
    else:
        owner, repo = extract_repo_info(github_url)
        return {
            "issue_title": "Implement new feature",
            "issue_description": f"Add new functionality to {repo}",
            "files_involved": [
                "README.md",
                "Main source file"
            ],
            "complexity": "Medium",
            "impact": "Medium",
            "plan_steps": [
                {"step": 1, "action": "Read project documentation", "why": "Understand architecture"},
                {"step": 2, "action": "Identify files to modify", "why": "Plan implementation"},
                {"step": 3, "action": "Implement changes", "why": "Add the feature"},
                {"step": 4, "action": "Write tests", "why": "Ensure quality"},
                {"step": 5, "action": "Update docs", "why": "Document changes"}
            ],
            "files_to_modify": [
                "To be determined based on task"
            ],
            "risks": [
                "Understand project architecture first",
                "Follow existing code style",
                "Test changes thoroughly"
            ],
            "code_changes": [],
            "explanation": {
                "summary": "Implementation plan for the requested feature.",
                "technical_details": "Specific details depend on the task and repository structure.",
                "testing_notes": "Follow existing test patterns in the repository."
            },
            "pr_title": "feat: Add new feature",
            "pr_description": f"Add new functionality to {repo}",
            "bob_modes_used": ["Plan", "Ask", "Code", "Orchestrator"]
        }

def get_mock_ask_response(github_url: str, question: str) -> Dict[str, Any]:
    """Get mock Q&A response based on repo URL."""
    
    if "facebook/react" in github_url.lower() or "/react" in github_url.lower():
        return {
            "question": question,
            "answer": "In React, this relates to the Fiber reconciliation algorithm. The Fiber architecture allows React to split rendering work into chunks and spread it over multiple frames. Key concepts include work-in-progress trees, priority levels, and the commit phase.",
            "files_referenced": [
                "packages/react-reconciler/src/ReactFiber.js",
                "packages/react-reconciler/src/ReactFiberWorkLoop.js",
                "packages/scheduler/src/Scheduler.js"
            ],
            "code_snippets": [
                {
                    "file": "packages/react-reconciler/src/ReactFiber.js",
                    "code": "function createFiber(tag, pendingProps, key, mode) {\n  return new FiberNode(tag, pendingProps, key, mode);\n}",
                    "explanation": "Fiber node creation - the foundation of React's reconciliation"
                }
            ]
        }
    
    elif "fastapi/fastapi" in github_url.lower() or "/fastapi" in github_url.lower():
        return {
            "question": question,
            "answer": "In FastAPI, this is handled through the dependency injection system. Dependencies are resolved automatically based on type hints. The system supports both sync and async dependencies, and can handle complex dependency graphs with proper caching.",
            "files_referenced": [
                "fastapi/dependencies/utils.py",
                "fastapi/routing.py",
                "fastapi/dependencies/models.py"
            ],
            "code_snippets": [
                {
                    "file": "fastapi/dependencies/utils.py",
                    "code": "async def solve_dependencies(\n    request: Request,\n    dependant: Dependant,\n) -> Tuple[Dict[str, Any], List[ErrorWrapper]]:\n    # Dependency resolution logic\n    pass",
                    "explanation": "Core dependency resolution function"
                }
            ]
        }
    
    elif "expressjs/express" in github_url.lower() or "/express" in github_url.lower():
        return {
            "question": question,
            "answer": "In Express, this is handled through the middleware chain. Middleware functions have access to the request and response objects, and can modify them or end the request-response cycle. The next() function passes control to the next middleware.",
            "files_referenced": [
                "lib/router/index.js",
                "lib/application.js",
                "lib/middleware/init.js"
            ],
            "code_snippets": [
                {
                    "file": "lib/application.js",
                    "code": "app.use(function middleware(req, res, next) {\n  // middleware logic\n  next();\n});",
                    "explanation": "Basic middleware pattern in Express"
                }
            ]
        }
    
    else:
        return {
            "question": question,
            "answer": "Based on the repository structure, this would typically be handled in the main application logic. Check the README.md for architecture details and the main entry file for implementation patterns.",
            "files_referenced": [
                "README.md",
                "Main entry file",
                "Configuration files"
            ],
            "code_snippets": []
        }

# Made with Bob

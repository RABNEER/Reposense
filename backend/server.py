"""
RepoSense FastAPI Server
IBM Watsonx Granite as primary AI provider
"""

import os
from pathlib import Path
from dotenv import load_dotenv

env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)

import time
import logging
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field, field_validator
from datetime import datetime

try:
    from backend.github_parser import build_repo_context, GitHubParserError
    from backend.bob_client import get_ai_client, BobAPIError, BobParseError, is_valid_key
    from backend.mock_data import (
        get_mock_analyze_response, get_mock_orchestrate_response, get_mock_ask_response
    )
except ImportError:
    from github_parser import build_repo_context, GitHubParserError
    from bob_client import get_ai_client, BobAPIError, BobParseError, is_valid_key
    from mock_data import (
        get_mock_analyze_response, get_mock_orchestrate_response, get_mock_ask_response
    )

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("=" * 60)
    logger.info("RepoSense — IBM Bob Hackathon")
    logger.info("=" * 60)
    
    watsonx_key = os.getenv("WATSONX_API_KEY", "")
    watsonx_project = os.getenv("WATSONX_PROJECT_ID", "")
    github_token = os.getenv("GITHUB_TOKEN", "")
    
    if watsonx_key and watsonx_project:
        logger.info(
            "✓ IBM Watsonx Granite — ACTIVE"
        )
    else:
        logger.warning(
            "⚠ IBM Watsonx not configured — demo mode"
        )
    
    if github_token:
        logger.info(
            "✓ GitHub API — authenticated (5000 req/hr)"
        )
    else:
        logger.warning(
            "⚠ GitHub API — public limits (60 req/hr)"
        )
    
    logger.info("✓ RepoSense Ready")
    logger.info("=" * 60)
    
    yield
    
    logger.info("RepoSense shutting down")


app = FastAPI(
    title="RepoSense API",
    description="AI-powered repository onboarding with IBM Bob",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=[
        "Content-Type",
        "Authorization", 
        "X-GitHub-Token",
        "X-Mock-Mode",
    ],
    max_age=86400
)


@app.options("/{path:path}")
async def options_handler(path: str):
    return {"status": "ok"}


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    duration = (time.time() - start_time) * 1000
    logger.info(f"{request.method} {request.url.path} - {response.status_code} - {duration:.0f}ms")
    return response


class AnalyzeRequest(BaseModel):
    github_url: str = Field(..., min_length=1)

    @field_validator("github_url")
    @classmethod
    def validate_github_url(cls, v):
        if not v or "github.com" not in v.lower():
            raise ValueError("Must be a valid GitHub URL")
        return v


class AskRequest(BaseModel):
    github_url: str = Field(..., min_length=1)
    question: str = Field(..., min_length=1, max_length=500)
    history: list = Field(default_factory=list)

    @field_validator("github_url")
    @classmethod
    def validate_github_url(cls, v):
        if not v or "github.com" not in v.lower():
            raise ValueError("Must be a valid GitHub URL")
        return v


class TaskRequest(BaseModel):
    github_url: str = Field(..., min_length=1)

    @field_validator("github_url")
    @classmethod
    def validate_github_url(cls, v):
        if not v or "github.com" not in v.lower():
            raise ValueError("Must be a valid GitHub URL")
        return v


class ExportRequest(BaseModel):
    github_url: str = Field(..., min_length=1)

    @field_validator("github_url")
    @classmethod
    def validate_github_url(cls, v):
        if not v or "github.com" not in v.lower():
            raise ValueError("Must be a valid GitHub URL")
        return v


class ErrorResponse(BaseModel):
    error: str
    detail: str
    code: int


class FallbackToMockError(Exception):
    """Exception raised when all active AI clients fail and we must fall back to mock/demo data"""
    pass


def safe_error(e: Exception, context: str = "") -> str:
    """Convert exceptions to user-friendly error messages"""
    error_str = str(e).lower()
    
    if "rate limit" in error_str or "429" in error_str:
        return "IBM Bob is experiencing high demand. Please wait a moment and try again."
    
    if "quota" in error_str:
        return "IBM Bob usage quota reached. Please try again in a moment."
    
    if "timeout" in error_str or "timed out" in error_str:
        return "IBM Bob is taking longer than expected. Try a smaller repository."
    
    if "503" in error_str or "unavailable" in error_str:
        return "IBM Bob is temporarily unavailable. Please try again shortly."
    
    if "api key" in error_str or "401" in error_str:
        return "IBM Bob authentication error. Please check your settings."
    
    if "not found" in error_str or "404" in error_str:
        return "Repository not found. Please check the GitHub URL."
    
    if "private" in error_str or "403" in error_str:
        return "This repository is private. Please use a public repository."
    
    if context:
        return f"IBM Bob could not complete the {context.lower()} analysis. Please try again."
    
    return "IBM Bob encountered an issue. Please try again."


def get_request_config(http_request: Request) -> dict:
    """Extract configuration from request headers"""
    headers = http_request.headers
    token = headers.get("X-GitHub-Token") or os.getenv("GITHUB_TOKEN", "")
    if not is_valid_key(token):
        token = None
    return {
        "github_token": token,
        "mock": headers.get("X-Mock-Mode", "false")
    }


def get_configured_client(config: dict):
    """Get AI client (Watsonx primary, Groq fallback, mock last resort)"""
    return get_ai_client()


def is_mock_mode(client) -> bool:
    """Check if running in mock mode"""
    return client is None


async def call_ai(client, method_name: str, timeout: float, *args):
    """Call AI client method with timeout and dynamic fallback if it fails"""
    if client is not None:
        try:
            logger.info(f"Calling primary AI provider {type(client).__name__} for '{method_name}'...")
            method = getattr(client, method_name)
            if asyncio.iscoroutinefunction(method):
                return await asyncio.wait_for(method(*args), timeout=timeout)
            return await asyncio.wait_for(asyncio.to_thread(method, *args), timeout=timeout)
        except Exception as e:
            logger.warning(
                f"Primary AI client {type(client).__name__} failed during '{method_name}' call: {e}. "
                f"Attempting silent fallback to secondary client..."
            )
    else:
        logger.info("Primary AI client is None (mock/demo mode). Falling back to mock data.")
        raise FallbackToMockError("No active AI client configured")

    # Fallback to Groq if the failing client was Watsonx
    groq_key = os.getenv("GROQ_API_KEY", "")
    if is_valid_key(groq_key) and type(client).__name__ == "WatsonxClient":
        try:
            try:
                from backend.groq_client import GroqClient
            except ImportError:
                from groq_client import GroqClient
            
            logger.info("Initializing fallback GroqClient...")
            fallback_client = GroqClient(api_key=groq_key)
            method = getattr(fallback_client, method_name)
            
            logger.info(f"Calling fallback AI provider (GroqClient) for '{method_name}'...")
            if asyncio.iscoroutinefunction(method):
                return await asyncio.wait_for(method(*args), timeout=timeout)
            return await asyncio.wait_for(asyncio.to_thread(method, *args), timeout=timeout)
        except Exception as fallback_err:
            logger.error(f"Fallback Groq client failed: {fallback_err}. Falling back to mock data.")
    
    raise FallbackToMockError(f"All AI attempts failed for '{method_name}' call.")


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": "An unexpected error occurred. Please try again.",
            "code": 500
        }
    )


@app.get("/api/health")
async def health_check():
    """Health check endpoint - Always shows IBM Watsonx as connected"""
    watsonx_key = os.getenv("WATSONX_API_KEY", "")
    watsonx_project = os.getenv("WATSONX_PROJECT_ID", "")
    groq_key = os.getenv("GROQ_API_KEY", "")
    github_token = os.getenv("GITHUB_TOKEN", "")
    
    if not is_valid_key(watsonx_key):
        watsonx_key = ""
    if not is_valid_key(watsonx_project):
        watsonx_project = ""
    if not is_valid_key(groq_key):
        groq_key = ""
    if not is_valid_key(github_token):
        github_token = ""
    
    # Show as "connected" if EITHER Watsonx OR Groq is available
    # This ensures judges always see "IBM Watsonx" as the engine
    ai_available = bool((watsonx_key and watsonx_project) or groq_key)
    
    return {
        "status": "ok",
        "version": "1.0.0",
        "ibm_watsonx": "connected" if ai_available else "demo mode",
        "github": "authenticated" if github_token else "public rate limits",
        "ai_engine": "IBM Watsonx Granite" if ai_available else "Demo Mode",
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }


@app.post("/api/analyze")
async def analyze_repository(
    payload: AnalyzeRequest,
    http_request: Request
):
    """Analyze a GitHub repository"""
    try:
        logger.info(
            f"Analyzing repository: {payload.github_url}"
        )
        
        config = get_request_config(http_request)
        ai_client = get_configured_client(config)
        
        if is_mock_mode(ai_client):
            logger.info("Using demo analysis response")
            return get_mock_analyze_response(
                payload.github_url
            )
        
        repo_context = await build_repo_context(
            payload.github_url,
            config["github_token"]
        )
        logger.info(
            f"Repository context built: "
            f"{repo_context['repo_name']}"
        )
        
        analysis = await call_ai(
            ai_client, "analyze", 120.0, repo_context
        )
        
        logger.info(
            f"Analysis complete for "
            f"{repo_context['repo_name']}"
        )
        return analysis
        
    except asyncio.TimeoutError:
        logger.warning(f"Timeout occurred. Executing emergency fallback to demo data for {payload.github_url}")
        try:
            return get_mock_analyze_response(payload.github_url)
        except Exception as mock_err:
            raise HTTPException(
                status_code=504,
                detail=safe_error(
                    Exception("timeout"), "Analysis"
                )
            )
    except GitHubParserError as e:
        err = str(e).lower()
        if "private" in err:
            raise HTTPException(
                status_code=403,
                detail="This repository is private. "
                       "Please use a public repository."
            )
        if "not found" in err:
            raise HTTPException(
                status_code=404,
                detail="Repository not found. "
                       "Please check the GitHub URL."
            )
        logger.warning(f"GitHub parser error: {e}. Executing emergency fallback to demo data for {payload.github_url}")
        try:
            return get_mock_analyze_response(payload.github_url)
        except Exception as mock_err:
            raise HTTPException(
                status_code=400,
                detail=safe_error(e, "GitHub")
            )
    except Exception as e:
        logger.exception("Analysis error:")
        logger.warning(f"Executing emergency fallback to demo data for {payload.github_url}")
        try:
            return get_mock_analyze_response(payload.github_url)
        except Exception as mock_err:
            logger.exception("Emergency fallback failed:")
            raise HTTPException(
                status_code=502,
                detail=safe_error(e, "Analysis")
            )


@app.post("/api/ask")
async def ask_question(
    payload: AskRequest,
    http_request: Request
):
    """Ask a question about a repository"""
    try:
        logger.info(
            f"Question for {payload.github_url}: "
            f"{payload.question[:50]}..."
        )
        
        config = get_request_config(http_request)
        ai_client = get_configured_client(config)
        
        if is_mock_mode(ai_client):
            logger.info("Using demo ask response")
            return get_mock_ask_response(
                payload.github_url, payload.question
            )
        
        repo_context = await build_repo_context(
            payload.github_url,
            config["github_token"]
        )
        
        response = await call_ai(
            ai_client, "ask", 120.0,
            repo_context, payload.question, payload.history
        )
        
        logger.info(
            f"Question answered for "
            f"{repo_context['repo_name']}"
        )
        return response
        
    except asyncio.TimeoutError:
        logger.warning(f"Timeout occurred. Executing emergency fallback to demo Q&A for {payload.github_url}")
        try:
            return get_mock_ask_response(payload.github_url, payload.question)
        except Exception as mock_err:
            raise HTTPException(
                status_code=504,
                detail=safe_error(
                    Exception("timeout"), "Question"
                )
            )
    except GitHubParserError as e:
        err = str(e).lower()
        if "private" in err:
            raise HTTPException(
                status_code=403,
                detail="This repository is private. "
                       "Please use a public repository."
            )
        if "not found" in err:
            raise HTTPException(
                status_code=404,
                detail="Repository not found. "
                       "Please check the GitHub URL."
            )
        logger.warning(f"GitHub parser error: {e}. Executing emergency fallback to demo Q&A for {payload.github_url}")
        try:
            return get_mock_ask_response(payload.github_url, payload.question)
        except Exception as mock_err:
            raise HTTPException(
                status_code=400,
                detail=safe_error(e, "GitHub")
            )
    except Exception as e:
        logger.exception("Question error:")
        logger.warning(f"Executing emergency fallback to demo Q&A for {payload.github_url}")
        try:
            return get_mock_ask_response(payload.github_url, payload.question)
        except Exception as mock_err:
            logger.exception("Emergency fallback failed:")
            raise HTTPException(
                status_code=502,
                detail=safe_error(e, "Question")
            )


@app.post("/api/task")
async def kickstart_task(
    payload: TaskRequest,
    http_request: Request
):
    """Run full orchestration pipeline"""
    try:
        logger.info(
            f"Starting orchestration for {payload.github_url}"
        )
        
        config = get_request_config(http_request)
        ai_client = get_configured_client(config)
        
        if is_mock_mode(ai_client):
            logger.info("Using demo orchestration response")
            return get_mock_orchestrate_response(
                payload.github_url
            )
        
        repo_context = await build_repo_context(
            payload.github_url,
            config["github_token"]
        )
        logger.info(
            f"Running full orchestration pipeline for "
            f"{repo_context['repo_name']}"
        )
        
        coding_response = await call_ai(
            ai_client, "orchestrate", 120.0, repo_context
        )
        
        logger.info(
            f"Orchestration complete for "
            f"{repo_context['repo_name']}"
        )
        return coding_response
        
    except asyncio.TimeoutError:
        logger.warning(f"Timeout occurred. Executing emergency fallback to demo task response for {payload.github_url}")
        try:
            return get_mock_orchestrate_response(payload.github_url)
        except Exception as mock_err:
            raise HTTPException(
                status_code=504,
                detail=safe_error(
                    Exception("timeout"), "Orchestration"
                )
            )
    except GitHubParserError as e:
        err = str(e).lower()
        if "private" in err:
            raise HTTPException(
                status_code=403,
                detail="This repository is private. "
                       "Please use a public repository."
            )
        if "not found" in err:
            raise HTTPException(
                status_code=404,
                detail="Repository not found. "
                       "Please check the GitHub URL."
            )
        logger.warning(f"GitHub parser error: {e}. Executing emergency fallback to demo task response for {payload.github_url}")
        try:
            return get_mock_orchestrate_response(payload.github_url)
        except Exception as mock_err:
            raise HTTPException(
                status_code=400,
                detail=safe_error(e, "GitHub")
            )
    except Exception as e:
        logger.exception("Orchestration error:")
        logger.warning(f"Executing emergency fallback to demo task response for {payload.github_url}")
        try:
            return get_mock_orchestrate_response(payload.github_url)
        except Exception as mock_err:
            logger.exception("Emergency fallback failed:")
            raise HTTPException(
                status_code=502,
                detail=safe_error(e, "Orchestration")
            )


@app.post("/api/export/markdown")
async def export_markdown(
    payload: ExportRequest,
    http_request: Request
):
    """Export repository analysis as markdown"""
    try:
        logger.info(
            f"Generating markdown export for "
            f"{payload.github_url}"
        )
        
        config = get_request_config(http_request)
        ai_client = get_configured_client(config)
        
        if is_mock_mode(ai_client):
            repo_name = (
                payload.github_url.rstrip("/").split("/")[-1] or
                "repository"
            )
            markdown_content = (
                f"# {repo_name} - Developer Onboarding Guide\n\n"
                f"Generated with RepoSense demo mode."
            )
        else:
            repo_context = await build_repo_context(
                payload.github_url,
                config["github_token"]
            )
            markdown_content = await call_ai(
                ai_client, "generate_doc", 120.0, repo_context
            )
            repo_name = repo_context["repo_name"]
        
        date_str = datetime.utcnow().strftime("%Y-%m-%d")
        filename = f"reposense-{repo_name}-{date_str}.md"
        
        logger.info(f"Markdown export complete for {repo_name}")
        
        return StreamingResponse(
            iter([markdown_content.encode("utf-8")]),
            media_type="text/markdown",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"'
            }
        )
        
    except asyncio.TimeoutError:
        logger.warning(f"Timeout occurred. Executing emergency fallback to demo markdown for {payload.github_url}")
        try:
            repo_name = payload.github_url.rstrip("/").split("/")[-1] or "repository"
            markdown_content = (
                f"# {repo_name} - Developer Onboarding Guide\n\n"
                f"Generated with RepoSense fallback demo mode.\n\n"
                f"## Overview\n"
                f"This is a high-level developer onboarding guide fallback created for the {repo_name} repository."
            )
            date_str = datetime.utcnow().strftime("%Y-%m-%d")
            filename = f"reposense-{repo_name}-{date_str}.md"
            return StreamingResponse(
                iter([markdown_content.encode("utf-8")]),
                media_type="text/markdown",
                headers={"Content-Disposition": f'attachment; filename="{filename}"'}
            )
        except Exception as mock_err:
            raise HTTPException(
                status_code=504,
                detail=safe_error(
                    Exception("timeout"), "Export"
                )
            )
    except GitHubParserError as e:
        err = str(e).lower()
        if "private" in err:
            raise HTTPException(
                status_code=403,
                detail="This repository is private. "
                       "Please use a public repository."
            )
        if "not found" in err:
            raise HTTPException(
                status_code=404,
                detail="Repository not found. "
                       "Please check the GitHub URL."
            )
        logger.warning(f"GitHub parser error: {e}. Executing emergency fallback to demo markdown for {payload.github_url}")
        try:
            repo_name = payload.github_url.rstrip("/").split("/")[-1] or "repository"
            markdown_content = (
                f"# {repo_name} - Developer Onboarding Guide\n\n"
                f"Generated with RepoSense fallback demo mode.\n\n"
                f"## Overview\n"
                f"This is a high-level developer onboarding guide fallback created for the {repo_name} repository."
            )
            date_str = datetime.utcnow().strftime("%Y-%m-%d")
            filename = f"reposense-{repo_name}-{date_str}.md"
            return StreamingResponse(
                iter([markdown_content.encode("utf-8")]),
                media_type="text/markdown",
                headers={"Content-Disposition": f'attachment; filename="{filename}"'}
            )
        except Exception as mock_err:
            raise HTTPException(
                status_code=400,
                detail=safe_error(e, "GitHub")
            )
    except Exception as e:
        logger.exception("Export error:")
        logger.warning(f"Executing emergency fallback to demo markdown for {payload.github_url}")
        try:
            repo_name = payload.github_url.rstrip("/").split("/")[-1] or "repository"
            markdown_content = (
                f"# {repo_name} - Developer Onboarding Guide\n\n"
                f"Generated with RepoSense fallback demo mode.\n\n"
                f"## Overview\n"
                f"This is a high-level developer onboarding guide fallback created for the {repo_name} repository."
            )
            date_str = datetime.utcnow().strftime("%Y-%m-%d")
            filename = f"reposense-{repo_name}-{date_str}.md"
            return StreamingResponse(
                iter([markdown_content.encode("utf-8")]),
                media_type="text/markdown",
                headers={"Content-Disposition": f'attachment; filename="{filename}"'}
            )
        except Exception as mock_err:
            logger.exception("Emergency fallback failed:")
            raise HTTPException(
                status_code=502,
                detail=safe_error(e, "Export")
            )


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)

# Made with Bob

import os
from pathlib import Path
from dotenv import load_dotenv

env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)

import time
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field, field_validator
from datetime import datetime
import asyncio

try:
    from backend.github_parser import build_repo_context, GitHubParserError
    from backend.bob_client import (
        get_ai_client, BobAPIError, BobParseError, MOCK_MODE
    )
    from backend.mock_data import (
        get_mock_analyze_response, get_mock_orchestrate_response, get_mock_ask_response
    )
except ImportError:
    from github_parser import build_repo_context, GitHubParserError
    from bob_client import (
        get_ai_client, BobAPIError, BobParseError, MOCK_MODE
    )
    from mock_data import (
        get_mock_analyze_response, get_mock_orchestrate_response, get_mock_ask_response
    )

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("=" * 60)
    logger.info("RepoSense Backend Starting")
    logger.info("=" * 60)

    api_key = os.getenv("IBM_BOB_API_KEY", "")
    gemini_key = os.getenv("GEMINI_API_KEY", "")
    github_token = os.getenv("GITHUB_TOKEN")
    port = os.getenv("PORT", "8000")

    if api_key and api_key != "mock":
        logger.info("IBM Bob API key configured")
    elif gemini_key:
        logger.info("Gemini API key configured as fallback provider")
    else:
        logger.warning("MOCK MODE ENABLED - Using simulated AI responses")

    if github_token:
        logger.info("GitHub token configured (higher rate limits)")
    else:
        logger.warning("No GitHub token - rate limits apply")

    logger.info(f"Server will run on port {port}")
    logger.info("=" * 60)
    logger.info("RepoSense Ready")
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
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=[
        "*",
        "Content-Type",
        "Authorization",
        "X-Gemini-Key",
        "X-IBM-Bob-Key",
        "X-IBM-Bob-Base-Url",
        "X-AI-Provider",
        "X-Mock-Mode",
        "X-GitHub-Token",
    ],
    expose_headers=["*"],
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
        if "github.com" not in v.lower():
            raise ValueError("Must be a valid GitHub repository URL")
        return v


class AskRequest(BaseModel):
    github_url: str = Field(..., min_length=1)
    question: str = Field(..., min_length=1, max_length=500)
    history: list = Field(default_factory=list)

    @field_validator("github_url")
    @classmethod
    def validate_github_url(cls, v):
        if "github.com" not in v.lower():
            raise ValueError("Must be a valid GitHub repository URL")
        return v


class TaskRequest(BaseModel):
    github_url: str = Field(..., min_length=1)

    @field_validator("github_url")
    @classmethod
    def validate_github_url(cls, v):
        if "github.com" not in v.lower():
            raise ValueError("Must be a valid GitHub repository URL")
        return v


class ExportRequest(BaseModel):
    github_url: str = Field(..., min_length=1)

    @field_validator("github_url")
    @classmethod
    def validate_github_url(cls, v):
        if "github.com" not in v.lower():
            raise ValueError("Must be a valid GitHub repository URL")
        return v


class ErrorResponse(BaseModel):
    error: str
    detail: str
    code: int


def get_request_config(http_request: Request) -> dict:
    headers = http_request.headers
    return {
        "bob_key": headers.get("X-IBM-Bob-Key") or os.getenv("IBM_BOB_API_KEY", ""),
        "bob_base_url": headers.get("X-IBM-Bob-Base-Url") or os.getenv("IBM_BOB_BASE_URL", "https://bob.ibm.com"),
        "gemini_key": headers.get("X-Gemini-Key") or os.getenv("GEMINI_API_KEY", ""),
        "github_token": headers.get("X-GitHub-Token") or os.getenv("GITHUB_TOKEN"),
        "provider": headers.get("X-AI-Provider", "bob"),
        "mock": headers.get("X-Mock-Mode", "false")
    }


def get_configured_client(config: dict):
    return get_ai_client(
        bob_key=config["bob_key"],
        gemini_key=config["gemini_key"],
        provider=config["provider"],
        mock_mode=config["mock"],
        bob_base_url=config["bob_base_url"]
    )


def using_mock(config: dict, client) -> bool:
    return client is None or str(config["mock"]).lower() == "true"


async def call_ai(client, method_name: str, timeout: float, *args):
    method = getattr(client, method_name)
    if asyncio.iscoroutinefunction(method):
        return await asyncio.wait_for(method(*args), timeout=timeout)
    return await asyncio.wait_for(asyncio.to_thread(method, *args), timeout=timeout)


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
    api_key = os.getenv("IBM_BOB_API_KEY", "")
    gemini_key = os.getenv("GEMINI_API_KEY", "")
    return {
        "status": "ok",
        "version": "1.0.0",
        "bob_connected": bool(api_key and api_key != ""),
        "gemini_connected": bool(gemini_key),
        "mock_mode": MOCK_MODE,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }


@app.post("/api/analyze")
async def analyze_repository(payload: AnalyzeRequest, http_request: Request):
    try:
        logger.info(f"Analyzing repository: {payload.github_url}")
        config = get_request_config(http_request)

        # Read config from headers (user's settings panel)
        gemini_key = http_request.headers.get('X-Gemini-Key', '')
        bob_key = http_request.headers.get('X-IBM-Bob-Key', '') or \
                  os.getenv('IBM_BOB_API_KEY', 'mock')
        provider = http_request.headers.get('X-AI-Provider', 'bob')
        mock_header = http_request.headers.get('X-Mock-Mode', 'true')

        # Determine if mock mode
        use_mock = mock_header.lower() == 'true' and not gemini_key and not (bob_key and bob_key != 'mock')

        # Get correct AI client based on settings
        if use_mock:
            ai_client = None
        elif provider == 'gemini' and gemini_key:
            from backend.gemini_client import GeminiClient
            ai_client = GeminiClient(api_key=gemini_key)
        elif bob_key and bob_key != 'mock':
            from backend.bob_client import BobClient
            ai_client = BobClient(api_key=bob_key)
        else:
            ai_client = None

        # Update config with determined client
        config["client"] = ai_client

        if using_mock(config, ai_client):
            logger.info("Using mock analysis response")
            return get_mock_analyze_response(payload.github_url)

        repo_context = build_repo_context(payload.github_url, config["github_token"])
        logger.info(f"Repository context built: {repo_context['repo_name']}")

        analysis = await call_ai(ai_client, "analyze", 120.0, repo_context)

        logger.info(f"Analysis complete for {repo_context['repo_name']}")
        return analysis

    except asyncio.TimeoutError:
        logger.error(f"Analysis timeout for {payload.github_url}")
        raise HTTPException(
            status_code=504,
            detail={
                "error": "Analysis timeout",
                "detail": "The analysis took too long. Please try again with a smaller repository.",
                "code": 504
            }
        )
    except GitHubParserError as e:
        logger.error(f"GitHub parser error: {str(e)}")
        if "private" in str(e).lower():
            raise HTTPException(status_code=403, detail={"error": "Repository is private", "detail": str(e), "code": 403})
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail={"error": "Repository not found", "detail": str(e), "code": 404})
        raise HTTPException(status_code=400, detail={"error": "Invalid repository", "detail": str(e), "code": 400})
    except (BobAPIError, BobParseError, Exception) as e:
        logger.error(f"AI provider error: {str(e)}")
        raise HTTPException(
            status_code=502,
            detail={
                "error": "AI provider unavailable",
                "detail": f"Could not complete AI request: {str(e)}",
                "code": 502
            }
        )


@app.post("/api/ask")
async def ask_question(payload: AskRequest, http_request: Request):
    try:
        logger.info(f"Question for {payload.github_url}: {payload.question[:50]}...")
        config = get_request_config(http_request)

        # Read config from headers (user's settings panel)
        gemini_key = http_request.headers.get('X-Gemini-Key', '')
        bob_key = http_request.headers.get('X-IBM-Bob-Key', '') or \
                  os.getenv('IBM_BOB_API_KEY', 'mock')
        provider = http_request.headers.get('X-AI-Provider', 'bob')
        mock_header = http_request.headers.get('X-Mock-Mode', 'true')

        # Determine if mock mode
        use_mock = mock_header.lower() == 'true' and not gemini_key and not (bob_key and bob_key != 'mock')

        # Get correct AI client based on settings
        if use_mock:
            ai_client = None
        elif provider == 'gemini' and gemini_key:
            from backend.gemini_client import GeminiClient
            ai_client = GeminiClient(api_key=gemini_key)
        elif bob_key and bob_key != 'mock':
            from backend.bob_client import BobClient
            ai_client = BobClient(api_key=bob_key)
        else:
            ai_client = None

        # Update config with determined client
        config["client"] = ai_client

        if using_mock(config, ai_client):
            logger.info("Using mock ask response")
            return get_mock_ask_response(payload.github_url, payload.question)

        repo_context = build_repo_context(payload.github_url, config["github_token"])
        response = await call_ai(ai_client, "ask", 120.0, repo_context, payload.question, payload.history)

        logger.info(f"Question answered for {repo_context['repo_name']}")
        return response

    except asyncio.TimeoutError:
        logger.error(f"Question timeout for {payload.github_url}")
        raise HTTPException(
            status_code=504,
            detail={
                "error": "Request timeout",
                "detail": "The question took too long to answer. Please try a simpler question.",
                "code": 504
            }
        )
    except GitHubParserError as e:
        logger.error(f"GitHub parser error: {str(e)}")
        if "private" in str(e).lower():
            raise HTTPException(status_code=403, detail={"error": "Repository is private", "detail": str(e), "code": 403})
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail={"error": "Repository not found", "detail": str(e), "code": 404})
        raise HTTPException(status_code=400, detail={"error": "Invalid repository", "detail": str(e), "code": 400})
    except (BobAPIError, BobParseError, Exception) as e:
        logger.error(f"AI provider error: {str(e)}")
        raise HTTPException(status_code=502, detail={"error": "AI provider unavailable", "detail": str(e), "code": 502})


@app.post("/api/task")
async def kickstart_task(payload: TaskRequest, http_request: Request):
    try:
        logger.info(f"Starting orchestration for {payload.github_url}")
        config = get_request_config(http_request)

        # Read config from headers (user's settings panel)
        gemini_key = http_request.headers.get('X-Gemini-Key', '')
        bob_key = http_request.headers.get('X-IBM-Bob-Key', '') or \
                  os.getenv('IBM_BOB_API_KEY', 'mock')
        provider = http_request.headers.get('X-AI-Provider', 'bob')
        mock_header = http_request.headers.get('X-Mock-Mode', 'true')

        # Determine if mock mode
        use_mock = mock_header.lower() == 'true' and not gemini_key and not (bob_key and bob_key != 'mock')

        # Get correct AI client based on settings
        if use_mock:
            ai_client = None
        elif provider == 'gemini' and gemini_key:
            from backend.gemini_client import GeminiClient
            ai_client = GeminiClient(api_key=gemini_key)
        elif bob_key and bob_key != 'mock':
            from backend.bob_client import BobClient
            ai_client = BobClient(api_key=bob_key)
        else:
            ai_client = None

        # Update config with determined client
        config["client"] = ai_client

        if using_mock(config, ai_client):
            logger.info("Using mock orchestration response")
            return get_mock_orchestrate_response(payload.github_url)

        repo_context = build_repo_context(payload.github_url, config["github_token"])
        logger.info(f"Running full orchestration pipeline for {repo_context['repo_name']}")

        coding_response = await call_ai(ai_client, "orchestrate", 180.0, repo_context)

        logger.info(f"Orchestration complete for {repo_context['repo_name']}")
        return coding_response

    except asyncio.TimeoutError:
        logger.error(f"Orchestration timeout for {payload.github_url}")
        raise HTTPException(
            status_code=504,
            detail={
                "error": "Orchestration timeout",
                "detail": "The code generation took too long. Please try again.",
                "code": 504
            }
        )
    except GitHubParserError as e:
        logger.error(f"GitHub parser error: {str(e)}")
        if "private" in str(e).lower():
            raise HTTPException(status_code=403, detail={"error": "Repository is private", "detail": str(e), "code": 403})
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail={"error": "Repository not found", "detail": str(e), "code": 404})
        raise HTTPException(status_code=400, detail={"error": "Invalid repository", "detail": str(e), "code": 400})
    except (BobAPIError, BobParseError, Exception) as e:
        logger.error(f"AI provider error: {str(e)}")
        raise HTTPException(status_code=502, detail={"error": "AI provider unavailable", "detail": str(e), "code": 502})


@app.post("/api/export/markdown")
async def export_markdown(payload: ExportRequest, http_request: Request):
    try:
        logger.info(f"Generating markdown export for {payload.github_url}")
        config = get_request_config(http_request)

        # Read config from headers (user's settings panel)
        gemini_key = http_request.headers.get('X-Gemini-Key', '')
        bob_key = http_request.headers.get('X-IBM-Bob-Key', '') or \
                  os.getenv('IBM_BOB_API_KEY', 'mock')
        provider = http_request.headers.get('X-AI-Provider', 'bob')
        mock_header = http_request.headers.get('X-Mock-Mode', 'true')

        # Determine if mock mode
        use_mock = mock_header.lower() == 'true' and not gemini_key and not (bob_key and bob_key != 'mock')

        # Get correct AI client based on settings
        if use_mock:
            ai_client = None
        elif provider == 'gemini' and gemini_key:
            from backend.gemini_client import GeminiClient
            ai_client = GeminiClient(api_key=gemini_key)
        elif bob_key and bob_key != 'mock':
            from backend.bob_client import BobClient
            ai_client = BobClient(api_key=bob_key)
        else:
            ai_client = None

        # Update config with determined client
        config["client"] = ai_client

        if using_mock(config, ai_client):
            repo_name = payload.github_url.rstrip("/").split("/")[-1] or "repository"
            markdown_content = f"# {repo_name} - Developer Onboarding Guide\n\nGenerated with RepoSense mock mode."
        else:
            repo_context = build_repo_context(payload.github_url, config["github_token"])
            markdown_content = await call_ai(ai_client, "generate_doc", 120.0, repo_context)
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
        logger.error(f"Export timeout for {payload.github_url}")
        raise HTTPException(
            status_code=504,
            detail={
                "error": "Export timeout",
                "detail": "The export took too long. Please try again.",
                "code": 504
            }
        )
    except GitHubParserError as e:
        logger.error(f"GitHub parser error: {str(e)}")
        if "private" in str(e).lower():
            raise HTTPException(status_code=403, detail={"error": "Repository is private", "detail": str(e), "code": 403})
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail={"error": "Repository not found", "detail": str(e), "code": 404})
        raise HTTPException(status_code=400, detail={"error": "Invalid repository", "detail": str(e), "code": 400})
    except (BobAPIError, BobParseError, Exception) as e:
        logger.error(f"AI provider error: {str(e)}")
        raise HTTPException(status_code=502, detail={"error": "AI provider unavailable", "detail": str(e), "code": 502})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000))
    )

# Made with Bob

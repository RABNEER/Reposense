import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from the same directory as this file
env_path = Path(__file__).parent / '.env'
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
        analyze, ask, orchestrate, generate_doc,
        BobAPIError, BobParseError, MOCK_MODE
    )
except ImportError:
    from github_parser import build_repo_context, GitHubParserError
    from bob_client import (
        analyze, ask, orchestrate, generate_doc,
        BobAPIError, BobParseError, MOCK_MODE
    )

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("=" * 60)
    logger.info("RepoSense Backend Starting")
    logger.info("=" * 60)
    
    api_key = os.getenv("IBM_BOB_API_KEY", "")
    github_token = os.getenv("GITHUB_TOKEN")
    port = os.getenv("PORT", "8000")
    
    if not api_key:
        logger.error("FATAL: IBM_BOB_API_KEY not set")
        raise RuntimeError("IBM_BOB_API_KEY environment variable is required")
    
    if api_key == "mock":
        logger.warning("⚠️  MOCK MODE ENABLED - Using simulated IBM Bob responses")
    else:
        logger.info("✓ IBM Bob API key configured")
    
    if github_token:
        logger.info("✓ GitHub token configured (higher rate limits)")
    else:
        logger.warning("⚠️  No GitHub token - rate limits apply")
    
    logger.info(f"✓ Server will run on port {port}")
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
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    duration = (time.time() - start_time) * 1000
    logger.info(f"{request.method} {request.url.path} - {response.status_code} - {duration:.0f}ms")
    return response

class AnalyzeRequest(BaseModel):
    github_url: str = Field(..., min_length=1)
    
    @field_validator('github_url')
    @classmethod
    def validate_github_url(cls, v):
        if 'github.com' not in v.lower():
            raise ValueError('Must be a valid GitHub repository URL')
        return v

class AskRequest(BaseModel):
    github_url: str = Field(..., min_length=1)
    question: str = Field(..., min_length=1, max_length=500)
    history: list = Field(default_factory=list)
    
    @field_validator('github_url')
    @classmethod
    def validate_github_url(cls, v):
        if 'github.com' not in v.lower():
            raise ValueError('Must be a valid GitHub repository URL')
        return v

class TaskRequest(BaseModel):
    github_url: str = Field(..., min_length=1)
    
    @field_validator('github_url')
    @classmethod
    def validate_github_url(cls, v):
        if 'github.com' not in v.lower():
            raise ValueError('Must be a valid GitHub repository URL')
        return v

class ExportRequest(BaseModel):
    github_url: str = Field(..., min_length=1)
    
    @field_validator('github_url')
    @classmethod
    def validate_github_url(cls, v):
        if 'github.com' not in v.lower():
            raise ValueError('Must be a valid GitHub repository URL')
        return v

class ErrorResponse(BaseModel):
    error: str
    detail: str
    code: int

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
    return {
        "status": "ok",
        "version": "1.0.0",
        "bob_connected": bool(api_key and api_key != ""),
        "mock_mode": MOCK_MODE,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }

@app.post("/api/analyze")
async def analyze_repository(request: AnalyzeRequest):
    try:
        logger.info(f"Analyzing repository: {request.github_url}")
        
        github_token = os.getenv("GITHUB_TOKEN")
        repo_context = build_repo_context(request.github_url, github_token)
        
        logger.info(f"Repository context built: {repo_context['repo_name']}")
        
        analysis = await asyncio.wait_for(
            asyncio.to_thread(analyze, repo_context),
            timeout=120.0
        )
        
        logger.info(f"Analysis complete for {repo_context['repo_name']}")
        return analysis
        
    except asyncio.TimeoutError:
        logger.error(f"Analysis timeout for {request.github_url}")
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
            raise HTTPException(
                status_code=403,
                detail={
                    "error": "Repository is private",
                    "detail": str(e),
                    "code": 403
                }
            )
        elif "not found" in str(e).lower():
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "Repository not found",
                    "detail": str(e),
                    "code": 404
                }
            )
        else:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "Invalid repository",
                    "detail": str(e),
                    "code": 400
                }
            )
    except (BobAPIError, BobParseError) as e:
        logger.error(f"IBM Bob error: {str(e)}")
        raise HTTPException(
            status_code=502,
            detail={
                "error": "IBM Bob unavailable",
                "detail": f"Could not connect to IBM Bob: {str(e)}",
                "code": 502
            }
        )
    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail={
                "error": "Invalid request",
                "detail": str(e),
                "code": 400
            }
        )

@app.post("/api/ask")
async def ask_question(request: AskRequest):
    try:
        logger.info(f"Question for {request.github_url}: {request.question[:50]}...")
        
        github_token = os.getenv("GITHUB_TOKEN")
        repo_context = build_repo_context(request.github_url, github_token)
        
        response = await asyncio.wait_for(
            asyncio.to_thread(ask, repo_context, request.question, request.history),
            timeout=120.0
        )
        
        logger.info(f"Question answered for {repo_context['repo_name']}")
        return response
        
    except asyncio.TimeoutError:
        logger.error(f"Question timeout for {request.github_url}")
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
        elif "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail={"error": "Repository not found", "detail": str(e), "code": 404})
        else:
            raise HTTPException(status_code=400, detail={"error": "Invalid repository", "detail": str(e), "code": 400})
    except (BobAPIError, BobParseError) as e:
        logger.error(f"IBM Bob error: {str(e)}")
        raise HTTPException(status_code=502, detail={"error": "IBM Bob unavailable", "detail": str(e), "code": 502})

@app.post("/api/task")
async def kickstart_task(request: TaskRequest):
    try:
        logger.info(f"Starting orchestration for {request.github_url}")
        
        github_token = os.getenv("GITHUB_TOKEN")
        repo_context = build_repo_context(request.github_url, github_token)
        
        logger.info(f"Running full orchestration pipeline for {repo_context['repo_name']}")
        
        coding_response = await asyncio.wait_for(
            asyncio.to_thread(orchestrate, repo_context),
            timeout=180.0
        )
        
        logger.info(f"Orchestration complete for {repo_context['repo_name']}")
        return coding_response
        
    except asyncio.TimeoutError:
        logger.error(f"Orchestration timeout for {request.github_url}")
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
        elif "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail={"error": "Repository not found", "detail": str(e), "code": 404})
        else:
            raise HTTPException(status_code=400, detail={"error": "Invalid repository", "detail": str(e), "code": 400})
    except (BobAPIError, BobParseError) as e:
        logger.error(f"IBM Bob error: {str(e)}")
        raise HTTPException(status_code=502, detail={"error": "IBM Bob unavailable", "detail": str(e), "code": 502})

@app.post("/api/export/markdown")
async def export_markdown(request: ExportRequest):
    try:
        logger.info(f"Generating markdown export for {request.github_url}")
        
        github_token = os.getenv("GITHUB_TOKEN")
        repo_context = build_repo_context(request.github_url, github_token)
        
        markdown_content = await asyncio.wait_for(
            asyncio.to_thread(generate_doc, repo_context),
            timeout=120.0
        )
        
        repo_name = repo_context['repo_name']
        date_str = datetime.utcnow().strftime('%Y-%m-%d')
        filename = f"reposense-{repo_name}-{date_str}.md"
        
        logger.info(f"Markdown export complete for {repo_name}")
        
        return StreamingResponse(
            iter([markdown_content.encode('utf-8')]),
            media_type="text/markdown",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"'
            }
        )
        
    except asyncio.TimeoutError:
        logger.error(f"Export timeout for {request.github_url}")
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
        elif "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail={"error": "Repository not found", "detail": str(e), "code": 404})
        else:
            raise HTTPException(status_code=400, detail={"error": "Invalid repository", "detail": str(e), "code": 400})
    except (BobAPIError, BobParseError) as e:
        logger.error(f"IBM Bob error: {str(e)}")
        raise HTTPException(status_code=502, detail={"error": "IBM Bob unavailable", "detail": str(e), "code": 502})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000))
    )

# Made with Bob

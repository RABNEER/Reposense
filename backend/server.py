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
        BobAPIError, BobParseError, MOCK_MODE, get_ai_client
    )
except ImportError:
    from github_parser import build_repo_context, GitHubParserError
    from bob_client import (
        analyze, ask, orchestrate, generate_doc,
        BobAPIError, BobParseError, MOCK_MODE, get_ai_client
    )

logging.basicConfig(level=logging.INFO)
# Set logging to a file as well for production debugging
log_file = Path(__file__).parent / 'server.log'
file_handler = logging.FileHandler(log_file)
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logging.getLogger().addHandler(file_handler)

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
    
    if not api_key and not gemini_key:
        logger.warning("⚠️  No API keys set - running in strict MOCK MODE")
    
    if api_key == "mock":
        logger.warning("⚠️  IBM Bob set to MOCK MODE")
    elif api_key:
        logger.info("✓ IBM Bob API key detected")
        
    if gemini_key:
        logger.info("✓ Gemini API key detected (Fallback/Alternative enabled)")
    
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
    description="AI-powered repository onboarding with IBM Bob & Gemini",
    version="1.1.0",
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

@app.get("/api/health")
async def health_check():
    api_key = os.getenv("IBM_BOB_API_KEY", "")
    gemini_key = os.getenv("GEMINI_API_KEY", "")
    return {
        "status": "ok",
        "version": "1.1.0",
        "bob_enabled": bool(api_key and api_key != "mock"),
        "gemini_enabled": bool(gemini_key),
        "mock_mode": MOCK_MODE,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }

@app.post("/api/analyze")
async def analyze_repository(request: Request, body: AnalyzeRequest):
    try:
        logger.info(f"Analyzing repository: {body.github_url}")
        
        # Check for custom GitHub token in header
        github_token = request.headers.get('X-GitHub-Token') or os.getenv("GITHUB_TOKEN")
        repo_context = build_repo_context(body.github_url, github_token)
        
        # Get appropriate AI client based on headers/env
        client = get_ai_client(request.headers)
        
        if client:
            logger.info(f"Using {client.__class__.__name__} for analysis")
            analysis = await client.analyze(repo_context)
        else:
            logger.info("Using mock mode for analysis")
            analysis = await asyncio.to_thread(analyze, repo_context)
            
        return analysis
        
    except Exception as e:
        logger.error(f"Analysis failed: {str(e)}")
        if isinstance(e, GitHubParserError):
            raise HTTPException(status_code=400, detail=str(e))
        if isinstance(e, (BobAPIError, BobParseError)):
            raise HTTPException(status_code=502, detail=f"AI Provider Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/ask")
async def ask_question(request: Request, body: AskRequest):
    try:
        logger.info(f"Question for {body.github_url}: {body.question[:50]}...")
        
        github_token = request.headers.get('X-GitHub-Token') or os.getenv("GITHUB_TOKEN")
        repo_context = build_repo_context(body.github_url, github_token)
        
        client = get_ai_client(request.headers)
        
        if client:
            response = await client.ask(repo_context, body.question, body.history)
        else:
            response = await asyncio.to_thread(ask, repo_context, body.question, body.history)
            
        return response
        
    except Exception as e:
        logger.error(f"Ask failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/task")
async def kickstart_task(request: Request, body: TaskRequest):
    try:
        logger.info(f"Starting orchestration for {body.github_url}")
        
        github_token = request.headers.get('X-GitHub-Token') or os.getenv("GITHUB_TOKEN")
        repo_context = build_repo_context(body.github_url, github_token)
        
        client = get_ai_client(request.headers)
        
        if client:
            logger.info(f"Using {client.__class__.__name__} for orchestration")
            coding_response = await client.orchestrate(repo_context)
        else:
            logger.info("Using mock mode for orchestration")
            coding_response = await asyncio.to_thread(orchestrate, repo_context)
            
        return coding_response
        
    except Exception as e:
        logger.error(f"Task orchestration failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/export/markdown")
async def export_markdown(request: Request, body: ExportRequest):
    try:
        logger.info(f"Generating markdown export for {body.github_url}")
        
        github_token = request.headers.get('X-GitHub-Token') or os.getenv("GITHUB_TOKEN")
        repo_context = build_repo_context(body.github_url, github_token)
        
        client = get_ai_client(request.headers)
        
        if client:
            markdown_content = await client.generate_doc(repo_context)
        else:
            markdown_content = await asyncio.to_thread(generate_doc, repo_context)
        
        repo_name = repo_context['repo_name']
        filename = f"reposense-{repo_name}.md"
        
        return StreamingResponse(
            iter([markdown_content.encode('utf-8')]),
            media_type="text/markdown",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'}
        )
        
    except Exception as e:
        logger.error(f"Export failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000))
    )

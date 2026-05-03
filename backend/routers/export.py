"""
Export Endpoints
POST /api/v1/export/markdown - Export onboarding doc as Markdown
POST /api/v1/export/json - Export analysis as JSON
"""
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import PlainTextResponse, JSONResponse
import structlog

from backend.models.schemas import ExportRequest, ExportResponse
from backend.services.github_parser import fetch_repo_context, GitHubError
from backend.services.bob_client import get_bob_client, BobClientError
from backend.services.prompt_engine import build_analysis_prompt, build_doc_prompt

logger = structlog.get_logger()
router = APIRouter(prefix="/api/v1/export", tags=["export"])


@router.post("/markdown", response_class=PlainTextResponse, status_code=status.HTTP_200_OK)
async def export_markdown(request: ExportRequest) -> str:
    """
    Export onboarding documentation as Markdown
    
    This endpoint:
    1. Fetches repository context from GitHub API
    2. Analyzes repository with IBM Bob (Plan mode)
    3. Generates comprehensive Markdown documentation (Plan mode)
    4. Returns raw Markdown text
    
    Args:
        request: ExportRequest with github_url
        
    Returns:
        Raw Markdown documentation string
        
    Raises:
        HTTPException: 400 for invalid URL, 404 for not found, 500 for server errors
    """
    logger.info("export_markdown_request", github_url=request.github_url)
    
    try:
        # Step 1: Fetch repository context
        logger.info("fetching_repo_context", url=request.github_url)
        repo_context = await fetch_repo_context(request.github_url)
        
        # Step 2: Analyze repository
        logger.info("analyzing_repository", mode="plan")
        bob_client = get_bob_client()
        analysis_prompt = build_analysis_prompt(repo_context)
        analysis = await bob_client.analyze_repository(analysis_prompt)
        
        # Step 3: Generate documentation
        logger.info("generating_documentation", mode="plan")
        doc_prompt = build_doc_prompt(repo_context, analysis)
        markdown_doc = await bob_client.generate_documentation(doc_prompt)
        
        logger.info(
            "markdown_generated",
            doc_length=len(markdown_doc),
            project_name=analysis.get("project_name")
        )
        
        return markdown_doc
    
    except GitHubError as e:
        logger.error("github_error", error=str(e), url=request.github_url)
        
        if "not found" in str(e).lower() or "404" in str(e):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Repository not found: {request.github_url}"
            )
        elif "rate limit" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="GitHub API rate limit exceeded. Please try again later."
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"GitHub API error: {str(e)}"
            )
    
    except BobClientError as e:
        logger.error("bob_client_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"IBM Bob API error: {str(e)}"
        )
    
    except Exception as e:
        logger.error("unexpected_error", error=str(e), error_type=type(e).__name__)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.post("/json", response_model=ExportResponse, status_code=status.HTTP_200_OK)
async def export_json(request: ExportRequest) -> ExportResponse:
    """
    Export analysis data as structured JSON
    
    This endpoint:
    1. Fetches repository context from GitHub API
    2. Analyzes repository with IBM Bob (Plan mode)
    3. Returns structured JSON with all analysis data
    
    Args:
        request: ExportRequest with github_url
        
    Returns:
        ExportResponse with complete analysis data
        
    Raises:
        HTTPException: 400 for invalid URL, 404 for not found, 500 for server errors
    """
    logger.info("export_json_request", github_url=request.github_url)
    
    try:
        # Step 1: Fetch repository context
        logger.info("fetching_repo_context", url=request.github_url)
        repo_context = await fetch_repo_context(request.github_url)
        
        # Step 2: Analyze repository
        logger.info("analyzing_repository", mode="plan")
        bob_client = get_bob_client()
        analysis_prompt = build_analysis_prompt(repo_context)
        analysis = await bob_client.analyze_repository(analysis_prompt)
        
        logger.info(
            "json_export_complete",
            project_name=analysis.get("project_name"),
            data_size=len(str(analysis))
        )
        
        # Step 3: Return structured response
        return ExportResponse(
            success=True,
            format="json",
            content=analysis,
            filename=f"{analysis.get('project_name', 'repository').replace(' ', '_')}_analysis.json",
            bob_modes_used=["Plan"]
        )
    
    except GitHubError as e:
        logger.error("github_error", error=str(e), url=request.github_url)
        
        if "not found" in str(e).lower() or "404" in str(e):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Repository not found: {request.github_url}"
            )
        elif "rate limit" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="GitHub API rate limit exceeded. Please try again later."
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"GitHub API error: {str(e)}"
            )
    
    except BobClientError as e:
        logger.error("bob_client_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"IBM Bob API error: {str(e)}"
        )
    
    except Exception as e:
        logger.error("unexpected_error", error=str(e), error_type=type(e).__name__)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )

# Made with Bob

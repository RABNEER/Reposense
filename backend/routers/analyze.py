"""
Repository Analysis Endpoint
POST /api/v1/analyze - Analyze a GitHub repository
"""
from fastapi import APIRouter, HTTPException, status
import structlog

from backend.models.schemas import AnalyzeRequest, AnalysisResponse
from backend.services.github_parser import fetch_repo_context, GitHubError
from backend.services.bob_client import get_bob_client, BobClientError
from backend.services.prompt_engine import build_analysis_prompt

logger = structlog.get_logger()
router = APIRouter(prefix="/api/v1", tags=["analysis"])


@router.post("/analyze", response_model=AnalysisResponse, status_code=status.HTTP_200_OK)
async def analyze_repository(request: AnalyzeRequest) -> AnalysisResponse:
    """
    Analyze a GitHub repository and generate onboarding report
    
    This endpoint:
    1. Fetches repository context from GitHub API
    2. Sends context to IBM Bob for analysis (Plan mode)
    3. Returns structured onboarding report
    
    Args:
        request: AnalyzeRequest with github_url
        
    Returns:
        AnalysisResponse with complete onboarding data
        
    Raises:
        HTTPException: 400 for invalid URL, 404 for not found, 500 for server errors
    """
    logger.info("analyze_request", github_url=request.github_url)
    
    try:
        # Step 1: Fetch repository context from GitHub
        logger.info("fetching_repo_context", url=request.github_url)
        repo_context = await fetch_repo_context(request.github_url)
        
        logger.info(
            "repo_context_fetched",
            repo_name=repo_context.get("metadata", {}).get("full_name"),
            file_count=repo_context.get("file_count", 0),
            key_files_count=len(repo_context.get("key_files", {}))
        )
        
        # Step 2: Build analysis prompt
        prompt = build_analysis_prompt(repo_context)
        
        # Step 3: Send to IBM Bob for analysis
        logger.info("calling_bob_api", mode="plan")
        bob_client = get_bob_client()
        analysis_result = await bob_client.analyze_repository(prompt)
        
        logger.info(
            "analysis_complete",
            project_name=analysis_result.get("project_name"),
            tech_stack_count=len(analysis_result.get("tech_stack", [])),
            key_files_count=len(analysis_result.get("key_files", []))
        )
        
        # Step 4: Return structured response
        return AnalysisResponse(
            success=True,
            project_name=analysis_result.get("project_name", "Unknown Project"),
            one_line_summary=analysis_result.get("one_line_summary", ""),
            what_it_does=analysis_result.get("what_it_does", ""),
            tech_stack=analysis_result.get("tech_stack", []),
            architecture_type=analysis_result.get("architecture_type", "Unknown"),
            architecture_overview=analysis_result.get("architecture_overview", ""),
            folder_structure=analysis_result.get("folder_structure", []),
            key_files=analysis_result.get("key_files", []),
            data_flow=analysis_result.get("data_flow", []),
            onboarding_steps=analysis_result.get("onboarding_steps", []),
            quick_wins=analysis_result.get("quick_wins", []),
            gotchas=analysis_result.get("gotchas", []),
            estimated_onboarding_minutes=analysis_result.get("estimated_onboarding_minutes", 30),
            bob_modes_used=analysis_result.get("bob_modes_used", ["Plan"]),
            repo_metadata={
                "full_name": repo_context.get("metadata", {}).get("full_name"),
                "description": repo_context.get("metadata", {}).get("description"),
                "stars": repo_context.get("metadata", {}).get("stars"),
                "language": repo_context.get("metadata", {}).get("language"),
                "url": request.github_url
            }
        )
    
    except GitHubError as e:
        logger.error("github_error", error=str(e), url=request.github_url)
        
        if "not found" in str(e).lower() or "404" in str(e):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Repository not found or is private: {request.github_url}"
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

"""
Task Kickstarter Endpoint
POST /api/v1/task - Get guidance on where to start for a coding task
"""
from fastapi import APIRouter, HTTPException, status
import structlog

from backend.models.schemas import TaskRequest, CodingResponse
from backend.services.github_parser import fetch_repo_context, GitHubError
from backend.services.bob_client import get_bob_client, BobClientError
from backend.services.prompt_engine import (
    build_issue_prompt,
    build_plan_prompt,
    build_code_prompt,
    build_explain_prompt
)

logger = structlog.get_logger()
router = APIRouter(prefix="/api/v1", tags=["task"])


@router.post("/task", response_model=CodingResponse, status_code=status.HTTP_200_OK)
async def kickstart_task(request: TaskRequest) -> CodingResponse:
    """
    Get guidance on where to start for a coding task
    
    This endpoint orchestrates multiple Bob modes:
    1. Fetches repository context from GitHub API
    2. If no task provided, finds a beginner-friendly issue (Ask mode)
    3. Creates implementation plan (Plan mode)
    4. Generates code changes (Code mode)
    5. Explains changes to junior developer (Ask mode)
    
    Args:
        request: TaskRequest with github_url and optional task_description
        
    Returns:
        CodingResponse with issue, plan, code changes, and explanation
        
    Raises:
        HTTPException: 400 for invalid input, 404 for not found, 500 for server errors
    """
    logger.info(
        "task_request",
        github_url=request.github_url,
        has_task=bool(request.task_description)
    )
    
    try:
        # Step 1: Fetch repository context
        logger.info("fetching_repo_context", url=request.github_url)
        repo_context = await fetch_repo_context(request.github_url)
        
        bob_client = get_bob_client()
        bob_modes_used = []
        
        # Step 2: Find or use provided task
        if request.task_description:
            # User provided a task - create a custom issue
            logger.info("using_provided_task", task=request.task_description[:100])
            issue = {
                "title": request.task_description,
                "why_it_matters": "User-requested task",
                "files_involved": [],
                "approach": "To be determined",
                "estimated_lines": 0,
                "complexity": "unknown",
                "impact": "unknown"
            }
        else:
            # Find a beginner-friendly issue
            logger.info("finding_issue", mode="ask")
            issue_prompt = build_issue_prompt(repo_context)
            issue = await bob_client.answer_question(issue_prompt)
            bob_modes_used.append("Ask")
            logger.info("issue_found", title=issue.get("title"))
        
        # Step 3: Create implementation plan
        logger.info("creating_plan", mode="plan")
        plan_prompt = build_plan_prompt(repo_context, issue)
        plan = await bob_client.analyze_repository(plan_prompt)
        bob_modes_used.append("Plan")
        logger.info("plan_created", steps=len(plan.get("steps", [])))
        
        # Step 4: Generate code changes
        logger.info("generating_code", mode="code")
        code_prompt = build_code_prompt(repo_context, issue, plan)
        code_result = await bob_client.generate_code(code_prompt)
        bob_modes_used.append("Code")
        logger.info("code_generated", changes=len(code_result.get("changes", [])))
        
        # Step 5: Explain to junior developer
        logger.info("generating_explanation", mode="ask")
        explain_prompt = build_explain_prompt(code_result.get("changes", []))
        explanation = await bob_client.answer_question(explain_prompt)
        bob_modes_used.append("Ask")
        
        # Step 6: Return comprehensive response
        return CodingResponse(
            success=True,
            issue_title=issue.get("title", "Unknown Task"),
            issue_description=issue.get("why_it_matters", ""),
            files_involved=issue.get("files_involved", []),
            complexity=issue.get("complexity", "unknown"),
            impact=issue.get("impact", "unknown"),
            implementation_steps=plan.get("steps", []),
            files_to_modify=plan.get("files_to_modify", []),
            files_to_create=plan.get("files_to_create", []),
            risks=plan.get("risks", []),
            testing_approach=plan.get("testing_approach", ""),
            code_changes=code_result.get("changes", []),
            summary=explanation.get("summary", ""),
            how_it_works=explanation.get("how_it_works", ""),
            why_this_approach=explanation.get("why_this_approach", ""),
            how_to_test=explanation.get("how_to_test", ""),
            bob_modes_used=bob_modes_used
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

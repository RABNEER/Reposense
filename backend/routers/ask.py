"""
Q&A Endpoint
POST /api/v1/ask - Ask questions about a repository
"""
from fastapi import APIRouter, HTTPException, status
import structlog

from backend.models.schemas import AskRequest, QAResponse
from backend.services.github_parser import fetch_repo_context, GitHubError
from backend.services.bob_client import get_bob_client, BobClientError
from backend.services.prompt_engine import build_qa_prompt

logger = structlog.get_logger()
router = APIRouter(prefix="/api/v1", tags=["qa"])


@router.post("/ask", response_model=QAResponse, status_code=status.HTTP_200_OK)
async def ask_question(request: AskRequest) -> QAResponse:
    """
    Ask a question about a GitHub repository
    
    This endpoint:
    1. Fetches repository context from GitHub API (cached if recent)
    2. Builds Q&A prompt with question and chat history
    3. Sends to IBM Bob for answer (Ask mode)
    4. Returns answer with file references
    
    Args:
        request: AskRequest with github_url, question, and optional chat_history
        
    Returns:
        QAResponse with answer and file references
        
    Raises:
        HTTPException: 400 for invalid input, 404 for not found, 500 for server errors
    """
    logger.info(
        "ask_request",
        github_url=request.github_url,
        question=request.question[:100],
        history_length=len(request.chat_history) if request.chat_history else 0
    )
    
    try:
        # Step 1: Fetch repository context
        logger.info("fetching_repo_context", url=request.github_url)
        repo_context = await fetch_repo_context(request.github_url)
        
        # Step 2: Build Q&A prompt with chat history
        prompt = build_qa_prompt(
            repo_context,
            request.question,
            request.chat_history or []
        )
        
        # Step 3: Send to IBM Bob
        logger.info("calling_bob_api", mode="ask", question=request.question[:50])
        bob_client = get_bob_client()
        qa_result = await bob_client.answer_question(prompt)
        
        logger.info(
            "qa_complete",
            answer_length=len(qa_result.get("answer", "")),
            files_referenced=len(qa_result.get("files_referenced", []))
        )
        
        # Step 4: Return response
        return QAResponse(
            success=True,
            answer=qa_result.get("answer", "I couldn't find an answer to that question."),
            files_referenced=qa_result.get("files_referenced", []),
            code_snippets=qa_result.get("code_snippets", []),
            bob_modes_used=["Ask"]
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

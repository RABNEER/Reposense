"""
Pydantic models for request/response validation
"""
from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, Literal
from datetime import datetime


# ============================================================================
# REQUEST MODELS
# ============================================================================

class AnalyzeRequest(BaseModel):
    """Request to analyze a GitHub repository"""
    github_url: str = Field(..., description="GitHub repository URL")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "github_url": "https://github.com/expressjs/express"
            }
        }
    }


class ChatMessage(BaseModel):
    """Single chat message"""
    role: Literal["user", "bob"] = Field(..., description="Message sender")
    content: str = Field(..., description="Message content")
    timestamp: Optional[datetime] = None


class AskRequest(BaseModel):
    """Request to ask a question about a repository"""
    github_url: str = Field(..., description="GitHub repository URL")
    question: str = Field(..., min_length=1, description="Question to ask")
    history: list[ChatMessage] = Field(default_factory=list, description="Chat history")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "github_url": "https://github.com/expressjs/express",
                "question": "How does routing work?",
                "history": []
            }
        }
    }


class TaskRequest(BaseModel):
    """Request to kickstart a task"""
    github_url: str = Field(..., description="GitHub repository URL")
    task_description: Optional[str] = Field(None, description="Optional task description")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "github_url": "https://github.com/expressjs/express",
                "task_description": "Add request timeout middleware"
            }
        }
    }


class ExportRequest(BaseModel):
    """Request to export documentation"""
    github_url: str = Field(..., description="GitHub repository URL")
    format: Literal["markdown", "pdf"] = Field("markdown", description="Export format")


# ============================================================================
# RESPONSE SUB-MODELS
# ============================================================================

class TechBadge(BaseModel):
    """Technology badge"""
    name: str = Field(..., description="Technology name")
    color: str = Field(..., description="Badge color (hex)")
    category: str = Field(..., description="Technology category")


class FolderItem(BaseModel):
    """Folder structure item"""
    path: str = Field(..., description="Folder path")
    purpose: str = Field(..., description="Folder purpose")
    importance: Literal["critical", "important", "reference"] = Field(..., description="Importance level")


class KeyFile(BaseModel):
    """Key file to read"""
    path: str = Field(..., description="File path")
    why_important: str = Field(..., description="Why this file is important")
    read_order: int = Field(..., description="Reading order (1-based)")
    importance: Literal["critical", "important", "reference"] = Field("important", description="Importance level")


class DataFlowStep(BaseModel):
    """Data flow step"""
    step: int = Field(..., description="Step number")
    description: str = Field(..., description="Step description")


class OnboardingStep(BaseModel):
    """Onboarding step"""
    step: int = Field(..., description="Step number")
    action: str = Field(..., description="Action to take")
    why: str = Field(..., description="Why this step matters")
    code_ref: Optional[str] = Field(None, description="Code reference")


class QuickWin(BaseModel):
    """Quick win opportunity"""
    title: str = Field(..., description="Issue title")
    description: str = Field(..., description="Issue description")
    files: list[str] = Field(..., description="Files involved")
    complexity: Literal["simple", "moderate", "complex"] = Field(..., description="Complexity level")
    impact: Literal["low", "medium", "high"] = Field(..., description="Impact level")


class DiffLine(BaseModel):
    """Single line in a code diff"""
    type: Literal["add", "remove", "context"] = Field(..., description="Line type")
    content: str = Field(..., description="Line content")
    line_num: Optional[int] = Field(None, description="Line number")


class CodeChange(BaseModel):
    """Code change for a file"""
    file: str = Field(..., description="File path")
    change_type: Literal["create", "modify", "delete"] = Field(..., description="Change type")
    diff_lines: list[DiffLine] = Field(..., description="Diff lines")
    explanation: str = Field(..., description="Explanation of changes")


class CodeSnippet(BaseModel):
    """Code snippet reference"""
    file: str = Field(..., description="File path")
    code: str = Field(..., description="Code snippet")
    line_start: Optional[int] = None
    line_end: Optional[int] = None


# ============================================================================
# MAIN RESPONSE MODELS
# ============================================================================

class AnalysisResponse(BaseModel):
    """Complete repository analysis response"""
    success: bool = True
    
    # Project metadata
    project_name: str = Field(..., description="Project name")
    one_line_summary: str = Field(..., description="One-line project summary")
    what_it_does: str = Field(..., description="Detailed project description")
    
    # Technical details
    tech_stack: list[TechBadge] = Field(..., description="Technology stack")
    architecture_type: str = Field(..., description="Architecture type (e.g., MVC, microservices)")
    architecture_overview: str = Field(..., description="Architecture overview")
    
    # Structure
    folder_structure: list[FolderItem] = Field(..., description="Key folders")
    key_files: list[KeyFile] = Field(..., description="Key files to read")
    
    # Flow and steps
    data_flow: list[DataFlowStep] = Field(..., description="Data flow steps")
    onboarding_steps: list[OnboardingStep] = Field(..., description="Onboarding steps")
    
    # Opportunities and warnings
    quick_wins: list[QuickWin] = Field(default_factory=list, description="Quick win opportunities")
    gotchas: list[str] = Field(default_factory=list, description="Important gotchas")
    
    # Metadata
    estimated_onboarding_minutes: int = Field(..., description="Estimated onboarding time")
    bob_modes_used: list[str] = Field(..., description="Bob modes used for analysis")
    
    # Repository info
    repo_info: dict = Field(default_factory=dict, description="Repository metadata")


class CodingResponse(BaseModel):
    """Complete coding task response"""
    success: bool = True
    
    # Issue details
    issue_title: str = Field(..., description="Issue title")
    issue_description: str = Field(..., description="Issue description")
    issue_files: list[str] = Field(..., description="Files involved")
    complexity: Literal["simple", "moderate", "complex"] = Field(..., description="Complexity")
    impact: Literal["low", "medium", "high"] = Field(..., description="Impact level")
    
    # Implementation
    implementation_plan: list[str] = Field(..., description="Implementation steps")
    code_changes: list[CodeChange] = Field(..., description="Code changes")
    
    # PR details
    pr_title: str = Field(..., description="PR title")
    pr_description: str = Field(..., description="PR description")
    
    # Explanation
    junior_explanation: str = Field(..., description="Junior-friendly explanation")
    
    # Metadata
    bob_modes_used: list[str] = Field(..., description="Bob modes used")


class QAResponse(BaseModel):
    """Q&A response"""
    success: bool = True
    answer: str = Field(..., description="Answer to the question")
    files_referenced: list[str] = Field(default_factory=list, description="Files referenced")
    code_snippets: list[CodeSnippet] = Field(default_factory=list, description="Code snippets")


class ExportResponse(BaseModel):
    """Export response"""
    success: bool = True
    content: str = Field(..., description="Exported content")
    filename: str = Field(..., description="Suggested filename")
    format: str = Field(..., description="Export format")


class HealthResponse(BaseModel):
    """Health check response"""
    status: str = Field(..., description="Service status")
    version: str = Field(..., description="API version")
    bob_connected: bool = Field(..., description="IBM Bob connection status")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Current timestamp")


class ErrorResponse(BaseModel):
    """Error response"""
    success: bool = False
    error: str = Field(..., description="Error message")
    detail: str = Field(..., description="Error details")
    code: int = Field(..., description="Error code")

# Made with Bob

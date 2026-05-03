"""
Prompt Engineering for IBM Bob
Constructs specialized prompts for different Bob modes
"""
from typing import Optional


SYSTEM_PROMPT = """You are a senior software engineer and architect with deep expertise across all major programming languages, frameworks, and architectural patterns. You excel at:

- Quickly understanding codebases from structure and key files
- Identifying architectural patterns and data flow
- Explaining technical concepts clearly to developers of all levels
- Finding beginner-friendly contribution opportunities
- Writing production-quality code that follows project conventions
- Providing actionable, specific guidance with file references

You are helping developers onboard to new codebases efficiently."""


def format_repo_context(repo_data: dict) -> str:
    """
    Format repository data into readable context string
    
    Args:
        repo_data: Repository context dictionary
        
    Returns:
        Formatted string representation
    """
    metadata = repo_data.get("metadata", {})
    key_files = repo_data.get("key_files", {})
    
    context = f"""
Repository: {metadata.get('full_name', 'Unknown')}
Description: {metadata.get('description', 'No description')}
Primary Language: {metadata.get('language', 'Unknown')}
Stars: {metadata.get('stars', 0):,}
License: {metadata.get('license') or 'None'}
Topics: {', '.join(metadata.get('topics', [])[:10])}

Total Files: {repo_data.get('file_count', 0):,}

Directory Structure (key directories):
{chr(10).join(f"  {d}" for d in repo_data.get('directory_structure', [])[:30])}

Key Files Analyzed ({len(key_files)} files):
"""
    
    for path, content in key_files.items():
        context += f"\n{'='*60}\nFile: {path}\n{'='*60}\n"
        # Truncate very long files
        if len(content) > 3000:
            context += content[:3000] + "\n... (truncated for context)\n"
        else:
            context += content + "\n"
    
    return context


def build_analysis_prompt(repo_context: dict) -> str:
    """
    Build prompt for repository analysis (Plan Mode)
    
    Returns structured JSON with complete onboarding guide
    """
    context = format_repo_context(repo_context)
    
    return f"""{SYSTEM_PROMPT}

{context}

Analyze this repository and provide a comprehensive onboarding guide. Return ONLY valid JSON (no markdown fences) with this exact structure:

{{
  "project_name": "string",
  "one_line_summary": "string (max 100 chars)",
  "what_it_does": "string (2-3 sentences explaining purpose and value)",
  "tech_stack": [
    {{"name": "JavaScript", "color": "#f5a623", "category": "language"}},
    {{"name": "Node.js", "color": "#22c98a", "category": "runtime"}}
  ],
  "architecture_type": "string (e.g., MVC, microservices, monolith)",
  "architecture_overview": "string (2-3 paragraphs explaining system design)",
  "folder_structure": [
    {{"path": "src/", "purpose": "Main source code", "importance": "critical"}},
    {{"path": "tests/", "purpose": "Test files", "importance": "important"}}
  ],
  "key_files": [
    {{
      "path": "src/index.js",
      "why_important": "Application entry point",
      "read_order": 1,
      "importance": "critical"
    }}
  ],
  "data_flow": [
    {{"step": 1, "description": "User request arrives at server"}},
    {{"step": 2, "description": "Router matches request to handler"}}
  ],
  "onboarding_steps": [
    {{
      "step": 1,
      "action": "Clone repository and install dependencies",
      "why": "Sets up local development environment",
      "code_ref": "npm install"
    }}
  ],
  "quick_wins": [
    {{
      "title": "Add input validation",
      "description": "Add validation to user input endpoint",
      "files": ["src/api/users.js"],
      "complexity": "simple",
      "impact": "medium"
    }}
  ],
  "gotchas": [
    "Environment variables must be set before running",
    "Database migrations run automatically on startup"
  ],
  "estimated_onboarding_minutes": 45,
  "bob_modes_used": ["Plan"]
}}

Important:
- Use ONLY real file paths from the repository
- Be specific and actionable
- Order key_files by reading priority (1 = read first)
- Include 3-5 folder_structure items
- Include 4-6 key_files
- Include 4-6 data_flow steps
- Include 4 onboarding_steps
- Include 1-3 quick_wins
- Include 2-4 gotchas
- Tech stack colors: JS/TS=#f5a623, Python=#3776ab, Node=#22c98a, Go=#00add8, Rust=#ce422b, CSS=#264de4
"""


def build_issue_prompt(repo_context: dict) -> str:
    """
    Build prompt to find a beginner-friendly issue (Ask Mode)
    """
    context = format_repo_context(repo_context)
    
    return f"""{SYSTEM_PROMPT}

{context}

Find ONE beginner-friendly but meaningful contribution opportunity in this codebase. Return ONLY valid JSON:

{{
  "title": "string (clear, specific issue title)",
  "why_it_matters": "string (why this improvement is valuable)",
  "files_involved": ["array of file paths"],
  "approach": "string (high-level approach to solve it)",
  "estimated_lines": 20,
  "complexity": "simple|moderate|complex",
  "impact": "low|medium|high"
}}

Look for:
- Missing input validation
- Missing error handling
- Code that could be more modular
- Missing tests for existing features
- Documentation improvements
- Performance optimizations

Choose something a junior developer could tackle but that adds real value."""


def build_plan_prompt(repo_context: dict, issue: dict) -> str:
    """
    Build prompt to create implementation plan (Plan Mode)
    """
    context = format_repo_context(repo_context)
    
    return f"""{SYSTEM_PROMPT}

{context}

Issue to implement:
Title: {issue.get('title')}
Description: {issue.get('why_it_matters')}
Files: {', '.join(issue.get('files_involved', []))}

Create a detailed implementation plan. Return ONLY valid JSON:

{{
  "steps": [
    "Step 1: Read existing validation patterns in src/validators.js",
    "Step 2: Create new validation function following the pattern",
    "Step 3: Import and apply validation to the endpoint"
  ],
  "files_to_modify": ["src/api/users.js", "src/validators.js"],
  "files_to_create": [],
  "risks": [
    "Breaking existing API contracts",
    "Missing edge cases in validation"
  ],
  "testing_approach": "Add unit tests for validation function, integration test for endpoint"
}}

Be specific about:
- Exact files to modify
- Order of implementation steps
- Potential risks
- How to test the changes"""


def build_code_prompt(repo_context: dict, issue: dict, plan: dict) -> str:
    """
    Build prompt to generate code (Code Mode)
    """
    context = format_repo_context(repo_context)
    
    return f"""{SYSTEM_PROMPT}

{context}

Issue: {issue.get('title')}
Plan: {chr(10).join(f"{i+1}. {step}" for i, step in enumerate(plan.get('steps', [])))}

Generate production-quality code changes. Return ONLY valid JSON:

{{
  "changes": [
    {{
      "file": "src/api/users.js",
      "change_type": "modify",
      "diff_lines": [
        {{"type": "context", "content": "const express = require('express');", "line_num": 1}},
        {{"type": "add", "content": "const {{ validateUser }} = require('../validators');", "line_num": 2}},
        {{"type": "context", "content": "", "line_num": 3}},
        {{"type": "context", "content": "router.post('/users', async (req, res) => {{", "line_num": 10}},
        {{"type": "add", "content": "  const validation = validateUser(req.body);", "line_num": 11}},
        {{"type": "add", "content": "  if (!validation.valid) {{", "line_num": 12}},
        {{"type": "add", "content": "    return res.status(400).json({{ error: validation.error }});", "line_num": 13}},
        {{"type": "add", "content": "  }}", "line_num": 14}}
      ],
      "explanation": "Added validation before processing user creation"
    }}
  ]
}}

Requirements:
- Follow existing code style and patterns
- Include proper error handling
- Add comments for complex logic
- Use existing utilities/helpers where possible
- Generate complete, working code"""


def build_explain_prompt(code_changes: list[dict]) -> str:
    """
    Build prompt to explain changes to junior developer (Ask Mode)
    """
    changes_summary = "\n\n".join([
        f"File: {change.get('file')}\nType: {change.get('change_type')}\n{change.get('explanation')}"
        for change in code_changes
    ])
    
    return f"""{SYSTEM_PROMPT}

Code changes made:
{changes_summary}

Explain these changes as if talking to a junior developer who just joined the team. Return ONLY valid JSON:

{{
  "summary": "string (one sentence summary of what changed)",
  "how_it_works": "string (2-3 paragraphs explaining the implementation)",
  "why_this_approach": "string (why we chose this approach over alternatives)",
  "how_to_test": "string (specific steps to test the changes)"
}}

Be friendly, clear, and educational. Assume they understand basic programming but not this specific codebase."""


def build_orchestrator_prompt(repo_context: dict) -> str:
    """
    Build prompt for full orchestration (Orchestrator Mode)
    Combines issue finding, planning, coding, and explanation
    """
    context = format_repo_context(repo_context)
    
    return f"""{SYSTEM_PROMPT}

{context}

Complete the full development workflow: find an issue, plan it, implement it, and explain it.

Return ONLY valid JSON with this structure:

{{
  "issue_title": "string",
  "issue_description": "string",
  "issue_files": ["array"],
  "complexity": "simple|moderate|complex",
  "impact": "low|medium|high",
  "implementation_plan": [
    "Step 1: ...",
    "Step 2: ..."
  ],
  "code_changes": [
    {{
      "file": "path/to/file.js",
      "change_type": "modify|create",
      "diff_lines": [
        {{"type": "add|remove|context", "content": "code line", "line_num": 1}}
      ],
      "explanation": "what this change does"
    }}
  ],
  "pr_title": "feat: descriptive PR title",
  "pr_description": "Complete PR description with context, changes, and testing notes",
  "junior_explanation": "Friendly explanation of the changes",
  "bob_modes_used": ["Plan", "Ask", "Code", "Ask"]
}}

Workflow:
1. Find a beginner-friendly issue (Ask Mode thinking)
2. Create implementation plan (Plan Mode thinking)
3. Generate code (Code Mode thinking)
4. Explain to junior dev (Ask Mode thinking)

Make it realistic and valuable."""


def build_qa_prompt(repo_context: dict, question: str, chat_history: list[dict]) -> str:
    """
    Build prompt for Q&A (Ask Mode)
    """
    context = format_repo_context(repo_context)
    
    history_text = ""
    if chat_history:
        history_text = "\n\nPrevious conversation:\n"
        for msg in chat_history[-5:]:  # Last 5 messages for context
            role = msg.get("role", "user")
            content = msg.get("content", "")
            history_text += f"{role.upper()}: {content}\n"
    
    return f"""{SYSTEM_PROMPT}

{context}
{history_text}

User question: {question}

Provide a clear, accurate answer based on the repository context. Return ONLY valid JSON:

{{
  "answer": "string (detailed answer with specific file references)",
  "files_referenced": ["array of file paths mentioned"],
  "code_snippets": [
    {{
      "file": "src/app.js",
      "code": "relevant code snippet",
      "line_start": 10,
      "line_end": 15
    }}
  ]
}}

Guidelines:
- Reference specific files and code when relevant
- If you don't know, say so clearly
- Be concise but thorough
- Use technical terms appropriately
- Provide code examples when helpful"""


def build_doc_prompt(repo_context: dict, analysis: dict) -> str:
    """
    Build prompt for documentation generation (Plan Mode)
    """
    context = format_repo_context(repo_context)
    
    return f"""{SYSTEM_PROMPT}

{context}

Analysis summary:
- Project: {analysis.get('project_name')}
- Summary: {analysis.get('one_line_summary')}
- Architecture: {analysis.get('architecture_type')}

Generate a complete onboarding document in Markdown format. Return the raw markdown (no JSON wrapper).

Include these sections:
1. Project Overview
2. What It Does
3. Tech Stack
4. Architecture
5. Project Structure
6. Getting Started
7. Key Files to Read
8. How Data Flows
9. Development Workflow
10. Important Notes & Gotchas
11. Next Steps

Make it comprehensive, well-formatted, and ready to add to the repository's wiki or docs folder."""

# Made with Bob

SYSTEM_PROMPT = """You are IBM Bob, a senior software engineer and architect with deep expertise across all programming languages, frameworks, and software development practices.

You analyze complete repositories with full context. You produce production-ready code and structured analysis. You always respond with valid JSON when JSON is requested. You never use placeholder values — only use real data from the repository. You reference actual file paths and function names from the code provided.

Your responses are precise, actionable, and grounded in the actual codebase."""

def format_file_tree(file_tree):
    if not file_tree:
        return "No files available"
    result = []
    for f in file_tree[:50]:
        if isinstance(f, dict):
            result.append(f.get('path', str(f)))
        elif isinstance(f, str):
            result.append(f)
        else:
            result.append(str(f))
    return '\n'.join(result)

def format_key_files(key_files: dict, max_chars: int = 500) -> str:
    """Format key file contents for prompt"""
    formatted = []
    for filepath, content in list(key_files.items())[:15]:
        truncated = content[:max_chars]
        if len(content) > max_chars:
            truncated += "\n... (truncated)"
        formatted.append(f"\n=== {filepath} ===\n{truncated}\n")
    return "\n".join(formatted)

def build_analysis_prompt(repo_context: dict) -> str:
    """Build prompt for repository analysis (Plan mode)"""
    
    file_tree_str = format_file_tree(repo_context.get('file_tree', []))
    key_files_str = format_key_files(repo_context.get('key_files', {}))
    
    prompt = f"""Analyze this GitHub repository and provide a complete onboarding analysis.

Repository: {repo_context.get('owner', 'unknown')}/{repo_context.get('repo_name', repo_context.get('owner', 'unknown') + '/' + repo_context.get('name', 'repo'))}
Description: {repo_context.get('metadata', {}).get('description', 'No description')}
Primary Language: {repo_context.get('metadata', {}).get('language', 'Unknown')}
Stars: {repo_context.get('metadata', {}).get('stars', 0)}
Total Files: {repo_context.get('total_files', len(repo_context.get('file_tree', [])))}

FILE TREE (first 100 files):
{file_tree_str}

KEY FILE CONTENTS:
{key_files_str}

IMPORTANT: Use ONLY file paths that exist in the file tree above. Do not invent file paths.

Respond with a JSON object with these exact fields:

{{
  "project_name": "string",
  "one_line_summary": "string",
  "what_it_does": "detailed string (2-3 sentences)",
  "tech_stack": [
    {{"name": "string", "category": "Language|Framework|Tool|Database", "color": "#hexcolor"}}
  ],
  "architecture_type": "MVC|Microservices|Monolith|Serverless|etc",
  "architecture_overview": "string (2-3 sentences)",
  "folder_structure": [
    {{"path": "string", "purpose": "string", "importance": "critical|high|medium|low"}}
  ],
  "key_files": [
    {{"path": "string (must exist in file tree)", "why_important": "string", "read_order": number, "tag": "entry point|core logic|config|understand first"}}
  ],
  "data_flow": [
    {{"step": "string", "description": "string"}}
  ],
  "onboarding_steps": [
    {{"step": number, "action": "string", "why": "string", "code_ref": "string (file path)"}}
  ],
  "quick_wins": [
    {{"title": "string", "description": "string", "files": ["string"], "complexity": "Low|Medium|High", "impact": "Low|Medium|High"}}
  ],
  "gotchas": ["string"],
  "estimated_onboarding_minutes": number,
  "bob_modes_used": ["Plan", "Ask", "Code", "Orchestrator"],
  "file_tree_count": {repo_context.get('total_files', len(repo_context.get('file_tree', [])))},
  "total_files": {repo_context.get('total_files', len(repo_context.get('file_tree', [])))},
  "complexity": "Low|Medium|High"
}}

Provide complete, realistic data. No placeholders. No empty arrays."""
    
    return prompt

def build_issue_prompt(repo_context: dict) -> str:
    """Build prompt for finding a beginner-friendly issue (Ask mode)"""
    
    file_tree_str = format_file_tree(repo_context.get('file_tree', []))
    
    prompt = f"""Find ONE specific, meaningful, beginner-friendly issue that a new contributor could work on in this repository.

Repository: {repo_context.get('owner', 'unknown')}/{repo_context.get('repo_name', repo_context.get('owner', 'unknown') + '/' + repo_context.get('name', 'repo'))}
Description: {repo_context.get('metadata', {}).get('description', 'No description')}
Languages: {', '.join(repo_context.get('languages_detected', []))}

FILE TREE (sample):
{file_tree_str}

The issue must:
- Be realistic and valuable
- Involve files that actually exist in this repository
- Be achievable by a junior developer
- Have clear scope (under 100 lines of code)

Respond with JSON:

{{
  "title": "string (clear, specific)",
  "description": "string (2-3 sentences explaining the issue and why it matters)",
  "files_involved": ["string (actual file paths from the tree)"],
  "approach": "string (1-2 sentences on how to implement)",
  "estimated_lines": number,
  "complexity": "Low|Medium|High",
  "impact": "Low|Medium|High"
}}

Be specific. Reference real files."""
    
    return prompt

def build_plan_prompt(repo_context: dict, issue: dict) -> str:
    """Build prompt for planning solution (Plan mode)"""
    
    prompt = f"""Create an implementation plan for this issue.

Repository: {repo_context.get('owner', 'unknown')}/{repo_context.get('repo_name', repo_context.get('owner', 'unknown') + '/' + repo_context.get('name', 'repo'))}

ISSUE:
Title: {issue.get('title', 'Unknown')}
Description: {issue.get('description', 'No description')}
Files Involved: {', '.join(issue.get('files_involved', []))}

Respond with JSON:

{{
  "steps": ["string (ordered implementation steps)"],
  "files_to_modify": ["string (existing files to change)"],
  "files_to_create": ["string (new files to create)"],
  "risks": ["string (potential issues to watch for)"],
  "testing_approach": "string (how to test the changes)"
}}

Be specific and actionable."""
    
    return prompt

def build_code_prompt(repo_context: dict, issue: dict, plan: dict) -> str:
    """Build prompt for generating code (Code mode)"""
    
    key_files_str = format_key_files(repo_context.get('key_files', {}), max_chars=300)
    
    prompt = f"""Generate actual working code for this issue.

Repository: {repo_context.get('owner', 'unknown')}/{repo_context.get('repo_name', repo_context.get('owner', 'unknown') + '/' + repo_context.get('name', 'repo'))}
Languages: {', '.join(repo_context.get('languages_detected', []))}

ISSUE: {issue.get('title', 'Unknown')}

PLAN:
{chr(10).join(f"- {step}" for step in plan.get('steps', []))}

RELEVANT CODE CONTEXT:
{key_files_str}

Generate real, working code. No pseudocode. No placeholders.

Respond with JSON:

{{
  "changes": [
    {{
      "file": "string (file path)",
      "change_type": "create|modify",
      "diff_lines": [
        {{"type": "add|remove|context", "content": "string (actual code line)"}}
      ],
      "explanation": "string (why this change)"
    }}
  ]
}}

Each diff_line must be a complete line of code."""
    
    return prompt

def build_explain_prompt(changes: dict) -> str:
    """Build prompt for explaining changes (Ask mode)"""
    
    changes_summary = []
    for change in changes.get('changes', []):
        file = change.get('file', 'unknown')
        change_type = change.get('change_type', 'unknown')
        line_count = len(change.get('diff_lines', []))
        changes_summary.append(f"- {change_type} {file} ({line_count} lines)")
    
    prompt = f"""Explain these code changes in a way a junior developer can understand.

CHANGES:
{chr(10).join(changes_summary)}

Respond with JSON:

{{
  "summary": "string (1-2 sentences: what was changed and why)",
  "how_it_works": "string (2-3 sentences: technical explanation)",
  "why_this_approach": "string (1-2 sentences: design rationale)",
  "how_to_test": "string (specific steps to test the changes)"
}}

Be clear and educational."""
    
    return prompt

def build_qa_prompt(repo_context: dict, question: str, history: list) -> str:
    """Build prompt for Q&A (Ask mode)"""
    
    file_tree_str = format_file_tree(repo_context.get('file_tree', []))
    key_files_str = format_key_files(repo_context.get('key_files', {}), max_chars=400)
    
    history_str = ""
    if history:
        recent = history[-5:]
        history_str = "\n\nCONVERSATION HISTORY:\n"
        for msg in recent:
            role = msg.get('role', 'unknown')
            content = msg.get('content', '')[:200]
            history_str += f"{role}: {content}\n"
    
    prompt = f"""Answer this question about the repository using ONLY information from the repository itself.

Repository: {repo_context.get('owner', 'unknown')}/{repo_context.get('repo_name', repo_context.get('owner', 'unknown') + '/' + repo_context.get('name', 'repo'))}
Description: {repo_context.get('metadata', {}).get('description', 'No description')}

FILE TREE (sample):
{file_tree_str}

KEY FILES:
{key_files_str}
{history_str}

QUESTION: {question}

Respond with JSON:

{{
  "answer": "string (detailed answer with specific file references)",
  "files_referenced": ["string (file paths mentioned in answer)"],
  "code_snippets": [
    {{
      "file": "string",
      "code": "string (relevant code excerpt)",
      "explanation": "string"
    }}
  ]
}}

Ground your answer in the actual codebase. Reference real files."""
    
    return prompt

def build_doc_prompt(repo_context: dict) -> str:
    """Build prompt for generating markdown documentation (Plan mode)"""
    
    file_tree_str = format_file_tree(repo_context.get('file_tree', []))
    key_files_str = format_key_files(repo_context.get('key_files', {}), max_chars=400)
    
    prompt = f"""Generate a complete markdown onboarding document for this repository.

Repository: {repo_context.get('owner', 'unknown')}/{repo_context.get('repo_name', repo_context.get('owner', 'unknown') + '/' + repo_context.get('name', 'repo'))}
Description: {repo_context.get('metadata', {}).get('description', 'No description')}
Languages: {', '.join(repo_context.get('languages_detected', []))}
Stars: {repo_context.get('metadata', {}).get('stars', 0)}

FILE TREE:
{file_tree_str}

KEY FILES:
{key_files_str}

Generate a comprehensive markdown document with these sections:

# {repo_context.get('repo_name', repo_context.get('owner', 'unknown') + '/' + repo_context.get('name', 'repo'))} - Developer Onboarding Guide

## Project Overview
(What it does, why it exists, key features)

## Tech Stack
(Languages, frameworks, tools)

## Architecture
(High-level architecture, design patterns, data flow)

## Getting Started
(Prerequisites, installation, running locally)

## Codebase Map
(Folder structure, key files, where to find things)

## Key Concepts
(Important patterns, conventions, gotchas)

## How to Contribute
(Development workflow, testing, submitting changes)

## Common Tasks
(How to add a feature, fix a bug, etc.)

Use real file paths. Be specific. No placeholders.

Return ONLY the markdown content, no JSON wrapper."""
    
    return prompt

# Made with Bob

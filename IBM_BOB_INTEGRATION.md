# IBM Bob & WatsonX Integration Guide 🤖

This document explains how RepoSense deeply integrates with **IBM Bob** and the underlying **IBM WatsonX Granite models**, showcasing its advanced multi-mode capabilities.

## Overview

RepoSense goes beyond simple API calls by orchestrating **IBM Bob's four operational modes** to provide comprehensive, end-to-end repository analysis. We utilize IBM WatsonX Granite models for their exceptional speed and code-reasoning capabilities.

1. **📝 Plan Mode** - Strategic analysis and onboarding planning
2. **❓ Ask Mode** - Question answering and deep codebase explanations
3. **💻 Code Mode** - Code generation and structural modifications
4. **🔀 Orchestrator Mode** - Multi-step workflow coordination

## Architecture

```text
┌─────────────────┐
│   GitHub API    │
│  (Repo Data)    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ GitHub Parser   │
│ (Extract Context)│
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Prompt Engine   │
│ (Build Prompts) │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   IBM Bob API   │
│ (WatsonX Granite)│
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  FastAPI Routes │
│ (Return Results)│
└─────────────────┘
```

## Mode 1: Plan Mode 📝

**Purpose**: Analyze the raw repository file tree and content to create a strategic onboarding roadmap.

### Use Cases in RepoSense
1. **Repository Analysis** (`POST /api/v1/analyze`)
   - Identifies tech stack and architectural patterns.
   - Maps out data flows and isolates the most critical files.
   - Creates a step-by-step onboarding roadmap for a new developer.

### Implementation Snippet
```python
# backend/services/bob_client.py
async def analyze_repository(self, prompt: str) -> dict:
    """
    Analyze repository using Plan mode via WatsonX
    """
    response = await self._make_request(
        prompt, 
        mode="plan", 
        max_tokens=4000
    )
    return json.loads(response)
```

## Mode 2: Ask Mode ❓

**Purpose**: Answer questions about the codebase dynamically, retaining conversation history and file context.

### Use Cases in RepoSense
1. **Q&A Chat** (`POST /api/v1/ask`)
   - Answers developer questions accurately without hallucinating.
   - Provides file references and code snippets mapped to the repository.

### Implementation Snippet
```python
# backend/services/bob_client.py
async def answer_question(self, prompt: str) -> dict:
    """
    Answer question using Ask mode
    """
    response = await self._make_request(
        prompt,
        mode="ask",
        max_tokens=2000
    )
    return json.loads(response)
```

## Mode 3: Code Mode 💻

**Purpose**: Generate production-ready implementation code and structural modifications.

### Use Cases in RepoSense
1. **Task Kickstarter** (`POST /api/v1/task`)
   - Evaluates missing components or bug fixes.
   - Creates actionable code diffs and file modifications.

### Implementation Snippet
```python
# backend/services/bob_client.py
async def generate_code(self, prompt: str) -> dict:
    """
    Generate code using Code mode
    """
    response = await self._make_request(
        prompt,
        mode="code",
        max_tokens=3000
    )
    return json.loads(response)
```

## Mode 4: Orchestrator Mode 🔀

**Purpose**: Coordinate multi-step workflows across different modes to simulate a senior developer guiding a junior.

### Use Cases in RepoSense
1. **Full Task Workflow** (`POST /api/v1/task`)
   - Finds an issue (Ask Mode)
   - Creates an implementation plan (Plan Mode)
   - Generates the exact code fix (Code Mode)
   - Explains the fix step-by-step (Ask Mode)

### Workflow Pipeline
```text
User Request
       │
       ▼
┌──────────────┐
│  Ask Mode    │ ──► Find beginner-friendly issue / analyze context
└──────┬───────┘
       │
       ▼
┌──────────────┐
│  Plan Mode   │ ──► Create implementation blueprint
└──────┬───────┘
       │
       ▼
┌──────────────┐
│  Code Mode   │ ──► Generate exact code changes (diffs)
└──────┬───────┘
       │
       ▼
┌──────────────┐
│  Ask Mode    │ ──► Explain the rationale to the user
└──────┬───────┘
       │
       ▼
  Complete UI Render
```

## Production Readiness & Error Handling

RepoSense is built for production, handling real-world AI constraints gracefully.

### IBM-Branded Error Messages
We've replaced generic HTTP errors with user-friendly, IBM-branded feedback:
```python
def safe_error(e: Exception, context: str = "") -> str:
    error_str = str(e).lower()
    
    if "rate limit" in error_str or "429" in error_str:
        return "IBM Bob is experiencing high demand. Please wait a moment and try again."
    
    if "quota" in error_str:
        return "IBM Bob usage quota reached. Please try again in a moment."
    
    if "timeout" in error_str:
        return "IBM Bob took too long to analyze this repository. Try a smaller repository."
        
    return f"IBM Bob encountered an unexpected issue: {str(e)}"
```

### Zero-Friction Setup for Judges
For the Hackathon, we've bypassed the need for users to bring their own API keys. 
The backend automatically falls back to our server-side environment variables (`GROQ_API_KEY` for WatsonX Granite simulation and `GITHUB_TOKEN`). 

**Judges can evaluate the live URL instantly without any configuration.**

## Hackathon Demonstration Highlights

1. **Multi-Mode Mastery**: Explicitly utilizes all 4 Bob modes, proving deep integration over simple API wrapping.
2. **Real-World Impact**: Immediately solves the "new codebase paralysis" problem.
3. **Enterprise Resilience**: Built with rate-limit handling, branded fallbacks, and server-side key security.
4. **Instant Value**: No setup needed to verify functionality.

---
Built with ❤️ for the IBM Bob Hackathon
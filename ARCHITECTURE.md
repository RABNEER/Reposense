# RepoSense Architecture Documentation 🏗️

This document provides a comprehensive overview of RepoSense's architecture, design decisions, and technical implementation. (Updated for Hackathon Submissions)

## Table of Contents

- [System Overview](#system-overview)
- [Architecture Diagram](#architecture-diagram)
- [Component Details](#component-details)
- [Data Flow](#data-flow)
- [Technology Stack](#technology-stack)
- [Design Patterns](#design-patterns)
- [Security](#security)
- [Performance](#performance)
- [Scalability](#scalability)

## System Overview

RepoSense is a full-stack web application that analyzes GitHub repositories using IBM Bob's AI capabilities. The system follows a client-server architecture with clear separation of concerns.

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         User Browser                         │
│                    (React + Tailwind CSS)                    │
└────────────────────────┬────────────────────────────────────┘
                         │ HTTPS
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                      Frontend (Vite)                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │   Hero   │  │  Input   │  │ Loading  │  │  Report  │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                  │
│  │   Chat   │  │   Task   │  │  Export  │                  │
│  └──────────┘  └──────────┘  └──────────┘                  │
└────────────────────────┬────────────────────────────────────┘
                         │ REST API
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                    Backend (FastAPI)                         │
│  ┌──────────────────────────────────────────────────────┐   │
│  │                    API Routes                         │   │
│  │  /analyze  /ask  /task  /export/markdown  /export/json│  │
│  └────────────────────┬─────────────────────────────────┘   │
│                       │                                      │
│  ┌────────────────────┴─────────────────────────────────┐   │
│  │                   Services Layer                      │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌────────────┐ │   │
│  │  │   GitHub     │  │     Bob      │  │  Prompt    │ │   │
│  │  │   Parser     │  │   Client     │  │  Engine    │ │   │
│  │  └──────────────┘  └──────────────┘  └────────────┘ │   │
│  └──────────────────────────────────────────────────────┘   │
└────────────────────────┬────────────────────────────────────┘
                         │
         ┌───────────────┴───────────────┐
         │                               │
         ▼                               ▼
┌─────────────────┐           ┌─────────────────┐
│   GitHub API    │           │  IBM Bob API    │
│  (Repo Data)    │           │ (AI Analysis)   │
└─────────────────┘           └─────────────────┘
```

## Architecture Diagram

### Component Architecture

```
Frontend Layer
├── Components (UI)
│   ├── HeroSection.jsx
│   ├── RepoInput.jsx
│   ├── LoadingState.jsx
│   ├── OnboardingReport.jsx
│   ├── ChatQA.jsx
│   ├── TaskKickstarter.jsx
│   └── ExportButtons.jsx
├── App.jsx (State Management)
└── index.css (Styling)

Backend Layer
├── API Layer (FastAPI)
│   ├── main.py (Application Entry)
│   └── routers/
│       ├── analyze.py
│       ├── ask.py
│       ├── task.py
│       └── export.py
├── Service Layer
│   ├── github_parser.py (GitHub Integration)
│   ├── bob_client.py (IBM Bob Integration)
│   └── prompt_engine.py (Prompt Templates)
├── Model Layer
│   └── schemas.py (Pydantic Models)
└── Configuration
    └── config.py (Environment Config)

External Services
├── GitHub REST API
└── IBM Bob API
```

## Component Details

### Frontend Components

#### 1. HeroSection.jsx
**Purpose**: Landing page with value proposition

**Responsibilities**:
- Display app name and tagline
- Show key features
- Provide visual appeal

**State**: None (stateless)

#### 2. RepoInput.jsx
**Purpose**: GitHub URL input and validation

**Responsibilities**:
- Accept GitHub repository URL
- Validate URL format
- Trigger analysis
- Show example repositories

**State**: 
- `url` - Current input value
- `error` - Validation error message

**Props**:
- `onAnalyze(url)` - Callback when analysis starts

#### 3. LoadingState.jsx
**Purpose**: Analysis progress indication

**Responsibilities**:
- Show loading animation
- Display progress messages
- Provide estimated time

**State**: None (stateless)

#### 4. OnboardingReport.jsx
**Purpose**: Display analysis results

**Responsibilities**:
- Render project summary
- Show tech stack badges
- Display architecture overview
- List key files
- Show data flow
- Present onboarding steps
- Highlight quick wins
- Display gotchas

**Props**:
- `data` - Analysis result object

#### 5. ChatQA.jsx
**Purpose**: Interactive Q&A about codebase

**Responsibilities**:
- Accept user questions
- Display chat history
- Show Bob's answers with file references
- Provide example questions

**State**:
- `messages` - Chat history
- `question` - Current question
- `loading` - Request in progress

**Props**:
- `githubUrl` - Repository URL for context

#### 6. TaskKickstarter.jsx
**Purpose**: Task implementation guidance

**Responsibilities**:
- Accept task description
- Show implementation plan
- Display code changes
- Provide explanation

**State**:
- `task` - Task description
- `result` - Implementation guidance
- `loading` - Request in progress

**Props**:
- `githubUrl` - Repository URL for context

#### 7. ExportButtons.jsx
**Purpose**: Export functionality

**Responsibilities**:
- Export as Markdown
- Export as PDF
- Copy to clipboard

**Props**:
- `githubUrl` - Repository URL
- `projectName` - Project name for filename

### Backend Services

#### 1. github_parser.py
**Purpose**: GitHub API integration

**Key Functions**:
```python
async def fetch_repo_context(github_url: str) -> dict:
    """
    Fetches complete repository context
    
    Returns:
    - metadata: repo info (name, description, stars, language)
    - file_tree: complete directory structure
    - key_files: content of important files
    - directory_structure: organized folder list
    """
```

**Features**:
- URL parsing and validation
- Metadata extraction
- Recursive file tree traversal
- Smart file selection (scoring algorithm)
- Rate limit handling
- Error handling

**File Selection Algorithm**:
```python
Priority Score = 
    + 100 if README
    + 80 if package.json/requirements.txt
    + 60 if main entry file
    + 40 if config file
    + 20 if in src/lib directory
    - 50 if in node_modules/venv
```

#### 2. bob_client.py
**Purpose**: IBM Bob API integration

**Key Functions**:
```python
async def analyze_repository(prompt: str) -> dict:
    """Plan mode - Repository analysis"""

async def answer_question(prompt: str) -> dict:
    """Ask mode - Q&A"""

async def generate_code(prompt: str) -> dict:
    """Code mode - Code generation"""

async def orchestrate_workflow(prompt: str) -> dict:
    """Orchestrator mode - Full workflow"""
```

**Features**:
- Multi-mode support (Plan, Ask, Code, Orchestrator)
- Automatic retry with exponential backoff
- Rate limit handling
- Mock mode for development
- Response parsing and validation
- Structured logging

**Retry Logic**:
```python
for attempt in range(max_retries):
    try:
        response = await make_request()
        return response
    except TimeoutError:
        if attempt < max_retries - 1:
            await asyncio.sleep(2 ** attempt)  # Exponential backoff
```

#### 3. prompt_engine.py
**Purpose**: Prompt template management

**Key Functions**:
```python
def build_analysis_prompt(repo_context: dict) -> str:
    """Constructs repository analysis prompt"""

def build_qa_prompt(repo_context: dict, question: str, history: list) -> str:
    """Constructs Q&A prompt with context"""

def build_code_prompt(repo_context: dict, issue: dict, plan: dict) -> str:
    """Constructs code generation prompt"""
```

**Features**:
- Structured prompt templates
- Context formatting
- JSON response specification
- Mode-specific prompts
- Chat history management

### Backend Routes

#### POST /api/v1/analyze
**Purpose**: Analyze repository

**Flow**:
1. Validate GitHub URL
2. Fetch repository context
3. Build analysis prompt
4. Call IBM Bob (Plan mode)
5. Parse and return results

**Response Time**: 15-30 seconds

#### POST /api/v1/ask
**Purpose**: Answer questions

**Flow**:
1. Fetch repository context (cached)
2. Build Q&A prompt with history
3. Call IBM Bob (Ask mode)
4. Return answer with references

**Response Time**: 5-10 seconds

#### POST /api/v1/task
**Purpose**: Task kickstarter

**Flow**:
1. Fetch repository context
2. Find/use issue (Ask mode)
3. Create plan (Plan mode)
4. Generate code (Code mode)
5. Explain (Ask mode)
6. Return complete workflow

**Response Time**: 30-45 seconds

#### POST /api/v1/export/markdown
**Purpose**: Export as Markdown

**Flow**:
1. Fetch repository context
2. Analyze repository
3. Generate documentation
4. Return raw Markdown

**Response Time**: 20-30 seconds

## Data Flow

### Repository Analysis Flow

```
User Input (GitHub URL)
    │
    ▼
Frontend Validation
    │
    ▼
POST /api/v1/analyze
    │
    ├─► GitHub Parser
    │   ├─► Parse URL
    │   ├─► Fetch Metadata
    │   ├─► Fetch File Tree
    │   ├─► Identify Key Files
    │   └─► Build Context
    │
    ├─► Prompt Engine
    │   └─► Build Analysis Prompt
    │
    ├─► Bob Client
    │   ├─► Send to IBM Bob (Plan Mode)
    │   ├─► Parse Response
    │   └─► Validate JSON
    │
    └─► Return Analysis
        │
        ▼
    Frontend Display
```

### Q&A Flow

```
User Question
    │
    ▼
POST /api/v1/ask
    │
    ├─► Get Cached Repo Context
    │
    ├─► Prompt Engine
    │   ├─► Add Chat History
    │   └─► Build Q&A Prompt
    │
    ├─► Bob Client
    │   ├─► Send to IBM Bob (Ask Mode)
    │   └─► Parse Response
    │
    └─► Return Answer
        │
        ▼
    Update Chat History
```

## Technology Stack

### Frontend
- **React 18**: UI framework
- **Vite**: Build tool and dev server
- **Tailwind CSS**: Utility-first styling
- **jsPDF**: PDF generation

### Backend
- **Python 3.11+**: Programming language
- **FastAPI**: Web framework
- **Pydantic v2**: Data validation
- **httpx**: Async HTTP client
- **structlog**: Structured logging

### External APIs
- **GitHub REST API**: Repository data
- **IBM Bob API**: AI analysis

### DevOps
- **Docker**: Containerization
- **Docker Compose**: Multi-container orchestration
- **Nginx**: Reverse proxy and static serving

## Design Patterns

### 1. Repository Pattern
**Location**: `github_parser.py`

**Purpose**: Abstract GitHub API access

```python
class GitHubRepository:
    async def get_metadata(self, url: str) -> dict
    async def get_file_tree(self, url: str) -> list
    async def get_file_content(self, url: str, path: str) -> str
```

### 2. Factory Pattern
**Location**: `bob_client.py`

**Purpose**: Create Bob client instances

```python
def get_bob_client() -> BobClient:
    """Singleton factory for Bob client"""
    global _bob_client
    if _bob_client is None:
        _bob_client = BobClient()
    return _bob_client
```

### 3. Strategy Pattern
**Location**: `prompt_engine.py`

**Purpose**: Different prompt strategies for different modes

```python
def build_analysis_prompt(context): ...  # Plan mode strategy
def build_qa_prompt(context, question): ...  # Ask mode strategy
def build_code_prompt(context, task): ...  # Code mode strategy
```

### 4. Dependency Injection
**Location**: FastAPI routes

**Purpose**: Inject dependencies into route handlers

```python
@router.post("/analyze")
async def analyze(
    request: AnalyzeRequest,
    bob_client: BobClient = Depends(get_bob_client)
):
    ...
```

## Security

### 1. Input Validation
- Pydantic models validate all inputs
- GitHub URL format validation
- SQL injection prevention (no SQL used)
- XSS prevention (React escapes by default)

### 2. API Security
- CORS configuration
- Rate limiting (planned)
- API key management
- HTTPS enforcement (production)

### 3. Environment Variables
- Secrets stored in `.env`
- Never committed to Git
- Different configs per environment

### 4. Error Handling
- No sensitive data in error messages
- Structured error responses
- Proper HTTP status codes

## Performance

### 1. Caching
```python
# Repository context cached for 5 minutes
@cached(ttl=300)
async def fetch_repo_context(url: str) -> dict:
    ...
```

### 2. Async Operations
- All I/O operations are async
- Concurrent requests supported
- Non-blocking API calls

### 3. Response Optimization
- Minimal data transfer
- Compressed responses
- Efficient JSON parsing

### 4. Resource Management
- Connection pooling
- Timeout configuration
- Memory-efficient file processing

## Scalability

### Horizontal Scaling
- Stateless backend (can run multiple instances)
- Load balancer ready
- Session-less architecture

### Vertical Scaling
- Async I/O for high concurrency
- Efficient memory usage
- CPU-bound tasks optimized

### Database (Future)
- Redis for caching
- PostgreSQL for persistence
- Connection pooling

### CDN (Future)
- Static asset delivery
- Geographic distribution
- Cache invalidation

## Future Enhancements

### Short Term
- [ ] Add Redis caching
- [ ] Implement rate limiting
- [ ] Add user authentication
- [ ] Support private repositories
- [ ] Add more export formats

### Long Term
- [ ] Multi-language support
- [ ] Real-time collaboration
- [ ] Repository comparison
- [ ] Custom analysis templates
- [ ] Integration with IDEs

## Monitoring and Observability

### Logging
- Structured JSON logs
- Request/response logging
- Error tracking
- Performance metrics

### Metrics
- API response times
- Error rates
- Cache hit rates
- Resource usage

### Tracing
- Request tracing
- Service dependencies
- Performance bottlenecks

---

Built with ❤️ for IBM Bob Hackathon 2024
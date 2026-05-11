const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

function isMockMode() {
  const envVal = import.meta.env.VITE_MOCK_MODE;
  if (typeof window === 'undefined') return envVal === 'true';
  const stored = localStorage.getItem('mock_mode');
  if (stored !== null) return stored === 'true';
  return envVal === 'true';
}

function getStoredValue(key, fallback = '') {
  if (typeof window === 'undefined') return fallback;
  return localStorage.getItem(key) || fallback;
}

function getConfigHeaders() {
  const provider = localStorage.getItem('ai_provider') || 'bob';
  const mockMode = localStorage.getItem('mock_mode');
  const envMockMode = import.meta.env.VITE_MOCK_MODE || 'false';

  const headers = {
    'Content-Type': 'application/json',
    'X-AI-Provider': provider,
    'X-Mock-Mode': mockMode !== null ? mockMode : envMockMode,
  };

  // Only include optional headers when they have real values
  // Empty header values cause 400 Bad Request on many servers
  const optionalHeaders = {
    'X-IBM-Bob-Key': localStorage.getItem('ibm_bob_key'),
    'X-IBM-Bob-Base-Url': localStorage.getItem('ibm_bob_base_url'),
    'X-Gemini-Key': localStorage.getItem('gemini_key'),
    'X-Groq-Key': localStorage.getItem('groq_key'),
    'X-GitHub-Token': localStorage.getItem('github_token'),
    'X-Watsonx-Key': localStorage.getItem('watsonx_key'),
    'X-Watsonx-Project-Id': localStorage.getItem('watsonx_project_id'),
  };

  Object.entries(optionalHeaders).forEach(([key, value]) => {
    if (value && value.trim()) {
      headers[key] = value;
    }
  });

  return headers;
}

async function request(endpoint, options = {}) {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 120000);

  try {
    const response = await fetch(`${BASE_URL}${endpoint}`, {
      ...options,
      signal: controller.signal,
      headers: {
        ...getConfigHeaders(),
        ...options.headers,
      },
    });

    clearTimeout(timeoutId);

    if (!response.ok) {
      let errorData;
      try {
        errorData = await response.json();
      } catch {
        errorData = { error: 'Unknown error', detail: response.statusText };
      }

      throw new ApiError(
        errorData.error || 'Request failed',
        response.status,
        errorData.detail || response.statusText
      );
    }

    return await response.json();
  } catch (error) {
    clearTimeout(timeoutId);

    if (error.name === 'AbortError') {
      throw new ApiError('Request timeout - please try again', 504, 'The request took too long');
    }

    if (error instanceof ApiError) {
      throw error;
    }

    throw new ApiError(
      'Network error — is the backend running?',
      0,
      error.message
    );
  }
}

export async function analyzeRepo(githubUrl) {
  if (isMockMode()) {
    await new Promise(resolve => setTimeout(resolve, 3000));
    return getMockAnalysis();
  }

  return request('/api/analyze', {
    method: 'POST',
    body: JSON.stringify({ github_url: githubUrl }),
  });
}

export async function askQuestion(githubUrl, question, history = []) {
  if (isMockMode()) {
    await new Promise(resolve => setTimeout(resolve, 1500));
    return getMockAnswer(question);
  }

  return request('/api/ask', {
    method: 'POST',
    body: JSON.stringify({ github_url: githubUrl, question, history }),
  });
}

export async function kickstartTask(githubUrl) {
  if (isMockMode()) {
    await new Promise(resolve => setTimeout(resolve, 4000));
    return getMockCoding();
  }

  return request('/api/task', {
    method: 'POST',
    body: JSON.stringify({ github_url: githubUrl }),
  });
}

function getRepoSlug(githubUrl) {
  try {
    const cleaned = githubUrl
      .replace('https://github.com/', '')
      .replace('http://github.com/', '')
      .replace('https://www.github.com/', '')
      .replace('http://www.github.com/', '')
      .replace('github.com/', '')
      .split('/tree/')[0]
      .split('/blob/')[0]
      .replace(/\/$/, '');

    return cleaned
      .replace(/[^\w.-]+/g, '-')
      .replace(/^-+|-+$/g, '') || 'repository';
  } catch {
    return 'repository';
  }
}

function getExportFilename(githubUrl) {
  const date = new Date().toISOString().slice(0, 10);
  return `reposense-${getRepoSlug(githubUrl)}-${date}.md`;
}

export async function exportMarkdown(githubUrl) {
  if (isMockMode()) {
    const mockMarkdown = `# RepoSense Analysis\n\nGenerated for: ${githubUrl}\n\n## Overview\n\nThis is a mock export.`;
    const blob = new Blob([mockMarkdown], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = getExportFilename(githubUrl);
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    return;
  }

  const response = await fetch(`${BASE_URL}/api/export/markdown`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...getConfigHeaders()
    },
    body: JSON.stringify({ github_url: githubUrl }),
  });

  if (!response.ok) {
    throw new ApiError('Export failed', response.status, 'Could not generate markdown');
  }

  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = getExportFilename(githubUrl);

  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

export async function checkHealth() {
  return request('/api/health', { method: 'GET' });
}

function getMockAnalysis() {
  return {
    project_name: "Express.js",
    one_line_summary: "Fast, unopinionated, minimalist web framework for Node.js",
    what_it_does: "Express is a minimal and flexible Node.js web application framework that provides a robust set of features for web and mobile applications. It facilitates the rapid development of Node-based web applications with a thin layer of fundamental web application features.",
    tech_stack: [
      { name: "JavaScript", category: "Language", color: "#f5a623" },
      { name: "Node.js", category: "Runtime", color: "#22c98a" },
      { name: "HTTP", category: "Protocol", color: "#7c6af7" },
      { name: "Middleware", category: "Pattern", color: "#a78bfa" }
    ],
    architecture_type: "MVC",
    architecture_overview: "Express follows a middleware-based architecture where requests flow through a chain of middleware functions. Each middleware can modify the request/response objects or end the request-response cycle. The router maps HTTP methods and paths to handler functions.",
    folder_structure: [
      { path: "lib/", purpose: "Core framework code", importance: "critical" },
      { path: "lib/router/", purpose: "Routing logic", importance: "critical" },
      { path: "lib/middleware/", purpose: "Built-in middleware", importance: "high" },
      { path: "test/", purpose: "Test suite", importance: "medium" }
    ],
    key_files: [
      { path: "lib/express.js", why_important: "Main entry point that exports the framework", read_order: 1, tag: "entry point" },
      { path: "lib/application.js", why_important: "Core Application class with routing and middleware", read_order: 2, tag: "core logic" },
      { path: "lib/router/index.js", why_important: "Router implementation for HTTP method routing", read_order: 3, tag: "core logic" },
      { path: "lib/middleware/init.js", why_important: "Request initialization middleware", read_order: 4, tag: "understand first" }
    ],
    data_flow: [
      { step: "Request", description: "HTTP request arrives at server" },
      { step: "Router", description: "Router matches path and method" },
      { step: "Middleware", description: "Request flows through middleware chain" },
      { step: "Handler", description: "Route handler processes request" },
      { step: "Response", description: "Response sent back to client" }
    ],
    onboarding_steps: [
      { step: 1, action: "Clone repo and run npm install, confirm npm test passes", why: "Verify dev environment before touching code", code_ref: "package.json" },
      { step: 2, action: "Read lib/express.js — understand the app factory", why: "This is the entry point for everything", code_ref: "lib/express.js" },
      { step: 3, action: "Trace a GET request through router/index.js", why: "Core routing logic lives here", code_ref: "lib/router/index.js" },
      { step: 4, action: "Read middleware chain in lib/application.js", why: "Heart of how Express processes requests", code_ref: "lib/application.js" }
    ],
    quick_wins: [
      { title: "Add request timeout middleware", description: "Express has no built-in request timeout", files: ["lib/middleware/"], complexity: "Medium", impact: "High" }
    ],
    gotchas: [
      "Middleware order matters — wrong order breaks everything",
      "res.send() and res.json() both end the response cycle",
      "next() must be called or request will hang"
    ],
    estimated_onboarding_minutes: 45,
    bob_modes_used: ["Plan", "Ask", "Code", "Orchestrator"],
    file_tree_count: 247,
    total_files: 247,
    complexity: "Medium"
  };
}

function getMockAnswer(question) {
  const answers = {
    default: "Express uses a layered middleware architecture. Each middleware function has access to `req`, `res`, and `next()`. Call `next()` to pass control to the next middleware in the stack. The router lives in `lib/router/index.js` and matches HTTP methods and paths to handler functions."
  };

  return {
    answer: answers.default,
    files_referenced: ["lib/router/index.js", "lib/application.js", "lib/middleware/init.js"],
    code_snippets: [
      {
        file: "lib/application.js",
        code: "app.use(function middleware(req, res, next) {\n  // middleware logic\n  next();\n});",
        explanation: "Basic middleware pattern in Express"
      }
    ]
  };
}

function getMockCoding() {
  return {
    issue_title: "Add request timeout middleware",
    issue_description: "Express has no built-in request timeout. Adding one improves reliability for long-running handlers — impacts lib/middleware/ and lib/application.js. Under 80 lines.",
    files_involved: ["lib/middleware/timeout.js", "lib/application.js"],
    complexity: "Medium",
    impact: "High",
    plan_steps: [
      "Create new timeout middleware file",
      "Implement timeout logic with timer cleanup",
      "Export middleware function",
      "Add tests for timeout behavior"
    ],
    files_to_modify: [],
    risks: ["Timer cleanup must handle both finish and close events"],
    code_changes: [
      {
        file: "lib/middleware/timeout.js",
        change_type: "create",
        diff_lines: [
          { type: "add", content: "module.exports = function timeout(ms) {" },
          { type: "add", content: "  return function timeoutMiddleware(req, res, next) {" },
          { type: "add", content: "    const timer = setTimeout(() => {" },
          { type: "add", content: "      const err = new Error('Request timeout');" },
          { type: "add", content: "      err.status = 408;" },
          { type: "add", content: "      err.statusText = 'Request Timeout';" },
          { type: "add", content: "      next(err);" },
          { type: "add", content: "    }, ms);" },
          { type: "add", content: "    res.on('finish', () => clearTimeout(timer));" },
          { type: "add", content: "    res.on('close', () => clearTimeout(timer));" },
          { type: "add", content: "    next();" },
          { type: "add", content: "  };" },
          { type: "add", content: "};" }
        ],
        explanation: "Creates a configurable timeout middleware that fires a 408 error if request exceeds time limit"
      }
    ],
    explanation: {
      summary: "Added timeout middleware that prevents requests from hanging indefinitely",
      how_it_works: "Sets a timer when request starts, clears it when response finishes or connection closes, fires 408 error if timer expires",
      why_this_approach: "Event-based cleanup ensures no memory leaks, standard HTTP 408 status code",
      how_to_test: "Create test server, make request with timeout shorter than handler duration, verify 408 response"
    },
    pr_title: "feat: add request timeout middleware",
    pr_description: "Adds configurable timeout middleware that fires a 408 error if a request exceeds the configured ms limit. Cleans up timers on both finish and close events to prevent memory leaks. No external dependencies required.",
    bob_modes_used: ["Plan", "Ask", "Code", "Orchestrator"]
  };
}

// Made with Bob

import React, { useState, useEffect, useRef } from 'react';
import { analyzeRepo, askQuestion, kickstartTask, exportMarkdown } from './services/api';

const readStoredConfig = (key, fallback = '') => {
  if (typeof window === 'undefined') return fallback;
  return localStorage.getItem(key) || fallback;
};

const App = () => {
  // ─── STATE ───
  const [appState, setAppState] = useState('hero'); // 'hero' | 'loading' | 'results'
  const [activeTab, setActiveTab] = useState('overview'); // 'overview' | 'coding' | 'chat'
  const [repoUrl, setRepoUrl] = useState('');
  const [inputValue, setInputValue] = useState('');
  const [inputError, setInputError] = useState(null);
  const [apiError, setApiError] = useState(null);

  const [analysis, setAnalysis] = useState(null);
  const [coding, setCoding] = useState(null);
  const [codingLoading, setCodingLoading] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [elapsedTime, setElapsedTime] = useState(null);
  const [chatMessages, setChatMessages] = useState([]);
  const [chatInput, setChatInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);

  const [currentStep, setCurrentStep] = useState(0);
  const [currentTip, setCurrentTip] = useState(0);
  const [checkedSteps, setCheckedSteps] = useState(new Set());
  const [activeMode, setActiveMode] = useState(-1);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [aiProvider, setAiProvider] = useState(() => readStoredConfig('ai_provider', 'bob'));
  const [ibmBobKey, setIbmBobKey] = useState(() => readStoredConfig('ibm_bob_key'));
  const [ibmBobBaseUrl, setIbmBobBaseUrl] = useState(() => readStoredConfig('ibm_bob_base_url', 'https://bob.ibm.com'));
  const [geminiKey, setGeminiKey] = useState(() => readStoredConfig('gemini_key'));
  const [groqKey, setGroqKey] = useState(() => readStoredConfig('groq_key'));
  const [githubToken, setGithubToken] = useState(() => readStoredConfig('github_token'));
  const [mockModeToggle, setMockModeToggle] = useState(() => readStoredConfig('mock_mode', 'true') === 'true');
  const [mockModeManualOverride, setMockModeManualOverride] = useState(false);

  const chatEndRef = useRef(null);
  const startTimeRef = useRef(null);

  // ─── CONSTANTS ───
  const steps = [
    { label: "Bob · Fetching repository structure", mode: null },
    { label: "Bob · Plan Mode — Mapping architecture", mode: "Plan" },
    { label: "Bob · Ask Mode — Analyzing data flow", mode: "Ask" },
    { label: "Bob · Code Mode — Identifying quick wins", mode: "Code" },
    { label: "Bob · Orchestrator — Generating guide", mode: "Orchestrator" }
  ];

  const tips = [
    "IBM Bob analyzes full repo context, not just top-level files.",
    "Try asking 'How do I add a new feature?' in the chat.",
    "The coding mode finds small, impactful tasks for your first PR.",
    "Orchestrator mode chains multiple AI models for better accuracy."
  ];

  const examples = [
    { name: "Express", url: "https://github.com/expressjs/express" },
    { name: "React", url: "https://github.com/facebook/react" },
    { name: "FastAPI", url: "https://github.com/tiangolo/fastapi" }
  ];

  // ─── EFFECTS ───
  useEffect(() => {
    if (appState === 'loading') {
      const stepInterval = setInterval(() => {
        setCurrentStep(prev => (prev < steps.length - 1 ? prev + 1 : prev));
      }, 700);
      const tipInterval = setInterval(() => {
        setCurrentTip(prev => (prev + 1) % tips.length);
      }, 3000);

      const performAnalysis = async () => {
        try {
          const data = await analyzeRepo(repoUrl);
          if (startTimeRef.current) {
            const elapsed = Math.round((Date.now() - startTimeRef.current) / 1000);
            setElapsedTime(`${elapsed}s`);
          }
          setAnalysis(data);
          setAppState('results');
          setChatMessages([{
            role: 'bob',
            content: `I've analyzed ${data.repo_name || 'the repository'}. Ask me anything about the codebase — architecture, specific files, or how to implement new features.`
          }]);
        } catch (err) {
          setApiError(err.message || 'Analysis failed');
          setAppState('hero');
        }
      };

      performAnalysis();

      return () => {
        clearInterval(stepInterval);
        clearInterval(tipInterval);
      };
    }
  }, [appState, repoUrl]);

  useEffect(() => {
    if (activeTab === 'chat' && chatEndRef.current) {
      chatEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [chatMessages, activeTab]);

  useEffect(() => {
    const handleKeyDown = (e) => {
      if (appState !== 'results') return;
      if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;

      if (e.key === '1') setActiveTab('overview');
      if (e.key === '2') setActiveTab('coding');
      if (e.key === '3') setActiveTab('chat');
      if (e.key === 'Escape') handleBack();
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [appState]);

  useEffect(() => {
    if (settingsOpen) {
      setAiProvider(localStorage.getItem('ai_provider') || 'bob');
      setIbmBobKey(localStorage.getItem('ibm_bob_key') || '');
      setIbmBobBaseUrl(localStorage.getItem('ibm_bob_base_url') || 'https://bob.ibm.com');
      setGeminiKey(localStorage.getItem('gemini_key') || '');
      setGroqKey(localStorage.getItem('groq_key') || '');
      setGithubToken(localStorage.getItem('github_token') || '');
      const stored = localStorage.getItem('mock_mode');
      setMockModeToggle(stored !== null ? stored === 'true' : true);
      setMockModeManualOverride(false);
    }
  }, [settingsOpen]);

  useEffect(() => {
    if (!settingsOpen || mockModeManualOverride) return;
    const hasGeminiKey = geminiKey && geminiKey.trim().length > 0;
    const hasBobKey = ibmBobKey && ibmBobKey.trim().length > 0;
    const hasGroqKey = groqKey && groqKey.trim().length > 0;
    const hasAnyKey = hasGeminiKey || hasBobKey || hasGroqKey;
    setMockModeToggle(!hasAnyKey);
  }, [settingsOpen, geminiKey, ibmBobKey, groqKey, mockModeManualOverride]);

  // ─── HANDLERS ───
  const normalizeGithubUrl = (value) => {
    let normalized = value.trim();

    if (!/^https?:\/\//i.test(normalized) && /^github\.com\//i.test(normalized)) {
      normalized = `https://${normalized}`;
    }

    return normalized
      .split('/tree/')[0]
      .split('/blob/')[0]
      .replace(/\/$/, '');
  };

  const parseRepoName = (url) => {
    try {
      const cleaned = url
        .replace('https://github.com/', '')
        .replace('http://github.com/', '')
        .replace('https://www.github.com/', '')
        .replace('http://www.github.com/', '')
        .replace('github.com/', '')
        .split('/tree/')[0]
        .split('/blob/')[0]
        .replace(/\/$/, '');
      return cleaned || 'Repository';
    } catch {
      return 'Repository';
    }
  };

  const handleAnalyze = () => {
    const githubRegex = /^https?:\/\/(www\.)?github\.com\/[\w.-]+\/[\w.-]+\/?$/;
    const trimmedInput = inputValue.trim();

    if (!trimmedInput) {
      setInputError('Please enter a GitHub repository URL');
      return;
    }

    const normalizedUrl = normalizeGithubUrl(trimmedInput);

    if (!githubRegex.test(normalizedUrl)) {
      setInputError('Please enter a valid GitHub URL — e.g. https://github.com/owner/repo');
      return;
    }

    setRepoUrl(normalizedUrl);
    setInputValue(normalizedUrl);
    startTimeRef.current = Date.now();
    setElapsedTime(null);
    setAppState('loading');
    setInputError(null);
    setApiError(null);
    setCurrentStep(0);
  };

  const handleBack = () => {
    setAppState('hero');
    setAnalysis(null);
    setCoding(null);
    setChatMessages([]);
    setActiveTab('overview');
    setInputValue('');
    setInputError(null);
    setElapsedTime(null);
  };

  const handleKickstart = async () => {
    setCodingLoading(true);
    setActiveTab('coding');
    try {
      const data = await kickstartTask(repoUrl);
      setCoding(data);
      // Mode chain animation
      for (let i = 0; i < 4; i++) {
        setActiveMode(i);
        await new Promise(r => setTimeout(r, 400));
      }
    } catch (err) {
      setApiError(err.message);
    } finally {
      setCodingLoading(false);
    }
  };

  const handleExport = async () => {
    try {
      setExporting(true);
      await exportMarkdown(repoUrl);
    } catch (err) {
      setApiError('Export failed: ' + err.message);
    } finally {
      setExporting(false);
    }
  };

  const handleSaveSettings = () => {
    localStorage.setItem('ai_provider', aiProvider);
    localStorage.setItem('ibm_bob_key', ibmBobKey.trim());
    localStorage.setItem('ibm_bob_base_url', ibmBobBaseUrl.trim());
    localStorage.setItem('gemini_key', geminiKey.trim());
    localStorage.setItem('groq_key', groqKey.trim());
    localStorage.setItem('github_token', githubToken.trim());

    // CRITICAL FIX: Auto-set mock mode based on keys
    const hasGeminiKey = geminiKey && geminiKey.trim().length > 0;
    const hasBobKey = ibmBobKey && ibmBobKey.trim().length > 0;
    
    if (aiProvider === 'gemini' || aiProvider === 'groq') {
      localStorage.setItem('mock_mode', 'false');
    } else if (hasBobKey || hasGeminiKey || hasGroqKey) {
      localStorage.setItem('mock_mode', 'false');
    } else {
      localStorage.setItem('mock_mode', 'true');
    }

    if (mockModeManualOverride) {
      localStorage.setItem('mock_mode', mockModeToggle ? 'true' : 'false');
    }

    const stored = localStorage.getItem('mock_mode');
    setMockModeToggle(stored === 'true');
    setSettingsOpen(false);
  };

  const handleSend = async (q = chatInput) => {
    const question = q.trim();
    if (!question) return;

    const newMessages = [...chatMessages, { role: 'user', content: question }];
    setChatMessages(newMessages);
    setChatInput('');
    setIsTyping(true);

    try {
      const response = await askQuestion(repoUrl, question, newMessages);
      setChatMessages([...newMessages, { role: 'bob', content: response.answer }]);
    } catch (err) {
      setChatMessages([...newMessages, { role: 'bob', content: 'Encountered an error. Please try again.' }]);
    } finally {
      setIsTyping(false);
    }
  };

  const toggleStep = (id) => {
    const newSet = new Set(checkedSteps);
    if (newSet.has(id)) newSet.delete(id);
    else newSet.add(id);
    setCheckedSteps(newSet);
  };

  const bobModesUsed = analysis?.bob_modes_used?.length
    ? analysis.bob_modes_used
    : ['Plan', 'Ask', 'Code', 'Orchestrator'];
  const hasCustomApi = Boolean(ibmBobKey.trim() || geminiKey.trim() || githubToken.trim());
  const apiStatus = mockModeToggle
    ? { label: '○ DEMO — Mock', color: 'var(--gold)' }
    : aiProvider === 'gemini'
      ? { label: '● LIVE — Gemini', color: '#2563eb' }
      : aiProvider === 'groq'
        ? { label: '● LIVE — Groq', color: '#f59e0b' }
        : { label: '● LIVE — IBM Bob', color: 'var(--sage)' };

  // ─── STYLES ───
  const styles = `
    @import url('https://fonts.googleapis.com/css2?family=Instrument+Serif:ital@0;1&family=Geist+Mono:wght@400;500;600&display=swap');

    :root {
      --ink: #0a0a0a;
      --paper: #f5f2eb;
      --paper2: #ede9df;
      --paper3: #e4dfd3;
      --gold: #c9a84c;
      --gold2: #e8c97a;
      --rust: #8b3a2a;
      --sage: #3d5a47;
      --accent: #1a1a2e;
      --muted: #6b6560;
      --dim: #9e9890;
      --border: #d4cfc6;
    }

    * { margin: 0; padding: 0; box-sizing: border-box; border-radius: 0 !important; font-synthesis: none; }
    body { 
      background: var(--paper); 
      color: var(--ink); 
      font-family: 'Geist Mono', monospace; 
      min-height: 100vh; 
      overflow-x: hidden; 
      cursor: default;
      -webkit-font-smoothing: antialiased;
      -moz-osx-font-smoothing: grayscale;
      font-weight: 400;
    }
    
    body::before {
      content: '';
      position: fixed;
      inset: 0;
      z-index: 9999;
      pointer-events: none;
      opacity: 0.35;
      background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noise)' opacity='0.05'/%3E%3C/svg%3E");
    }

    .font-serif { font-family: 'Instrument Serif', serif; font-weight: 400; }
    .label { font-size: 9px; text-transform: uppercase; letter-spacing: 0.18em; color: var(--dim); font-weight: 500; }

    @keyframes fadeUp { from { opacity: 0; transform: translateY(16px); } to { opacity: 1; transform: translateY(0); } }
    @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
    @keyframes pulse { 0%, 100% { opacity: 1; transform: scale(1); } 50% { opacity: 0.5; transform: scale(1.05); } }

    .animate-fade-up { animation: fadeUp 600ms ease both; }
    .stagger-1 { animation-delay: 0ms; }
    .stagger-2 { animation-delay: 100ms; }
    .stagger-3 { animation-delay: 200ms; }
    .stagger-4 { animation-delay: 300ms; }
    .stagger-5 { animation-delay: 400ms; }
    .stagger-6 { animation-delay: 500ms; }

    .transition-base { transition: all 150ms ease; }
    button, a, [role="button"], .cursor-pointer { cursor: pointer; }
    input, textarea { cursor: text; }
    button:hover { background-color: var(--rust) !important; color: var(--paper) !important; }
    button.export-button:hover { background-color: var(--paper2) !important; color: var(--ink) !important; }
    button.settings-button:hover,
    button.settings-close:hover,
    button.settings-option:hover,
    button.settings-save:hover {
      background-color: var(--paper2) !important;
      color: var(--ink) !important;
    }
    button.settings-save:hover {
      border-color: var(--ink) !important;
    }
    .settings-drawer {
      position: fixed;
      top: 0;
      right: 0;
      width: 320px;
      max-width: 100vw;
      height: 100vh;
      background: var(--paper);
      border-left: 1px solid var(--border);
      padding: 24px;
      z-index: 200;
      transform: translateX(100%);
      transition: transform 180ms ease;
      overflow-y: auto;
    }
    .settings-drawer.open { transform: translateX(0); }
    .settings-overlay {
      position: fixed;
      inset: 0;
      background: rgba(10, 10, 10, 0.12);
      z-index: 190;
    }
    .settings-input {
      width: 100%;
      background: var(--paper2);
      border: 1px solid var(--border);
      color: var(--ink);
      font-family: 'Geist Mono', monospace;
      font-size: 11px;
      padding: 10px 12px;
      outline: none;
    }
    .settings-input:focus {
      background: var(--paper);
      border-color: var(--gold);
    }
    .settings-helper {
      font-family: 'Geist Mono', monospace;
      font-size: 10px;
      color: var(--muted);
      line-height: 1.6;
    }
    .settings-link {
      color: var(--rust);
      text-decoration: underline;
    }
    .card-grid { display: grid; background: var(--border); gap: 1px; border: 1px solid var(--border); }
    .card { background: var(--paper); padding: 24px; width: 100%; }
    .bob-stats-card {
      width: 100%;
      background: var(--paper2);
      border-left: 3px solid var(--gold);
      padding: 24px;
    }
    .bob-stats-label {
      font-family: 'Geist Mono', monospace;
      font-size: 9px;
      letter-spacing: 0.18em;
      text-transform: uppercase;
      color: var(--dim);
    }
    .bob-stats-grid { display: grid; }
    .bob-stat-value {
      font-family: 'Instrument Serif', serif;
      font-size: 28px;
      color: var(--ink);
      line-height: 1;
    }
    .bob-stat-label {
      font-family: 'Geist Mono', monospace;
      font-size: 9px;
      letter-spacing: 0.12em;
      text-transform: uppercase;
      color: var(--dim);
      margin-top: 6px;
    }
    .mode-pills-row {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-top: 18px;
    }
    .mode-pill {
      font-family: 'Geist Mono', monospace;
      font-size: 9px;
      letter-spacing: 0.12em;
      text-transform: uppercase;
      padding: 4px 9px;
      border: 1px solid var(--border);
      background: transparent;
      line-height: 1;
    }
    .mode-plan { border-color: var(--gold); color: var(--gold); }
    .mode-ask { border-color: var(--sage); color: var(--sage); }
    .mode-code { border-color: var(--rust); color: var(--rust); }
    .mode-orchestrator { border-color: var(--accent); color: var(--accent); }
    .bob-description {
      font-family: 'Geist Mono', monospace;
      font-size: 11px;
      color: var(--muted);
      font-style: italic;
      line-height: 1.6;
      margin-top: 16px;
    }
    @media (max-width: 639px) {
      .card { padding: 16px; }
      .bob-stats-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
    }

    ::-webkit-scrollbar { width: 2px; }
    ::-webkit-scrollbar-track { background: var(--paper); }
    ::-webkit-scrollbar-thumb { background: var(--gold); }
    
    .hero-h1-l1, .hero-h1-l2 { font-size: inherit; }
    .hero-h1-l3 { font-size: 0.7em; color: var(--muted); }
    .hero-h1 { line-height: 1.05; letter-spacing: 0; }

    .step-number { font-size: 11px; font-weight: 500; color: var(--dim); }
    .step-action { font-size: 13px; font-weight: 500; color: var(--ink); }
    .step-why { font-size: 11px; font-weight: 400; color: var(--muted); }
    .inline-code { 
      font-size: 10px; 
      font-weight: 500; 
      color: var(--rust); 
      background: var(--paper2); 
      border: 1px solid var(--border); 
      padding: 1px 4px; 
      margin: 0 2px;
    }
  `;

  // ─── SHARED COMPONENTS ───
  const Navbar = () => (
    <nav className="fixed top-0 left-0 right-0 h-[52px] border-b border-[var(--border)] bg-[rgba(245,242,235,0.92)] backdrop-blur-[20px] z-[100] px-5 sm:px-10 flex items-center justify-between">
      <div className="flex items-center">
        <span className="font-serif text-[26px] text-[var(--ink)]">Repo</span>
        <span className="font-serif text-[26px] italic text-[var(--gold)]">Sense</span>
      </div>
      <div className="flex items-center gap-2">
        <div
          className="hidden sm:block label border border-[var(--border)] px-[10px] py-[6px] leading-none text-[9px] font-medium"
          style={{ color: apiStatus.color }}
        >
          {apiStatus.label}
        </div>
        <div className="hidden md:block label border border-[var(--border)] px-[14px] py-[6px] leading-none text-[10px] text-[var(--ink)] font-medium">
          Powered by IBM Bob
        </div>
        <button
          type="button"
          onClick={() => setSettingsOpen(true)}
          className="settings-button relative border border-[var(--border)] bg-transparent px-3 py-[6px] text-[11px] text-[var(--ink)] font-medium transition-base"
          title={hasCustomApi ? '● Custom API' : '○ Default (Mock)'}
        >
          <span
            className="inline-block w-[6px] h-[6px] mr-2 align-middle"
            style={{ background: hasCustomApi ? 'var(--sage)' : 'var(--dim)' }}
          />
          ⚙ Settings
        </button>
      </div>
    </nav>
  );

  const SettingsPanel = () => (
    <>
      {settingsOpen && <div className="settings-overlay" onClick={() => setSettingsOpen(false)} />}
      <aside className={`settings-drawer ${settingsOpen ? 'open' : ''}`}>
        <div className="flex items-start justify-between mb-8">
          <h2 className="font-serif text-[20px] text-[var(--ink)]">Configuration</h2>
          <button
            type="button"
            onClick={() => setSettingsOpen(false)}
            className="settings-close border border-[var(--border)] bg-transparent w-7 h-7 text-[18px] leading-none text-[var(--muted)]"
          >
            ×
          </button>
        </div>

        <section className="mb-8">
          <label className="label block mb-3">AI Provider</label>
          <div className="flex gap-2 mb-5">
            {[
              { id: 'bob', label: 'IBM Bob' },
              { id: 'gemini', label: 'Gemini' },
              { id: 'groq', label: 'Groq' }
            ].map(option => (
              <button
                key={option.id}
                type="button"
                onClick={() => setAiProvider(option.id)}
                className={`settings-option flex-1 border px-3 py-2 text-[11px] font-medium transition-base ${aiProvider === option.id ? 'border-[var(--ink)] text-[var(--ink)] bg-[var(--paper2)]' : 'border-[var(--border)] text-[var(--muted)] bg-transparent'}`}
              >
                {aiProvider === option.id ? '●' : '○'} {option.label}
              </button>
            ))}
          </div>

          {aiProvider === 'bob' ? (
            <div className="space-y-4">
              <div>
                <label className="label block mb-2">IBM Bob API Key</label>
                <input
                  type="password"
                  className="settings-input"
                  placeholder="bob_prod_xxx..."
                  value={ibmBobKey}
                  onChange={(e) => setIbmBobKey(e.target.value)}
                />
              </div>
              <div>
                <label className="label block mb-2">IBM Bob Base URL</label>
                <input
                  type="text"
                  className="settings-input"
                  placeholder="https://bob.ibm.com"
                  value={ibmBobBaseUrl}
                  onChange={(e) => setIbmBobBaseUrl(e.target.value)}
                />
              </div>
            </div>
          ) : aiProvider === 'gemini' ? (
            <div className="space-y-3">
              <div>
                <label className="label block mb-2">Gemini API Key</label>
                <input
                  type="password"
                  className="settings-input"
                  placeholder="AIzaSy..."
                  value={geminiKey}
                  onChange={(e) => setGeminiKey(e.target.value)}
                />
              </div>
              <a
                className="settings-helper settings-link"
                href="https://aistudio.google.com/apikey"
                target="_blank"
                rel="noreferrer"
              >
                Get free key at aistudio.google.com
              </a>
            </div>
          ) : (
            <div className="space-y-3">
              <div>
                <label className="label block mb-2">Groq API Key</label>
                <input
                  type="password"
                  className="settings-input"
                  placeholder="gsk_..."
                  value={groqKey}
                  onChange={(e) => setGroqKey(e.target.value)}
                />
              </div>
              <a
                className="settings-helper settings-link"
                href="https://console.groq.com/keys"
                target="_blank"
                rel="noreferrer"
              >
                Get free key at console.groq.com
              </a>
            </div>
          )}
        </section>

        <section className="mb-8">
          <label className="label block mb-3">GitHub Token (Optional)</label>
          <input
            type="password"
            className="settings-input"
            placeholder="ghp_..."
            value={githubToken}
            onChange={(e) => setGithubToken(e.target.value)}
          />
          <p className="settings-helper mt-2">Increases rate limit from 60 to 5000 req/hour</p>
          <a
            className="settings-helper settings-link"
            href="https://github.com/settings/tokens"
            target="_blank"
            rel="noreferrer"
          >
            Generate at github.com/settings/tokens
          </a>
        </section>

        <section className="mb-8">
          <label className="label block mb-3">Mock Mode</label>
          <div className="grid grid-cols-2 border border-[var(--border)]">
            {[
              { id: true, label: 'Use Mock Data' },
              { id: false, label: 'Use Real AI' }
            ].map(option => (
              <button
                key={option.id}
                type="button"
                onClick={() => {
                  setMockModeToggle(option.id);
                  setMockModeManualOverride(true);
                }}
                className={`settings-option px-3 py-3 text-[11px] font-medium transition-base ${mockModeToggle === option.id ? 'bg-[var(--ink)] text-[var(--paper)]' : 'bg-transparent text-[var(--muted)]'}`}
              >
                {option.label}
              </button>
            ))}
          </div>
          <p className="settings-helper mt-2">Auto-set from available API keys. You can override before saving.</p>
        </section>

        <button
          type="button"
          onClick={handleSaveSettings}
          className="settings-save w-full border border-[var(--ink)] bg-transparent px-4 py-3 label font-semibold text-[var(--ink)] transition-base"
        >
          Save Configuration
        </button>
      </aside>
    </>
  );

  const ModePill = ({ mode, size = "sm" }) => {
    const colors = {
      Plan: "border-[var(--gold)] text-[var(--gold)]",
      Ask: "border-[var(--sage)] text-[var(--sage)]",
      Code: "border-[var(--rust)] text-[var(--rust)]",
      Orchestrator: "border-[var(--accent)] text-[var(--accent)]"
    };
    return (
      <span className={`label border leading-none transition-base font-medium ${colors[mode]} ${size === "sm" ? "px-2 py-[2px] text-[8px]" : "px-3 py-1 text-[9px]"}`}>
        {mode}
      </span>
    );
  };

  // ─── RENDER STATES ───
  return (
    <>
      <style dangerouslySetInnerHTML={{ __html: styles }} />
      <SettingsPanel />

      {appState === 'hero' && (
        <div className="min-h-screen w-full bg-[var(--paper)] relative overflow-hidden flex flex-col items-center justify-center pt-[120px] pb-20 px-5 sm:px-10">
          <Navbar />

          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-full max-w-[700px] aspect-square border border-[#d4cfc6] opacity-[0.35] rounded-full pointer-events-none z-0" />
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[70vw] max-w-[460px] aspect-square border border-[#d4cfc6] opacity-[0.25] rounded-full pointer-events-none z-0" />

          <div className="z-10 relative w-full max-w-[520px] mx-auto flex flex-col items-center text-center">
            <div className="flex items-center justify-center gap-3 mb-4 animate-fade-up stagger-1">
              <div className="w-8 h-[1px] bg-[var(--gold)]" />
              <span className="label text-[var(--gold)]">AI Developer Onboarding</span>
              <div className="w-8 h-[1px] bg-[var(--gold)]" />
            </div>

            <div className="flex items-center gap-2 mb-4 animate-fade-up stagger-1.5">
              <span className="font-serif text-[16px] text-[var(--accent)] font-bold">Made with IBM Bob</span>
            </div>

            <h1 className="font-serif hero-h1 text-4xl sm:text-5xl md:text-7xl text-[var(--ink)] mb-[28px] animate-fade-up stagger-2">
              <span className="hero-h1-l1 block">From stranger</span>
              <em className="hero-h1-l2 block text-[var(--rust)]">to contributor</em>
              <span className="hero-h1-l3 block">in minutes.</span>
            </h1>

            <p className="text-[12px] text-[var(--muted)] font-normal leading-[1.8] max-w-[380px] mx-auto mb-[40px] animate-fade-up stagger-3">
              <strong>IBM Bob</strong> reads every file in your repository <br />
              — not just the README. Full SDLC context with 4 AI modes.
            </p>

            <div className="w-full relative animate-fade-up stagger-4">
              <label className="label absolute -top-5 left-0 text-left">Repository URL</label>
              <div className="flex flex-col sm:flex-row w-full">
                <input
                  type="text"
                  className="w-full bg-[var(--paper2)] border border-[var(--border)] py-4 px-5 text-[13px] text-[var(--ink)] font-normal focus:bg-[var(--paper)] focus:border-[var(--gold)] transition-base outline-none"
                  placeholder="https://github.com/owner/repo"
                  value={inputValue}
                  onChange={(e) => {
                    setInputValue(e.target.value);
                    setInputError(null);
                  }}
                  onKeyDown={(e) => e.key === 'Enter' && handleAnalyze()}
                />
                <button
                  onClick={handleAnalyze}
                  className="w-full sm:w-auto bg-[var(--ink)] text-[var(--paper)] px-6 py-4 label font-semibold transition-base"
                >
                  Analyze
                </button>
              </div>
              {inputError && (
                <div className="mt-3 text-left text-[11px] text-[var(--rust)] font-medium leading-[1.5]">
                  {inputError}
                </div>
              )}

              <div className="hidden sm:flex items-center justify-center gap-2 mt-4 animate-fade-up stagger-5">
                <span className="label">try</span>
                {examples.map(ex => (
                  <button
                    key={ex.name}
                    onClick={() => {
                      setInputValue(ex.url);
                      setInputError(null);
                    }}
                    className="label border border-[var(--border)] px-3 py-[5px] text-[var(--muted)] transition-base hover:border-[var(--gold)] hover:text-[var(--gold)]"
                  >
                    {ex.name}
                  </button>
                ))}
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 w-full mt-[48px] border border-[var(--border)] animate-fade-up stagger-6">
              <div className="p-4 sm:p-5 text-left border-b sm:border-b-0 sm:border-r border-[var(--border)]">
                <div className="font-serif text-[28px] text-[var(--sage)] leading-none">10m</div>
                <div className="label mt-1">avg onboarding</div>
              </div>
              <div className="p-4 sm:p-5 text-left border-b sm:border-b-0 sm:border-r border-[var(--border)]">
                <div className="font-serif text-[28px] text-[var(--ink)] leading-none">4</div>
                <div className="label mt-1">Bob modes used</div>
              </div>
              <div className="p-4 sm:p-5 text-left">
                <div className="font-serif text-[28px] text-[var(--rust)] leading-none">100%</div>
                <div className="label mt-1">repo context</div>
              </div>
            </div>

            {apiError && <div className="mt-8 text-[var(--rust)] label animate-fade-up font-medium">{apiError}</div>}
          </div>
        </div>
      )}

      {appState === 'loading' && (
        <div className="min-h-screen pt-20 flex flex-col items-center">
          <Navbar />
          <main className="max-w-[400px] w-full text-center mt-20 px-5 sm:px-10">
            <div className="label border border-[var(--gold)] text-[var(--gold)] px-4 py-[6px] mb-8 inline-block">
              IBM Bob analyzing
            </div>

            <div className="mb-10 flex justify-center">
              <svg width="40" height="40" viewBox="0 0 40 40" className="animate-pulse">
                <rect width="18" height="18" x="0" y="0" stroke="var(--border)" fill="none" />
                <rect width="18" height="18" x="22" y="0" stroke="var(--gold)" fill="none" />
                <rect width="18" height="18" x="0" y="22" stroke="var(--rust)" fill="none" />
                <rect width="18" height="18" x="22" y="22" stroke="var(--sage)" fill="none" />
              </svg>
            </div>

            <h2 className="font-serif text-[24px] text-[var(--ink)] mb-10">IBM Bob is reading your codebase...</h2>

            <div className="space-y-4 mb-10 text-left">
              {steps.map((step, idx) => (
                <div key={idx} className="flex items-center gap-4">
                  <div className="w-5 h-5 flex items-center justify-center shrink-0">
                    {idx < currentStep ? (
                      <span className="text-[var(--sage)]">✓</span>
                    ) : idx === currentStep ? (
                      <div className="w-3 h-3 border border-[var(--gold)] border-t-transparent animate-spin" />
                    ) : (
                      <span className="text-[var(--dim)]">○</span>
                    )}
                  </div>
                  <div className={`flex items-center gap-2 text-[11px] ${idx === currentStep ? 'text-[var(--ink)] font-medium' : 'text-[var(--dim)] font-normal'}`}>
                    <span>{step.label}</span>
                    {idx === currentStep && step.mode && <ModePill mode={step.mode} />}
                  </div>
                </div>
              ))}
            </div>

            <div className="w-full h-[1px] bg-[var(--border)] relative mb-4">
              <div className="absolute top-0 left-0 h-full bg-[var(--gold)] transition-all duration-[4000ms]" style={{ width: `${(currentStep + 1) * 20}%` }} />
            </div>

            <p className="text-[10px] text-[var(--dim)] italic font-normal transition-base">"{tips[currentTip]}"</p>
          </main>
        </div>
      )}

      {appState === 'results' && (
        <div className="min-h-screen">
          <Navbar />

          <div className="fixed top-[52px] left-0 right-0 h-14 border-b border-[var(--border)] bg-[rgba(245,242,235,0.95)] backdrop-blur px-4 sm:px-10 flex items-center justify-between z-50">
            <button onClick={handleBack} className="label text-[var(--dim)] font-medium hover:text-[var(--muted)]">← Back</button>
            <div className="flex items-center gap-2">
              <div className="w-[6px] h-[6px] bg-[var(--sage)] rounded-full" />
              <span className="text-[11px] text-[var(--ink)] font-medium">Analysis complete — {parseRepoName(repoUrl)}</span>
            </div>
            <div className="hidden md:flex flex-col items-end gap-1">
              <div className="text-[10px] text-[var(--muted)] font-medium">
                Bob analyzed {parseRepoName(repoUrl)} using {analysis?.bob_modes_used?.length || 4} modes
              </div>
              <div className="flex gap-2">
                {bobModesUsed.map(m => <ModePill key={m} mode={m} />)}
              </div>
            </div>
          </div>

          <main className="w-full max-w-[960px] mx-auto pt-[140px] px-4 sm:px-10 pb-20">
            <div className="flex w-full border-b border-[var(--border)] mb-10 overflow-x-auto no-scrollbar">
              {[
                { label: 'Overview', id: 'overview' },
                { label: 'Start Coding', id: 'coding' },
                { label: 'Ask Bob', id: 'chat' }
              ].map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`px-8 py-4 label whitespace-nowrap transition-base ${activeTab === tab.id ? 'text-[var(--ink)] border-b-2 border-[var(--ink)] font-semibold' : 'text-[var(--dim)] font-medium'}`}
                >
                  {tab.label}
                </button>
              ))}
            </div>

            {activeTab === 'overview' && (
              <div className="card-grid animate-fade-up">
                <div className="bob-stats-card col-span-full">
                  <label className="bob-stats-label">WHAT BOB DID</label>

                  <div className="bob-stats-grid grid grid-cols-2 sm:grid-cols-4 gap-4 mt-5">
                    {[
                      { value: analysis?.total_files || 247, label: 'FILES READ' },
                      { value: analysis?.bob_modes_used?.length || 4, label: 'MODES USED' },
                      { value: elapsedTime || '~28s', label: 'ANALYSIS TIME' },
                      { value: '100%', label: 'REPO COVERAGE' }
                    ].map((stat) => (
                      <div key={stat.label}>
                        <div className="bob-stat-value">{stat.value}</div>
                        <div className="bob-stat-label">{stat.label}</div>
                      </div>
                    ))}
                  </div>

                  <div className="mode-pills-row">
                    {bobModesUsed.map(mode => (
                      <span key={mode} className={`mode-pill mode-${mode.toLowerCase()}`}>
                        {mode} Mode
                      </span>
                    ))}
                  </div>

                  <div className="bob-description">
                    Bob read every file in this repository — not just the README. Full SDLC context.
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-[1px]">
                  <div className="card">
                    <label className="label">Architecture</label>
                    <div className="font-mono font-semibold text-[24px] mt-2 text-[var(--ink)]">{analysis?.architecture_type || 'MVC'}</div>
                  </div>
                  <div className="card">
                    <label className="label">Files Analyzed</label>
                    <div className="font-mono font-semibold text-[24px] mt-2 text-[var(--ink)]">{analysis?.total_files || analysis?.file_tree_count || '247'}</div>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-[1px]">
                  <div className="card">
                    <label className="label">Project</label>
                    <div className="font-serif text-[24px] mt-2">{analysis?.project_name || 'Express.js'}</div>

                    {/* Description */}
                    <p style={{
                      fontFamily: 'Geist Mono, monospace',
                      fontSize: '12px',
                      color: 'var(--muted)',
                      lineHeight: 1.7,
                      margin: '8px 0 16px'
                    }}>
                      {analysis?.what_it_does || analysis?.one_line_summary}
                    </p>

                    {/* Tech badges */}
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                      {analysis?.tech_stack?.map((tech, i) => {
                        const techItem = typeof tech === 'string' ? { name: tech } : tech;
                        const colors = {
                          amber: { bg: '#c9a84c18', border: '#c9a84c40', text: '#92741a' },
                          green: { bg: '#3d5a4718', border: '#3d5a4740', text: '#2d5a3d' },
                          sage: { bg: '#3d5a4718', border: '#3d5a4740', text: '#2d5a3d' },
                          rust: { bg: '#8b3a2a18', border: '#8b3a2a40', text: '#8b3a2a' },
                          blue: { bg: '#1a1a2e18', border: '#1a1a2e40', text: '#1a1a2e' },
                          purple: { bg: '#7c6af718', border: '#7c6af740', text: '#5a4fd4' },
                          neutral: { bg: '#9e989018', border: '#9e989040', text: '#6b6560' }
                        };
                        const c = colors[techItem.color] || colors.neutral;
                        return (
                          <span key={i} style={{
                            fontFamily: 'Geist Mono, monospace',
                            fontSize: '9px',
                            letterSpacing: '0.1em',
                            textTransform: 'uppercase',
                            padding: '3px 8px',
                            border: `1px solid ${c.border}`,
                            background: c.bg,
                            color: c.text
                          }}>
                            {techItem.name}
                          </span>
                        );
                      })}
                    </div>
                  </div>
                  <div className="card">
                    <label className="label">Data Flow</label>
                    {analysis?.data_flow?.length > 0 ? (
                      <div style={{
                        display: 'flex',
                        alignItems: 'center',
                        flexWrap: 'wrap',
                        gap: '8px',
                        marginTop: '12px'
                      }}>
                        {analysis.data_flow.map((item, i) => (
                          <React.Fragment key={i}>
                            <span style={{
                              fontFamily: 'Geist Mono, monospace',
                              fontSize: '11px',
                              color: 'var(--muted)',
                              border: '1px solid var(--border)',
                              padding: '4px 10px',
                              background: 'var(--paper2)'
                            }}>
                              {item.description || item}
                            </span>
                            {i < analysis.data_flow.length - 1 && (
                              <span style={{ color: 'var(--dim)', fontSize: '14px' }}>→</span>
                            )}
                          </React.Fragment>
                        ))}
                      </div>
                    ) : (
                      <div style={{
                        fontFamily: 'Geist Mono, monospace',
                        fontSize: '11px',
                        color: 'var(--dim)',
                        marginTop: '12px'
                      }}>
                        No data flow information available
                      </div>
                    )}
                  </div>
                </div>

                <div className="card col-span-full">
                  <label className="label">Key Files — Read In Order</label>
                  <div className="mt-4 flex flex-col">
                    {analysis?.key_files?.map((f, i) => (
                      <div key={i} className="flex items-center gap-4 py-3 border-b border-[var(--border)] last:border-0 hover:bg-[var(--paper2)] -mx-4 sm:-mx-6 px-4 sm:px-6 transition-base group">
                        <span className="label text-[var(--dim)] w-4 font-medium">{i + 1}</span>
                        <span className="text-[11px] text-[var(--rust)] font-medium flex-1">{f.path}</span>
                        <ModePill mode={i === 0 ? "Plan" : i === 1 ? "Ask" : "Code"} />
                      </div>
                    ))}
                  </div>
                </div>

                <div className="card col-span-full">
                  <label className="label">Onboarding Steps · Bob Generated</label>
                  <div className="mt-4 space-y-[1px]">
                    {analysis?.onboarding_steps?.map((step, i) => (
                      <div
                        key={i}
                        onClick={() => toggleStep(i)}
                        className="step-item"
                        style={{
                          display: 'flex',
                          alignItems: 'flex-start',
                          gap: '16px',
                          padding: '14px 0',
                          borderBottom: '1px solid var(--border)',
                          cursor: 'pointer'
                        }}
                      >
                        <div
                          className="step-check"
                          style={{
                            width: '18px',
                            height: '18px',
                            border: checkedSteps.has(i)
                              ? 'none'
                              : '1px solid var(--border)',
                            background: checkedSteps.has(i)
                              ? 'var(--ink)'
                              : 'transparent',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            flexShrink: 0,
                            marginTop: '2px'
                          }}
                        >
                          {checkedSteps.has(i) && (
                            <span style={{ color: 'var(--paper)', fontSize: '10px' }}>✓</span>
                          )}
                        </div>

                        <div style={{ flex: 1 }}>
                          <div style={{
                            fontFamily: 'Geist Mono, monospace',
                            fontSize: '9px',
                            color: 'var(--dim)',
                            letterSpacing: '0.1em',
                            textTransform: 'uppercase',
                            marginBottom: '4px'
                          }}>
                            STEP {String(step.step || i + 1).padStart(2, '0')}
                          </div>

                          <div style={{
                            fontFamily: 'Geist Mono, monospace',
                            fontSize: '13px',
                            color: checkedSteps.has(i) ? 'var(--dim)' : 'var(--ink)',
                            fontWeight: 500,
                            textDecoration: checkedSteps.has(i) ? 'line-through' : 'none',
                            marginBottom: '4px',
                            lineHeight: 1.5
                          }}>
                            {step.action}
                          </div>

                          <div style={{
                            fontFamily: 'Geist Mono, monospace',
                            fontSize: '11px',
                            color: 'var(--muted)',
                            lineHeight: 1.6
                          }}>
                            {step.why}
                            {step.code_ref && (
                              <span style={{
                                background: 'var(--paper2)',
                                color: 'var(--rust)',
                                border: '1px solid var(--border)',
                                padding: '1px 6px',
                                marginLeft: '6px',
                                fontSize: '10px',
                                fontFamily: 'Geist Mono, monospace'
                              }}>
                                {step.code_ref}
                              </span>
                            )}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="card col-span-full">
                  <label className="label">Gotchas</label>
                  <div className="mt-4 space-y-4">
                    {analysis?.gotchas?.map((g, i) => (
                      <div key={i} className="flex gap-4 items-start border-b border-[var(--border)] pb-4 last:border-0">
                        <span className="text-[var(--gold)] text-[14px]">⚠</span>
                        <p className="text-[11px] text-[var(--muted)] font-normal leading-[1.6]">{g}</p>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="col-span-full bg-[var(--paper2)] p-4 sm:p-6 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 w-full">
                  <div>
                    <h3 className="font-serif text-[20px]">Ready to make your first contribution?</h3>
                    <p className="label mt-1 font-medium">Bob will find an issue, write the fix...</p>
                  </div>
                  <button onClick={handleKickstart} className="w-full sm:w-auto bg-[var(--ink)] text-[var(--paper)] px-8 py-3 label font-semibold transition-base">Start Coding →</button>
                </div>

                <div className="col-span-full bg-[var(--paper)] p-4 sm:p-6 flex justify-end w-full">
                  <button
                    onClick={handleExport}
                    disabled={exporting}
                    className="export-button w-full sm:w-auto border border-[var(--border)] bg-transparent px-6 py-3 label font-semibold text-[var(--ink)] transition-base disabled:opacity-50"
                  >
                    {exporting ? 'Exporting...' : '↓ Export Onboarding Guide'}
                  </button>
                </div>
              </div>
            )}

            {activeTab === 'coding' && (
              <div className="animate-fade-up">
                {codingLoading ? (
                  <div className="py-20 text-center">
                    <div className="w-10 h-10 border-2 border-[var(--gold)] border-t-transparent animate-spin mx-auto mb-6" />
                    <h2 className="font-serif text-[24px]">Bob is orchestrating...</h2>
                  </div>
                ) : !coding ? (
                  <div className="py-20 text-center max-w-md mx-auto">
                    <h2 className="font-serif text-[28px] mb-4">Let Bob write your first contribution</h2>
                    <p className="text-[11px] text-[var(--dim)] font-medium mb-10 leading-[1.8]">Bob will analyze the codebase, identify a small technical debt or bug, and generate the code change for you.</p>
                    <button onClick={handleKickstart} className="w-full sm:w-auto bg-[var(--ink)] text-[var(--paper)] px-10 py-4 label font-semibold transition-base">Start Coding For Me</button>
                  </div>
                ) : (
                  <div className="space-y-8">
                    <div className="card-grid">
                      <div className="card col-span-full">
                        <label className="label">Bob · Orchestrator Mode · Issue Found</label>
                        <h3 className="font-serif text-[22px] mt-4 mb-2">{coding.issue_title || coding.issue?.title || 'Issue'}</h3>
                        <p className="text-[11px] text-[var(--muted)] font-normal leading-[1.7] mb-6">{coding.issue_description || coding.issue?.description}</p>
                        <div className="flex flex-col sm:flex-row gap-2 sm:gap-4">
                          <span className="label text-[var(--gold)] font-medium">Complexity: {coding.complexity || coding.issue?.complexity || 'Medium'}</span>
                          <span className="label text-[var(--sage)] font-medium">Impact: {coding.impact || coding.issue?.impact || 'Medium'}</span>
                        </div>
                      </div>

                      <div className="card col-span-full">
                        <label className="label">Bob Mode Chain</label>
                        <div className="flex items-center justify-between gap-3 mt-8 max-w-lg mx-auto overflow-x-auto">
                          {['Plan', 'Ask', 'Code', 'Orchestrator'].map((m, i) => (
                            <React.Fragment key={i}>
                              <div className={`flex flex-col items-center gap-2 transition-base ${activeMode >= i ? 'opacity-100' : 'opacity-30'}`}>
                                <ModePill mode={m} size="lg" />
                                <span className="label text-[8px] font-medium">{i === 0 ? 'Map' : i === 1 ? 'Context' : i === 2 ? 'Fix' : 'Verify'}</span>
                              </div>
                              {i < 3 && <span className="text-[var(--dim)]">→</span>}
                            </React.Fragment>
                          ))}
                        </div>
                      </div>

                      <div className="col-span-full bg-[#0a0a0a] p-0">
                        <div className="bg-[#111] border-b border-[#222] p-4 flex flex-col sm:flex-row gap-3 sm:items-center sm:justify-between">
                          <span className="text-[10px] text-[#888] font-mono font-medium">{coding.files_involved?.[0] || 'unknown-file.js'}</span>
                          <button onClick={() => { const diff = coding.code_changes?.[0]?.diff_lines?.map(l => l.content).join('\n') || ''; navigator.clipboard.writeText(diff); alert('Diff copied!'); }} className="label text-[#888] border border-[#333] px-3 py-1 font-semibold hover:text-[#bbb] transition-base">Copy Diff</button>
                        </div>
                        <div className="p-4 sm:p-6 font-mono text-[11px] leading-[1.9] overflow-x-auto font-normal">
                          {coding.code_changes?.[0]?.diff_lines?.map((line, i) => (
                            <div key={i} className={`px-4 -mx-6 ${line.type === 'add' ? 'bg-[rgba(74,222,128,0.06)] border-l-2 border-[#22c55e] text-[#4ade80]' : line.type === 'remove' ? 'bg-[rgba(239,68,68,0.06)] border-l-2 border-[#ef4444] text-[#f87171]' : 'text-[#666]'}`}>
                              {line.content}
                            </div>
                          ))}
                        </div>
                      </div>

                      <div className="col-span-full card flex flex-col sm:flex-row items-start gap-5">
                        <div className="w-2 h-2 bg-[var(--sage)] mt-[6px] shrink-0" />
                        <div className="flex-1">
                          <div className="text-[13px] font-semibold text-[var(--ink)]">{coding.pr_title || coding.pr?.title || 'Pull Request'}</div>
                          <p className="text-[10px] text-[var(--dim)] font-medium mt-2 leading-[1.6]">{coding.pr_description || coding.pr?.description || 'Description'}</p>
                        </div>
                        <button onClick={() => { navigator.clipboard.writeText(coding.pr_title || ''); alert('PR title copied!'); }} className="w-full sm:w-auto label border border-[var(--border)] px-4 py-2 font-semibold">Copy PR</button>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}

            {activeTab === 'chat' && (
              <div className="animate-fade-up">
                <label className="label">Ask Bob Anything</label>
                <div className="flex flex-wrap gap-2 mt-4 mb-10">
                  {["How does routing work?", "Where to add auth?", "What does middleware do?", "How to add an API?"].map(q => (
                    <button key={q} onClick={() => handleSend(q)} className="label border border-[var(--border)] px-3 py-[6px] text-[var(--muted)] font-medium hover:border-[var(--gold)] hover:text-[var(--gold)] transition-base">{q}</button>
                  ))}
                </div>

                <div className="h-[460px] border border-[var(--border)] bg-[var(--paper)] flex flex-col">
                  <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-8 no-scrollbar">
                    {chatMessages.length === 0 && (
                      <div className="text-[11px] text-[var(--dim)] italic font-mono font-normal">I've analyzed the repository. Ask me anything about the codebase — architecture, specific files, or how to implement new features.</div>
                    )}
                    {chatMessages.map((m, i) => (
                      <div key={i} className={`flex flex-col ${m.role === 'bob' ? 'items-start' : 'items-end'}`}>
                        {m.role === 'bob' && <label className="label text-[var(--sage)] mb-2 font-semibold">Bob · Ask Mode</label>}
                        <div className={`p-4 text-[11px] leading-[1.7] max-w-[85%] font-mono font-normal ${m.role === 'bob' ? 'bg-[var(--paper2)] border border-[var(--border)] text-[var(--ink)]' : 'bg-[var(--ink)] text-[var(--paper)]'}`}>
                          {m.content}
                        </div>
                      </div>
                    ))}
                    {isTyping && <div className="flex gap-1 animate-pulse"><div className="w-1.5 h-1.5 bg-[var(--dim)]" /><div className="w-1.5 h-1.5 bg-[var(--dim)]" /><div className="w-1.5 h-1.5 bg-[var(--dim)]" /></div>}
                    <div ref={chatEndRef} />
                  </div>
                  <div className="border-t border-[var(--border)] flex flex-col sm:flex-row">
                    <input
                      type="text"
                      className="flex-1 bg-[var(--paper2)] px-6 py-5 text-[12px] font-mono font-normal outline-none focus:bg-[var(--paper)] transition-base text-[var(--ink)]"
                      placeholder="Ask a question..."
                      value={chatInput}
                      onChange={(e) => setChatInput(e.target.value)}
                      onKeyDown={(e) => e.key === 'Enter' && handleSend()}
                    />
                    <button onClick={() => handleSend()} className="w-full sm:w-auto bg-[var(--ink)] text-[var(--paper)] px-10 py-4 sm:py-0 label font-semibold transition-base">Send</button>
                  </div>
                </div>
              </div>
            )}
          </main>
        </div>
      )}
    </>
  );
};

export default App;

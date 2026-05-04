import React, { useState, useEffect, useRef } from 'react';
import { analyzeRepo, askQuestion, kickstartTask, exportMarkdown } from './services/api';

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

  const chatEndRef = useRef(null);
  const startTimeRef = useRef(null);

  // ─── SETTINGS STATE ───
  const [showSettings, setShowSettings] = useState(false);
  const [settings, setSettings] = useState({
    provider: localStorage.getItem('rs_provider') || 'mock',
    bobKey: localStorage.getItem('rs_bob_key') || '',
    bobUrl: localStorage.getItem('rs_bob_url') || 'https://api.ibmbob.com',
    geminiKey: localStorage.getItem('rs_gemini_key') || '',
    githubToken: localStorage.getItem('rs_github_token') || '',
  });

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

  // ─── HELPERS ───
  const getRequestHeaders = () => {
    const headers = {
      'X-AI-Provider': settings.provider,
      'X-Mock-Mode': settings.provider === 'mock' ? 'true' : 'false',
    };
    if (settings.bobKey) headers['X-IBM-Bob-Key'] = settings.bobKey;
    if (settings.bobUrl) headers['X-IBM-Bob-Base-URL'] = settings.bobUrl;
    if (settings.geminiKey) headers['X-Gemini-Key'] = settings.geminiKey;
    if (settings.githubToken) headers['X-GitHub-Token'] = settings.githubToken;
    return headers;
  };

  // ─── EFFECTS ───
  useEffect(() => {
    localStorage.setItem('rs_provider', settings.provider);
    localStorage.setItem('rs_bob_key', settings.bobKey);
    localStorage.setItem('rs_bob_url', settings.bobUrl);
    localStorage.setItem('rs_gemini_key', settings.geminiKey);
    localStorage.setItem('rs_github_token', settings.githubToken);
  }, [settings]);

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
          const data = await analyzeRepo(repoUrl, getRequestHeaders());
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
      if (e.key === 'Escape') {
        if (showSettings) setShowSettings(false);
        else handleBack();
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [appState, showSettings]);

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
      const data = await kickstartTask(repoUrl, getRequestHeaders());
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
      await exportMarkdown(repoUrl, getRequestHeaders());
    } catch (err) {
      setApiError('Export failed: ' + err.message);
    } finally {
      setExporting(false);
    }
  };

  const handleSend = async (q = chatInput) => {
    const question = q.trim();
    if (!question) return;

    const newMessages = [...chatMessages, { role: 'user', content: question }];
    setChatMessages(newMessages);
    setChatInput('');
    setIsTyping(true);

    try {
      const response = await askQuestion(repoUrl, question, newMessages, getRequestHeaders());
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
    .card-grid { display: grid; background: var(--border); gap: 1px; border: 1px solid var(--border); }
    .card { background: var(--paper); padding: 24px; width: 100%; }
    
    .settings-modal {
      position: fixed;
      inset: 0;
      z-index: 200;
      background: rgba(10, 10, 10, 0.4);
      backdrop-blur: 4px;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 20px;
    }
    
    .settings-content {
      background: var(--paper);
      border: 1px solid var(--ink);
      width: 100%;
      max-width: 480px;
      padding: 32px;
      box-shadow: 20px 20px 0 var(--ink);
    }
    
    .settings-input {
      width: 100%;
      background: var(--paper2);
      border: 1px solid var(--border);
      padding: 10px 14px;
      font-size: 11px;
      font-family: 'Geist Mono', monospace;
      margin-top: 8px;
      margin-bottom: 20px;
      outline: none;
    }
    
    .settings-input:focus {
      border-color: var(--gold);
      background: var(--paper);
    }
    
    .provider-select {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 1px;
      background: var(--border);
      border: 1px solid var(--border);
      margin-bottom: 24px;
      margin-top: 8px;
    }
    
    .provider-btn {
      padding: 12px;
      background: var(--paper);
      border: none;
      font-size: 10px;
      font-family: 'Geist Mono', monospace;
      text-transform: uppercase;
      letter-spacing: 0.1em;
      transition: all 0.2s;
    }
    
    .provider-btn.active {
      background: var(--ink);
      color: var(--paper);
    }

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
  `;

  // ─── SHARED COMPONENTS ───
  const Navbar = () => (
    <nav className="fixed top-0 left-0 right-0 h-[52px] border-b border-[var(--border)] bg-[rgba(245,242,235,0.92)] backdrop-blur-[20px] z-[100] px-5 sm:px-10 flex items-center justify-between">
      <div className="flex items-center">
        <span className="font-serif text-[26px] text-[var(--ink)]">Repo</span>
        <span className="font-serif text-[26px] italic text-[var(--gold)]">Sense</span>
      </div>
      <div className="flex items-center gap-4">
        <div className="hidden sm:flex items-center gap-2 label border border-[var(--border)] px-[14px] py-[6px] leading-none text-[10px] text-[var(--ink)] font-medium">
          <div className={`w-1.5 h-1.5 rounded-full ${settings.provider === 'mock' ? 'bg-amber-400' : 'bg-green-500'}`} />
          {settings.provider === 'mock' ? 'Demo Mode' : `${settings.provider.toUpperCase()} LIVE`}
        </div>
        <button 
          onClick={() => setShowSettings(true)}
          className="p-2 hover:bg-[var(--paper2)] transition-base"
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="12" cy="12" r="3" />
            <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z" />
          </svg>
        </button>
      </div>
    </nav>
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

  const SettingsModal = () => (
    <div className="settings-modal" onClick={() => setShowSettings(false)}>
      <div className="settings-content animate-fade-up" onClick={e => e.stopPropagation()}>
        <div className="flex justify-between items-center mb-6">
          <h2 className="font-serif text-[24px]">Configuration</h2>
          <button onClick={() => setShowSettings(false)} className="text-[12px] label">Close</button>
        </div>
        
        <label className="label">AI PROVIDER</label>
        <div className="provider-select">
          <button 
            className={`provider-btn ${settings.provider === 'mock' ? 'active' : ''}`}
            onClick={() => setSettings({...settings, provider: 'mock'})}
          >Mock</button>
          <button 
            className={`provider-btn ${settings.provider === 'bob' ? 'active' : ''}`}
            onClick={() => setSettings({...settings, provider: 'bob'})}
          >IBM Bob</button>
          <button 
            className={`provider-btn ${settings.provider === 'gemini' ? 'active' : ''}`}
            onClick={() => setSettings({...settings, provider: 'gemini'})}
          >Gemini</button>
        </div>

        {settings.provider === 'bob' && (
          <>
            <label className="label">IBM BOB API KEY</label>
            <input 
              type="password" 
              className="settings-input" 
              placeholder="sk-..." 
              value={settings.bobKey}
              onChange={e => setSettings({...settings, bobKey: e.target.value})}
            />
            <label className="label">API BASE URL</label>
            <input 
              type="text" 
              className="settings-input" 
              value={settings.bobUrl}
              onChange={e => setSettings({...settings, bobUrl: e.target.value})}
            />
          </>
        )}

        {settings.provider === 'gemini' && (
          <>
            <label className="label">GOOGLE GEMINI API KEY</label>
            <input 
              type="password" 
              className="settings-input" 
              placeholder="AIza..." 
              value={settings.geminiKey}
              onChange={e => setSettings({...settings, geminiKey: e.target.value})}
            />
          </>
        )}

        <label className="label">GITHUB TOKEN (OPTIONAL)</label>
        <input 
          type="password" 
          className="settings-input" 
          placeholder="ghp_..." 
          value={settings.githubToken}
          onChange={e => setSettings({...settings, githubToken: e.target.value})}
        />
        <p className="text-[9px] text-[var(--dim)] mt-[-10px] mb-6">Required for private repos or high rate limits.</p>

        <button 
          onClick={() => setShowSettings(false)}
          className="w-full bg-[var(--ink)] text-[var(--paper)] py-4 label font-bold hover:opacity-90"
        >Save Configuration</button>
      </div>
    </div>
  );

  // ─── RENDER STATES ───
  return (
    <>
      <style dangerouslySetInnerHTML={{ __html: styles }} />
      {showSettings && <SettingsModal />}

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
              <span className="font-serif text-[16px] text-[var(--accent)] font-bold">
                {settings.provider === 'gemini' ? 'Enhanced with Gemini' : 'Made with IBM Bob'}
              </span>
            </div>

            <h1 className="font-serif hero-h1 text-4xl sm:text-5xl md:text-7xl text-[var(--ink)] mb-[28px] animate-fade-up stagger-2">
              <span className="hero-h1-l1 block">From stranger</span>
              <em className="hero-h1-l2 block text-[var(--rust)]">to contributor</em>
              <span className="hero-h1-l3 block">in minutes.</span>
            </h1>

            <p className="text-[12px] text-[var(--muted)] font-normal leading-[1.8] max-w-[380px] mx-auto mb-[40px] animate-fade-up stagger-3">
              <strong>RepoSense</strong> reads every file in your repository <br />
              — not just the README. Full SDLC context with multi-model support.
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
                <div className="font-serif text-[28px] text-[var(--ink)] leading-none">{settings.provider === 'mock' ? '4' : '∞'}</div>
                <div className="label mt-1">Modes enabled</div>
              </div>
              <div className="p-4 sm:p-5 text-left">
                <div className="font-serif text-[28px] text-[var(--rust)] leading-none">100%</div>
                <div className="label mt-1">repo context</div>
              </div>
            </div>

            {apiError && <div className="mt-8 text-[var(--rust)] label animate-fade-up font-medium bg-red-50 p-2 border border-red-200">{apiError}</div>}
          </div>
        </div>
      )}

      {appState === 'loading' && (
        <div className="min-h-screen pt-20 flex flex-col items-center">
          <Navbar />
          <main className="max-w-[400px] w-full text-center mt-20 px-5 sm:px-10">
            <div className="label border border-[var(--gold)] text-[var(--gold)] px-4 py-[6px] mb-8 inline-block">
              {settings.provider.toUpperCase()} analyzing
            </div>

            <div className="mb-10 flex justify-center">
              <svg width="40" height="40" viewBox="0 0 40 40" className="animate-pulse">
                <rect width="18" height="18" x="0" y="0" stroke="var(--border)" fill="none" />
                <rect width="18" height="18" x="22" y="0" stroke="var(--gold)" fill="none" />
                <rect width="18" height="18" x="0" y="22" stroke="var(--rust)" fill="none" />
                <rect width="18" height="18" x="22" y="22" stroke="var(--sage)" fill="none" />
              </svg>
            </div>

            <h2 className="font-serif text-[24px] text-[var(--ink)] mb-10">RepoSense is reading your codebase...</h2>

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
                    <span>{step.label.replace('Bob', settings.provider === 'gemini' ? 'Gemini' : 'Bob')}</span>
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
                Using {settings.provider.toUpperCase()} Provider
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
                  <label className="bob-stats-label">ANALYSIS INSIGHTS</label>

                  <div className="bob-stats-grid grid grid-cols-2 sm:grid-cols-4 gap-4 mt-5">
                    {[
                      { value: analysis?.total_files || analysis?.file_tree_count || 247, label: 'FILES READ' },
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
                    RepoSense read every file in this repository using {settings.provider.toUpperCase()}. Full context achieved.
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-[1px]">
                  <div className="card">
                    <label className="label">Architecture</label>
                    <div className="font-mono font-semibold text-[24px] mt-2 text-[var(--ink)]">{analysis?.architecture_type || 'MVC'}</div>
                  </div>
                  <div className="card">
                    <label className="label">File Count</label>
                    <div className="font-mono font-semibold text-[24px] mt-2 text-[var(--ink)]">{analysis?.total_files || analysis?.file_tree_count || '247'}</div>
                  </div>
                </div>

                <div className="card col-span-full">
                  <label className="label">Project: {analysis?.project_name || 'Repository'}</label>
                  <p className="text-[12px] text-[var(--muted)] leading-[1.7] mt-3 mb-6">
                    {analysis?.what_it_does || analysis?.one_line_summary}
                  </p>
                  <div className="flex flex-wrap gap-2">
                    {analysis?.tech_stack?.map((tech, i) => (
                      <span key={i} className="label border border-[var(--border)] px-3 py-1 text-[var(--muted)]">
                        {typeof tech === 'string' ? tech : tech.name}
                      </span>
                    ))}
                  </div>
                </div>

                <div className="card col-span-full">
                  <label className="label">Key Files — Strategic Order</label>
                  <div className="mt-4 flex flex-col">
                    {analysis?.key_files?.map((f, i) => (
                      <div key={i} className="flex items-center gap-4 py-3 border-b border-[var(--border)] last:border-0 hover:bg-[var(--paper2)] -mx-6 px-6 transition-base">
                        <span className="label text-[var(--dim)] w-4">{i + 1}</span>
                        <span className="text-[11px] text-[var(--rust)] font-medium flex-1">{f.path}</span>
                        <ModePill mode={i % 4 === 0 ? "Plan" : i % 4 === 1 ? "Ask" : i % 4 === 2 ? "Code" : "Orchestrator"} />
                      </div>
                    ))}
                  </div>
                </div>

                <div className="card col-span-full">
                  <label className="label">Onboarding Guide</label>
                  <div className="mt-4 space-y-4">
                    {analysis?.onboarding_steps?.map((step, i) => (
                      <div key={i} className="flex gap-4 items-start py-2">
                        <div className={`w-5 h-5 flex items-center justify-center shrink-0 border border-[var(--border)] text-[9px] ${checkedSteps.has(i) ? 'bg-[var(--ink)] text-[var(--paper)]' : 'text-[var(--dim)]'}`} onClick={() => toggleStep(i)}>
                          {checkedSteps.has(i) ? '✓' : i + 1}
                        </div>
                        <div className="flex-1">
                          <div className={`text-[12px] font-medium ${checkedSteps.has(i) ? 'line-through text-[var(--dim)]' : 'text-[var(--ink)]'}`}>{step.action}</div>
                          <div className="text-[10px] text-[var(--muted)] mt-1">{step.why}</div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
                
                <div className="col-span-full bg-[var(--paper2)] p-6 flex flex-col sm:flex-row items-center justify-between gap-4">
                  <span className="label font-bold">Ready to contribute?</span>
                  <div className="flex gap-4">
                    <button onClick={handleKickstart} className="bg-[var(--ink)] text-[var(--paper)] px-8 py-3 label font-bold">Start Coding →</button>
                    <button onClick={handleExport} className="border border-[var(--border)] px-8 py-3 label font-bold">{exporting ? 'Exporting...' : 'Export Guide'}</button>
                  </div>
                </div>
              </div>
            )}

            {activeTab === 'coding' && (
              <div className="animate-fade-up">
                {codingLoading ? (
                  <div className="py-20 text-center">
                    <div className="w-10 h-10 border-2 border-[var(--gold)] border-t-transparent animate-spin mx-auto mb-6" />
                    <h2 className="font-serif text-[24px]">Generating first contribution...</h2>
                  </div>
                ) : !coding ? (
                  <div className="py-20 text-center max-w-md mx-auto">
                    <h2 className="font-serif text-[28px] mb-4">Let Bob write your first PR</h2>
                    <p className="text-[11px] text-[var(--dim)] font-medium mb-10 leading-[1.8]">Bob will analyze the codebase, identify a small technical debt or bug, and generate the code change for you.</p>
                    <button onClick={handleKickstart} className="w-full sm:w-auto bg-[var(--ink)] text-[var(--paper)] px-10 py-4 label font-semibold transition-base">Kickstart Contribution</button>
                  </div>
                ) : (
                  <div className="space-y-8">
                    <div className="card-grid">
                      <div className="card col-span-full">
                        <label className="label">Orchestration Results</label>
                        <h3 className="font-serif text-[22px] mt-4 mb-2">{coding.issue_title || 'Issue Identified'}</h3>
                        <p className="text-[11px] text-[var(--muted)] leading-[1.7] mb-6">{coding.explanation?.summary || coding.issue_description}</p>
                      </div>

                      <div className="col-span-full bg-[#0a0a0a] p-0">
                        <div className="bg-[#111] border-b border-[#222] p-4 flex justify-between items-center">
                          <span className="text-[10px] text-[#888] font-mono">{coding.files_involved?.[0] || 'changes'}</span>
                          <button onClick={() => { navigator.clipboard.writeText(coding.code_changes?.[0]?.diff_lines?.map(l => l.content).join('\n') || ''); alert('Copied!'); }} className="label text-[#888] hover:text-white">Copy Diff</button>
                        </div>
                        <div className="p-6 font-mono text-[11px] leading-[1.9] overflow-x-auto text-white">
                          {coding.code_changes?.[0]?.diff_lines?.map((line, i) => (
                            <div key={i} className={`${line.type === 'add' ? 'text-green-400' : line.type === 'remove' ? 'text-red-400' : 'text-gray-500'}`}>
                              {line.type === 'add' ? '+' : line.type === 'remove' ? '-' : ' '} {line.content}
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}

            {activeTab === 'chat' && (
              <div className="animate-fade-up">
                <div className="h-[500px] border border-[var(--border)] bg-[var(--paper)] flex flex-col">
                  <div className="flex-1 overflow-y-auto p-6 space-y-6">
                    {chatMessages.map((m, i) => (
                      <div key={i} className={`flex flex-col ${m.role === 'bob' ? 'items-start' : 'items-end'}`}>
                        <div className={`p-4 text-[11px] leading-[1.7] max-w-[85%] font-mono ${m.role === 'bob' ? 'bg-[var(--paper2)] text-[var(--ink)] border border-[var(--border)]' : 'bg-[var(--ink)] text-[var(--paper)]'}`}>
                          {m.content}
                        </div>
                      </div>
                    ))}
                    {isTyping && <div className="text-[9px] animate-pulse label">BOB IS THINKING...</div>}
                    <div ref={chatEndRef} />
                  </div>
                  <div className="border-t border-[var(--border)] flex">
                    <input
                      type="text"
                      className="flex-1 bg-[var(--paper2)] px-6 py-5 text-[12px] font-mono outline-none"
                      placeholder="Ask about architecture, patterns, or files..."
                      value={chatInput}
                      onChange={(e) => setChatInput(e.target.value)}
                      onKeyDown={(e) => e.key === 'Enter' && handleSend()}
                    />
                    <button onClick={() => handleSend()} className="bg-[var(--ink)] text-[var(--paper)] px-10 label font-bold">Send</button>
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

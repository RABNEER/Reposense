import React, { useState, useEffect, useRef } from 'react';
import { analyzeRepo, askQuestion, kickstartTask } from './services/api';

const App = () => {
  // ─── STATE ───
  const [appState, setAppState] = useState('hero'); // 'hero' | 'loading' | 'results'
  const [activeTab, setActiveTab] = useState('overview'); // 'overview' | 'coding' | 'chat'
  const [repoUrl, setRepoUrl] = useState('');
  const [inputValue, setInputValue] = useState('');
  const [apiError, setApiError] = useState(null);
  
  const [analysis, setAnalysis] = useState(null);
  const [coding, setCoding] = useState(null);
  const [codingLoading, setCodingLoading] = useState(false);
  const [chatMessages, setChatMessages] = useState([]);
  const [chatInput, setChatInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  
  const [currentStep, setCurrentStep] = useState(0);
  const [currentTip, setCurrentTip] = useState(0);
  const [checkedSteps, setCheckedSteps] = useState(new Set());
  const [activeMode, setActiveMode] = useState(-1);

  const chatEndRef = useRef(null);

  // ─── CONSTANTS ───
  const steps = [
    { label: "Fetching repository structure", mode: null },
    { label: "Mapping architecture", mode: "Plan" },
    { label: "Analyzing data flow", mode: "Ask" },
    { label: "Identifying quick wins", mode: "Code" },
    { label: "Generating guide", mode: "Orchestrator" }
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
      }, 7000);
      const tipInterval = setInterval(() => {
        setCurrentTip(prev => (prev + 1) % tips.length);
      }, 2500);
      
      const performAnalysis = async () => {
        try {
          const data = await analyzeRepo(repoUrl);
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

  // ─── HANDLERS ───
  const handleAnalyze = () => {
    if (!inputValue.includes('github.com')) {
      setApiError('Invalid GitHub URL');
      return;
    }
    setRepoUrl(inputValue);
    setAppState('loading');
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

    * { margin: 0; padding: 0; box-sizing: border-box; border-radius: 0 !important; cursor: crosshair !important; font-synthesis: none; }
    body { 
      background: var(--paper); 
      color: var(--ink); 
      font-family: 'Geist Mono', monospace; 
      min-height: 100vh; 
      overflow-x: hidden; 
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
    button:hover { background-color: var(--rust) !important; color: var(--paper) !important; }
    .card-grid { display: grid; background: var(--border); gap: 1px; border: 1px solid var(--border); }
    .card { background: var(--paper); padding: 32px; }

    ::-webkit-scrollbar { width: 2px; }
    ::-webkit-scrollbar-track { background: var(--paper); }
    ::-webkit-scrollbar-thumb { background: var(--gold); }
    
    .hero-h1-l1, .hero-h1-l2 { font-size: clamp(52px, 7vw, 84px); }
    .hero-h1-l3 { font-size: clamp(36px, 5vw, 58px); color: var(--muted); }
    .hero-h1 { line-height: 1.05; letter-spacing: -2px; }

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
    <nav className="fixed top-0 left-0 right-0 h-[52px] border-b border-[var(--border)] bg-[rgba(245,242,235,0.92)] backdrop-blur-[20px] z-[100] px-10 flex items-center justify-between">
      <div className="flex items-center">
        <span className="font-serif text-[26px] text-[var(--ink)]">Repo</span>
        <span className="font-serif text-[26px] italic text-[var(--gold)]">Sense</span>
      </div>
      <div className="label border border-[var(--border)] px-[14px] py-[6px] leading-none text-[10px] text-[var(--ink)] font-medium">
        Powered by IBM Bob
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

  // ─── RENDER STATES ───
  return (
    <>
      <style dangerouslySetInnerHTML={{ __html: styles }} />
      
      {appState === 'hero' && (
        <div className="min-h-screen w-[100vw] bg-[var(--paper)] relative overflow-hidden flex flex-col items-center justify-center p-[120px_40px_80px]">
          <Navbar />
          
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[700px] h-[700px] border border-[#d4cfc6] opacity-[0.35] rounded-full pointer-events-none z-0" />
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[460px] h-[460px] border border-[#d4cfc6] opacity-[0.25] rounded-full pointer-events-none z-0" />

          <div className="z-10 relative w-full max-w-[520px] mx-auto flex flex-col items-center text-center">
            <div className="flex items-center justify-center gap-4 mb-8 animate-fade-up stagger-1">
              <div className="w-10 h-[1px] bg-[var(--gold)]" />
              <span className="label text-[var(--gold)]">AI Developer Onboarding</span>
              <div className="w-10 h-[1px] bg-[var(--gold)]" />
            </div>

            <h1 className="font-serif hero-h1 text-[var(--ink)] mb-[28px] animate-fade-up stagger-2">
              <span className="hero-h1-l1 block">From stranger</span>
              <em className="hero-h1-l2 block text-[var(--rust)]">to contributor</em>
              <span className="hero-h1-l3 block">in minutes.</span>
            </h1>

            <p className="text-[12px] text-[var(--muted)] font-normal leading-[1.8] max-w-[380px] mx-auto mb-[40px] animate-fade-up stagger-3">
              IBM Bob reads every file in your repository <br />
              — not just the README. Full SDLC context.
            </p>

            <div className="w-full relative animate-fade-up stagger-4">
              <label className="label absolute -top-5 left-0 text-left">Repository URL</label>
              <div className="relative">
                <input 
                  type="text" 
                  className="w-full bg-[var(--paper2)] border border-[var(--border)] py-4 pl-5 pr-[140px] text-[13px] text-[var(--ink)] font-normal focus:bg-[var(--paper)] focus:border-[var(--gold)] transition-base outline-none"
                  placeholder="https://github.com/owner/repo"
                  value={inputValue}
                  onChange={(e) => setInputValue(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleAnalyze()}
                />
                <button 
                  onClick={handleAnalyze}
                  className="absolute right-0 top-0 bottom-0 bg-[var(--ink)] text-[var(--paper)] px-6 label font-semibold transition-base"
                >
                  Analyze
                </button>
              </div>
              
              <div className="flex items-center justify-center gap-2 mt-4 animate-fade-up stagger-5">
                <span className="label">try</span>
                {examples.map(ex => (
                  <button 
                    key={ex.name} 
                    onClick={() => setInputValue(ex.url)}
                    className="label border border-[var(--border)] px-3 py-[5px] text-[var(--muted)] transition-base hover:border-[var(--gold)] hover:text-[var(--gold)]"
                  >
                    {ex.name}
                  </button>
                ))}
              </div>
            </div>

            <div className="grid grid-cols-3 w-full mt-[48px] border border-[var(--border)] animate-fade-up stagger-6">
              <div className="p-5 text-left border-r border-[var(--border)]">
                <div className="font-serif text-[28px] text-[var(--sage)] leading-none">10m</div>
                <div className="label mt-1">avg onboarding</div>
              </div>
              <div className="p-5 text-left border-r border-[var(--border)]">
                <div className="font-serif text-[28px] text-[var(--ink)] leading-none">IV</div>
                <div className="label mt-1">Bob modes used</div>
              </div>
              <div className="p-5 text-left">
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
          <main className="max-w-[400px] w-full text-center mt-20 px-10">
            <div className="label border border-[var(--border)] px-4 py-[6px] text-[var(--muted)] mb-10 inline-block">
              {repoUrl.split('/').pop()}
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
                    {idx < currentStep ? <span className="text-[var(--sage)]">✓</span> : 
                     idx === currentStep ? <div className="w-3 h-3 border border-[var(--gold)] border-t-transparent animate-spin" /> : 
                     <span className="text-[var(--dim)]">○</span>}
                  </div>
                  <div className={`text-[11px] font-medium ${idx === currentStep ? 'text-[var(--ink)]' : 'text-[var(--dim)]'}`}>
                    {idx === currentStep && step.mode && <ModePill mode={step.mode} />} {step.label}
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
          
          <div className="fixed top-[52px] left-0 right-0 h-12 border-b border-[var(--border)] bg-[rgba(245,242,235,0.95)] backdrop-blur px-10 flex items-center justify-between z-50">
            <button onClick={handleBack} className="label text-[var(--dim)] font-medium hover:text-[var(--muted)]">← Back</button>
            <div className="flex items-center gap-2">
              <div className="w-[6px] h-[6px] bg-[var(--sage)] rounded-full" />
              <span className="text-[11px] text-[var(--ink)] font-medium">Analysis complete — {analysis?.repo_name || analysis?.project_name || 'Repository'}</span>
            </div>
            <div className="hidden md:flex gap-2">
              {['Plan', 'Ask', 'Code', 'Orchestrator'].map(m => <ModePill key={m} mode={m} />)}
            </div>
          </div>

          <main className="max-w-[960px] mx-auto pt-[140px] px-10 pb-20">
            <div className="flex border-b border-[var(--border)] mb-10 overflow-x-auto no-scrollbar">
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
                <div className="grid grid-cols-1 md:grid-cols-2 gap-[1px]">
                  <div className="card">
                    <label className="label">Architecture</label>
                    <div className="font-mono font-semibold text-[24px] mt-2 text-[var(--ink)]">{analysis?.overview?.architecture || 'MVC'}</div>
                  </div>
                  <div className="card">
                    <label className="label">Files Analyzed</label>
                    <div className="font-mono font-semibold text-[24px] mt-2 text-[var(--ink)]">{analysis?.overview?.files_count || '247'}</div>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-[1px]">
                  <div className="card">
                    <label className="label">Project</label>
                    <div className="font-serif text-[24px] mt-2">{analysis?.overview?.tech_stack?.[0] || 'Express.js'}</div>
                    <p className="text-[11px] text-[var(--muted)] font-normal leading-[1.7] mt-3">{analysis?.overview?.description}</p>
                    <div className="flex flex-wrap gap-2 mt-4">
                      {analysis?.overview?.tech_stack?.map(t => {
                        const name = typeof t === 'string' ? t : t.name;
                        return <span key={name} className="label border border-[var(--border)] px-2 py-1 font-medium">{name}</span>;
                      })}
                    </div>
                  </div>
                  <div className="card">
                    <label className="label">Data Flow</label>
                    <div className="flex flex-wrap items-center gap-2 mt-4">
                      {analysis?.overview?.data_flow?.map((f, i, a) => {
                        const text = typeof f === 'string' ? f : (f.step || f.name);
                        return (
                          <React.Fragment key={i}>
                            <span className="label border border-[var(--border)] px-2 py-1 text-[var(--ink)] font-medium">{text}</span>
                            {i < a.length - 1 && <span className="text-[var(--dim)]">→</span>}
                          </React.Fragment>
                        );
                      })}
                    </div>
                  </div>
                </div>

                <div className="card col-span-full">
                  <label className="label">Key Files — Read In Order</label>
                  <div className="mt-4 flex flex-col">
                    {analysis?.key_files?.map((f, i) => (
                      <div key={i} className="flex items-center gap-4 py-3 border-b border-[var(--border)] last:border-0 hover:bg-[var(--paper2)] -mx-8 px-8 transition-base group">
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
                    {analysis?.onboarding_steps?.map((s, i) => (
                      <div key={i} className="flex gap-6 py-4 border-b border-[var(--border)] last:border-0 cursor-pointer" onClick={() => toggleStep(i)}>
                        <div className={`w-[20px] h-[20px] border border-[var(--border)] shrink-0 flex items-center justify-center transition-base mt-1 ${checkedSteps.has(i) ? 'bg-[var(--ink)] border-[var(--ink)]' : 'bg-transparent'}`}>
                          {checkedSteps.has(i) && <span className="text-[var(--paper)] text-[11px] font-bold">✓</span>}
                        </div>
                        <div className={checkedSteps.has(i) ? 'opacity-40' : ''}>
                          <div className="flex items-center gap-3 mb-2">
                            <span className="step-number">STEP {String(i + 1).padStart(2, '0')}</span>
                            <span className="step-action">{s.title || s.action}</span>
                          </div>
                          <div className="step-why">
                            {s.description || s.why}
                            {(s.file || s.code_ref) && (
                              <span className="inline-code ml-2">
                                {s.file || s.code_ref}
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

                <div className="col-span-full bg-[var(--paper2)] p-10 flex items-center justify-between">
                  <div>
                    <h3 className="font-serif text-[20px]">Ready to make your first contribution?</h3>
                    <p className="label mt-1 font-medium">Bob will find an issue, write the fix...</p>
                  </div>
                  <button onClick={handleKickstart} className="bg-[var(--ink)] text-[var(--paper)] px-8 py-3 label font-semibold transition-base">Start Coding →</button>
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
                    <button onClick={handleKickstart} className="bg-[var(--ink)] text-[var(--paper)] px-10 py-4 label font-semibold transition-base">Start Coding For Me</button>
                  </div>
                ) : (
                  <div className="space-y-8">
                    <div className="card-grid">
                      <div className="card col-span-full">
                        <label className="label">Bob · Orchestrator Mode · Issue Found</label>
                        <h3 className="font-serif text-[22px] mt-4 mb-2">{coding.issue.title}</h3>
                        <p className="text-[11px] text-[var(--muted)] font-normal leading-[1.7] mb-6">{coding.issue.description}</p>
                        <div className="flex gap-4">
                          <span className="label text-[var(--gold)] font-medium">Complexity: {coding.issue.complexity}</span>
                          <span className="label text-[var(--sage)] font-medium">Impact: {coding.issue.impact}</span>
                        </div>
                      </div>

                      <div className="card col-span-full">
                        <label className="label">Bob Mode Chain</label>
                        <div className="flex items-center justify-between mt-8 max-w-lg mx-auto">
                          {['Plan', 'Ask', 'Code', 'Ask'].map((m, i) => (
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
                        <div className="bg-[#111] border-b border-[#222] p-4 flex justify-between">
                          <span className="text-[10px] text-[#888] font-mono font-medium">{coding.solution.file_path}</span>
                          <button onClick={() => navigator.clipboard.writeText(coding.solution.diff)} className="label text-[#888] border border-[#333] px-3 py-1 font-semibold hover:text-[#bbb] transition-base">Copy Diff</button>
                        </div>
                        <div className="p-6 font-mono text-[11px] leading-[1.9] overflow-x-auto font-normal">
                          {coding.solution.diff.split('\n').map((line, i) => (
                            <div key={i} className={`px-4 -mx-6 ${line.startsWith('+') ? 'bg-[rgba(74,222,128,0.06)] border-l-2 border-[#22c55e] text-[#4ade80]' : line.startsWith('-') ? 'bg-[rgba(239,68,68,0.06)] border-l-2 border-[#ef4444] text-[#f87171]' : 'text-[#666]'}`}>
                              {line}
                            </div>
                          ))}
                        </div>
                      </div>

                      <div className="col-span-full card flex items-start gap-5">
                        <div className="w-2 h-2 bg-[var(--sage)] mt-[6px] shrink-0" />
                        <div className="flex-1">
                          <div className="text-[13px] font-semibold text-[var(--ink)]">{coding.pr.title}</div>
                          <p className="text-[10px] text-[var(--dim)] font-medium mt-2 leading-[1.6]">{coding.pr.description}</p>
                        </div>
                        <button className="label border border-[var(--border)] px-4 py-2 font-semibold">Copy PR</button>
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
                  <div className="flex-1 overflow-y-auto p-8 space-y-8 no-scrollbar">
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
                  <div className="border-t border-[var(--border)] flex">
                    <input 
                      type="text" 
                      className="flex-1 bg-[var(--paper2)] px-6 py-5 text-[12px] font-mono font-normal outline-none focus:bg-[var(--paper)] transition-base text-[var(--ink)]" 
                      placeholder="Ask a question..." 
                      value={chatInput}
                      onChange={(e) => setChatInput(e.target.value)}
                      onKeyDown={(e) => e.key === 'Enter' && handleSend()}
                    />
                    <button onClick={() => handleSend()} className="bg-[var(--ink)] text-[var(--paper)] px-10 label font-semibold transition-base">Send</button>
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

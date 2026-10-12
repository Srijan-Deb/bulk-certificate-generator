import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import type { FormEvent, ReactNode } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import {
  Activity,
  ArrowDownToLine,
  ArrowRight,
  BadgeCheck,
  Bell,
  Check,
  CheckCircle2,
  ChevronDown,
  CircleHelp,
  Clock3,
  Cloud,
  CloudUpload,
  Database,
  Eye,
  FileSpreadsheet,
  FileText,
  Image as ImageIcon,
  Layers,
  LayoutDashboard,
  LoaderCircle,
  LogIn,
  LogOut,
  Menu,
  Palette,
  Plus,
  RefreshCw,
  Search,
  ShieldCheck,
  Sliders,
  Sparkles,
  Trash2,
  User as UserIcon,
  Wand2,
  X,
  XCircle,
  Zap,
} from 'lucide-react';
import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import {
  aiAnalyzeTemplateLayout,
  applyLayoutPreset,
  createUploadJob,
  downloadCertificate,
  downloadTemplate,
  downloadZip,
  getAuthConfig,
  getCertificates,
  getHealth,
  getJob,
  getMe,
  getStats,
  getStoredToken,
  getStoredUser,
  getTemplateAssetsStatus,
  getTemplateLayoutConfig,
  listServerJobs,
  loginWithDevGoogle,
  loginWithGoogle,
  logoutUser,
  POLL_MS,
  removeStoredToken,
  removeStoredUser,
  resetBackgroundTemplate,
  resetSignature,
  setStoredToken,
  setStoredUser,
  updateTemplateLayoutConfig,
  uploadBackgroundTemplateFile,
  uploadSignatureFile,
} from './lib/api';
import type { AuthConfig, CertificateRecord, JobStatus, Stats, TemplateAssetsStatus, TemplateLayoutConfig, UserProfile } from './lib/api';

type Page = 'overview' | 'generate' | 'templates' | 'jobs';
type RecentJob = { id: string; event: string; created: string };
const STORAGE_KEY = 'certflow.recent-jobs.v1';
function readRecent(): RecentJob[] { try { return JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]'); } catch { return []; } }
function saveRecent(items: RecentJob[]) { try { localStorage.setItem(STORAGE_KEY, JSON.stringify(items.slice(0, 20))); } catch { /* ignore */ } }
function formatNumber(n?: number) { return new Intl.NumberFormat('en-US').format(n || 0); }
function formatDate(v?: string | null) { if (!v) return '—'; const d = new Date(v); return Number.isNaN(d.getTime()) ? v : d.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' }); }
function formatTime(v?: string | null) { if (!v) return '—'; const d = new Date(v); return Number.isNaN(d.getTime()) ? v : d.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' }); }
function statusTone(s?: string) { const v = (s || '').toUpperCase(); if (['SUCCESS','COMPLETED','COMPLETE','SUCCEEDED'].includes(v)) return 'success'; if (['FAILED','ERROR'].includes(v)) return 'danger'; if (['PROCESSING','RUNNING','IN_PROGRESS'].includes(v)) return 'info'; if (['PENDING','QUEUED','ACCEPTED'].includes(v)) return 'warning'; return 'neutral'; }
function StatusPill({ status }: {status?: string}) { return <span className={`status-pill ${statusTone(status)}`}><span className="status-dot" />{(status || 'UNKNOWN').replace(/_/g,' ').toLowerCase()}</span>; }
function Initials({ name }: {name: string}) { return <span className="avatar">{name.split(/\s+/).slice(0,2).map(x=>x[0]).join('').toUpperCase()}</span>; }

function GoogleGLogo() {
  return (
    <svg className="google-icon" viewBox="0 0 24 24" width="18" height="18" xmlns="http://www.w3.org/2000/svg">
      <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4" />
      <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853" />
      <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z" fill="#FBBC05" />
      <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z" fill="#EA4335" />
    </svg>
  );
}

export default function App() {
  const [page, setPage] = useState<Page>('overview');
  const [mobileNav, setMobileNav] = useState(false);
  const [stats, setStats] = useState<Stats | null>(null);
  const [health, setHealth] = useState<'checking'|'healthy'|'degraded'>('checking');
  const [recent, setRecent] = useState<RecentJob[]>(readRecent);
  const [selectedId, setSelectedId] = useState('');
  const [selectedJob, setSelectedJob] = useState<JobStatus | null>(null);
  const [records, setRecords] = useState<CertificateRecord[]>([]);
  const [recordFilter, setRecordFilter] = useState('');
  const [query, setQuery] = useState('');
  const [busy, setBusy] = useState(false);
  const [loadingJob, setLoadingJob] = useState(false);
  const [notice, setNotice] = useState<{kind:'error'|'success'|'info';text:string}|null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const [eventName, setEventName] = useState('');
  const [issuerName, setIssuerName] = useState('');
  const [issueDate, setIssueDate] = useState(new Date().toISOString().slice(0,10));
  const [certificateTitle, setCertificateTitle] = useState('Certificate of Completion');
  const [file, setFile] = useState<File | null>(null);
  const [dragging, setDragging] = useState(false);
  const [actionBusy, setActionBusy] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  // Authentication & Cloud Storage state
  const [user, setUser] = useState<UserProfile | null>(getStoredUser);
  const [authConfig, setAuthConfig] = useState<AuthConfig | null>(null);
  const [authModalOpen, setAuthModalOpen] = useState(false);

  // Template & Signature Assets state
  const [templateAssets, setTemplateAssets] = useState<TemplateAssetsStatus | null>(null);
  const [assetBusy, setAssetBusy] = useState(false);
  const [sigPreviewVer, setSigPreviewVer] = useState(Date.now());
  const [bgPreviewVer, setBgPreviewVer] = useState(Date.now());
  const sigFileRef = useRef<HTMLInputElement>(null);
  const bgFileRef = useRef<HTMLInputElement>(null);

  const refreshTemplateAssets = useCallback(async () => {
    try {
      const status = await getTemplateAssetsStatus();
      setTemplateAssets(status);
    } catch {
      // ignore
    }
  }, []);

  const handleUploadSignature = async (uploadedFile?: File) => {
    if (!uploadedFile) return;
    setAssetBusy(true);
    try {
      await uploadSignatureFile(uploadedFile);
      setNotice({ kind: 'success', text: 'Authorized signature photo processed with Pillow into transparent ink!' });
      setSigPreviewVer(Date.now());
      await refreshTemplateAssets();
    } catch (err: any) {
      setNotice({ kind: 'error', text: err.message || 'Failed to upload signature' });
    } finally {
      setAssetBusy(false);
    }
  };

  const handleResetSignature = async () => {
    if (!window.confirm('Reset authorized signature graphic back to text fallback?')) return;
    setAssetBusy(true);
    try {
      await resetSignature();
      setNotice({ kind: 'info', text: 'Signature graphic removed. Fallback text will be used.' });
      setSigPreviewVer(Date.now());
      await refreshTemplateAssets();
    } catch (err: any) {
      setNotice({ kind: 'error', text: err.message || 'Failed to reset signature' });
    } finally {
      setAssetBusy(false);
    }
  };

  const handleUploadBackground = async (uploadedFile?: File) => {
    if (!uploadedFile) return;
    setAssetBusy(true);
    try {
      await uploadBackgroundTemplateFile(uploadedFile);
      setNotice({ kind: 'success', text: 'Custom certificate background template uploaded and live-activated!' });
      setBgPreviewVer(Date.now());
      await refreshTemplateAssets();
    } catch (err: any) {
      setNotice({ kind: 'error', text: err.message || 'Failed to upload template' });
    } finally {
      setAssetBusy(false);
    }
  };

  const handleResetBackground = async () => {
    if (!window.confirm('Revert certificate background template to Executive Classic vector design?')) return;
    setAssetBusy(true);
    try {
      await resetBackgroundTemplate();
      setNotice({ kind: 'info', text: 'Reverted to built-in Executive Classic vector template.' });
      setBgPreviewVer(Date.now());
      await refreshTemplateAssets();
      await loadLayoutConfig();
    } catch (err: any) {
      setNotice({ kind: 'error', text: err.message || 'Failed to reset background template' });
    } finally {
      setAssetBusy(false);
    }
  };

  // AI Layout & Alignment Assistant state
  const [layoutConfig, setLayoutConfig] = useState<TemplateLayoutConfig | null>(null);
  const [aiBusy, setAiBusy] = useState(false);
  const [showApiKeyInput, setShowApiKeyInput] = useState(false);
  const [geminiApiKey, setGeminiApiKey] = useState(() => localStorage.getItem('certflow.gemini_key') || '');

  const loadLayoutConfig = useCallback(async () => {
    try {
      const cfg = await getTemplateLayoutConfig();
      setLayoutConfig(cfg);
    } catch {
      // ignore
    }
  }, []);

  const handleApplyPreset = async (preset: 'preprinted' | 'frame') => {
    try {
      const updated = await applyLayoutPreset(preset);
      setLayoutConfig(updated);
      setBgPreviewVer(Date.now());
      setNotice({
        kind: 'success',
        text: preset === 'preprinted'
          ? 'Applied Canva / Pre-printed layout preset! Duplicate titles and text hidden to eliminate overlap.'
          : 'Applied Blank Border Frame preset (all titles and decorations enabled).',
      });
    } catch (err: any) {
      setNotice({ kind: 'error', text: err.message || 'Failed to apply preset' });
    }
  };

  const handleUpdateLayoutField = async <K extends keyof TemplateLayoutConfig>(
    key: K,
    val: TemplateLayoutConfig[K]
  ) => {
    if (!layoutConfig) return;
    const nextConfig = { ...layoutConfig, [key]: val };
    setLayoutConfig(nextConfig);
    try {
      await updateTemplateLayoutConfig(nextConfig);
      setBgPreviewVer(Date.now());
    } catch {
      // optimistic
    }
  };

  const handleAiAnalyze = async () => {
    setAiBusy(true);
    try {
      if (geminiApiKey) {
        localStorage.setItem('certflow.gemini_key', geminiApiKey);
      }
      const res = await aiAnalyzeTemplateLayout(geminiApiKey);
      setLayoutConfig(res.layout);
      setBgPreviewVer(Date.now());
      setNotice({
        kind: 'success',
        text: `✨ ${res.message}`,
      });
    } catch (err: any) {
      setNotice({ kind: 'error', text: err.message || 'AI layout detection failed' });
    } finally {
      setAiBusy(false);
    }
  };


  const refreshOverview = useCallback(async () => {
    const [s, h, cfg, tmpl] = await Promise.allSettled([getStats(), getHealth(), getAuthConfig(), getTemplateAssetsStatus()]);
    if (s.status === 'fulfilled') setStats(s.value);
    if (h.status === 'fulfilled') setHealth(h.value.status === 'ok' ? 'healthy' : 'degraded'); else setHealth('degraded');
    if (cfg.status === 'fulfilled') setAuthConfig(cfg.value);
    if (tmpl.status === 'fulfilled') setTemplateAssets(tmpl.value);
    setLastUpdated(new Date());
  }, []);

  // Fetch server jobs and merge with local storage
  const syncServerJobs = useCallback(async () => {
    try {
      const serverJobs = await listServerJobs(25);
      if (serverJobs && serverJobs.length > 0) {
        setRecent(old => {
          const map = new Map<string, RecentJob>();
          old.forEach(j => map.set(j.id, j));
          serverJobs.forEach(j => map.set(j.job_id, { id: j.job_id, event: j.event_name, created: j.created_at }));
          const combined = Array.from(map.values()).sort((a, b) => new Date(b.created).getTime() - new Date(a.created).getTime()).slice(0, 20);
          saveRecent(combined);
          return combined;
        });
      }
    } catch {
      // ignore
    }
  }, []);

  // Check current user if token exists on boot
  useEffect(() => {
    const token = getStoredToken();
    if (token) {
      getMe()
        .then(u => { setUser(u); setStoredUser(u); })
        .catch(() => { removeStoredToken(); removeStoredUser(); setUser(null); });
    }
  }, []);

  const refreshJob = useCallback(async (id: string, filter = recordFilter) => {
    if (!id) return;
    setLoadingJob(true);
    try {
      const [job, certs] = await Promise.all([getJob(id), getCertificates(id, filter, 0, 100)]);
      setSelectedJob(job); setRecords(certs); setNotice(null);
      setRecent(old => { const updated = [{id, event:job.event_name, created:job.created_at}, ...old.filter(x=>x.id !== id)].slice(0,20); saveRecent(updated); return updated; });
    } catch (e) { setNotice({kind:'error',text:e instanceof Error ? e.message : 'Unable to load job.'}); }
    finally { setLoadingJob(false); }
  }, [recordFilter]);

  useEffect(() => {
    void refreshOverview();
    void syncServerJobs();
    const timer = window.setInterval(() => { void refreshOverview(); }, POLL_MS * 2);
    return () => window.clearInterval(timer);
  }, [refreshOverview, syncServerJobs]);

  useEffect(() => { if (selectedId) void refreshJob(selectedId); }, [selectedId, refreshJob]);
  useEffect(() => {
    if (!selectedId) return;
    const timer = window.setInterval(() => { void refreshJob(selectedId); }, POLL_MS);
    return () => window.clearInterval(timer);
  }, [selectedId, refreshJob]);

  const openJob = (id: string) => { setSelectedId(id); setPage('jobs'); setMobileNav(false); };
  const go = (next: Page) => { setPage(next); setMobileNav(false); setNotice(null); };
  const chooseFile = (f?: File) => { if (!f) return; const valid = /\.(xlsx|csv)$/i.test(f.name); if (!valid) { setNotice({kind:'error',text:'Choose an Excel .xlsx or CSV .csv file.'}); return; } setFile(f); setNotice(null); };

  const handleDevLogin = async (name: string, email: string) => {
    try {
      setBusy(true);
      const res = await loginWithDevGoogle(name, email);
      setStoredToken(res.access_token);
      setStoredUser(res.user);
      setUser(res.user);
      setAuthModalOpen(false);
      setNotice({ kind: 'success', text: `Signed in as ${res.user.full_name} (${res.user.email}).` });
      void syncServerJobs();
    } catch (e) {
      setNotice({ kind: 'error', text: e instanceof Error ? e.message : 'Login failed.' });
    } finally {
      setBusy(false);
    }
  };

  const handleLogout = async () => {
    try { await logoutUser(); } catch { /* ignore */ }
    removeStoredToken();
    removeStoredUser();
    setUser(null);
    setNotice({ kind: 'info', text: 'You have signed out.' });
  };

  const submitJob = async (e: FormEvent) => {
    e.preventDefault();
    if (!file) { setNotice({kind:'error',text:'Add a recipient spreadsheet before continuing.'}); return; }
    if (eventName.trim().length < 2 || issuerName.trim().length < 2 || issueDate.trim().length < 4) { setNotice({kind:'error',text:'Complete the event, issuer and issue date fields.'}); return; }
    setBusy(true); setNotice(null);
    try {
      const accepted = await createUploadJob({file, event_name:eventName.trim(), issuer_name:issuerName.trim(), issue_date:issueDate, certificate_title:certificateTitle.trim() || 'Certificate of Completion'});
      const next = [{id:accepted.job_id,event:eventName.trim(),created:accepted.created_at}, ...recent.filter(j=>j.id !== accepted.job_id)].slice(0,20);
      setRecent(next); saveRecent(next); setSelectedId(accepted.job_id); setSelectedJob(null); setPage('jobs'); setNotice({kind:'success',text:`Generation queued successfully for ${accepted.total_recipients} recipients.`});
      setFile(null); if(fileRef.current) fileRef.current.value='';
    } catch (e) { setNotice({kind:'error',text:e instanceof Error ? e.message : 'Could not create generation job.'}); }
    finally { setBusy(false); }
  };

  const filteredRecent = useMemo(() => recent.filter(j => `${j.event} ${j.id}`.toLowerCase().includes(query.toLowerCase())), [recent, query]);
  const chartData = selectedJob ? [
    {name:'Successful', count:selectedJob.successful_count, fill:'#16a777'},
    {name:'Failed', count:selectedJob.failed_count, fill:'#e45b68'},
    {name:'Processing', count:selectedJob.processing_count, fill:'#4c76ed'},
    {name:'Pending', count:selectedJob.pending_count, fill:'#d8a13a'},
  ] : [
    {name:'Successful', count:stats?.certificates?.generated_success || 0, fill:'#16a777'},
    {name:'Failed', count:stats?.certificates?.generated_failed || 0, fill:'#e45b68'},
  ];

  const doDownloadZip = async (id: string) => { setActionBusy(true); try { await downloadZip(id); setNotice({kind:'success',text:'Your ZIP download has started.'}); } catch(e) { setNotice({kind:'error',text:e instanceof Error ? e.message : 'Download failed.'}); } finally { setActionBusy(false); } };
  const doDownloadCertificate = async (id: string) => { try { await downloadCertificate(id); } catch(e) { setNotice({kind:'error',text:e instanceof Error ? e.message : 'Download failed.'}); } };

  const storageProviderName = authConfig?.cloud_storage_configured
    ? `${(authConfig.cloud_storage_provider || 'S3').toUpperCase()} (10 GB Free)`
    : 'Local Storage (Zero-Cost)';

  return (
    <div className="app-shell">
      <aside className={`sidebar ${mobileNav?'mobile-open':''}`}>
        <div className="brand">
          <div className="brand-mark"><BadgeCheck size={22}/></div>
          <div><div className="brand-name">certflow<span>.</span></div><div className="brand-caption">CERTIFICATE STUDIO</div></div>
          <button className="icon-btn sidebar-close" onClick={()=>setMobileNav(false)} aria-label="Close menu"><X size={18}/></button>
        </div>
        <div className="workspace-switch">
          <div className="workspace-logo"><Sparkles size={17}/></div>
          <div className="workspace-copy">
            <strong>{user ? `${user.full_name}'s Space` : 'Workspace'}</strong>
            <span>{user ? user.email : 'Certificate operations'}</span>
          </div>
          <ChevronDown size={15} className="muted-icon"/>
        </div>
        <div className="nav-label">WORKSPACE</div>
        <nav className="nav-list">
          <button className={`nav-item ${page==='overview'?'active':''}`} onClick={()=>go('overview')}><LayoutDashboard size={18}/><span>Overview</span></button>
          <button className={`nav-item ${page==='generate'?'active':''}`} onClick={()=>go('generate')}><Plus size={18}/><span>Generate certificates</span><span className="nav-new">NEW</span></button>
          <button className={`nav-item ${page==='templates'?'active':''}`} onClick={()=>go('templates')}><Sparkles size={18}/><span>Design & Templates</span><span className="nav-new">LIVE</span></button>
          <button className={`nav-item ${page==='jobs'?'active':''}`} onClick={()=>go('jobs')}><Activity size={18}/><span>Generation jobs</span>{recent.length>0&&<span className="nav-count">{recent.length}</span>}</button>
        </nav>
        <div className="nav-label nav-label-spaced">SYSTEM & STORAGE</div>
        <div className="system-card">
          <div className="system-card-top">
            <span className={`system-pulse ${health}`}/>
            <span>API status</span>
            <span className={`system-status ${health}`}>{health==='checking'?'Checking':health==='healthy'?'Operational':'Degraded'}</span>
          </div>
          <p>{health==='healthy'?'Backend is ready & accepting requests.':health==='degraded'?'Unable to verify all services.':'Checking connectivity…'}</p>

          <div className="cloud-storage-card">
            <div className="cloud-storage-top">
              <Cloud size={14}/>
              <span>Storage</span>
              <span className={`cloud-pill ${authConfig?.cloud_storage_configured ? 'cloud' : 'local'}`}>
                {authConfig?.cloud_storage_configured ? 'Cloud' : 'Local'}
              </span>
            </div>
            <p>{storageProviderName}</p>
          </div>

          <button onClick={()=>void refreshOverview()} className="system-refresh" style={{marginTop:'8px'}}><RefreshCw size={13}/> Refresh status</button>
        </div>

        <div className="sidebar-bottom">
          <div className="help-row">
            <span className="help-icon"><CircleHelp size={17}/></span>
            <span><strong>Need a hand?</strong><small>Explore the API docs</small></span>
            <a href={`${import.meta.env.VITE_API_BASE_URL||'http://127.0.0.1:8000'}/docs`} target="_blank" rel="noreferrer" aria-label="Open API docs"><ArrowRight size={15}/></a>
          </div>

          {user ? (
            <div className="profile-row">
              {user.avatar_url ? (
                <img src={user.avatar_url} alt={user.full_name} className="user-avatar-img" />
              ) : (
                <div className="profile-avatar">{user.full_name.slice(0, 2).toUpperCase()}</div>
              )}
              <div className="profile-copy">
                <strong>{user.full_name}</strong>
                <span>{user.email}</span>
              </div>
              <button className="user-logout-btn" onClick={handleLogout} title="Sign Out">
                <LogOut size={16}/>
              </button>
            </div>
          ) : (
            <div className="profile-row" style={{cursor:'pointer'}} onClick={()=>setAuthModalOpen(true)}>
              <div className="profile-avatar"><UserIcon size={16}/></div>
              <div className="profile-copy">
                <strong>Sign In with Google</strong>
                <span>Unlock sync & cloud</span>
              </div>
              <LogIn size={15} style={{color:'#5575e8'}}/>
            </div>
          )}
        </div>
      </aside>

      {mobileNav&&<button className="mobile-backdrop" onClick={()=>setMobileNav(false)} aria-label="Close navigation"/>}

      <main className="main-area">
        <header className="topbar">
          <div className="topbar-left">
            <button className="icon-btn mobile-menu" onClick={()=>setMobileNav(true)} aria-label="Open menu"><Menu size={20}/></button>
            <div className="breadcrumb">Workspace <span>/</span> <strong>{page==='overview'?'Overview':page==='generate'?'Generate certificates':page==='templates'?'Design & Template Studio':'Generation jobs'}</strong></div>
          </div>
          <div className="topbar-right">
            <div className="live-indicator"><span className={`system-pulse ${health}`}/><span>{health==='healthy'?'Systems operational':'System status'}</span></div>
            <div className="topbar-divider"/>

            {/* Google Authentication in Topbar */}
            {user ? (
              <div className="user-profile-badge" onClick={()=>setAuthModalOpen(true)}>
                {user.avatar_url ? (
                  <img src={user.avatar_url} alt={user.full_name} className="user-avatar-img" />
                ) : (
                  <div className="mini-profile">{user.full_name.slice(0, 2).toUpperCase()}</div>
                )}
                <div className="user-meta">
                  <span className="user-name">{user.full_name}</span>
                  <span className="user-email">{user.email}</span>
                </div>
                <button
                  className="user-logout-btn"
                  onClick={(e)=>{e.stopPropagation();void handleLogout();}}
                  title="Sign Out"
                >
                  <LogOut size={14}/>
                </button>
              </div>
            ) : (
              <button className="google-sign-in-btn" onClick={()=>setAuthModalOpen(true)}>
                <GoogleGLogo />
                <span>Sign in with Google</span>
              </button>
            )}

            <button className="icon-btn notification-btn" aria-label="Notifications"><Bell size={18}/><i/></button>
          </div>
        </header>

        <div className="page-content">
          {notice&&<motion.div initial={{opacity:0,y:-6}} animate={{opacity:1,y:0}} className={`notice ${notice.kind}`}><span>{notice.kind==='success'?<CheckCircle2 size={18}/>:notice.kind==='error'?<XCircle size={18}/>:<Activity size={18}/>}</span><p>{notice.text}</p><button onClick={()=>setNotice(null)} aria-label="Dismiss"><X size={16}/></button></motion.div>}

          <AnimatePresence mode="wait">
            {page==='overview'&&<motion.section key="overview" className="page-view" initial={{opacity:0,y:8}} animate={{opacity:1,y:0}} exit={{opacity:0,y:-6}} transition={{duration:.2}}>
              <div className="page-heading">
                <div>
                  <div className="eyebrow"><span className="eyebrow-dot"/> YOUR CERTIFICATE OPERATIONS</div>
                  <h1>Good work starts <span>with clarity.</span></h1>
                  <p>Create, track, and deliver verified certificates with free S3 cloud backup.</p>
                </div>
                <button className="primary-btn" onClick={()=>go('generate')}><Plus size={17}/> Create a batch <ArrowRight size={16}/></button>
              </div>

              <div className="welcome-banner">
                <div className="banner-content">
                  <div className="banner-chip"><Sparkles size={13}/> CERTIFICATE STUDIO</div>
                  <h2>Make every achievement<br/><span>worth celebrating.</span></h2>
                  <p>Turn a recipient spreadsheet into a polished batch of verified certificates. Backed by free cloud storage and Google Sign-In.</p>
                  <button className="banner-btn" onClick={()=>go('generate')}>Generate certificates <ArrowRight size={15}/></button>
                </div>
                <div className="banner-art" aria-hidden="true">
                  <div className="art-orbit orbit-one"/><div className="art-orbit orbit-two"/><div className="art-glow"/>
                  <div className="certificate-illustration">
                    <div className="cert-topline"><span>✦</span><small>RECOGNITION</small><span>✦</span></div>
                    <div className="cert-seal"><BadgeCheck size={34}/></div>
                    <div className="cert-script">Certificate</div>
                    <div className="cert-subtitle">OF ACHIEVEMENT</div>
                    <div className="cert-rule"/>
                    <div className="cert-lines"><i/><i/><i/></div>
                    <div className="cert-bottom"><span/><span>✦</span><span/></div>
                  </div>
                  <div className="floating-check"><Check size={17}/></div>
                  <div className="floating-spark"><Sparkles size={16}/></div>
                </div>
              </div>

              <div className="section-heading">
                <div><h2>At a glance</h2><p>A live snapshot of your certificate operations.</p></div>
                <span className="updated-label"><span className="system-pulse healthy"/> Updates automatically{lastUpdated?` · ${formatTime(lastUpdated.toISOString())}`:''}</span>
              </div>
              <div className="stats-grid">
                <StatCard label="Jobs submitted" value={stats?.jobs?.submitted_total} icon={<FileText size={18}/>} tone="blue" foot="Total batches accepted" loading={!stats}/>
                <StatCard label="Certificates generated" value={stats?.certificates?.generated_success} icon={<BadgeCheck size={18}/>} tone="green" foot="Successfully created PDFs" loading={!stats}/>
                <StatCard label="Failed certificates" value={stats?.certificates?.generated_failed} icon={<ShieldCheck size={18}/>} tone="rose" foot="Review errors in job details" loading={!stats}/>
                <StatCard label="Cloud / Local Storage" value={stats?.storage?.stored_pdf_count} icon={<Cloud size={18}/>} tone="violet" foot={stats?.storage?.human_readable_size?`${stats.storage.human_readable_size} (${authConfig?.cloud_storage_configured ? 'Cloud' : 'Local'})`: 'Stored certificate files'} loading={!stats}/>
              </div>

              <div className="dashboard-grid">
                <div className="panel chart-panel">
                  <div className="panel-heading">
                    <div><h3>Generation outcomes</h3><p>{selectedJob?'Selected job · live recipient status':'All-time totals reported by the backend'}</p></div>
                    <div className="chart-legend"><span><i className="legend-success"/> Successful</span><span><i className="legend-failed"/> Failed</span></div>
                  </div>
                  <div className="chart-area">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={chartData} layout="vertical" margin={{top:5,right:24,left:10,bottom:5}} barSize={22}>
                        <CartesianGrid strokeDasharray="3 5" horizontal={false} stroke="#e9edf5"/>
                        <XAxis type="number" axisLine={false} tickLine={false} tick={{fill:'#8791a5',fontSize:11}} allowDecimals={false}/>
                        <YAxis type="category" dataKey="name" axisLine={false} tickLine={false} tick={{fill:'#58647a',fontSize:12}} width={88}/>
                        <Tooltip cursor={{fill:'#f6f8fc'}} contentStyle={{border:'1px solid #e7ebf3',borderRadius:12,boxShadow:'0 8px 24px #1a2b4b12'}}/>
                        <Bar dataKey="count" radius={[5,5,5,5]}>{chartData.map((entry) => <Cell key={entry.name} fill={entry.fill}/>)}</Bar>
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                  <div className="chart-footer">
                    <span><span className="tiny-dot green-dot"/> {formatNumber(selectedJob?selectedJob.successful_count:stats?.certificates?.generated_success)} successful</span>
                    <span><span className="tiny-dot rose-dot"/> {formatNumber(selectedJob?selectedJob.failed_count:stats?.certificates?.generated_failed)} failed</span>
                    {selectedJob&&<button className="text-btn" onClick={()=>setSelectedJob(null)}>Show all-time totals</button>}
                  </div>
                </div>

                <div className="panel quick-panel">
                  <div className="panel-heading"><div><h3>Quick actions</h3><p>Pick up where you left off.</p></div><div className="quick-icon"><Zap size={17}/></div></div>
                  <button className="quick-action" onClick={()=>go('generate')}><span className="quick-action-icon blue-bg"><CloudUpload size={19}/></span><span><strong>Generate a new batch</strong><small>Upload your recipient spreadsheet</small></span><ArrowRight size={17}/></button>
                  <button className="quick-action" onClick={()=>{void downloadTemplate().catch(e=>setNotice({kind:'error',text:e.message}));}}><span className="quick-action-icon green-bg"><FileSpreadsheet size={19}/></span><span><strong>Get spreadsheet template</strong><small>Use the expected column format</small></span><ArrowDownToLine size={17}/></button>
                  <button className="quick-action" onClick={()=>go('jobs')}><span className="quick-action-icon violet-bg"><Activity size={19}/></span><span><strong>Track generation jobs</strong><small>Review progress and recipients</small></span><ArrowRight size={17}/></button>
                  <div className="tip-box"><Sparkles size={15}/><p><strong>Storage Note</strong> — Cloud storage connects seamlessly with Cloudflare R2 (10 GB free) or Supabase Storage (1 GB free).</p></div>
                </div>
              </div>

              <div className="panel recent-panel">
                <div className="panel-heading">
                  <div><h3>Recent generation jobs</h3><p>{user ? `Jobs associated with ${user.email}` : 'Recent batches saved in your session'}</p></div>
                  <button className="subtle-btn" onClick={()=>go('jobs')}>View all <ArrowRight size={15}/></button>
                </div>
                {recent.length===0?<EmptyState title="Your first batch starts here" body="Create a batch to track recipients and certificate downloads in this workspace." action="Create a batch" onAction={()=>go('generate')}/>:<div className="table-wrap"><table><thead><tr><th>JOB / EVENT</th><th>CREATED</th><th>JOB ID</th><th>STATUS</th><th/></tr></thead><tbody>{recent.slice(0,5).map(j=><tr key={j.id} onClick={()=>openJob(j.id)} className="click-row"><td><div className="event-cell"><span className="event-icon"><FileText size={16}/></span><strong>{j.event||'Certificate batch'}</strong></div></td><td>{formatDate(j.created)}</td><td><code>{j.id.slice(0,8)}…</code></td><td><StatusPill status={selectedId===j.id?selectedJob?.status:'TRACKED'}/></td><td><button className="row-arrow" aria-label="Open job"><ArrowRight size={16}/></button></td></tr>)}</tbody></table></div>}
              </div>
            </motion.section>}

            {page==='generate'&&<motion.section key="generate" className="page-view" initial={{opacity:0,y:8}} animate={{opacity:1,y:0}} exit={{opacity:0,y:-6}} transition={{duration:.2}}>
              <div className="page-heading">
                <div>
                  <div className="eyebrow"><span className="eyebrow-dot"/> NEW GENERATION JOB</div>
                  <h1>Bring your <span>batch to life.</span></h1>
                  <p>One spreadsheet in. A whole batch of verified certificates out.</p>
                </div>
                <button className="subtle-btn" onClick={()=>go('jobs')}>View generation jobs <ArrowRight size={15}/></button>
              </div>

              <div className="design-banner-widget">
                <div className="design-widget-info">
                  <span className="design-widget-icon"><Sparkles size={18}/></span>
                  <div>
                    <strong>Active Design Template & Signature Graphic</strong>
                    <span>
                      Template: {templateAssets?.background.exists ? 'Custom Canva/Figma Template Active' : 'Executive Classic (Vector)'} · Signature: {templateAssets?.signature.exists ? 'Pillow Transparent Graphic Active' : 'Authorized Text Line'}
                    </span>
                  </div>
                </div>
                <button type="button" className="secondary-btn" onClick={()=>go('templates')}>
                  <Palette size={14}/> Customize in Studio <ArrowRight size={14}/>
                </button>
              </div>

              <div className="generation-layout">
                <form className="panel generation-form" onSubmit={submitJob}>
                  <div className="form-title"><span className="form-step">01</span><div><h2>Batch details</h2><p>These details appear on each certificate in this batch.</p></div></div>
                  <div className="field-grid">
                    <label className="field full"><span>Event or course name <b>*</b></span><input value={eventName} onChange={e=>setEventName(e.target.value)} placeholder="e.g. Advanced Python Engineering" minLength={2} maxLength={255} required/><small>Use the official name of your event, course, or workshop.</small></label>
                    <label className="field"><span>Issuing organization <b>*</b></span><input value={issuerName} onChange={e=>setIssuerName(e.target.value)} placeholder="e.g. Acme Learning" minLength={2} maxLength={255} required/></label>
                    <label className="field"><span>Issue date <b>*</b></span><input type="date" value={issueDate} onChange={e=>setIssueDate(e.target.value)} required/></label>
                    <label className="field full"><span>Certificate heading</span><input value={certificateTitle} onChange={e=>setCertificateTitle(e.target.value)} placeholder="Certificate of Completion" maxLength={255}/><small>Customize the main heading printed on the certificate.</small></label>
                  </div>
                  <div className="form-divider"/>
                  <div className="form-title"><span className="form-step">02</span><div><h2>Recipient spreadsheet</h2><p>Upload a CSV or Excel file with recipient information.</p></div><button type="button" className="template-link" onClick={()=>void downloadTemplate().catch(e=>setNotice({kind:'error',text:e.message}))}><ArrowDownToLine size={15}/> Download template</button></div>
                  <input ref={fileRef} type="file" accept=".xlsx,.csv" hidden onChange={e=>chooseFile(e.target.files?.[0])}/>
                  <div className={`dropzone ${dragging?'dragging':''} ${file?'has-file':''}`} onDragOver={e=>{e.preventDefault();setDragging(true)}} onDragLeave={()=>setDragging(false)} onDrop={e=>{e.preventDefault();setDragging(false);chooseFile(e.dataTransfer.files?.[0])}} onClick={()=>fileRef.current?.click()} role="button" tabIndex={0} onKeyDown={e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();fileRef.current?.click()}}}>
                    <div className="upload-symbol">{file?<FileSpreadsheet size={25}/>:<CloudUpload size={25}/>}</div>
                    {file?<><strong>{file.name}</strong><p>{(file.size/1024).toFixed(1)} KB · Ready to upload</p><span className="file-change">Choose a different file</span></>:<><strong>Drop your spreadsheet here</strong><p>or <span>browse files</span> from your computer</p><div className="file-types"><span>.XLSX</span><span>.CSV</span><span>MAX 10 MB</span></div></>}
                  </div>
                  <div className="requirements"><div><CheckCircle2 size={15}/> Required: <code>recipient_name</code></div><div><CheckCircle2 size={15}/> Optional: <code>recipient_email</code>, <code>custom_remarks</code></div></div>
                  <div className="submit-row">
                    <div className="secure-note"><ShieldCheck size={16}/><span>Protected by cryptographic verification code and isolation safeguards.</span></div>
                    <button className="primary-btn" type="submit" disabled={busy}>{busy?<><LoaderCircle className="spin" size={17}/> Queueing batch…</>:<>Generate certificates <ArrowRight size={16}/></>}</button>
                  </div>
                </form>
                <aside className="generation-aside">
                  <div className="panel process-panel">
                    <div className="aside-heading"><Sparkles size={17}/><h3>How it works</h3></div>
                    <div className="process-step"><div className="process-number">1</div><div><strong>Upload recipients</strong><p>Add your validated recipient spreadsheet.</p></div></div>
                    <div className="process-connector"/>
                    <div className="process-step"><div className="process-number">2</div><div><strong>Generation begins</strong><p>Backend generates vector PDFs and backs them up to cloud.</p></div></div>
                    <div className="process-connector"/>
                    <div className="process-step"><div className="process-number">3</div><div><strong>Track & download</strong><p>Follow live progress and download successful certificates.</p></div></div>
                  </div>
                  <div className="panel privacy-panel">
                    <div className="privacy-icon"><ShieldCheck size={20}/></div>
                    <h3>Built around your workflow</h3>
                    <p>Certificates can be stored locally or backed up to Cloudflare R2 / Supabase free tier.</p>
                    <div className="privacy-foot"><span className="system-pulse healthy"/> {storageProviderName}</div>
                  </div>
                  <div className="aside-note"><CircleHelp size={15}/><p>Need the exact spreadsheet columns? Download the sample template above before uploading.</p></div>
                </aside>
              </div>
            </motion.section>}

            {page==='templates'&&<motion.section key="templates" className="page-view" initial={{opacity:0,y:8}} animate={{opacity:1,y:0}} exit={{opacity:0,y:-6}} transition={{duration:.2}}>
              <div className="page-heading">
                <div>
                  <div className="eyebrow"><span className="eyebrow-dot"/> DESIGN & TEMPLATES STUDIO</div>
                  <h1>Live Assets & <span>Certificate Design.</span></h1>
                  <p>Provide your authorized signature photo for live Pillow background removal, or upload custom certificate template designs.</p>
                </div>
                <div style={{display:'flex',gap:'10px'}}>
                  <button className="subtle-btn" onClick={()=>{void refreshTemplateAssets(); setSigPreviewVer(Date.now()); setBgPreviewVer(Date.now());}}><RefreshCw size={15}/> Reload assets</button>
                  <button className="primary-btn" onClick={()=>go('generate')}>Generate batch <ArrowRight size={15}/></button>
                </div>
              </div>

              <div className="studio-layout">
                <div>
                  <div className="studio-grid">
                    {/* Card 1: Authorized Signature */}
                    <div className="studio-card">
                      <div className="studio-header">
                        <div>
                          <h3><Sparkles size={17} style={{color:'#4e72ed'}}/> Authorized Signature</h3>
                          <p>Upload a smartphone photo or scan of your signature.</p>
                        </div>
                        <span className={`asset-status ${templateAssets?.signature.exists ? 'active' : 'inactive'}`}>
                          {templateAssets?.signature.exists ? 'Active' : 'Fallback'}
                        </span>
                      </div>

                      <div className="pillow-badge">
                        <Sparkles size={12}/> Pillow AI Background Stripper Active
                      </div>

                      <div className="checkerboard-bg">
                        {templateAssets?.signature.exists ? (
                          <img
                            src={`${import.meta.env.VITE_API_BASE_URL || ''}/api/v1/templates/signature/preview?v=${sigPreviewVer}`}
                            alt="Processed Signature"
                            className="signature-preview-img"
                            key={sigPreviewVer}
                          />
                        ) : (
                          <div className="preview-empty-state">
                            <ImageIcon size={32}/>
                            <span>No signature graphic yet</span>
                            <small>Using issuer text line fallback</small>
                          </div>
                        )}
                      </div>

                      <div className="studio-meta">
                        <span><strong>Format:</strong> Transparent 32-bit PNG</span>
                        <span><strong>Source:</strong> {templateAssets?.signature.filename || 'None'}</span>
                      </div>

                      <div className="folder-hint">
                        <CircleHelp size={16}/>
                        <div>
                          <strong>Filesystem Live Fetch:</strong>
                          <span>You can also drop any image directly into <code>templates/signatures/</code> on the server!</span>
                        </div>
                      </div>

                      <input
                        ref={sigFileRef}
                        type="file"
                        accept="image/png,image/jpeg,image/webp"
                        hidden
                        onChange={e => {
                          const f = e.target.files?.[0];
                          if (f) void handleUploadSignature(f);
                        }}
                      />

                      <div className="studio-actions">
                        <button
                          type="button"
                          className="primary-btn"
                          disabled={assetBusy}
                          onClick={() => sigFileRef.current?.click()}
                        >
                          <CloudUpload size={15}/> {templateAssets?.signature.exists ? 'Replace signature' : 'Upload photo'}
                        </button>
                        {templateAssets?.signature.exists && (
                          <button
                            type="button"
                            className="subtle-btn"
                            disabled={assetBusy}
                            onClick={() => void handleResetSignature()}
                          >
                            <Trash2 size={15}/> Reset
                          </button>
                        )}
                      </div>
                    </div>

                    {/* Card 2: Custom Background Template */}
                    <div className="studio-card">
                      <div className="studio-header">
                        <div>
                          <h3><Palette size={17} style={{color:'#159b71'}}/> Certificate Template</h3>
                          <p>Upload a custom design from Canva, Photoshop, or Figma.</p>
                        </div>
                        <span className={`asset-status ${templateAssets?.background.exists ? 'active' : 'inactive'}`}>
                          {templateAssets?.background.exists ? 'Custom' : 'Executive Classic'}
                        </span>
                      </div>

                      <div className="pillow-badge" style={{background:'#eefcf5',borderColor:'#c1ebd7',color:'#159b71'}}>
                        <Sparkles size={12}/> Vector & Backdrop Live Overlay
                      </div>

                      <div className="template-preview-box">
                        {templateAssets?.background.exists ? (
                          <img
                            src={`${import.meta.env.VITE_API_BASE_URL || ''}/api/v1/templates/background/preview?v=${bgPreviewVer}`}
                            alt="Certificate Template"
                            className="template-preview-img"
                            key={bgPreviewVer}
                          />
                        ) : (
                          <div className="preview-empty-state">
                            <BadgeCheck size={36} style={{color:'#b89a53'}}/>
                            <strong style={{color:'#334155'}}>Executive Classic (Vector)</strong>
                            <small>Gold & Navy double borders with verified seal</small>
                          </div>
                        )}
                      </div>

                      <div className="studio-meta">
                        <span><strong>Layout:</strong> A4 Landscape (842 x 595 pt)</span>
                        <span><strong>Active:</strong> {templateAssets?.background.exists ? templateAssets.background.filename : 'Built-in Classic'}</span>
                      </div>

                      <div className="folder-hint">
                        <CircleHelp size={16}/>
                        <div>
                          <strong>Filesystem Live Fetch:</strong>
                          <span>You can also drop your template image into <code>templates/backgrounds/</code>!</span>
                        </div>
                      </div>

                      <input
                        ref={bgFileRef}
                        type="file"
                        accept="image/png,image/jpeg,image/webp"
                        hidden
                        onChange={e => {
                          const f = e.target.files?.[0];
                          if (f) void handleUploadBackground(f);
                        }}
                      />

                      <div className="studio-actions">
                        <button
                          type="button"
                          className="primary-btn"
                          disabled={assetBusy}
                          onClick={() => bgFileRef.current?.click()}
                        >
                          <CloudUpload size={15}/> {templateAssets?.background.exists ? 'Replace template' : 'Upload template'}
                        </button>
                        {templateAssets?.background.exists && (
                          <button
                            type="button"
                            className="subtle-btn"
                            disabled={assetBusy}
                            onClick={() => void handleResetBackground()}
                          >
                            <Trash2 size={15}/> Reset to Classic
                          </button>
                        )}
                      </div>
                    </div>

                    {/* Card 3: AI Layout & Alignment Assistant (Overlap Solution) */}
                    <div className="ai-layout-card">
                      <div className="ai-layout-header">
                        <div>
                          <h3><Wand2 size={17} style={{color:'#6366f1'}}/> AI Layout & Alignment Assistant</h3>
                          <p>Eliminate overlapping text on pre-printed Canva/Figma certificates with Gemini Vision or 1-click presets.</p>
                        </div>
                        <span className="ai-model-badge">
                          <Sparkles size={11}/> Gemini Vision 2.5
                        </span>
                      </div>

                      {/* Presets and AI Auto-Detect Actions */}
                      <div className="ai-action-bar">
                        <button
                          type="button"
                          className="ai-preset-btn sparkle-btn"
                          disabled={aiBusy || !templateAssets?.background.exists}
                          onClick={() => void handleAiAnalyze()}
                          title="Sends template to Google Gemini Vision Multimodal LLM to auto-detect text zones"
                        >
                          {aiBusy ? <LoaderCircle className="spin" size={14}/> : <Sparkles size={14}/>}
                          {aiBusy ? 'Analyzing Layout…' : '✨ Auto-Detect with AI (Gemini Vision)'}
                        </button>

                        <button
                          type="button"
                          className={`ai-preset-btn ${layoutConfig?.template_mode === 'preprinted' ? 'active' : ''}`}
                          onClick={() => void handleApplyPreset('preprinted')}
                          title="Hides duplicate title, subtitle, and ribbon, perfectly positioning name and event without overlaps."
                        >
                          <Zap size={13} style={{color:'#d97706'}}/> Canva Pre-printed (Overlap Fix)
                        </button>

                        <button
                          type="button"
                          className={`ai-preset-btn ${layoutConfig?.template_mode === 'frame' ? 'active' : ''}`}
                          onClick={() => void handleApplyPreset('frame')}
                          title="Renders all standard certificate titles, underlines, and seals for blank border frames."
                        >
                          <LayoutDashboard size={13}/> Blank Border Frame
                        </button>

                        <button
                          type="button"
                          className="subtle-btn"
                          style={{padding:'7px 10px',fontSize:'11px'}}
                          onClick={() => setShowApiKeyInput(s => !s)}
                          title="Configure custom Gemini API key"
                        >
                          <Sliders size={13}/> {showApiKeyInput ? 'Hide Key' : 'API Key'}
                        </button>
                      </div>

                      {showApiKeyInput && (
                        <div className="ai-key-input-row">
                          <span style={{fontWeight:600,color:'#4f46e5'}}>Gemini API Key:</span>
                          <input
                            type="password"
                            placeholder="AIzaSy... (leave blank to use server .env or intelligent preset)"
                            value={geminiApiKey}
                            onChange={e => setGeminiApiKey(e.target.value)}
                          />
                          <button
                            type="button"
                            className="primary-btn"
                            style={{padding:'6px 12px',fontSize:'10px'}}
                            onClick={() => void handleAiAnalyze()}
                            disabled={aiBusy}
                          >
                            Analyze
                          </button>
                        </div>
                      )}

                      {/* Component Visibility Toggles */}
                      <div>
                        <div style={{fontSize:'11px',fontWeight:700,color:'#334155',marginBottom:'8px',display:'flex',alignItems:'center',gap:'6px'}}>
                          <Eye size={13}/> Text Visibility Toggles (Hide pre-printed elements to prevent overlap):
                        </div>
                        <div className="ai-toggles-grid">
                          <label className={`ai-toggle-chip ${layoutConfig?.render_title ? 'enabled' : ''}`}>
                            <input
                              type="checkbox"
                              checked={!!layoutConfig?.render_title}
                              onChange={e => void handleUpdateLayoutField('render_title', e.target.checked)}
                            />
                            <span>Certificate Title</span>
                          </label>

                          <label className={`ai-toggle-chip ${layoutConfig?.render_subtitle ? 'enabled' : ''}`}>
                            <input
                              type="checkbox"
                              checked={!!layoutConfig?.render_subtitle}
                              onChange={e => void handleUpdateLayoutField('render_subtitle', e.target.checked)}
                            />
                            <span>Presentation Subtitle</span>
                          </label>

                          <label className={`ai-toggle-chip ${layoutConfig?.render_issuer ? 'enabled' : ''}`}>
                            <input
                              type="checkbox"
                              checked={!!layoutConfig?.render_issuer}
                              onChange={e => void handleUpdateLayoutField('render_issuer', e.target.checked)}
                            />
                            <span>Issuer Organization Header</span>
                          </label>

                          <label className={`ai-toggle-chip ${layoutConfig?.render_description ? 'enabled' : ''}`}>
                            <input
                              type="checkbox"
                              checked={!!layoutConfig?.render_description}
                              onChange={e => void handleUpdateLayoutField('render_description', e.target.checked)}
                            />
                            <span>Curriculum Description</span>
                          </label>

                          <label className={`ai-toggle-chip ${layoutConfig?.render_recipient_underline ? 'enabled' : ''}`}>
                            <input
                              type="checkbox"
                              checked={!!layoutConfig?.render_recipient_underline}
                              onChange={e => void handleUpdateLayoutField('render_recipient_underline', e.target.checked)}
                            />
                            <span>Name Underline Accent</span>
                          </label>

                          <label className={`ai-toggle-chip ${layoutConfig?.render_seal ? 'enabled' : ''}`}>
                            <input
                              type="checkbox"
                              checked={!!layoutConfig?.render_seal}
                              onChange={e => void handleUpdateLayoutField('render_seal', e.target.checked)}
                            />
                            <span>Official Vector Seal</span>
                          </label>
                        </div>
                      </div>

                      {/* Precise Coordinate Tuning Sliders */}
                      <div>
                        <div style={{fontSize:'11px',fontWeight:700,color:'#334155',marginBottom:'8px',display:'flex',alignItems:'center',gap:'6px'}}>
                          <Sliders size={13}/> Precise Placement Sliders (A4 Landscape Canvas):
                        </div>
                        <div className="ai-sliders-container">
                          <div className="ai-slider-item">
                            <div className="ai-slider-label">
                              <span>Recipient Name Y-Position</span>
                              <span className="ai-slider-value">{layoutConfig?.recipient_name_y ?? 335} pt</span>
                            </div>
                            <input
                              type="range"
                              min="200"
                              max="460"
                              step="2"
                              value={layoutConfig?.recipient_name_y ?? 335}
                              onChange={e => void handleUpdateLayoutField('recipient_name_y', Number(e.target.value))}
                            />
                          </div>

                          <div className="ai-slider-item">
                            <div className="ai-slider-label">
                              <span>Recipient Font Size</span>
                              <span className="ai-slider-value">{layoutConfig?.recipient_name_font_size ?? 30} pt</span>
                            </div>
                            <input
                              type="range"
                              min="18"
                              max="44"
                              step="1"
                              value={layoutConfig?.recipient_name_font_size ?? 30}
                              onChange={e => void handleUpdateLayoutField('recipient_name_font_size', Number(e.target.value))}
                            />
                          </div>

                          <div className="ai-slider-item">
                            <div className="ai-slider-label">
                              <span>Event / Course Y-Position</span>
                              <span className="ai-slider-value">{layoutConfig?.event_y ?? 255} pt</span>
                            </div>
                            <input
                              type="range"
                              min="150"
                              max="340"
                              step="2"
                              value={layoutConfig?.event_y ?? 255}
                              onChange={e => void handleUpdateLayoutField('event_y', Number(e.target.value))}
                            />
                          </div>

                          <div className="ai-slider-item">
                            <div className="ai-slider-label">
                              <span>Signature Horizontal (X)</span>
                              <span className="ai-slider-value">{layoutConfig?.signature_x ?? 680} pt</span>
                            </div>
                            <input
                              type="range"
                              min="450"
                              max="760"
                              step="5"
                              value={layoutConfig?.signature_x ?? 680}
                              onChange={e => void handleUpdateLayoutField('signature_x', Number(e.target.value))}
                            />
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Right Column: Live Certificate Sample Preview */}
                <div className="live-preview-panel">
                  <div className="live-preview-header">
                    <h3><Eye size={17} style={{color:'#4e72ed'}}/> Live Certificate Preview</h3>
                    <div style={{display:'flex',gap:'8px'}}>
                      <button
                        className="subtle-btn"
                        style={{padding:'6px 10px',fontSize:'10px'}}
                        onClick={()=>{setSigPreviewVer(Date.now()); setBgPreviewVer(Date.now());}}
                        title="Re-render live preview"
                      >
                        <RefreshCw size={13}/> Refresh
                      </button>
                      <a
                        href={`${import.meta.env.VITE_API_BASE_URL || ''}/api/v1/templates/sample-preview`}
                        target="_blank"
                        rel="noreferrer"
                        className="subtle-btn"
                        style={{padding:'6px 10px',fontSize:'10px'}}
                      >
                        Fullscreen <ArrowRight size={13}/>
                      </a>
                    </div>
                  </div>
                  <iframe
                    key={`${sigPreviewVer}_${bgPreviewVer}`}
                    src={`${import.meta.env.VITE_API_BASE_URL || ''}/api/v1/templates/sample-preview?v=${sigPreviewVer}_${bgPreviewVer}`}
                    className="live-preview-frame"
                    title="Live Sample Certificate Preview"
                  />
                  <div style={{fontSize:'10px',color:'#8c98ac',marginTop:'10px',textAlign:'center'}}>
                    Preview reflects current live signature and background template.
                  </div>
                </div>
              </div>
            </motion.section>}

            {page==='jobs'&&<motion.section key="jobs" className="page-view" initial={{opacity:0,y:8}} animate={{opacity:1,y:0}} exit={{opacity:0,y:-6}} transition={{duration:.2}}>
              <div className="page-heading">
                <div>
                  <div className="eyebrow"><span className="eyebrow-dot"/> JOB MONITOR</div>
                  <h1>Every batch, <span>in view.</span></h1>
                  <p>Monitor progress, inspect recipient outcomes, and retrieve finished certificates.</p>
                </div>
                <button className="primary-btn" onClick={()=>go('generate')}><Plus size={17}/> New batch</button>
              </div>
              <div className="jobs-layout">
                <div className="panel jobs-list-panel">
                  <div className="panel-heading">
                    <div><h3>Tracked jobs</h3><p>Live progress from your backend.</p></div>
                    <button className="icon-btn" onClick={()=>{void syncServerJobs(); void refreshOverview();}} aria-label="Refresh jobs"><RefreshCw size={16}/></button>
                  </div>
                  <div className="search-box"><Search size={16}/><input value={query} onChange={e=>setQuery(e.target.value)} placeholder="Search event or job ID…"/><span>{filteredRecent.length}</span></div>
                  {filteredRecent.length===0?<EmptyState title="No tracked jobs yet" body="Create a batch or paste a job ID below to start monitoring." action="Create a batch" onAction={()=>go('generate')}/>:<div className="tracked-list">{filteredRecent.map(j=><button key={j.id} className={`tracked-job ${selectedId===j.id?'selected':''}`} onClick={()=>{setSelectedId(j.id);setNotice(null)}}><span className="tracked-icon"><FileText size={17}/></span><span className="tracked-copy"><strong>{j.event||'Certificate batch'}</strong><small>{formatDate(j.created)} · {j.id.slice(0,13)}…</small></span><ArrowRight size={15}/></button>)}</div>}
                  <form className="lookup-form" onSubmit={e=>{e.preventDefault();if(query.trim().length>8)openJob(query.trim());else setNotice({kind:'info',text:'Paste a full job ID into search to open it.'})}}><label>Open a job by ID</label><div><input value={query} onChange={e=>setQuery(e.target.value)} placeholder="Paste job UUID"/><button type="submit" className="secondary-btn">Open</button></div><small>Useful for opening jobs from another browser session.</small></form>
                </div>

                <div className="job-detail-column">
                  {!selectedId?<div className="panel job-placeholder"><div className="placeholder-art"><Activity size={31}/></div><h2>Select a generation job</h2><p>Choose a tracked job to see its progress, recipient results, and available downloads.</p><button className="secondary-btn" onClick={()=>go('generate')}><Plus size={16}/> Create a batch</button></div>:<>
                    <div className="panel job-detail-panel">
                      <div className="job-detail-top">
                        <div>
                          <div className="eyebrow">JOB DETAILS</div>
                          <h2>{selectedJob?.event_name||recent.find(j=>j.id===selectedId)?.event||'Loading job…'}</h2>
                          <p className="job-id">ID <code>{selectedId}</code> <button className="copy-id" onClick={()=>void navigator.clipboard?.writeText(selectedId)} title="Copy job ID"><FileText size={13}/></button></p>
                        </div>
                        <button className="icon-btn" onClick={()=>void refreshJob(selectedId)} aria-label="Refresh selected job"><RefreshCw size={16} className={loadingJob?'spin':''}/></button>
                      </div>
                      {selectedJob?<>
                        <div className="job-status-line">
                          <StatusPill status={selectedJob.status}/>
                          <span>Created {formatDate(selectedJob.created_at)} at {formatTime(selectedJob.created_at)}</span>
                          <span className="auto-refresh"><span className="system-pulse healthy"/> Auto-refresh</span>
                        </div>
                        <div className="progress-heading"><span>Generation progress</span><strong>{Math.round(selectedJob.progress_percentage||0)}%</strong></div>
                        <div className="progress-track"><motion.div className="progress-fill" initial={{width:0}} animate={{width:`${Math.min(100,Math.max(0,selectedJob.progress_percentage||0))}%`}} transition={{duration:.6}}/></div>
                        <div className="progress-foot"><span>{formatNumber((selectedJob.successful_count||0)+(selectedJob.failed_count||0))} of {formatNumber(selectedJob.total_recipients)} processed</span><span>{formatNumber(selectedJob.pending_count)} pending</span></div>
                        <div className="job-metrics">
                          <div><span className="metric-icon green-bg"><CheckCircle2 size={17}/></span><span><small>Successful</small><strong>{formatNumber(selectedJob.successful_count)}</strong></span></div>
                          <div><span className="metric-icon rose-bg"><XCircle size={17}/></span><span><small>Failed</small><strong>{formatNumber(selectedJob.failed_count)}</strong></span></div>
                          <div><span className="metric-icon blue-bg"><LoaderCircle size={17}/></span><span><small>Processing</small><strong>{formatNumber(selectedJob.processing_count)}</strong></span></div>
                          <div><span className="metric-icon amber-bg"><Clock3 size={17}/></span><span><small>Pending</small><strong>{formatNumber(selectedJob.pending_count)}</strong></span></div>
                        </div>
                        {selectedJob.zip_download_url&&selectedJob.successful_count>0&&<button className="download-zip-btn" disabled={actionBusy} onClick={()=>void doDownloadZip(selectedId)}><ArrowDownToLine size={17}/> Download all successful certificates <span>{selectedJob.successful_count} PDFs</span></button>}
                      </>:<div className="loading-state"><LoaderCircle className="spin" size={20}/> Fetching job status from API…</div>}
                    </div>

                    <div className="panel recipients-panel">
                      <div className="panel-heading recipients-heading">
                        <div><h3>Recipient results</h3><p>Inspect each recipient's generation status.</p></div>
                        <select value={recordFilter} onChange={e=>{setRecordFilter(e.target.value);void refreshJob(selectedId,e.target.value)}} aria-label="Filter recipient status">
                          <option value="">All statuses</option>
                          <option value="SUCCESS">Successful</option>
                          <option value="FAILED">Failed</option>
                          <option value="PROCESSING">Processing</option>
                          <option value="PENDING">Pending</option>
                        </select>
                      </div>
                      {records.length===0?<EmptyState title="No recipient records returned" body={selectedJob?'No records match this filter yet. Results refresh automatically.':'Loading recipients from your backend.'}/>:<div className="recipient-table-wrap"><table><thead><tr><th>RECIPIENT</th><th>STATUS</th><th>DETAILS</th><th/></tr></thead><tbody>{records.map(r=><tr key={r.id}><td><div className="recipient-cell"><Initials name={r.recipient_name}/><span><strong>{r.recipient_name}</strong><small>{r.recipient_email||'No email supplied'}</small></span></div></td><td><StatusPill status={r.status}/></td><td>{r.status==='FAILED'?<span className="error-detail" title={r.error_message||''}>{r.error_message||r.error_code||'Generation failed'}</span>:r.certificate_id?<code>{r.certificate_id}</code>:<span className="muted">{r.status==='SUCCESS'?'Certificate ready':'Waiting for worker'}</span>}</td><td>{r.status==='SUCCESS'&&r.certificate_id&&<button className="download-icon" onClick={()=>void doDownloadCertificate(r.certificate_id!)} title="Download certificate"><ArrowDownToLine size={16}/></button>}</td></tr>)}</tbody></table></div>}
                      <div className="table-foot"><span>Showing up to 100 recipient records</span><span>Refresh interval · {Math.round(POLL_MS/1000)}s</span></div>
                    </div>
                  </>}
                </div>
              </div>
            </motion.section>}
          </AnimatePresence>

          <footer className="footer">
            <span>© {new Date().getFullYear()} CertFlow <i/> Bulk Certificate Generator with Free Cloud Storage.</span>
            <span>
              <span className={`system-pulse ${health}`}/> {health==='healthy'?'Connected to backend':'Backend connection needs attention'}
              <a href={`${import.meta.env.VITE_API_BASE_URL||'http://127.0.0.1:8000'}/docs`} target="_blank" rel="noreferrer">API docs <ArrowRight size={12}/></a>
            </span>
          </footer>
        </div>
      </main>

      {/* Google Authentication & Cloud Storage Modal */}
      <AnimatePresence>
        {authModalOpen && (
          <div className="auth-modal-backdrop" onClick={()=>setAuthModalOpen(false)}>
            <motion.div
              className="auth-modal-card"
              initial={{scale:0.95,opacity:0}}
              animate={{scale:1,opacity:1}}
              exit={{scale:0.95,opacity:0}}
              onClick={e=>e.stopPropagation()}
            >
              <div className="auth-modal-header">
                <button className="auth-modal-close" onClick={()=>setAuthModalOpen(false)} aria-label="Close modal">
                  <X size={16}/>
                </button>
                <div className="auth-modal-badge">
                  <GoogleGLogo />
                  <span>GOOGLE IDENTITY</span>
                </div>
                <h2>{user ? 'Account & Storage' : 'Sign in to CertFlow'}</h2>
                <p>{user ? 'Your certificate workspace is connected.' : 'Sign in with your Google account to associate jobs and sync across devices.'}</p>
              </div>

              <div className="auth-modal-body">
                {user ? (
                  <div>
                    <div className="demo-account-chip" style={{background:'#f0fdf4',borderColor:'#bbf7d0',marginBottom:'14px'}}>
                      {user.avatar_url ? (
                        <img src={user.avatar_url} alt={user.full_name} className="user-avatar-img" />
                      ) : (
                        <div className="profile-avatar">{user.full_name.slice(0, 2).toUpperCase()}</div>
                      )}
                      <div>
                        <strong>{user.full_name}</strong>
                        <small>{user.email}</small>
                      </div>
                      <BadgeCheck size={18} style={{marginLeft:'auto',color:'#16a34a'}}/>
                    </div>
                    <button className="primary-btn auth-btn-full" onClick={()=>{void handleLogout(); setAuthModalOpen(false);}}>
                      <LogOut size={16}/> Sign Out
                    </button>
                  </div>
                ) : (
                  <div>
                    {authConfig?.google_client_id ? (
                      <div>
                        <button
                          className="google-sign-in-btn auth-btn-full"
                          onClick={() => {
                            setNotice({ kind: 'info', text: 'Google OAuth Client ID is registered. Sign-in popup opening...' });
                          }}
                        >
                          <GoogleGLogo />
                          <span>Continue with Google</span>
                        </button>
                      </div>
                    ) : (
                      <div>
                        <div style={{marginBottom:'12px'}}>
                          <button
                            className="google-sign-in-btn auth-btn-full"
                            onClick={() => void handleDevLogin('Google Demo User', 'user@gmail.com')}
                          >
                            <GoogleGLogo />
                            <span>Sign in with Google (Instant Dev Login)</span>
                          </button>
                        </div>
                      </div>
                    )}

                    <div className="auth-divider">OR CHOOSE A DEMO PROFILE</div>

                    <div className="demo-accounts-grid">
                      <div className="demo-account-chip" onClick={() => void handleDevLogin('Sarah Connor', 'sarah.connor@edu.org')}>
                        <div className="avatar">SC</div>
                        <div>
                          <strong>Sarah Connor</strong>
                          <small>sarah.connor@edu.org · Course Director</small>
                        </div>
                        <ArrowRight size={14} style={{marginLeft:'auto',color:'#94a3b8'}}/>
                      </div>

                      <div className="demo-account-chip" onClick={() => void handleDevLogin('Alex Rivera', 'alex.rivera@techacademy.io')}>
                        <div className="avatar">AR</div>
                        <div>
                          <strong>Alex Rivera</strong>
                          <small>alex.rivera@techacademy.io · Certification Lead</small>
                        </div>
                        <ArrowRight size={14} style={{marginLeft:'auto',color:'#94a3b8'}}/>
                      </div>
                    </div>
                  </div>
                )}

                {/* Cloud Storage Status Banner */}
                <div className={`storage-status-banner ${authConfig?.cloud_storage_configured ? '' : 'local'}`}>
                  <Cloud size={20}/>
                  <div>
                    <strong>Cloud Storage: {storageProviderName}</strong>
                    <small>
                      {authConfig?.cloud_storage_configured
                        ? '100% Free Tier S3 Storage connected with zero egress fees.'
                        : 'Using zero-cost local SQLite & storage. Add Cloudflare R2 / Supabase in .env for remote sync.'}
                    </small>
                  </div>
                </div>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
}

function StatCard({label,value,icon,tone,foot,loading}:{label:string;value?:number;icon:ReactNode;tone:string;foot:string;loading:boolean}) {
  return (
    <motion.div className="stat-card" whileHover={{y:-2}} transition={{duration:.15}}>
      <div className="stat-top"><span>{label}</span><span className={`stat-icon ${tone}`}>{icon}</span></div>
      <div className="stat-value">{loading?<span className="skeleton-value"/>:formatNumber(value)}</div>
      <div className="stat-foot"><span className="stat-foot-dot"/>{foot}</div>
    </motion.div>
  );
}

function EmptyState({title,body,action,onAction}:{title:string;body:string;action?:string;onAction?:()=>void}) {
  return (
    <div className="empty-state">
      <div className="empty-icon"><FileText size={22}/></div>
      <strong>{title}</strong>
      <p>{body}</p>
      {action&&onAction&&<button className="secondary-btn" onClick={onAction}>{action} <ArrowRight size={14}/></button>}
    </div>
  );
}

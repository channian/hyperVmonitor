// Shared components for HV Dashboard
const { useState: useStateC, useEffect: useEffectC } = React;

// API 基底 URL：同源時留空，跨域時設為 FastAPI 位址（例如 http://192.168.1.200:8000）
const API_BASE = window.HVM_API_BASE || '';

function useFetch(path) {
  const [data, setData]     = useStateC(null);
  const [loading, setLoading] = useStateC(true);
  const [error, setError]   = useStateC(null);
  useEffectC(() => {
    let cancelled = false;
    setLoading(true);
    fetch(API_BASE + path)
      .then(r => { if (!r.ok) throw new Error(r.statusText); return r.json(); })
      .then(d => { if (!cancelled) { setData(d); setLoading(false); } })
      .catch(e => { if (!cancelled) { setError(e.message); setLoading(false); } });
    return () => { cancelled = true; };
  }, [path]);
  return { data, loading, error };
}

function LoadingCard() {
  return (
    <div className="card-ui" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: 120, color: '#475569', gap: 10 }}>
      <div className="dot" style={{ width: 8, height: 8, borderRadius: '50%', background: '#22d3ee', animation: 'pulse 1.2s infinite' }}></div>
      <span style={{ fontSize: 13 }}>載入中…</span>
    </div>
  );
}

function ErrorCard({ msg }) {
  return (
    <div className="card-ui" style={{ display: 'flex', alignItems: 'center', gap: 10, minHeight: 80, color: '#ef4444' }}>
      <Icon.alertTri style={{ width: 16, height: 16 }} />
      <span style={{ fontSize: 13 }}>API 錯誤：{msg}</span>
    </div>
  );
}

// ── Brand Mark ──────────────────────────────────────────────
function BrandMark() {
  return (
    <div className="brand">
      <svg className="brand-mark" viewBox="0 0 38 38">
        <rect x="1" y="1" width="36" height="36" rx="9" fill="#0f172a" stroke="#22d3ee" strokeOpacity="0.4" strokeWidth="1.5"/>
        <rect x="1" y="1" width="36" height="36" rx="9" fill="url(#hvG)" opacity="0.5"/>
        <text x="19" y="24" textAnchor="middle" fontFamily="Inter,sans-serif" fontWeight="800" fontSize="13" fill="#e6edf7" letterSpacing="-0.03em">HVM</text>
        <circle className="logo-pulse" cx="30" cy="30" r="3" fill="#22d3ee"/>
        <defs>
          <radialGradient id="hvG" cx="0.8" cy="0.2" r="0.9">
            <stop offset="0" stopColor="#22d3ee" stopOpacity="0.5"/>
            <stop offset="1" stopColor="#0f172a" stopOpacity="0"/>
          </radialGradient>
        </defs>
      </svg>
      <div>
        <div className="brand-title">Hyper-V</div>
        <div className="brand-sub">MONITOR</div>
      </div>
    </div>
  );
}

// ── Sidebar ──────────────────────────────────────────────────
function Sidebar({ page, setPage, alertCount }) {
  const items = [
    { id: 'overview',   label: '總覽',     en: 'Overview',   icon: <Icon.dashboard /> },
    { id: 'resources',  label: '資源監控', en: 'Resources',  icon: <Icon.cpu /> },
    { id: 'snapshots',  label: '快照合規', en: 'Snapshots',  icon: <Icon.camera />, badge: 8, badgeKind: 'err' },
    { id: 'backup',     label: '備份 / HA',en: 'Backup',     icon: <Icon.backup />, badge: 1, badgeKind: 'err' },
    { id: 'security',   label: '資安監控', en: 'Security',   icon: <Icon.shieldAlert />, badge: 3, badgeKind: 'err' },
    { id: 'alerts',     label: '告警設定', en: 'Alerts',     icon: <Icon.settings /> },
  ];
  return (
    <aside className="sidebar">
      <BrandMark />
      <div className="nav-section">MONITORING</div>
      {items.map(it => (
        <div key={it.id} className={`nav-item ${page === it.id ? 'active' : ''}`} onClick={() => setPage(it.id)}>
          {it.icon}
          <span>{it.label}</span>
          {it.badge ? (
            <span className={it.badgeKind === 'warn' ? 'badge-warn' : 'badge'}>{it.badge}</span>
          ) : null}
        </div>
      ))}
      <div className="nav-section">SYSTEM</div>
      <div className="nav-item"><Icon.settings /><span>系統設定</span></div>
      <div className="nav-item"><Icon.user /><span>管理帳號</span></div>
    </aside>
  );
}

// ── Topbar ───────────────────────────────────────────────────
function Topbar({ page }) {
  const [time, setTime] = useStateC(new Date());
  useEffectC(() => {
    const t = setInterval(() => setTime(new Date()), 30000);
    return () => clearInterval(t);
  }, []);
  const fmt = d => d.toLocaleTimeString('zh-TW', { hour: '2-digit', minute: '2-digit' });

  const titles = {
    overview:  { h1: 'Hyper-V 管理儀表板', crumb: 'home / overview' },
    resources: { h1: '資源監控',           crumb: 'home / resources' },
    snapshots: { h1: '快照合規管理',       crumb: 'home / snapshots' },
    backup:    { h1: '備份 / HA 狀態',    crumb: 'home / backup' },
    security:  { h1: '資安監控',           crumb: 'home / security' },
    alerts:    { h1: '告警規則設定',       crumb: 'home / alert-settings' },
  };
  const t = titles[page] || titles.overview;
  return (
    <header className="topbar">
      <div className="title">
        <h1>{t.h1}</h1>
        <div className="crumbs">{t.crumb}</div>
      </div>
      <span className="top-spacer"></span>
      <div className="top-meta">
        <div className="poll"><span className="dot"></span>LIVE · 最後更新 {fmt(time)}</div>
        <div className="avatar">IT</div>
      </div>
    </header>
  );
}

// ── Primitive Components ─────────────────────────────────────
function Pill({ kind = 'muted', children }) {
  return (
    <span className={`pill p-${kind}`}>
      <span className="dot"></span>
      {children}
    </span>
  );
}

function Dot({ kind = 'muted' }) {
  return <span className={`status-dot ${kind}`}></span>;
}

function Btn({ variant = 'ghost', size = 'sm', icon, children, onClick }) {
  return (
    <button className={`btn btn-${variant} ${size === 'sm' ? 'btn-sm' : ''}`} onClick={onClick}>
      {icon}{children}
    </button>
  );
}

function Card({ title, icon, actions, children, style, className }) {
  return (
    <div className={`card-ui ${className || ''}`} style={style}>
      {title && (
        <div className="card-hd">
          {icon}
          <span className="t">{title}</span>
          <span className="spacer"></span>
          {actions}
        </div>
      )}
      {children}
    </div>
  );
}

function Metric({ title, icon, value, unit, delta, deltaColor, active }) {
  const dc = deltaColor || '#64748b';
  return (
    <div className={`card-ui ${active ? 'metric-active' : ''}`}>
      <div className="card-hd">
        {icon}
        <span className="t" style={active ? { color: '#22d3ee' } : {}}>{title}</span>
      </div>
      <div className="metric-v">
        {value}
        {unit && <span style={{ fontSize: 14, color: '#94a3b8', marginLeft: 4, fontWeight: 500 }}>{unit}</span>}
      </div>
      {delta && <div className="metric-delta" style={{ color: dc }}>{delta}</div>}
    </div>
  );
}

// ── ProgressBar ──────────────────────────────────────────────
function ProgressBar({ pct, kind }) {
  const k = kind || (pct >= 85 ? 'err' : pct >= 70 ? 'warn' : 'ok');
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
      <div className="prog-wrap" style={{ flex: 1 }}>
        <div className={`prog-bar ${k}`} style={{ width: `${Math.min(pct, 100)}%` }}></div>
      </div>
      <span style={{ fontFamily: 'var(--font-mono)', fontSize: 12, color: k === 'err' ? '#ef4444' : k === 'warn' ? '#f59e0b' : '#22c55e', minWidth: 36, textAlign: 'right', fontVariantNumeric: 'tabular-nums' }}>{pct}%</span>
    </div>
  );
}

// ── Sparkline ────────────────────────────────────────────────
function Sparkline({ data, color = '#22d3ee', height = 48, width = 200 }) {
  if (!data || data.length < 2) return null;
  const max = Math.max(...data, 1);
  const min = 0;
  const range = max - min || 1;
  const pts = data.map((v, i) => {
    const x = (i / (data.length - 1)) * width;
    const y = height - ((v - min) / range) * height;
    return `${x},${y}`;
  });
  const area = `M${pts[0]} ` + pts.slice(1).map(p => `L${p}`).join(' ') + ` L${width},${height} L0,${height} Z`;
  const line = `M${pts[0]} ` + pts.slice(1).map(p => `L${p}`).join(' ');
  return (
    <svg className="sparkline" viewBox={`0 0 ${width} ${height}`} width="100%" height={height} preserveAspectRatio="none">
      <defs>
        <linearGradient id={`sg_${color.replace('#','')}`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity="0.25"/>
          <stop offset="100%" stopColor={color} stopOpacity="0.02"/>
        </linearGradient>
      </defs>
      <path d={area} fill={`url(#sg_${color.replace('#','')})`}/>
      <path d={line} fill="none" stroke={color} strokeWidth="1.5" strokeLinejoin="round" strokeLinecap="round"/>
    </svg>
  );
}

// ── Banner ───────────────────────────────────────────────────
function Banner({ kind = 'err', title, msg, actions }) {
  return (
    <div className={`banner ${kind}`}>
      <div className="banner-icon">
        {kind === 'err' ? <Icon.alertTri /> : <Icon.alert />}
      </div>
      <div className="banner-body">
        <h4>{title}</h4>
        <p>{msg}</p>
      </div>
      {actions}
    </div>
  );
}

Object.assign(window, { BrandMark, Sidebar, Topbar, Pill, Dot, Btn, Card, Metric, ProgressBar, Sparkline, Banner, useFetch, LoadingCard, ErrorCard, API_BASE });

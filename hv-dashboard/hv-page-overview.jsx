// Page: Overview 總覽頁
const { useState: useStateOv } = React;

function PageOverview({ setPage }) {
  const actionItems = [
    { sev: 'err',  who: 'KHTWXDB',      msg: 'CPU 持續 >90%，建議擴增 vCPU（目前 4 核）' },
    { sev: 'err',  who: '全部 VM（8台）', msg: '快照未清理，合規率 0/8，需排定維護視窗' },
    { sev: 'err',  who: 'KHTWIOTPWR',   msg: '備份連續失敗，上次備份 昨日 02:00，RPO 超標' },
    { sev: 'err',  who: 'KHTWIOTPWR',   msg: '複寫中斷 3 小時，DR 站點同步異常' },
    { sev: 'warn', who: 'KHTWIOTPWR',   msg: '記憶體壓力 79%，接近門檻 80%' },
    { sev: 'err',  who: 'KHTWXDB',      msg: '今日 03:42 偵測到連續登入失敗 × 8（暴力破解）' },
  ];

  const sectionCards = [
    {
      id: 'resources',
      title: '資源監控',
      icon: <Icon.cpu />,
      status: 'warn',
      summary: '2 台主機正常',
      detail: '1 台 VM CPU > 90%・1 台記憶體接近門檻',
      counts: [{ label: '實體主機', v: 2, k: 'ok' }, { label: '警告 VM', v: 2, k: 'warn' }],
    },
    {
      id: 'snapshots',
      title: '快照合規',
      icon: <Icon.camera />,
      status: 'err',
      summary: '合規率 0 / 8',
      detail: '8 台 VM 皆有快照，最舊已 397 天',
      counts: [{ label: '違規', v: 8, k: 'err' }, { label: '合規', v: 0, k: 'ok' }],
    },
    {
      id: 'backup',
      title: '備份 / HA',
      icon: <Icon.backup />,
      status: 'err',
      summary: '備份成功率 90%',
      detail: '1 台備份失敗・1 台複寫中斷 3hr',
      counts: [{ label: '備份失敗', v: 1, k: 'err' }, { label: '複寫中斷', v: 1, k: 'err' }],
    },
    {
      id: 'security',
      title: '資安監控',
      icon: <Icon.shieldAlert />,
      status: 'err',
      summary: '今日 3 件異常',
      detail: '暴力破解偵測・帳號鎖定・群組異動',
      counts: [{ label: '嚴重', v: 3, k: 'err' }, { label: '警告', v: 1, k: 'warn' }],
    },
  ];

  // Health score
  const healthPct = 52;
  const healthColor = '#ef4444';

  return (
    <>
      <Banner
        kind="err"
        title="[嚴重] 快照合規違規 · 8 台 VM 均存在超齡快照"
        msg="最嚴重：KHTWXDB / KHTWXAR 快照存在 397 天 · 需立即排定維護視窗清除"
        actions={<Btn variant="outline" size="sm" onClick={() => setPage('snapshots')}>查看快照</Btn>}
      />

      {/* KPI row */}
      <div className="metrics-5" style={{ marginBottom: 20 }}>
        <Metric title="實體主機" icon={<Icon.server />} value="2" delta="全部在線" deltaColor="#22c55e" />
        <Metric title="VM 總數" icon={<Icon.vm />} value="8" delta="全部 Running" deltaColor="#22c55e" />
        <Metric title="告警事項" icon={<Icon.bell />} value="6" delta="4 嚴重 · 2 警告" deltaColor="#ef4444" active />
        <Metric title="快照違規" icon={<Icon.camera />} value="8" delta="合規率 0%" deltaColor="#ef4444" active />
        <div className="card-ui" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 4 }}>
          <div className="card-hd" style={{ marginBottom: 8 }}>
            <Icon.activity style={{ width: 16, height: 16, color: '#22d3ee' }} />
            <span className="t">系統健康度</span>
          </div>
          <HealthGauge pct={healthPct} color={healthColor} />
        </div>
      </div>

      {/* Status section cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 16, marginBottom: 20 }}>
        {sectionCards.map(sc => (
          <div key={sc.id} className="card-ui overview-card" onClick={() => setPage(sc.id)}
            style={sc.status === 'err' ? { borderColor: 'rgba(239,68,68,0.3)' } : sc.status === 'warn' ? { borderColor: 'rgba(245,158,11,0.3)' } : {}}>
            <div className="card-hd" style={{ marginBottom: 10 }}>
              <div style={{ color: sc.status === 'err' ? '#ef4444' : sc.status === 'warn' ? '#f59e0b' : '#22c55e' }}>{sc.icon}</div>
              <span className="t">{sc.title}</span>
              <span className="spacer"></span>
              <Icon.chevR style={{ width: 14, height: 14, color: '#475569' }} />
            </div>
            <div style={{ display: 'flex', gap: 16, marginBottom: 10 }}>
              {sc.counts.map((c, i) => (
                <div key={i}>
                  <div style={{ fontFamily: 'var(--font-mono)', fontSize: 24, fontWeight: 700, color: c.k === 'err' ? '#ef4444' : c.k === 'warn' ? '#f59e0b' : '#22c55e', fontVariantNumeric: 'tabular-nums' }}>{c.v}</div>
                  <div style={{ fontSize: 11, color: '#64748b' }}>{c.label}</div>
                </div>
              ))}
            </div>
            <div style={{ fontSize: 12, color: '#94a3b8', lineHeight: 1.5 }}>{sc.detail}</div>
          </div>
        ))}
      </div>

      {/* Action items */}
      <Card title="待處理事項 · ACTION ITEMS" icon={<Icon.alertTri />}
        actions={<span style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: '#64748b' }}>{actionItems.length} 項</span>}>
        {actionItems.map((a, i) => (
          <div key={i} className="action-item">
            <div className={`action-sev ${a.sev}`}></div>
            <div className="action-body">
              <div className="who">{a.who}</div>
              <div className="msg">{a.msg}</div>
            </div>
            <Pill kind={a.sev === 'err' ? 'err' : 'warn'}>{a.sev === 'err' ? '嚴重' : '警告'}</Pill>
          </div>
        ))}
      </Card>
    </>
  );
}

function HealthGauge({ pct, color }) {
  const r = 32, stroke = 7;
  const circ = 2 * Math.PI * r;
  const dash = (pct / 100) * circ;
  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
      <svg width="80" height="80" viewBox="0 0 80 80">
        <circle cx="40" cy="40" r={r} fill="none" stroke="#1e293b" strokeWidth={stroke}/>
        <circle cx="40" cy="40" r={r} fill="none" stroke={color} strokeWidth={stroke}
          strokeDasharray={`${dash} ${circ}`} strokeDashoffset={circ * 0.25}
          strokeLinecap="round" style={{ transition: 'stroke-dasharray 600ms' }}/>
        <text x="40" y="44" textAnchor="middle" fill={color} fontSize="16" fontWeight="700" fontFamily="var(--font-mono)">{pct}%</text>
      </svg>
    </div>
  );
}

window.PageOverview = PageOverview;

// Page: Overview 總覽頁
function PageOverview({ setPage }) {
  const { data, loading, error } = useFetch('/api/overview');

  if (loading) return <LoadingCard />;
  if (error)   return <ErrorCard msg={error} />;

  const { action_items: actionItems, section_cards: sectionCards, health_pct, alert_count, vm_count, host_count, snapshot_violation_count } = data;

  const healthColor = health_pct >= 80 ? '#22c55e' : health_pct >= 60 ? '#f59e0b' : '#ef4444';
  const criticalBanner = sectionCards.find(s => s.status === 'err');

  return (
    <>
      {criticalBanner && (
        <Banner
          kind="err"
          title={`[嚴重] ${criticalBanner.title} · ${criticalBanner.summary}`}
          msg={criticalBanner.detail}
          actions={<Btn variant="outline" size="sm" onClick={() => setPage(criticalBanner.id)}>查看詳情</Btn>}
        />
      )}

      {/* KPI row */}
      <div className="metrics-5" style={{ marginBottom: 20 }}>
        <Metric title="實體主機" icon={<Icon.server />} value={String(host_count)} delta="全部在線" deltaColor="#22c55e" />
        <Metric title="VM 總數"  icon={<Icon.vm />}     value={String(vm_count)}   delta="全部 Running" deltaColor="#22c55e" />
        <Metric title="告警事項" icon={<Icon.bell />}   value={String(alert_count)} delta={`${actionItems.filter(a=>a.severity==='err').length} 嚴重 · ${actionItems.filter(a=>a.severity==='warn').length} 警告`} deltaColor="#ef4444" active={alert_count > 0} />
        <Metric title="快照違規" icon={<Icon.camera />} value={String(snapshot_violation_count)} delta={`合規率 ${8 - snapshot_violation_count}/${vm_count}`} deltaColor="#ef4444" active={snapshot_violation_count > 0} />
        <div className="card-ui" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 4 }}>
          <div className="card-hd" style={{ marginBottom: 8 }}>
            <Icon.activity style={{ width: 16, height: 16, color: '#22d3ee' }} />
            <span className="t">系統健康度</span>
          </div>
          <HealthGauge pct={health_pct} color={healthColor} />
        </div>
      </div>

      {/* Status section cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 16, marginBottom: 20 }}>
        {sectionCards.map(sc => {
          const iconMap = { resources: <Icon.cpu />, snapshots: <Icon.camera />, backup: <Icon.backup />, security: <Icon.shieldAlert /> };
          return (
            <div key={sc.id} className="card-ui overview-card" onClick={() => setPage(sc.id)}
              style={sc.status === 'err' ? { borderColor: 'rgba(239,68,68,0.3)' } : sc.status === 'warn' ? { borderColor: 'rgba(245,158,11,0.3)' } : {}}>
              <div className="card-hd" style={{ marginBottom: 10 }}>
                <div style={{ color: sc.status === 'err' ? '#ef4444' : sc.status === 'warn' ? '#f59e0b' : '#22c55e' }}>{iconMap[sc.id]}</div>
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
          );
        })}
      </div>

      {/* Action items */}
      <Card title="待處理事項 · ACTION ITEMS" icon={<Icon.alertTri />}
        actions={<span style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: '#64748b' }}>{actionItems.length} 項</span>}>
        {actionItems.map((a, i) => (
          <div key={i} className="action-item">
            <div className={`action-sev ${a.severity}`}></div>
            <div className="action-body">
              <div className="who">{a.source}</div>
              <div className="msg">{a.message}</div>
            </div>
            <Pill kind={a.severity === 'err' ? 'err' : 'warn'}>{a.severity === 'err' ? '嚴重' : '警告'}</Pill>
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

// Page: 快照合規管理
const { useState: useStateSn } = React;

function PageSnapshots() {
  const [selected, setSelected] = useStateSn(null);
  const { data, loading, error } = useFetch('/api/snapshots');

  if (loading) return <LoadingCard />;
  if (error)   return <ErrorCard msg={error} />;

  const { items: snapshots, compliance_count, violation_count, total_count } = data;

  const oldestDays = snapshots.length ? Math.max(...snapshots.map(s => s.age_days)) : 0;
  const sqlViolation = snapshots.filter(s => s.is_sql && s.snapshot_count > 0).length;

  const fmtDate = (iso) => iso ? iso.slice(0, 10) : '—';

  const daysBar = (d) => {
    const pct = Math.min((d / 400) * 100, 100);
    const color = d > 7 ? '#ef4444' : d > 3 ? '#f59e0b' : '#22c55e';
    return (
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <div style={{ flex: 1, height: 6, background: '#1e293b', borderRadius: 3, overflow: 'hidden' }}>
          <div style={{ width: `${pct}%`, height: '100%', background: color, borderRadius: 3 }}></div>
        </div>
        <span style={{ fontFamily: 'var(--font-mono)', fontSize: 12, color, minWidth: 48, fontVariantNumeric: 'tabular-nums' }}>{d} 天</span>
      </div>
    );
  };

  return (
    <>
      {violation_count > 0 && (
        <Banner
          kind="err"
          title={`快照合規率 ${compliance_count} / ${total_count} · ${violation_count} 台 VM 違規`}
          msg="管理辦法 5.2 節：一般 VM 快照保留上限 7 天 · SQL Server VM 禁止保留快照"
        />
      )}

      {/* Summary metrics */}
      <div className="metrics-4" style={{ marginBottom: 20 }}>
        <Metric title="違規 VM" icon={<Icon.alertTri />} value={String(violation_count)} delta={`合規目標：0 台`} deltaColor="#ef4444" active={violation_count > 0} />
        <Metric title="快照總數" icon={<Icon.camera />} value={String(snapshots.reduce((a,s)=>a+s.snapshot_count,0))} delta="需全部清除" deltaColor="#ef4444" />
        <Metric title="最舊快照" icon={<Icon.clock />} value={String(oldestDays)} unit="天"
          delta={snapshots.find(s=>s.age_days===oldestDays)?.vm_name || '—'} deltaColor="#ef4444" />
        <Metric title="SQL Server 違規" icon={<Icon.server />} value={String(sqlViolation)} delta="禁止有快照" deltaColor={sqlViolation > 0 ? '#ef4444' : '#22c55e'} active={sqlViolation > 0} />
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: 20, marginBottom: 20 }}>
        <Card title="快照違規清單" icon={<Icon.camera />}
          actions={<Btn variant="outline" size="sm" icon={<Icon.download />}>匯出報告</Btn>}>
          <div className="tbl-wrap">
            <table>
              <thead>
                <tr>
                  <th>VM 名稱</th>
                  <th className="td-center">快照數</th>
                  <th>最舊快照</th>
                  <th style={{ minWidth: 180 }}>存在時間</th>
                  <th>合規狀態</th>
                  <th>備註</th>
                </tr>
              </thead>
              <tbody>
                {snapshots.map(s => (
                  <tr key={s.vm_name} onClick={() => setSelected(selected === s.vm_name ? null : s.vm_name)}
                    style={selected === s.vm_name ? { background: 'rgba(239,68,68,0.06)' } : {}}>
                    <td style={{ fontWeight: 600 }}>
                      <Dot kind={s.compliance_status} />
                      {s.vm_name}
                    </td>
                    <td className="td-center td-mono">{s.snapshot_count}</td>
                    <td className="td-mono">{fmtDate(s.oldest_snapshot_date)}</td>
                    <td>{daysBar(s.age_days)}</td>
                    <td><Pill kind={s.compliance_status}>{s.compliance_label}</Pill></td>
                    <td style={{ fontSize: 12, color: '#64748b' }}>
                      {s.is_sql ? 'SQL Server VM' : s.age_days > 7 ? `超出 ${s.age_days - 7} 天` : '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {selected && (() => {
            const s = snapshots.find(x => x.vm_name === selected);
            return s ? (
              <div style={{ marginTop: 14, padding: '14px 16px', background: 'var(--bg-1)', borderRadius: 8, border: '1px solid var(--border-1)' }}>
                <div style={{ fontSize: 11, textTransform: 'uppercase', letterSpacing: '0.06em', color: '#64748b', marginBottom: 8 }}>快照詳情 · {selected}</div>
                <div style={{ fontFamily: 'var(--font-mono)', fontSize: 12, lineHeight: 2, color: '#94a3b8' }}>
                  <div>快照數量：<span style={{ color: '#e2e8f0' }}>{s.snapshot_count} 個</span></div>
                  <div>最舊建立：<span style={{ color: '#e2e8f0' }}>{fmtDate(s.oldest_snapshot_date)}</span></div>
                  <div>存在天數：<span style={{ color: '#ef4444', fontWeight: 600 }}>{s.age_days} 天</span></div>
                  {s.is_sql && <div style={{ color: '#ef4444', marginTop: 4 }}>⚠ SQL Server VM — 任何快照均為違規</div>}
                  <div style={{ marginTop: 8, paddingTop: 8, borderTop: '1px solid var(--border-1)' }}>
                    建議動作：<span style={{ color: '#f59e0b' }}>排定維護視窗，執行 Remove-VMSnapshot</span>
                  </div>
                </div>
              </div>
            ) : null;
          })()}
        </Card>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <Card title="合規規則說明" icon={<Icon.shield />}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              {[
                { kind: 'err',  label: 'SQL Server VM', desc: '禁止保留快照（有即違規）' },
                { kind: 'err',  label: '超過 7 天',     desc: '一般 VM 快照存在 > 7 天' },
                { kind: 'warn', label: '3 – 7 天',      desc: '接近門檻，需注意' },
                { kind: 'ok',   label: '0 – 3 天',      desc: '變更緩衝期內，合規' },
                { kind: 'ok',   label: '無快照',        desc: '最佳狀態' },
              ].map((r, i) => (
                <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 10, fontSize: 13, padding: '6px 0', borderBottom: i < 4 ? '1px solid var(--border-1)' : 'none' }}>
                  <Dot kind={r.kind} />
                  <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 600, minWidth: 80 }}>{r.label}</span>
                  <span style={{ color: '#94a3b8', fontSize: 12 }}>{r.desc}</span>
                </div>
              ))}
            </div>
          </Card>
        </div>
      </div>

      {/* Aging bar chart */}
      <Card title="快照存在天數 · 視覺化" icon={<Icon.activity />}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {[...snapshots].sort((a, b) => b.age_days - a.age_days).map(s => (
            <div key={s.vm_name} style={{ display: 'grid', gridTemplateColumns: '180px 1fr 60px', gap: 12, alignItems: 'center' }}>
              <div style={{ fontFamily: 'var(--font-mono)', fontSize: 12, color: '#94a3b8', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{s.vm_name}</div>
              <div style={{ background: 'var(--bg-1)', borderRadius: 4, height: 20, overflow: 'hidden', position: 'relative' }}>
                <div style={{
                  width: `${Math.min((s.age_days / 400) * 100, 100)}%`,
                  height: '100%',
                  background: s.is_sql || s.age_days > 7 ? '#ef4444' : '#f59e0b',
                  borderRadius: 4, position: 'relative', overflow: 'hidden',
                }}>
                  <div style={{ position: 'absolute', inset: 0, background: 'repeating-linear-gradient(45deg,transparent,transparent 6px,rgba(255,255,255,0.08) 6px,rgba(255,255,255,0.08) 12px)' }}></div>
                </div>
                <div style={{ position: 'absolute', top: 0, left: `${(7/400)*100}%`, width: 1, height: '100%', background: '#475569' }}></div>
              </div>
              <div style={{ fontFamily: 'var(--font-mono)', fontSize: 12, color: s.age_days > 7 ? '#ef4444' : '#f59e0b', textAlign: 'right', fontVariantNumeric: 'tabular-nums' }}>{s.age_days}d</div>
            </div>
          ))}
          <div style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: '#475569', marginTop: 4 }}>｜ = 7 天門檻</div>
        </div>
      </Card>
    </>
  );
}

window.PageSnapshots = PageSnapshots;

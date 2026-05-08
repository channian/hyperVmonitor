// Page: 快照合規管理
const { useState: useStateSn } = React;

const SNAPSHOTS = [
  { vm: 'KHTWXDB',          count: 2, oldest: '2024-03-15', days: 397, isSql: true,  status: 'critical' },
  { vm: 'KHTWXAR',          count: 2, oldest: '2024-03-15', days: 397, isSql: false, status: 'critical' },
  { vm: 'KHTWXML',          count: 3, oldest: '2024-08-15', days: 248, isSql: false, status: 'critical' },
  { vm: 'KHTWIOTPWR',       count: 1, oldest: '2024-06-20', days: 300, isSql: false, status: 'critical' },
  { vm: 'KHTWIOTVIB',       count: 1, oldest: '2024-06-20', days: 300, isSql: false, status: 'critical' },
  { vm: 'KHTWXFD',          count: 2, oldest: '2024-11-01', days: 170, isSql: false, status: 'critical' },
  { vm: 'FACCENTRALJUMP01', count: 1, oldest: '2025-01-10', days: 95,  isSql: false, status: 'critical' },
  { vm: 'FACCENTRALJUMP02', count: 1, oldest: '2025-01-10', days: 95,  isSql: false, status: 'critical' },
];

const ALERT_HISTORY = [
  { time: '2026-04-26 08:00', vm: 'KHTWXDB',  type: '嚴重告警', msg: 'SQL Server VM 禁止保留快照，已存在 397 天' },
  { time: '2026-04-25 08:00', vm: 'KHTWXAR',  type: '嚴重告警', msg: '快照存在 396 天，遠超門檻 7 天' },
  { time: '2026-04-24 08:00', vm: 'KHTWXML',  type: '嚴重告警', msg: '3 個快照，最舊 247 天' },
  { time: '2026-04-23 08:00', vm: 'KHTWIOTPWR',type: '嚴重告警', msg: '快照存在 299 天' },
];

function PageSnapshots() {
  const [selected, setSelected] = useStateSn(null);

  const daysColor = (d, isSql) => {
    if (isSql) return '#ef4444';
    if (d > 7) return '#ef4444';
    if (d > 3) return '#f59e0b';
    return '#22c55e';
  };

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
      <Banner
        kind="err"
        title="快照合規率 0 / 8 · 全部 VM 違規"
        msg="管理辦法 5.2 節：一般 VM 快照保留上限 7 天 · SQL Server VM 禁止保留快照"
      />

      {/* Summary metrics */}
      <div className="metrics-4" style={{ marginBottom: 20 }}>
        <Metric title="違規 VM" icon={<Icon.alertTri />} value="8" delta="合規目標：0 台" deltaColor="#ef4444" active />
        <Metric title="快照總數" icon={<Icon.camera />} value="13" delta="需全部清除" deltaColor="#ef4444" />
        <Metric title="最舊快照" icon={<Icon.clock />} value="397" unit="天" delta="KHTWXDB / KHTWXAR" deltaColor="#ef4444" />
        <Metric title="SQL Server 違規" icon={<Icon.server />} value="1" delta="KHTWXDB 禁止有快照" deltaColor="#ef4444" />
      </div>

      {/* Compliance rules */}
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
                {SNAPSHOTS.map(s => (
                  <tr key={s.vm} onClick={() => setSelected(selected === s.vm ? null : s.vm)}
                    style={selected === s.vm ? { background: 'rgba(239,68,68,0.06)' } : {}}>
                    <td style={{ fontWeight: 600 }}>
                      <Dot kind="err" />
                      {s.vm}
                    </td>
                    <td className="td-center td-mono">{s.count}</td>
                    <td className="td-mono">{s.oldest}</td>
                    <td>{daysBar(s.days)}</td>
                    <td>
                      <Pill kind="err">
                        {s.isSql ? 'SQL 禁止快照' : s.days > 7 ? '嚴重違規' : s.days > 3 ? '警告' : '合規'}
                      </Pill>
                    </td>
                    <td style={{ fontSize: 12, color: '#64748b' }}>
                      {s.isSql ? 'SQL Server VM' : `超出 ${s.days - 7} 天`}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {selected && (
            <div style={{ marginTop: 14, padding: '14px 16px', background: 'var(--bg-1)', borderRadius: 8, border: '1px solid var(--border-1)' }}>
              <div style={{ fontSize: 11, textTransform: 'uppercase', letterSpacing: '0.06em', color: '#64748b', marginBottom: 8 }}>快照詳情 · {selected}</div>
              <div style={{ fontFamily: 'var(--font-mono)', fontSize: 12, lineHeight: 2, color: '#94a3b8' }}>
                {(() => {
                  const s = SNAPSHOTS.find(x => x.vm === selected);
                  if (!s) return null;
                  return <>
                    <div>快照數量：<span style={{ color: '#e2e8f0' }}>{s.count} 個</span></div>
                    <div>最舊建立：<span style={{ color: '#e2e8f0' }}>{s.oldest}</span></div>
                    <div>存在天數：<span style={{ color: '#ef4444', fontWeight: 600 }}>{s.days} 天</span></div>
                    {s.isSql && <div style={{ color: '#ef4444', marginTop: 4 }}>⚠ SQL Server VM — 任何快照均為違規</div>}
                    <div style={{ marginTop: 8, paddingTop: 8, borderTop: '1px solid var(--border-1)' }}>
                      建議動作：<span style={{ color: '#f59e0b' }}>排定維護視窗，執行 Remove-VMSnapshot</span>
                    </div>
                  </>;
                })()}
              </div>
            </div>
          )}
        </Card>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          {/* Compliance rules */}
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

          {/* Alert history */}
          <Card title="近期告警紀錄" icon={<Icon.bell />}>
            {ALERT_HISTORY.map((a, i) => (
              <div key={i} className="diag">
                <div className="diag-icon err"><Icon.alert style={{ width: 13, height: 13 }} /></div>
                <div className="diag-body">
                  <div className="who">{a.vm}</div>
                  <div className="msg">{a.msg}</div>
                </div>
                <div className="diag-time">{a.time.slice(5)}</div>
              </div>
            ))}
          </Card>
        </div>
      </div>

      {/* Aging bar chart */}
      <Card title="快照存在天數 · 視覺化" icon={<Icon.activity />}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {SNAPSHOTS.sort((a, b) => b.days - a.days).map(s => (
            <div key={s.vm} style={{ display: 'grid', gridTemplateColumns: '180px 1fr 60px', gap: 12, alignItems: 'center' }}>
              <div style={{ fontFamily: 'var(--font-mono)', fontSize: 12, color: '#94a3b8', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{s.vm}</div>
              <div style={{ background: 'var(--bg-1)', borderRadius: 4, height: 20, overflow: 'hidden', position: 'relative' }}>
                <div style={{
                  width: `${Math.min((s.days / 400) * 100, 100)}%`,
                  height: '100%',
                  background: s.isSql || s.days > 7 ? '#ef4444' : '#f59e0b',
                  borderRadius: 4,
                  position: 'relative',
                  overflow: 'hidden',
                }}>
                  <div style={{ position: 'absolute', inset: 0, background: 'repeating-linear-gradient(45deg,transparent,transparent 6px,rgba(255,255,255,0.08) 6px,rgba(255,255,255,0.08) 12px)' }}></div>
                </div>
                {/* 7-day threshold marker */}
                <div style={{ position: 'absolute', top: 0, left: `${(7/400)*100}%`, width: 1, height: '100%', background: '#475569' }}></div>
              </div>
              <div style={{ fontFamily: 'var(--font-mono)', fontSize: 12, color: s.days > 7 ? '#ef4444' : '#f59e0b', textAlign: 'right', fontVariantNumeric: 'tabular-nums' }}>{s.days}d</div>
            </div>
          ))}
          <div style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: '#475569', marginTop: 4 }}>｜ = 7 天門檻</div>
        </div>
      </Card>
    </>
  );
}

window.PageSnapshots = PageSnapshots;

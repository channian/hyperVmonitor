// Page: 告警規則設定
const { useState: useStateAl, useEffect: useEffectAl } = React;

function PageAlerts() {
  const [tab, setTab] = useStateAl('thresholds');
  const [saved, setSaved] = useStateAl(false);
  const [rules, setRules] = useStateAl([]);
  const [notify, setNotify] = useStateAl(null);
  const [notifyLoading, setNotifyLoading] = useStateAl(false);
  const [testResult, setTestResult] = useStateAl(null);

  const { data, loading, error } = useFetch('/api/alerts');

  useEffectAl(() => {
    if (data) setRules(data);
  }, [data]);

  // 切換到通知設定 tab 時才載入
  useEffectAl(() => {
    if (tab === 'notify' && notify === null) {
      fetch(`${API_BASE}/api/settings/notify`)
        .then(r => r.json())
        .then(d => setNotify(d))
        .catch(() => setNotify({}));
    }
  }, [tab]);

  const updateThreshold = (id, val) => {
    setRules(prev => prev.map(r => r.id === id ? { ...r, threshold_value: Number(val) } : r));
  };

  const toggleEnabled = async (id) => {
    const rule = rules.find(r => r.id === id);
    if (!rule) return;
    const newEnabled = !rule.enabled;
    setRules(prev => prev.map(r => r.id === id ? { ...r, enabled: newEnabled } : r));
    try {
      await fetch(`${API_BASE}/api/alerts/${id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ enabled: newEnabled }),
      });
    } catch (e) {
      setRules(prev => prev.map(r => r.id === id ? { ...r, enabled: !newEnabled } : r));
    }
  };

  const handleSaveThresholds = async () => {
    for (const r of rules) {
      try {
        await fetch(`${API_BASE}/api/alerts/${r.id}`, {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ threshold_value: r.threshold_value, enabled: r.enabled }),
        });
      } catch {}
    }
    setSaved(true);
    setTimeout(() => setSaved(false), 2500);
  };

  const handleSaveNotify = async () => {
    if (!notify) return;
    setNotifyLoading(true);
    try {
      const r = await fetch(`${API_BASE}/api/settings/notify`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(notify),
      });
      const d = await r.json();
      setNotify(d);
      setSaved(true);
      setTimeout(() => setSaved(false), 2500);
    } catch {}
    setNotifyLoading(false);
  };

  const handleTestEmail = async () => {
    setTestResult(null);
    try {
      const r = await fetch(`${API_BASE}/api/settings/notify/test`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ recipient: notify?.alert_email_it || '' }),
      });
      const d = await r.json();
      setTestResult(d);
    } catch (e) {
      setTestResult({ ok: false, error: e.message });
    }
  };

  if (loading) return <LoadingCard />;
  if (error)   return <ErrorCard msg={error} />;

  const categoryOrder = ['resource', 'snapshot', 'backup', 'security'];
  const categoryLabels = { resource: '資源監控', snapshot: '快照合規', backup: '備份 / HA', security: '資安監控' };

  const grouped = categoryOrder.reduce((acc, cat) => {
    acc[cat] = rules.filter(r => r.category === cat);
    return acc;
  }, {});

  const handleSave = tab === 'notify' ? handleSaveNotify : handleSaveThresholds;

  return (
    <>
      <div className="section-hd">
        <h2>告警規則設定</h2>
        <span className="count">管理員功能</span>
        <div className="actions">
          {saved && <Pill kind="ok">已儲存</Pill>}
          <Btn variant="primary" onClick={handleSave}>儲存設定</Btn>
        </div>
      </div>

      <div className="ctabs">
        <div className={`ctab ${tab === 'thresholds' ? 'active' : ''}`} onClick={() => setTab('thresholds')}>
          <Icon.activity style={{ width: 15, height: 15 }} />門檻值設定
        </div>
        <div className={`ctab ${tab === 'notify' ? 'active' : ''}`} onClick={() => setTab('notify')}>
          <Icon.bell style={{ width: 15, height: 15 }} />通知設定
        </div>
      </div>

      {tab === 'thresholds' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
          {categoryOrder.map(cat => (
            grouped[cat].length > 0 && (
              <Card key={cat} title={categoryLabels[cat]} icon={<Icon.settings />}>
                <div className="tbl-wrap">
                  <table>
                    <thead>
                      <tr>
                        <th>規則名稱</th>
                        <th>條件說明</th>
                        <th className="td-center">嚴重度</th>
                        <th style={{ minWidth: 160 }}>門檻值</th>
                        <th className="td-center">即時通知</th>
                        <th className="td-center">啟用</th>
                      </tr>
                    </thead>
                    <tbody>
                      {grouped[cat].map(r => (
                        <tr key={r.id} style={!r.enabled ? { opacity: 0.45 } : {}}>
                          <td style={{ fontWeight: 600, fontSize: 13 }}>{r.rule_name}</td>
                          <td style={{ fontSize: 12, color: '#94a3b8', maxWidth: 220, whiteSpace: 'normal', lineHeight: 1.4 }}>{r.description}</td>
                          <td className="td-center">
                            <Pill kind={r.severity === 'err' ? 'err' : 'warn'}>{r.severity === 'err' ? '嚴重' : '警告'}</Pill>
                          </td>
                          <td>
                            {r.threshold_value == null ? (
                              <span style={{ fontFamily: 'var(--font-mono)', fontSize: 12, color: '#64748b' }}>觸發即告警</span>
                            ) : (
                              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                                <input
                                  type="number"
                                  className="input"
                                  style={{ width: 80, padding: '5px 10px', fontSize: 13 }}
                                  value={r.threshold_value}
                                  onChange={e => updateThreshold(r.id, e.target.value)}
                                  disabled={!r.enabled}
                                />
                                <span style={{ fontFamily: 'var(--font-mono)', fontSize: 12, color: '#64748b' }}>{r.threshold_unit}</span>
                              </div>
                            )}
                          </td>
                          <td className="td-center">
                            <span style={{ fontFamily: 'var(--font-mono)', fontSize: 12, color: r.notify_immediate ? '#22c55e' : '#475569' }}>
                              {r.notify_immediate ? '✓ 即時' : '彙整'}
                            </span>
                          </td>
                          <td className="td-center">
                            <ToggleSwitch enabled={r.enabled} onChange={() => toggleEnabled(r.id)} />
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </Card>
            )
          ))}
        </div>
      )}

      {tab === 'notify' && (
        <>
          {notify === null ? <LoadingCard /> : (
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20 }}>
              <Card title="SMTP 設定" icon={<Icon.bell />}>
                {[
                  { label: 'SMTP 主機',   key: 'smtp_host',         type: 'text'   },
                  { label: 'SMTP 連接埠', key: 'smtp_port',         type: 'number' },
                  { label: '寄件人地址', key: 'smtp_sender_email',  type: 'text'   },
                  { label: '寄件人名稱', key: 'smtp_sender_name',   type: 'text'   },
                ].map(f => (
                  <div key={f.key} style={{ marginBottom: 16 }}>
                    <div style={{ fontSize: 12, color: '#64748b', marginBottom: 6, textTransform: 'uppercase', letterSpacing: '0.06em' }}>{f.label}</div>
                    <input type={f.type} className="input" style={{ width: '100%' }}
                      value={notify[f.key] ?? ''} onChange={e => setNotify(n => ({ ...n, [f.key]: f.type === 'number' ? Number(e.target.value) : e.target.value }))} />
                  </div>
                ))}
                <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginTop: 8 }}>
                  <Btn variant="ghost" size="sm" onClick={handleTestEmail}>發送測試郵件</Btn>
                  {testResult && (
                    <span style={{ fontSize: 12, color: testResult.ok ? '#22c55e' : '#ef4444' }}>
                      {testResult.ok ? '✓ 發送成功' : `✗ ${testResult.error}`}
                    </span>
                  )}
                </div>
              </Card>

              <Card title="收件人設定" icon={<Icon.user />}>
                {[
                  { label: 'IT 工程師群組（所有告警）', key: 'alert_email_it' },
                  { label: '主管群組（嚴重 + 日報）',   key: 'alert_email_manager' },
                ].map(f => (
                  <div key={f.key} style={{ marginBottom: 16 }}>
                    <div style={{ fontSize: 12, color: '#64748b', marginBottom: 6, textTransform: 'uppercase', letterSpacing: '0.06em' }}>{f.label}</div>
                    <input type="text" className="input" style={{ width: '100%' }}
                      value={notify[f.key] ?? ''} onChange={e => setNotify(n => ({ ...n, [f.key]: e.target.value }))} />
                  </div>
                ))}
                <div>
                  <div style={{ fontSize: 12, color: '#64748b', marginBottom: 6, textTransform: 'uppercase', letterSpacing: '0.06em' }}>每日報告發送時間</div>
                  <input type="time" className="input" style={{ width: 120 }}
                    value={notify.daily_report_time ?? '08:00'} onChange={e => setNotify(n => ({ ...n, daily_report_time: e.target.value }))} />
                </div>
                <div style={{ marginTop: 20, padding: '14px 16px', background: 'var(--bg-1)', borderRadius: 8, border: '1px solid var(--border-1)' }}>
                  <div style={{ fontSize: 11, textTransform: 'uppercase', letterSpacing: '0.06em', color: '#64748b', marginBottom: 8 }}>通知策略</div>
                  {[
                    { label: '嚴重告警', desc: '立即發送 → IT + 主管' },
                    { label: '警告事件', desc: '每小時彙整 → IT 群組' },
                    { label: '每日摘要', desc: `${notify.daily_report_time ?? '08:00'} 發送 → IT + 主管` },
                  ].map((s, i) => (
                    <div key={i} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '6px 0', borderBottom: i < 2 ? '1px solid var(--border-1)' : 'none', fontSize: 12 }}>
                      <span style={{ color: '#e2e8f0', fontWeight: 600 }}>{s.label}</span>
                      <span style={{ color: '#64748b', fontFamily: 'var(--font-mono)' }}>{s.desc}</span>
                    </div>
                  ))}
                </div>
              </Card>
            </div>
          )}
        </>
      )}
    </>
  );
}

function ToggleSwitch({ enabled, onChange }) {
  return (
    <div onClick={onChange} style={{
      width: 40, height: 22, borderRadius: 999, cursor: 'pointer',
      background: enabled ? '#22d3ee' : '#1e293b',
      border: `1.5px solid ${enabled ? '#22d3ee' : '#334155'}`,
      position: 'relative', transition: 'all 200ms',
      boxShadow: enabled ? '0 0 8px rgba(34,211,238,0.4)' : 'none',
    }}>
      <div style={{
        width: 16, height: 16, borderRadius: '50%', background: '#fff',
        position: 'absolute', top: 1, left: enabled ? 20 : 2,
        transition: 'left 200ms', boxShadow: '0 1px 4px rgba(0,0,0,0.4)',
      }}></div>
    </div>
  );
}

window.PageAlerts = PageAlerts;

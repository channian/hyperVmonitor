// Page: 告警規則設定
const { useState: useStateAl } = React;

const DEFAULT_RULES = [
  { id: 'cpu_crit',    name: 'CPU 嚴重告警',    desc: 'VM CPU 使用率 >', threshold: 85, unit: '%',   sev: 'err',  enabled: true },
  { id: 'cpu_warn',    name: 'CPU 警告',         desc: 'VM CPU 使用率 >', threshold: 75, unit: '%',   sev: 'warn', enabled: true },
  { id: 'ram_crit',    name: '記憶體嚴重告警',   desc: 'RAM Pressure >',  threshold: 80, unit: '%',   sev: 'err',  enabled: true },
  { id: 'ram_warn',    name: '記憶體警告',       desc: 'RAM Pressure >',  threshold: 70, unit: '%',   sev: 'warn', enabled: true },
  { id: 'snap_sql',    name: 'SQL 快照告警',     desc: 'SQL Server VM 存在快照',   threshold: 0,  unit: '個',  sev: 'err',  enabled: true },
  { id: 'snap_old',    name: '快照超齡嚴重',     desc: '快照存在超過',    threshold: 7,  unit: '天',  sev: 'err',  enabled: true },
  { id: 'snap_warn',   name: '快照超齡警告',     desc: '快照存在超過',    threshold: 3,  unit: '天',  sev: 'warn', enabled: true },
  { id: 'backup_fail', name: '備份失敗告警',     desc: '備份工作失敗',    threshold: 0,  unit: '次',  sev: 'err',  enabled: true },
  { id: 'rep_lag',     name: '複寫延遲告警',     desc: '複寫延遲超過',    threshold: 30, unit: '分鐘',sev: 'err',  enabled: true },
  { id: 'login_fail',  name: '暴力破解偵測',     desc: '10 分鐘內登入失敗 ≥', threshold: 5, unit: '次', sev: 'err',  enabled: true },
  { id: 'offhour',     name: '非上班時段登入',   desc: '22:00–07:00 管理員登入成功', threshold: 0, unit: '次', sev: 'warn', enabled: true },
  { id: 'priv_group',  name: '特權群組異動',     desc: 'HV-Admins / DA 新增成員', threshold: 0, unit: '次', sev: 'err',  enabled: true },
];

const NOTIFY_CONFIG = {
  smtpHost: 'mail.company.com',
  smtpPort: 587,
  from: 'hv-monitor@company.com',
  itGroup: 'it-team@company.com',
  mgmtGroup: 'it-manager@company.com',
  scheduleTime: '08:00',
};

function PageAlerts() {
  const [rules, setRules] = useStateAl(DEFAULT_RULES.map(r => ({ ...r })));
  const [tab, setTab] = useStateAl('thresholds');
  const [saved, setSaved] = useStateAl(false);

  const updateThreshold = (id, val) => {
    setRules(prev => prev.map(r => r.id === id ? { ...r, threshold: Number(val) } : r));
  };
  const toggleEnabled = (id) => {
    setRules(prev => prev.map(r => r.id === id ? { ...r, enabled: !r.enabled } : r));
  };
  const handleSave = () => {
    setSaved(true);
    setTimeout(() => setSaved(false), 2500);
  };

  const [notify, setNotify] = useStateAl({ ...NOTIFY_CONFIG });

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
        <Card title="告警門檻值" icon={<Icon.settings />}>
          <div className="tbl-wrap">
            <table>
              <thead>
                <tr>
                  <th>規則名稱</th>
                  <th>條件說明</th>
                  <th className="td-center">嚴重度</th>
                  <th style={{ minWidth: 160 }}>門檻值</th>
                  <th className="td-center">啟用</th>
                </tr>
              </thead>
              <tbody>
                {rules.map(r => (
                  <tr key={r.id} style={!r.enabled ? { opacity: 0.45 } : {}}>
                    <td style={{ fontWeight: 600, fontSize: 13 }}>{r.name}</td>
                    <td style={{ fontSize: 12, color: '#94a3b8' }}>{r.desc}</td>
                    <td className="td-center">
                      <Pill kind={r.sev === 'err' ? 'err' : 'warn'}>{r.sev === 'err' ? '嚴重' : '警告'}</Pill>
                    </td>
                    <td>
                      {r.threshold === 0 && r.unit === '個' ? (
                        <span style={{ fontFamily: 'var(--font-mono)', fontSize: 12, color: '#64748b' }}>觸發即告警</span>
                      ) : r.threshold === 0 && r.unit === '次' ? (
                        <span style={{ fontFamily: 'var(--font-mono)', fontSize: 12, color: '#64748b' }}>觸發即告警</span>
                      ) : (
                        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                          <input
                            type="number"
                            className="input"
                            style={{ width: 80, padding: '5px 10px', fontSize: 13 }}
                            value={r.threshold}
                            onChange={e => updateThreshold(r.id, e.target.value)}
                            disabled={!r.enabled}
                          />
                          <span style={{ fontFamily: 'var(--font-mono)', fontSize: 12, color: '#64748b' }}>{r.unit}</span>
                        </div>
                      )}
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
      )}

      {tab === 'notify' && (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20 }}>
          <Card title="SMTP 設定" icon={<Icon.bell />}>
            {[
              { label: 'SMTP 主機', key: 'smtpHost', type: 'text' },
              { label: 'SMTP 連接埠', key: 'smtpPort', type: 'number' },
              { label: '寄件人地址', key: 'from', type: 'text' },
            ].map(f => (
              <div key={f.key} style={{ marginBottom: 16 }}>
                <div style={{ fontSize: 12, color: '#64748b', marginBottom: 6, textTransform: 'uppercase', letterSpacing: '0.06em' }}>{f.label}</div>
                <input
                  type={f.type}
                  className="input"
                  style={{ width: '100%' }}
                  value={notify[f.key]}
                  onChange={e => setNotify(n => ({ ...n, [f.key]: e.target.value }))}
                />
              </div>
            ))}
          </Card>

          <Card title="收件人設定" icon={<Icon.user />}>
            {[
              { label: 'IT 工程師群組（所有告警）', key: 'itGroup' },
              { label: '主管群組（嚴重 + 日報）', key: 'mgmtGroup' },
            ].map(f => (
              <div key={f.key} style={{ marginBottom: 16 }}>
                <div style={{ fontSize: 12, color: '#64748b', marginBottom: 6, textTransform: 'uppercase', letterSpacing: '0.06em' }}>{f.label}</div>
                <input
                  type="text"
                  className="input"
                  style={{ width: '100%' }}
                  value={notify[f.key]}
                  onChange={e => setNotify(n => ({ ...n, [f.key]: e.target.value }))}
                />
              </div>
            ))}
            <div>
              <div style={{ fontSize: 12, color: '#64748b', marginBottom: 6, textTransform: 'uppercase', letterSpacing: '0.06em' }}>每日報告發送時間</div>
              <input
                type="time"
                className="input"
                style={{ width: 120 }}
                value={notify.scheduleTime}
                onChange={e => setNotify(n => ({ ...n, scheduleTime: e.target.value }))}
              />
            </div>

            <div style={{ marginTop: 20, padding: '14px 16px', background: 'var(--bg-1)', borderRadius: 8, border: '1px solid var(--border-1)' }}>
              <div style={{ fontSize: 11, textTransform: 'uppercase', letterSpacing: '0.06em', color: '#64748b', marginBottom: 8 }}>通知策略</div>
              {[
                { label: '嚴重告警', desc: '立即發送 → IT + 主管' },
                { label: '警告事件', desc: '每小時彙整 → IT 群組' },
                { label: '每日摘要', desc: `${notify.scheduleTime} 發送 → IT + 主管` },
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

// Page: 資安監控
const { useState: useStateSec } = React;

const SEC_EVENTS = [
  { time: '03:42', src: 'KHTWXDB',  type: 'err', typeLabel: '登入失敗', account: 'administrator', desc: '連續 8 次失敗，10 分鐘內', eventId: '4625' },
  { time: '03:43', src: 'KHTWXDB',  type: 'err', typeLabel: '帳號鎖定', account: 'administrator', desc: '超過門檻，帳號已鎖定',     eventId: '4740' },
  { time: '14:22', src: 'AD-01',    type: 'warn', typeLabel: '群組異動', account: 'jsmith-adm',    desc: '加入 HV-Admins 群組',   eventId: '4728' },
  { time: '22:15', src: 'KHTWXFD',  type: 'warn', typeLabel: '非上班時段', account: 'svc-backup', desc: '管理員帳號於 22:15 登入成功', eventId: '4624' },
  { time: '09:30', src: 'KHTWXML',  type: 'ok',  typeLabel: '正常登入',  account: 'itadmin',      desc: '上班時段互動式登入',     eventId: '4624' },
  { time: '10:05', src: 'KHFACVS01',type: 'ok',  typeLabel: '正常操作',  account: 'itadmin',      desc: 'VM 管理操作紀錄',       eventId: '13002' },
];

const ALERT_RULES = [
  { name: '暴力破解偵測',    cond: '同一帳號 10 分鐘內登入失敗 ≥ 5 次', sev: 'err',  notify: '即時 Email', triggered: true  },
  { name: '非上班時段管理員登入', cond: '管理員帳號於 22:00–07:00 登入成功', sev: 'warn', notify: '即時 Email', triggered: true  },
  { name: '特權群組新增成員', cond: 'HV-Admins / Domain Admins 有新成員', sev: 'err',  notify: '即時 Email', triggered: true  },
  { name: '服務帳號互動式登入', cond: 'svc-* 帳號出現互動式登入（非服務啟動）', sev: 'err', notify: '即時 Email', triggered: false },
  { name: '網路流量突增',    cond: '任一 VM 網路流量超過基線 P95 × 3',   sev: 'warn', notify: 'Email 彙整', triggered: false },
  { name: 'OT 非預期對外連線', cond: 'Kepware VM 出現 OT-DMZ 以外連線',  sev: 'err',  notify: '即時 Email', triggered: false },
  { name: 'VM 非預期關機',   cond: 'Running VM 被關機（非排程維護）',    sev: 'warn', notify: '即時 Email', triggered: false },
  { name: '新快照建立',      cond: '任一 VM 出現新快照',                 sev: 'warn', notify: 'Email 彙整', triggered: false },
];

const METRICS_SEC = {
  loginFail: 8, accountLock: 1, groupChange: 1, trafficAnomaly: 0,
  vmAudit: 0, otComm: 0,
};

function PageSecurity() {
  const [timeRange, setTimeRange] = useStateSec('today');
  const [tab, setTab] = useStateSec('events');

  const sevCards = [
    { id: 'loginFail',      label: '登入異常',  count: METRICS_SEC.loginFail,      kind: 'err',  icon: <Icon.lock /> },
    { id: 'accountLock',    label: '帳號事件',  count: METRICS_SEC.accountLock,    kind: 'warn', icon: <Icon.user /> },
    { id: 'trafficAnomaly', label: '流量異常',  count: METRICS_SEC.trafficAnomaly, kind: 'ok',   icon: <Icon.net /> },
    { id: 'vmAudit',        label: 'VM 操作稽核',count: METRICS_SEC.vmAudit,       kind: 'ok',   icon: <Icon.eye /> },
    { id: 'groupChange',    label: '群組異動',  count: METRICS_SEC.groupChange,    kind: 'warn', icon: <Icon.shield /> },
    { id: 'otComm',         label: 'OT 通訊',   count: METRICS_SEC.otComm,        kind: 'ok',   icon: <Icon.net /> },
  ];

  return (
    <>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 20 }}>
        <div className="section-hd" style={{ marginBottom: 0 }}>
          <h2>資安監控總覽</h2>
          <span className="count">今日 {SEC_EVENTS.filter(e => e.type === 'err' || e.type === 'warn').length} 件異常</span>
        </div>
        <div style={{ display: 'flex', gap: 4 }}>
          {['today', 'week', 'month'].map(r => (
            <button key={r} className={`btn btn-sm ${timeRange === r ? 'btn-outline' : 'btn-ghost'}`} onClick={() => setTimeRange(r)}>
              {r === 'today' ? '今日' : r === 'week' ? '本週' : '本月'}
            </button>
          ))}
        </div>
      </div>

      {/* Summary cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16, marginBottom: 20 }}>
        {sevCards.slice(0, 3).map(c => (
          <div key={c.id} className="card-ui" style={c.count > 0 && c.kind !== 'ok' ? { borderColor: c.kind === 'err' ? 'rgba(239,68,68,0.35)' : 'rgba(245,158,11,0.35)' } : {}}>
            <div className="card-hd" style={{ marginBottom: 8 }}>
              <div style={{ color: c.kind === 'err' ? '#ef4444' : c.kind === 'warn' ? '#f59e0b' : '#22c55e' }}>{c.icon}</div>
              <span className="t">{c.label}</span>
            </div>
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: 28, fontWeight: 700, color: c.count > 0 && c.kind !== 'ok' ? (c.kind === 'err' ? '#ef4444' : '#f59e0b') : '#22c55e', fontVariantNumeric: 'tabular-nums' }}>
              {c.count > 0 ? `${c.count} 筆` : '正常'}
            </div>
            <div style={{ fontSize: 12, color: '#64748b', marginTop: 4 }}>
              {c.count > 0 && c.kind !== 'ok' ? <Pill kind={c.kind}>{c.kind === 'err' ? '需立即處理' : '需關注'}</Pill> : <Pill kind="ok">無異常</Pill>}
            </div>
          </div>
        ))}
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16, marginBottom: 20 }}>
        {sevCards.slice(3, 6).map(c => (
          <div key={c.id} className="card-ui" style={c.count > 0 && c.kind !== 'ok' ? { borderColor: c.kind === 'err' ? 'rgba(239,68,68,0.35)' : 'rgba(245,158,11,0.35)' } : {}}>
            <div className="card-hd" style={{ marginBottom: 8 }}>
              <div style={{ color: c.kind === 'err' ? '#ef4444' : c.kind === 'warn' ? '#f59e0b' : '#22c55e' }}>{c.icon}</div>
              <span className="t">{c.label}</span>
            </div>
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: 28, fontWeight: 700, color: c.count > 0 && c.kind !== 'ok' ? (c.kind === 'err' ? '#ef4444' : '#f59e0b') : '#22c55e', fontVariantNumeric: 'tabular-nums' }}>
              {c.count > 0 ? `${c.count} 筆` : '正常'}
            </div>
            <div style={{ fontSize: 12, color: '#64748b', marginTop: 4 }}>
              {c.count > 0 && c.kind !== 'ok' ? <Pill kind={c.kind}>{c.kind === 'err' ? '需立即處理' : '需關注'}</Pill> : <Pill kind="ok">無異常</Pill>}
            </div>
          </div>
        ))}
      </div>

      {/* Tabs */}
      <div className="ctabs">
        <div className={`ctab ${tab === 'events' ? 'active' : ''}`} onClick={() => setTab('events')}>
          <Icon.activity style={{ width: 15, height: 15 }} />異常事件明細
        </div>
        <div className={`ctab ${tab === 'rules' ? 'active' : ''}`} onClick={() => setTab('rules')}>
          <Icon.settings style={{ width: 15, height: 15 }} />告警規則狀態
        </div>
      </div>

      {tab === 'events' && (
        <Card title="異常事件明細" icon={<Icon.shieldAlert />}
          actions={<Btn variant="ghost" size="sm" icon={<Icon.download />}>匯出 CSV</Btn>}>
          <div className="tbl-wrap">
            <table>
              <thead>
                <tr>
                  <th>時間</th>
                  <th>來源主機</th>
                  <th>事件類型</th>
                  <th>帳號</th>
                  <th>Event ID</th>
                  <th>說明</th>
                </tr>
              </thead>
              <tbody>
                {SEC_EVENTS.map((e, i) => (
                  <tr key={i}>
                    <td className="td-mono">{e.time}</td>
                    <td className="td-mono">{e.src}</td>
                    <td>
                      <Pill kind={e.type === 'err' ? 'err' : e.type === 'warn' ? 'warn' : 'ok'}>{e.typeLabel}</Pill>
                    </td>
                    <td className="td-mono" style={{ color: '#e2e8f0' }}>{e.account}</td>
                    <td className="td-mono">{e.eventId}</td>
                    <td style={{ fontSize: 12.5, color: '#94a3b8' }}>{e.desc}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {tab === 'rules' && (
        <Card title="告警規則狀態" icon={<Icon.shield />}>
          <div className="tbl-wrap">
            <table>
              <thead>
                <tr>
                  <th>規則名稱</th>
                  <th>偵測條件</th>
                  <th className="td-center">嚴重度</th>
                  <th>通知方式</th>
                  <th className="td-center">今日狀態</th>
                </tr>
              </thead>
              <tbody>
                {ALERT_RULES.map((r, i) => (
                  <tr key={i}>
                    <td style={{ fontWeight: 600, fontSize: 13 }}>{r.name}</td>
                    <td style={{ fontSize: 12, color: '#94a3b8', maxWidth: 260, whiteSpace: 'normal', lineHeight: 1.4 }}>{r.cond}</td>
                    <td className="td-center">
                      <Pill kind={r.sev === 'err' ? 'err' : 'warn'}>{r.sev === 'err' ? '嚴重' : '警告'}</Pill>
                    </td>
                    <td className="td-mono" style={{ fontSize: 12 }}>{r.notify}</td>
                    <td className="td-center">
                      {r.triggered
                        ? <Pill kind="err">已觸發</Pill>
                        : <Pill kind="ok">正常</Pill>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}
    </>
  );
}

window.PageSecurity = PageSecurity;

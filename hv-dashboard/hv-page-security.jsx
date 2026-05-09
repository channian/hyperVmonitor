// Page: 資安監控
const { useState: useStateSec } = React;

const EVENT_TYPE_LABELS = {
  login_fail:    '登入失敗',
  login_success: '正常登入',
  lockout:       '帳號鎖定',
  group_change:  '群組異動',
  unknown:       '其他',
};

function PageSecurity() {
  const [timeRange, setTimeRange] = useStateSec('today');
  const [tab, setTab] = useStateSec('events');

  const { data, loading, error } = useFetch(`/api/security?period=${timeRange}`);

  if (loading) return <LoadingCard />;
  if (error)   return <ErrorCard msg={error} />;

  const { summary_cards, events } = data;
  const abnormalCount = events.filter(e => e.severity !== 'info').length;

  const fmtTime = (iso) => {
    if (!iso) return '—';
    const d = new Date(iso);
    return `${d.getHours().toString().padStart(2,'0')}:${d.getMinutes().toString().padStart(2,'0')}`;
  };

  const cardIconMap = {
    login:        <Icon.lock />,
    account:      <Icon.user />,
    network:      <Icon.net />,
    vm_operation: <Icon.eye />,
    ot:           <Icon.net />,
  };

  return (
    <>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 20 }}>
        <div className="section-hd" style={{ marginBottom: 0 }}>
          <h2>資安監控總覽</h2>
          <span className="count">
            {timeRange === 'today' ? '今日' : timeRange === 'week' ? '本週' : '本月'} {abnormalCount} 件異常
          </span>
        </div>
        <div style={{ display: 'flex', gap: 4 }}>
          {['today', 'week', 'month'].map(r => (
            <button key={r} className={`btn btn-sm ${timeRange === r ? 'btn-outline' : 'btn-ghost'}`} onClick={() => setTimeRange(r)}>
              {r === 'today' ? '今日' : r === 'week' ? '本週' : '本月'}
            </button>
          ))}
        </div>
      </div>

      {/* Summary cards：3 + 2 格局 */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16, marginBottom: 16 }}>
        {summary_cards.slice(0, 3).map(c => (
          <div key={c.category} className="card-ui"
            style={c.count > 0 && c.status !== 'ok' ? { borderColor: c.status === 'err' ? 'rgba(239,68,68,0.35)' : 'rgba(245,158,11,0.35)' } : {}}>
            <div className="card-hd" style={{ marginBottom: 8 }}>
              <div style={{ color: c.status === 'err' ? '#ef4444' : c.status === 'warn' ? '#f59e0b' : '#22c55e' }}>{cardIconMap[c.category] || <Icon.shield />}</div>
              <span className="t">{c.label}</span>
            </div>
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: 28, fontWeight: 700, color: c.count > 0 && c.status !== 'ok' ? (c.status === 'err' ? '#ef4444' : '#f59e0b') : '#22c55e', fontVariantNumeric: 'tabular-nums' }}>
              {c.count > 0 ? `${c.count} 筆` : '正常'}
            </div>
            <div style={{ fontSize: 12, color: '#64748b', marginTop: 4 }}>
              {c.count > 0 && c.status !== 'ok' ? <Pill kind={c.status}>{c.status === 'err' ? '需立即處理' : '需關注'}</Pill> : <Pill kind="ok">無異常</Pill>}
            </div>
          </div>
        ))}
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16, marginBottom: 20 }}>
        {summary_cards.slice(3).map(c => (
          <div key={c.category} className="card-ui">
            <div className="card-hd" style={{ marginBottom: 8 }}>
              <div style={{ color: '#22c55e' }}>{cardIconMap[c.category] || <Icon.shield />}</div>
              <span className="t">{c.label}</span>
            </div>
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: 28, fontWeight: 700, color: '#22c55e' }}>正常</div>
            <div style={{ fontSize: 12, marginTop: 4 }}><Pill kind="ok">無異常</Pill></div>
          </div>
        ))}
      </div>

      {/* Tabs */}
      <div className="ctabs">
        <div className={`ctab ${tab === 'events' ? 'active' : ''}`} onClick={() => setTab('events')}>
          <Icon.activity style={{ width: 15, height: 15 }} />異常事件明細
        </div>
      </div>

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
              {events.map((e, i) => (
                <tr key={i}>
                  <td className="td-mono">{fmtTime(e.occurred_at)}</td>
                  <td className="td-mono">{e.source_host}</td>
                  <td>
                    <Pill kind={e.severity === 'err' ? 'err' : e.severity === 'warn' ? 'warn' : 'ok'}>
                      {EVENT_TYPE_LABELS[e.event_type] || e.event_type}
                    </Pill>
                  </td>
                  <td className="td-mono" style={{ color: '#e2e8f0' }}>{e.account}</td>
                  <td className="td-mono">{e.event_id}</td>
                  <td style={{ fontSize: 12.5, color: '#94a3b8' }}>{e.description}</td>
                </tr>
              ))}
              {events.length === 0 && (
                <tr><td colSpan="6" style={{ textAlign: 'center', color: '#475569', padding: '20px 0' }}>此時間區間無異常事件</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </Card>
    </>
  );
}

window.PageSecurity = PageSecurity;

// Page: 系統設定
const { useState: useStateSt, useEffect: useEffectSt } = React;

function PageSettings({ setPage }) {
  const { data: sys, loading: sysLoading } = useFetch('/api/settings/system');
  const { data: overview } = useFetch('/api/overview');

  if (sysLoading) return <LoadingCard />;

  const info = sys || {};
  const ov   = overview || {};

  const InfoRow = ({ label, value, mono }) => (
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                  padding: '10px 0', borderBottom: '1px solid var(--border-1)', fontSize: 13 }}>
      <span style={{ color: '#64748b' }}>{label}</span>
      <span style={{ color: '#e2e8f0', fontFamily: mono ? 'var(--font-mono)' : undefined,
                     fontSize: mono ? 12 : 13 }}>{value}</span>
    </div>
  );

  return (
    <>
      <div className="section-hd">
        <h2>系統設定</h2>
        <span className="count">環境概覽</span>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20, marginBottom: 20 }}>
        {/* 環境概況 */}
        <Card title="監控環境" icon={<Icon.dashboard />}>
          <InfoRow label="資料庫類型"    value={info.db_type || '—'} mono />
          <InfoRow label="監控主機數"    value={`${info.host_count ?? '—'} 台`} />
          <InfoRow label="虛擬機器數"    value={`${info.vm_count ?? '—'} 台`} />
          <InfoRow label="WinRM 帳號"    value={info.winrm_user || '—'} mono />
          <InfoRow label="宿主機 IP 清單" value={info.hv_hosts || '（未設定）'} mono />
        </Card>

        {/* 採樣排程 */}
        <Card title="採樣排程" icon={<Icon.activity />}>
          <InfoRow label="VM / 資源採樣間隔"   value={`每 ${info.collection_interval_vm ?? 15} 分鐘`} />
          <InfoRow label="資安事件採樣間隔"    value={`每 ${info.collection_interval_sec ?? 5} 分鐘`} />
          <InfoRow label="快照 / 複寫採樣間隔" value={`每 ${info.collection_interval_vm ?? 15} 分鐘`} />
          <div style={{ marginTop: 16, padding: '10px 12px', background: 'var(--bg-1)',
                        borderRadius: 6, border: '1px solid var(--border-1)', fontSize: 12, color: '#64748b' }}>
            排程由 <code style={{ color: '#22d3ee' }}>collector/scheduler.py</code> 管理，
            修改採樣頻率請調整 scheduler.py 後重啟服務。
          </div>
        </Card>

        {/* 通知設定狀態 */}
        <Card title="通知設定狀態" icon={<Icon.bell />}
          actions={
            <Btn variant="ghost" size="sm" onClick={() => setPage('alerts')}>
              前往設定 →
            </Btn>
          }>
          <InfoRow label="SMTP 主機"
            value={info.smtp_host ? <span style={{ color: '#22c55e' }}>{info.smtp_host}</span>
                                  : <span style={{ color: '#ef4444' }}>未設定</span>} />
          <InfoRow label="Email 通知"
            value={info.smtp_configured
              ? <Pill kind="ok">已啟用</Pill>
              : <Pill kind="err">未設定</Pill>} />
          <InfoRow label="Webhook 推播"
            value={info.webhook_configured
              ? <Pill kind="ok">已啟用</Pill>
              : <Pill kind="muted">未啟用</Pill>} />
          {info.dashboard_url && (
            <InfoRow label="Dashboard URL" value={info.dashboard_url} mono />
          )}
        </Card>

        {/* 系統健康度 */}
        <Card title="系統健康度" icon={<Icon.shieldAlert />}>
          {overview ? (
            <>
              <div style={{ display: 'flex', alignItems: 'center', gap: 16, padding: '12px 0',
                            borderBottom: '1px solid var(--border-1)' }}>
                <div style={{ fontFamily: 'var(--font-mono)', fontSize: 40, fontWeight: 800,
                              color: ov.health_pct >= 80 ? '#22c55e' : ov.health_pct >= 60 ? '#f59e0b' : '#ef4444' }}>
                  {ov.health_pct ?? '—'}%
                </div>
                <div>
                  <div style={{ fontSize: 12, color: '#64748b' }}>系統健康度</div>
                  <div style={{ fontSize: 12, color: '#94a3b8', marginTop: 4 }}>
                    告警數：{ov.alert_count ?? 0} 件
                  </div>
                </div>
              </div>
              <InfoRow label="快照違規"
                value={`${ov.snapshot_violation_count ?? 0} 台`} />
              <InfoRow label="上次資料更新"
                value={ov.last_updated
                  ? new Date(ov.last_updated).toLocaleString('zh-TW')
                  : '—'} />
            </>
          ) : <LoadingCard />}
        </Card>
      </div>

      <Card title="設定說明" icon={<Icon.settings />}>
        <div style={{ fontSize: 13, color: '#94a3b8', lineHeight: 2 }}>
          <p style={{ margin: '0 0 12px' }}>
            環境變數設定請編輯 <code style={{ color: '#22d3ee' }}>backend/.env</code> 檔案，
            修改後重啟 FastAPI 服務使設定生效。
          </p>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--border-1)' }}>
                <th style={{ textAlign: 'left', padding: '6px 8px', color: '#64748b' }}>變數</th>
                <th style={{ textAlign: 'left', padding: '6px 8px', color: '#64748b' }}>說明</th>
              </tr>
            </thead>
            <tbody>
              {[
                ['DATABASE_URL',    'SQLite 或 PostgreSQL 連線字串'],
                ['WINRM_USER',      'Hyper-V 宿主機管理員帳號'],
                ['WINRM_PASSWORD',  'Hyper-V 宿主機管理員密碼'],
                ['HV_HOSTS',        '宿主機 IP 清單（逗號分隔）'],
                ['VM_WINRM_USER',   'VM 直連帳號（IS 故障 fallback）'],
                ['VM_WINRM_PASSWORD','VM 直連密碼'],
                ['SMTP_HOST',       'SMTP 主機（Email 告警）'],
                ['DASHBOARD_URL',   '儀表板網址（Email 附連結）'],
              ].map(([k, v]) => (
                <tr key={k} style={{ borderBottom: '1px solid var(--border-1)' }}>
                  <td style={{ padding: '7px 8px', fontFamily: 'var(--font-mono)', color: '#22d3ee' }}>{k}</td>
                  <td style={{ padding: '7px 8px', color: '#94a3b8' }}>{v}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </>
  );
}

window.PageSettings = PageSettings;

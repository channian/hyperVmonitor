// Page: 管理帳號
const { useState: useStateAdm, useEffect: useEffectAdm } = React;

function PageAdmin() {
  const { data: sys } = useFetch('/api/settings/system');
  const [pwForm, setPwForm] = useStateAdm({ current: '', next: '', confirm: '' });
  const [pwMsg, setPwMsg]   = useStateAdm(null);

  const handlePwChange = async () => {
    if (!pwForm.next) { setPwMsg({ ok: false, msg: '請輸入新密碼' }); return; }
    if (pwForm.next !== pwForm.confirm) { setPwMsg({ ok: false, msg: '兩次密碼不一致' }); return; }
    // 目前無後端認證系統，僅前端示意
    setPwMsg({ ok: true, msg: '（示意）密碼變更需修改 .env 中的 WINRM_PASSWORD 並重啟服務' });
  };

  const winrmUser = sys?.winrm_user || '—';

  return (
    <>
      <div className="section-hd">
        <h2>管理帳號</h2>
        <span className="count">帳號資訊</span>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20, marginBottom: 20 }}>
        {/* 目前帳號 */}
        <Card title="目前連線帳號" icon={<Icon.user />}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 16, padding: '20px 0' }}>
            <div style={{ width: 56, height: 56, borderRadius: '50%',
                          background: 'linear-gradient(135deg,#22d3ee,#3b82f6)',
                          display: 'flex', alignItems: 'center', justifyContent: 'center',
                          fontSize: 22, fontWeight: 700, color: '#0f172a' }}>
              {winrmUser.slice(0, 2).toUpperCase()}
            </div>
            <div>
              <div style={{ fontFamily: 'var(--font-mono)', fontSize: 16, fontWeight: 600,
                            color: '#e2e8f0' }}>{winrmUser}</div>
              <div style={{ fontSize: 12, color: '#64748b', marginTop: 4 }}>WinRM 管理員帳號</div>
              <div style={{ marginTop: 8 }}>
                <Pill kind="ok">系統管理員</Pill>
              </div>
            </div>
          </div>
          <div style={{ padding: '12px', background: 'var(--bg-1)', borderRadius: 6,
                        border: '1px solid var(--border-1)', fontSize: 12, color: '#64748b' }}>
            此帳號用於 WinRM 連線至各 Hyper-V 宿主機。
            帳號密碼設定於 <code style={{ color: '#22d3ee' }}>backend/.env</code>。
          </div>
        </Card>

        {/* 存取控制說明 */}
        <Card title="存取控制" icon={<Icon.shield />}>
          <div style={{ fontSize: 13, color: '#94a3b8', lineHeight: 1.8 }}>
            <div style={{ marginBottom: 12 }}>
              <div style={{ color: '#e2e8f0', fontWeight: 600, marginBottom: 4 }}>目前架構</div>
              目前儀表板未實作使用者認證（Auth）。建議透過以下方式限制存取：
            </div>
            {[
              ['防火牆規則', '僅允許管理 VLAN 的 IP 存取 Port 8000'],
              ['Nginx 反向代理', '加入 HTTP Basic Auth 或 IP 白名單'],
              ['VPN 限制',  '要求從 VPN 連入才能存取儀表板'],
            ].map(([title, desc]) => (
              <div key={title} style={{ display: 'flex', gap: 10, padding: '8px 0',
                                        borderBottom: '1px solid var(--border-1)' }}>
                <span style={{ color: '#22d3ee', flexShrink: 0, width: 110 }}>{title}</span>
                <span style={{ color: '#64748b', fontSize: 12 }}>{desc}</span>
              </div>
            ))}
          </div>
        </Card>
      </div>

      {/* WinRM 連線帳密說明 */}
      <Card title="WinRM 帳密管理" icon={<Icon.settings />}>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20 }}>
          <div>
            <div style={{ fontSize: 12, color: '#64748b', marginBottom: 12, textTransform: 'uppercase',
                          letterSpacing: '0.06em' }}>宿主機帳密</div>
            <div style={{ fontSize: 13, color: '#94a3b8', lineHeight: 1.8 }}>
              修改宿主機 WinRM 帳密，請編輯 <code style={{ color: '#22d3ee' }}>backend/.env</code>：
              <pre style={{ background: 'var(--bg-1)', border: '1px solid var(--border-1)',
                            borderRadius: 6, padding: '10px 12px', marginTop: 8, fontSize: 11,
                            color: '#e2e8f0', overflow: 'auto' }}>
{`WINRM_USER=administrator
WINRM_PASSWORD=your_password`}
              </pre>
            </div>
          </div>
          <div>
            <div style={{ fontSize: 12, color: '#64748b', marginBottom: 12, textTransform: 'uppercase',
                          letterSpacing: '0.06em' }}>VM 直連帳密</div>
            <div style={{ fontSize: 13, color: '#94a3b8', lineHeight: 1.8 }}>
              各 VM 的個別帳密儲存於 <code style={{ color: '#22d3ee' }}>backend/vm_credentials.json</code>：
              <pre style={{ background: 'var(--bg-1)', border: '1px solid var(--border-1)',
                            borderRadius: 6, padding: '10px 12px', marginTop: 8, fontSize: 11,
                            color: '#e2e8f0', overflow: 'auto' }}>
{`{
  "VMNAME": {
    "user": "administrator",
    "password": "vm_password"
  }
}`}
              </pre>
            </div>
          </div>
        </div>

        <div style={{ marginTop: 16, padding: '12px 14px', background: 'rgba(245,158,11,0.08)',
                      border: '1px solid rgba(245,158,11,0.3)', borderRadius: 8,
                      fontSize: 12, color: '#f59e0b', display: 'flex', gap: 10, alignItems: 'flex-start' }}>
          <Icon.alertTri style={{ width: 15, height: 15, flexShrink: 0, marginTop: 1 }} />
          <span>
            <strong>.env</strong> 與 <strong>vm_credentials.json</strong> 已列入 .gitignore，
            請勿將這兩個檔案提交到版本控制系統。
          </span>
        </div>
      </Card>
    </>
  );
}

window.PageAdmin = PageAdmin;

// Page: 系統設定
const { useState: useStateSt, useEffect: useEffectSt } = React;

// ── 主機管理區塊 ─────────────────────────────────────────────
function HostManageSection() {
  const [hosts, setHosts]         = useStateSt([]);
  const [groups, setGroups]       = useStateSt([]);
  const [loading, setLoading]     = useStateSt(true);
  const [editId, setEditId]       = useStateSt(null);
  const [editBuf, setEditBuf]     = useStateSt({});
  const [showAdd, setShowAdd]     = useStateSt(false);
  const [addForm, setAddForm]     = useStateSt({ ip: '', description: '', host_type: 'windows', owner_group_id: '' });
  const [saving, setSaving]       = useStateSt(false);
  const [msg, setMsg]             = useStateSt(null);

  const flash = (text, ok = true) => {
    setMsg({ text, ok });
    setTimeout(() => setMsg(null), 3000);
  };

  const loadData = () => {
    setLoading(true);
    Promise.all([
      fetch(`${API_BASE}/api/settings/hosts`).then(r => r.json()),
      fetch(`${API_BASE}/api/settings/owner-groups`).then(r => r.json()),
    ]).then(([h, g]) => { setHosts(h); setGroups(g); setLoading(false); })
      .catch(() => setLoading(false));
  };

  useEffectSt(() => { loadData(); }, []);

  const startEdit = (h) => {
    setEditId(h.id);
    setEditBuf({ description: h.description || '', owner_group_id: h.owner_group_id || '' });
  };

  const saveEdit = async (id) => {
    setSaving(true);
    try {
      const body = {
        description: editBuf.description,
        owner_group_id: editBuf.owner_group_id ? Number(editBuf.owner_group_id) : null,
      };
      const r = await fetch(`${API_BASE}/api/settings/hosts/${id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      if (!r.ok) throw new Error();
      const updated = await r.json();
      setHosts(prev => prev.map(h => h.id === id ? updated : h));
      setEditId(null);
      flash('已儲存');
    } catch { flash('儲存失敗', false); }
    setSaving(false);
  };

  const deleteHost = async (id, name) => {
    if (!confirm(`確定要移除主機 ${name}？`)) return;
    try {
      await fetch(`${API_BASE}/api/settings/hosts/${id}`, { method: 'DELETE' });
      setHosts(prev => prev.filter(h => h.id !== id));
      flash('已移除');
    } catch { flash('移除失敗', false); }
  };

  const addHost = async () => {
    if (!addForm.ip.trim()) return;
    setSaving(true);
    try {
      const body = {
        ip: addForm.ip.trim(),
        description: addForm.description || null,
        host_type: addForm.host_type,
        owner_group_id: addForm.owner_group_id ? Number(addForm.owner_group_id) : null,
      };
      const r = await fetch(`${API_BASE}/api/settings/hosts`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      if (r.status === 409) { flash('此主機已存在', false); setSaving(false); return; }
      if (!r.ok) throw new Error();
      const created = await r.json();
      setHosts(prev => [...prev, created]);
      setShowAdd(false);
      setAddForm({ ip: '', description: '', host_type: 'windows', owner_group_id: '' });
      flash('主機已新增');
    } catch { flash('新增失敗', false); }
    setSaving(false);
  };

  const TypeBadge = ({ type }) => (
    <span style={{
      display: 'inline-block', padding: '2px 8px', borderRadius: 999, fontSize: 11, fontWeight: 600,
      background: type === 'hyperv' ? 'rgba(34,211,238,0.15)' : 'rgba(99,102,241,0.15)',
      color: type === 'hyperv' ? '#22d3ee' : '#818cf8',
    }}>{type === 'hyperv' ? 'Hyper-V' : 'Windows'}</span>
  );

  if (loading) return <LoadingCard />;

  return (
    <Card title="主機清單管理" icon={<Icon.dashboard />}
      actions={
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          {msg && <span style={{ fontSize: 12, color: msg.ok ? '#22c55e' : '#ef4444' }}>{msg.text}</span>}
          <Btn variant="primary" size="sm" onClick={() => setShowAdd(true)}>＋ 新增主機</Btn>
        </div>
      }>

      {/* 新增表單 */}
      {showAdd && (
        <div style={{ padding: '16px', marginBottom: 16, background: 'var(--bg-1)',
                      border: '1px solid var(--border-1)', borderRadius: 8 }}>
          <div style={{ fontSize: 12, color: '#64748b', marginBottom: 12, fontWeight: 600,
                        textTransform: 'uppercase', letterSpacing: '0.06em' }}>新增監控主機</div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr', gap: 12, marginBottom: 12 }}>
            <div>
              <div style={{ fontSize: 11, color: '#64748b', marginBottom: 4 }}>IP / Hostname *</div>
              <input className="input" style={{ width: '100%', padding: '6px 10px', fontSize: 12 }}
                placeholder="192.168.1.100"
                value={addForm.ip} onChange={e => setAddForm(f => ({ ...f, ip: e.target.value }))} />
            </div>
            <div>
              <div style={{ fontSize: 11, color: '#64748b', marginBottom: 4 }}>服務說明</div>
              <input className="input" style={{ width: '100%', padding: '6px 10px', fontSize: 12 }}
                placeholder="例：檔案伺服器"
                value={addForm.description} onChange={e => setAddForm(f => ({ ...f, description: e.target.value }))} />
            </div>
            <div>
              <div style={{ fontSize: 11, color: '#64748b', marginBottom: 4 }}>類型</div>
              <select className="input" style={{ width: '100%', padding: '6px 10px', fontSize: 12 }}
                value={addForm.host_type} onChange={e => setAddForm(f => ({ ...f, host_type: e.target.value }))}>
                <option value="windows">Windows Server</option>
                <option value="hyperv">Hyper-V</option>
              </select>
            </div>
            <div>
              <div style={{ fontSize: 11, color: '#64748b', marginBottom: 4 }}>歸屬單位</div>
              <select className="input" style={{ width: '100%', padding: '6px 10px', fontSize: 12 }}
                value={addForm.owner_group_id} onChange={e => setAddForm(f => ({ ...f, owner_group_id: e.target.value }))}>
                <option value="">— 未指定 —</option>
                {groups.map(g => <option key={g.id} value={g.id}>{g.name}</option>)}
              </select>
            </div>
          </div>
          <div style={{ display: 'flex', gap: 8 }}>
            <Btn variant="primary" size="sm" onClick={addHost}>確認新增</Btn>
            <Btn variant="ghost" size="sm" onClick={() => setShowAdd(false)}>取消</Btn>
          </div>
        </div>
      )}

      {/* 主機列表 */}
      <div className="tbl-wrap">
        <table>
          <thead>
            <tr>
              <th>主機名稱 / IP</th>
              <th>類型</th>
              <th>服務說明</th>
              <th>歸屬單位</th>
              <th>狀態</th>
              <th className="td-center">操作</th>
            </tr>
          </thead>
          <tbody>
            {hosts.map(h => (
              <tr key={h.id}>
                <td className="td-mono" style={{ fontSize: 12 }}>{h.name}</td>
                <td><TypeBadge type={h.host_type} /></td>
                <td>
                  {editId === h.id ? (
                    <input className="input" style={{ width: '100%', padding: '4px 8px', fontSize: 12 }}
                      value={editBuf.description}
                      onChange={e => setEditBuf(b => ({ ...b, description: e.target.value }))} />
                  ) : (
                    <span style={{ fontSize: 13, color: h.description ? '#e2e8f0' : '#475569' }}>
                      {h.description || '— 未填寫 —'}
                    </span>
                  )}
                </td>
                <td>
                  {editId === h.id ? (
                    <select className="input" style={{ padding: '4px 8px', fontSize: 12 }}
                      value={editBuf.owner_group_id}
                      onChange={e => setEditBuf(b => ({ ...b, owner_group_id: e.target.value }))}>
                      <option value="">— 未指定 —</option>
                      {groups.map(g => <option key={g.id} value={g.id}>{g.name}</option>)}
                    </select>
                  ) : (
                    <span style={{ fontSize: 13, color: h.owner_group_name ? '#e2e8f0' : '#475569' }}>
                      {h.owner_group_name || '—'}
                    </span>
                  )}
                </td>
                <td>
                  {h.online
                    ? <Pill kind="ok">連線中</Pill>
                    : <Pill kind="err">離線</Pill>}
                </td>
                <td className="td-center">
                  {editId === h.id ? (
                    <div style={{ display: 'flex', gap: 6, justifyContent: 'center' }}>
                      <Btn variant="primary" size="sm" onClick={() => saveEdit(h.id)}>儲存</Btn>
                      <Btn variant="ghost" size="sm" onClick={() => setEditId(null)}>取消</Btn>
                    </div>
                  ) : (
                    <div style={{ display: 'flex', gap: 6, justifyContent: 'center' }}>
                      <Btn variant="ghost" size="sm" onClick={() => startEdit(h)}>編輯</Btn>
                      {h.host_type !== 'hyperv' && (
                        <Btn variant="ghost" size="sm" onClick={() => deleteHost(h.id, h.name)}>移除</Btn>
                      )}
                    </div>
                  )}
                </td>
              </tr>
            ))}
            {hosts.length === 0 && (
              <tr><td colSpan="6" style={{ textAlign: 'center', color: '#475569', padding: '20px 0' }}>
                尚無主機資料
              </td></tr>
            )}
          </tbody>
        </table>
      </div>
      <div style={{ marginTop: 10, fontSize: 11, color: '#475569' }}>
        ＊ Hyper-V 主機由 .env HV_HOSTS 自動建立，不可從此處移除。Windows Server 可手動新增/移除。
      </div>
    </Card>
  );
}

// ── 主頁面 ───────────────────────────────────────────────────
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
        <Card title="監控環境" icon={<Icon.dashboard />}>
          <InfoRow label="資料庫類型"     value={info.db_type || '—'} mono />
          <InfoRow label="監控主機數"     value={`${info.host_count ?? '—'} 台`} />
          <InfoRow label="虛擬機器數"     value={`${info.vm_count ?? '—'} 台`} />
          <InfoRow label="WinRM 帳號"     value={info.winrm_user || '—'} mono />
          <InfoRow label="宿主機 IP 清單" value={info.hv_hosts || '（未設定）'} mono />
        </Card>

        <Card title="採樣排程" icon={<Icon.activity />}>
          <InfoRow label="VM / 資源採樣間隔"   value={`每 ${info.collection_interval_vm ?? 15} 分鐘`} />
          <InfoRow label="資安事件採樣間隔"    value={`每 ${info.collection_interval_sec ?? 5} 分鐘`} />
          <InfoRow label="快照 / 複寫採樣間隔" value={`每 ${info.collection_interval_vm ?? 15} 分鐘`} />
          <div style={{ marginTop: 16, padding: '10px 12px', background: 'var(--bg-1)',
                        borderRadius: 6, border: '1px solid var(--border-1)', fontSize: 12, color: '#64748b' }}>
            排程由 <code style={{ color: '#22d3ee' }}>collector/scheduler.py</code> 管理，
            修改採樣頻率請調整後重啟服務。
          </div>
        </Card>

        <Card title="通知設定狀態" icon={<Icon.bell />}
          actions={<Btn variant="ghost" size="sm" onClick={() => setPage('alerts')}>前往設定 →</Btn>}>
          <InfoRow label="SMTP 主機"
            value={info.smtp_host
              ? <span style={{ color: '#22c55e' }}>{info.smtp_host}</span>
              : <span style={{ color: '#ef4444' }}>未設定</span>} />
          <InfoRow label="Email 通知"
            value={info.smtp_configured ? <Pill kind="ok">已啟用</Pill> : <Pill kind="err">未設定</Pill>} />
          <InfoRow label="Webhook 推播"
            value={info.webhook_configured ? <Pill kind="ok">已啟用</Pill> : <Pill kind="muted">未啟用</Pill>} />
          {info.dashboard_url && <InfoRow label="Dashboard URL" value={info.dashboard_url} mono />}
        </Card>

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
                  <div style={{ fontSize: 12, color: '#94a3b8', marginTop: 4 }}>告警數：{ov.alert_count ?? 0} 件</div>
                </div>
              </div>
              <InfoRow label="快照違規"   value={`${ov.snapshot_violation_count ?? 0} 台`} />
              <InfoRow label="上次資料更新" value={ov.last_updated ? new Date(ov.last_updated).toLocaleString('zh-TW') : '—'} />
            </>
          ) : <LoadingCard />}
        </Card>
      </div>

      {/* 主機清單管理 */}
      <div style={{ marginBottom: 20 }}>
        <HostManageSection />
      </div>

      <Card title="環境變數說明" icon={<Icon.settings />}>
        <div style={{ fontSize: 13, color: '#94a3b8', lineHeight: 2 }}>
          <p style={{ margin: '0 0 12px' }}>
            以下設定請編輯 <code style={{ color: '#22d3ee' }}>backend/.env</code>，修改後重啟 FastAPI 服務生效。
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
                ['DATABASE_URL',         'PostgreSQL 連線字串'],
                ['WINRM_USER',           'Hyper-V 宿主機管理員帳號'],
                ['WINRM_PASSWORD',       'Hyper-V 宿主機管理員密碼'],
                ['HV_HOSTS',             'Hyper-V 宿主機 IP（逗號分隔）'],
                ['WS_HOSTS',             '一般 Windows Server IP（逗號分隔，可留空從 UI 新增）'],
                ['VM_WINRM_USER',        'VM 直連帳號（IS 故障 fallback）'],
                ['VM_WINRM_PASSWORD',    'VM 直連密碼'],
                ['LDAP_SERVER',          'AD 伺服器位址'],
                ['LDAP_DOMAIN',          'Windows 網域名稱'],
                ['LDAP_BASE_DN',         'LDAP Base DN'],
                ['SECRET_KEY',           'JWT 簽章金鑰（請設定隨機長字串）'],
                ['LOCAL_ADMIN_USERNAME', '本機管理員帳號（LDAP 故障 fallback）'],
                ['SMTP_HOST',            'SMTP 主機（Email 告警）'],
                ['DASHBOARD_URL',        '儀表板網址（Email 附連結）'],
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

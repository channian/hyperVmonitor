// Page: 資源監控
const { useState: useStateR } = React;

function PageResources() {
  const [expandedVm, setExpandedVm] = useStateR(null);
  const [expandDetail, setExpandDetail] = useStateR(null);
  const [filterHost, setFilterHost] = useStateR('all');
  const [tab, setTab] = useStateR('host');

  const { data, loading, error } = useFetch('/api/resources');

  if (loading) return <LoadingCard />;
  if (error)   return <ErrorCard msg={error} />;

  const { hosts, vms } = data;
  const filtered = filterHost === 'all' ? vms : vms.filter(v => v.host === filterHost);
  const hostNames = [...new Set(vms.map(v => v.host))];

  const ramPct = (h) => Math.round((h.ram_used_gb / h.ram_total_gb) * 100);
  const storagePct = (h) => Math.round((h.storage_used_tb / h.storage_total_tb) * 100);

  return (
    <>
      {/* Tab switch */}
      <div className="ctabs">
        <div className={`ctab ${tab === 'host' ? 'active' : ''}`} onClick={() => setTab('host')}>
          <Icon.server style={{ width: 15, height: 15 }} />實體主機
        </div>
        <div className={`ctab ${tab === 'vm' ? 'active' : ''}`} onClick={() => setTab('vm')}>
          <Icon.vm style={{ width: 15, height: 15 }} />VM 清單
        </div>
      </div>

      {tab === 'host' && (
        <>
          <div className="two-col-eq" style={{ marginBottom: 20 }}>
            {hosts.map(h => (
              <Card key={h.name} title={`HOST · ${h.name}`} icon={<Icon.server />}
                actions={<Pill kind={h.cpu_pct > 75 || ramPct(h) > 75 ? 'warn' : 'ok'}>{h.cpu_pct > 75 || ramPct(h) > 75 ? 'WARNING' : 'NORMAL'}</Pill>}>
                <div className="host-bar">
                  <div className="host-bar-label"><Icon.cpu style={{ width:12,height:12,marginRight:6,verticalAlign:'middle' }}/>CPU 使用率</div>
                  <ProgressBar pct={h.cpu_pct} />
                </div>
                <div className="host-bar">
                  <div className="host-bar-label"><Icon.memory style={{ width:12,height:12,marginRight:6,verticalAlign:'middle' }}/>記憶體</div>
                  <ProgressBar pct={ramPct(h)} />
                  <div className="host-bar-val">{h.ram_used_gb.toFixed(0)} GB</div>
                </div>
                <div className="host-bar">
                  <div className="host-bar-label"><Icon.hdd style={{ width:12,height:12,marginRight:6,verticalAlign:'middle' }}/>儲存空間</div>
                  <ProgressBar pct={storagePct(h)} kind="blue" />
                  <div className="host-bar-val" style={{ color: 'var(--fg-2)' }}>{h.storage_used_tb.toFixed(1)} TB</div>
                </div>
                <div style={{ marginTop: 14, display: 'flex', gap: 16 }}>
                  <div style={{ fontFamily: 'var(--font-mono)', fontSize: 12, color: '#64748b' }}>RAM 合計 <span style={{ color: '#e2e8f0', marginLeft: 4 }}>{h.ram_total_gb} GB</span></div>
                  <div style={{ fontFamily: 'var(--font-mono)', fontSize: 12, color: '#64748b' }}>儲存合計 <span style={{ color: '#e2e8f0', marginLeft: 4 }}>{h.storage_total_tb} TB</span></div>
                </div>
              </Card>
            ))}
          </div>
          <Card title="主機資源趨勢（過去 24 小時）" icon={<Icon.activity />}>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24 }}>
              {hosts.map(h => (
                <div key={h.name}>
                  <div className="chart-label">{h.name} · CPU</div>
                  <Sparkline
                    data={Array.from({length:24}, (_,i) => Math.round(h.cpu_pct * (0.8 + Math.sin(i*0.5)*0.2))).map(v=>Math.min(v,100))}
                    color={h.cpu_pct > 75 ? '#f59e0b' : '#22d3ee'} height={56} width={300} />
                </div>
              ))}
            </div>
          </Card>
        </>
      )}

      {tab === 'vm' && (
        <Card title="VM 資源使用總覽" icon={<Icon.vm />}
          actions={
            <select className="select" value={filterHost} onChange={e => setFilterHost(e.target.value)}>
              <option value="all">全部主機</option>
              {hostNames.map(n => <option key={n} value={n}>{n}</option>)}
            </select>
          }>
          <div className="tbl-wrap">
            <table>
              <thead>
                <tr>
                  <th>VM 名稱</th>
                  <th>主機</th>
                  <th className="td-center">vCPU</th>
                  <th style={{ minWidth: 140 }}>CPU 使用率</th>
                  <th style={{ minWidth: 140 }}>記憶體壓力</th>
                  <th>網路</th>
                  <th>狀態</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map(vm => (
                  <React.Fragment key={vm.name}>
                    <tr onClick={() => {
                      const next = expandedVm === vm.name ? null : vm.name;
                      setExpandedVm(next);
                      setExpandDetail(null);
                    }}>
                      <td style={{ fontWeight: 600 }}>
                        <span style={{ marginRight: 8, color: '#475569', fontSize: 11 }}>{expandedVm === vm.name ? '▼' : '▶'}</span>
                        <Dot kind={vm.cpu_status} />
                        {vm.name}
                      </td>
                      <td className="td-mono">{vm.host}</td>
                      <td className="td-center td-mono">{vm.vcpu}</td>
                      <td><ProgressBar pct={vm.cpu_pct} /></td>
                      <td>{vm.ram_pressure_pct != null ? <ProgressBar pct={vm.ram_pressure_pct} /> : <span style={{ color: '#475569', fontSize: 12 }}>—</span>}</td>
                      <td className="td-mono">{(vm.net_in_kbps + vm.net_out_kbps).toFixed(0)} KB/s</td>
                      <td><Pill kind="ok">RUNNING</Pill></td>
                    </tr>
                    {expandedVm === vm.name && (
                      <tr>
                        <td colSpan="7" style={{ padding: 0 }}>
                          <VMExpandRow vm={vm} />
                        </td>
                      </tr>
                    )}
                  </React.Fragment>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}
    </>
  );
}

function VMExpandRow({ vm }) {
  const { data, loading, error } = useFetch(`/api/resources/vms/${vm.name}`);

  if (loading) return <div className="vm-expand"><LoadingCard /></div>;
  if (error)   return <div className="vm-expand"><ErrorCard msg={error} /></div>;

  const { history, cpu_p95, cpu_avg, recommended_vcpu } = data;
  const cpuData = history.map(h => h.cpu_pct);
  const ramData = history.map(h => h.ram_pressure_pct || 0);

  return (
    <div className="vm-expand">
      <div>
        <div className="chart-label">CPU 趨勢（過去 7 天）</div>
        <Sparkline data={cpuData} color={vm.cpu_pct >= 85 ? '#ef4444' : '#22d3ee'} height={72} width={400} />
        <div className="chart-stats">
          <div className="chart-stat"><span className="lbl">P95 </span><span className="val">{cpu_p95}%</span></div>
          <div className="chart-stat"><span className="lbl">平均 </span><span className="val">{cpu_avg}%</span></div>
        </div>
        <div className="chart-label" style={{ marginTop: 16 }}>記憶體壓力趨勢</div>
        <Sparkline data={ramData} color={vm.ram_pressure_pct >= 80 ? '#ef4444' : vm.ram_pressure_pct >= 70 ? '#f59e0b' : '#22c55e'} height={72} width={400} />
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 12, minWidth: 180 }}>
        <div className="card-ui" style={{ padding: '14px 16px' }}>
          <div style={{ fontSize: 11, color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 8 }}>VM 規格</div>
          <div style={{ fontFamily: 'var(--font-mono)', fontSize: 12, lineHeight: 2 }}>
            <div>vCPU：<span style={{ color: '#e2e8f0' }}>{vm.vcpu} 核</span></div>
            <div>RAM：<span style={{ color: '#e2e8f0' }}>{vm.ram_used_gb.toFixed(1)} GB</span></div>
            <div>網路 IN：<span style={{ color: '#e2e8f0' }}>{vm.net_in_kbps} KB/s</span></div>
            <div>主機：<span style={{ color: '#e2e8f0' }}>{vm.host}</span></div>
          </div>
        </div>
        {recommended_vcpu && (
          <div className="card-ui" style={{ padding: '14px 16px', borderColor: 'rgba(239,68,68,0.4)', background: 'rgba(239,68,68,0.05)' }}>
            <div style={{ fontSize: 11, color: '#ef4444', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 6 }}>建議</div>
            <div style={{ fontSize: 12, color: '#94a3b8', lineHeight: 1.6 }}>CPU 持續高負載<br/>建議擴增至 <span style={{ color: '#e2e8f0', fontWeight: 600 }}>{recommended_vcpu} vCPU</span></div>
          </div>
        )}
      </div>
    </div>
  );
}

window.PageResources = PageResources;

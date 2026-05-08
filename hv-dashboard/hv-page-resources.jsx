// Page: 資源監控
const { useState: useStateR } = React;

const HOSTS = [
  { name: 'KHFACVS01', cpu: 42, ram: 78, ramUsed: '62 GB', ramTotal: '80 GB', storage: '1.2 TB', storageTotal: '4 TB', storagePct: 70, vms: 5, status: 'warn' },
  { name: 'KHFACVS02', cpu: 21, ram: 55, ramUsed: '44 GB', ramTotal: '80 GB', storage: '2.8 TB', storageTotal: '4 TB', storagePct: 30, vms: 3, status: 'ok' },
];

const VMS = [
  { name: 'KHTWXDB',         host: 'KHFACVS01', vcpu: 4,  cpu: 90, ram: 87, ramVal: '14 GB', net: '279 KB/s', status: 'Running', tier: 1,
    cpuHistory: [72,78,82,85,88,91,87,90,92,90,91,93,90,91,92,90,93,92,91,93,90,92,91,90,92,93,91,90],
    ramHistory: [80,82,83,84,85,86,85,86,87,86,87,87,86,87,87,86,87,87,86,87,87,86,87,87,86,87,87,87] },
  { name: 'KHTWXAR',         host: 'KHFACVS01', vcpu: 4,  cpu: 35, ram: 60, ramVal: '9.6 GB', net: '45 KB/s',  status: 'Running', tier: 1,
    cpuHistory: [28,30,32,35,33,36,34,35,36,35,34,35,36,35,34,35,36,35,34,35,36,35,34,35,36,35,34,35],
    ramHistory: [55,56,57,58,59,60,60,61,60,60,61,60,60,61,60,60,61,60,60,61,60,60,61,60,60,61,60,60] },
  { name: 'KHTWIOTPWR',      host: 'KHFACVS01', vcpu: 4,  cpu: 25, ram: 79, ramVal: '12.6 GB', net: '21 KB/s', status: 'Running', tier: 1,
    cpuHistory: [20,22,24,25,23,26,24,25,26,25,24,25,26,25,24,25,26,25,24,25,26,25,24,25,26,25,24,25],
    ramHistory: [74,75,76,77,78,78,79,79,79,79,79,79,79,79,79,79,79,79,79,79,79,79,79,79,79,79,79,79] },
  { name: 'KHTWIOTVIB',      host: 'KHFACVS01', vcpu: 2,  cpu: 18, ram: 45, ramVal: '3.6 GB',  net: '8 KB/s',  status: 'Running', tier: 2,
    cpuHistory: [14,15,16,18,16,19,17,18,19,18,17,18,19,18,17,18,19,18,17,18,19,18,17,18,19,18,17,18],
    ramHistory: [40,41,42,43,44,45,45,45,45,45,45,45,45,45,45,45,45,45,45,45,45,45,45,45,45,45,45,45] },
  { name: 'KHTWXFD',         host: 'KHFACVS01', vcpu: 4,  cpu: 40, ram: 50, ramVal: '8 GB',    net: '1 MB/s',  status: 'Running', tier: 2,
    cpuHistory: [35,37,38,40,38,41,39,40,41,40,39,40,41,40,39,40,41,40,39,40,41,40,39,40,41,40,39,40],
    ramHistory: [45,46,47,48,49,50,50,50,50,50,50,50,50,50,50,50,50,50,50,50,50,50,50,50,50,50,50,50] },
  { name: 'KHTWXML',         host: 'KHFACVS02', vcpu: 16, cpu: 12, ram: 43, ramVal: '34.4 GB', net: '2 KB/s',  status: 'Running', tier: 2,
    cpuHistory: [9,10,11,12,10,13,11,12,13,12,11,12,13,12,11,12,13,12,11,12,13,12,11,12,13,12,11,12],
    ramHistory: [38,39,40,41,42,43,43,43,43,43,43,43,43,43,43,43,43,43,43,43,43,43,43,43,43,43,43,43] },
  { name: 'FACCENTRALJUMP01',host: 'KHFACVS02', vcpu: 2,  cpu: 8,  ram: 30, ramVal: '2.4 GB',  net: '5 KB/s',  status: 'Running', tier: 2,
    cpuHistory: [5,6,7,8,6,9,7,8,9,8,7,8,9,8,7,8,9,8,7,8,9,8,7,8,9,8,7,8],
    ramHistory: [25,26,27,28,29,30,30,30,30,30,30,30,30,30,30,30,30,30,30,30,30,30,30,30,30,30,30,30] },
  { name: 'FACCENTRALJUMP02',host: 'KHFACVS02', vcpu: 2,  cpu: 6,  ram: 28, ramVal: '2.2 GB',  net: '3 KB/s',  status: 'Running', tier: 2,
    cpuHistory: [4,5,6,6,5,7,5,6,7,6,5,6,7,6,5,6,7,6,5,6,7,6,5,6,7,6,5,6],
    ramHistory: [22,23,24,25,26,27,28,28,28,28,28,28,28,28,28,28,28,28,28,28,28,28,28,28,28,28,28,28] },
];

function PageResources() {
  const [expandedVm, setExpandedVm] = useStateR(null);
  const [filterHost, setFilterHost] = useStateR('all');
  const [tab, setTab] = useStateR('host');

  const filtered = filterHost === 'all' ? VMS : VMS.filter(v => v.host === filterHost);

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
            {HOSTS.map(h => (
              <Card key={h.name} title={`HOST · ${h.name}`} icon={<Icon.server />}
                actions={<Pill kind={h.status === 'ok' ? 'ok' : 'warn'}>{h.status === 'ok' ? 'NORMAL' : 'WARNING'}</Pill>}>
                <div className="host-bar">
                  <div className="host-bar-label"><Icon.cpu style={{ width:12,height:12,marginRight:6,verticalAlign:'middle' }}/>CPU 使用率</div>
                  <ProgressBar pct={h.cpu} />
                  <div className="host-bar-val">{h.cpu}%</div>
                </div>
                <div className="host-bar">
                  <div className="host-bar-label"><Icon.memory style={{ width:12,height:12,marginRight:6,verticalAlign:'middle' }}/>記憶體</div>
                  <ProgressBar pct={h.ram} />
                  <div className="host-bar-val">{h.ramUsed}</div>
                </div>
                <div className="host-bar">
                  <div className="host-bar-label"><Icon.hdd style={{ width:12,height:12,marginRight:6,verticalAlign:'middle' }}/>儲存空間</div>
                  <ProgressBar pct={h.storagePct} kind="blue" />
                  <div className="host-bar-val" style={{ color: 'var(--fg-2)' }}>{h.storage}</div>
                </div>
                <div style={{ marginTop: 14, display: 'flex', gap: 16 }}>
                  <div style={{ fontFamily: 'var(--font-mono)', fontSize: 12, color: '#64748b' }}>VM 數量 <span style={{ color: '#e2e8f0', marginLeft: 4 }}>{h.vms} 台</span></div>
                  <div style={{ fontFamily: 'var(--font-mono)', fontSize: 12, color: '#64748b' }}>RAM 合計 <span style={{ color: '#e2e8f0', marginLeft: 4 }}>{h.ramTotal}</span></div>
                  <div style={{ fontFamily: 'var(--font-mono)', fontSize: 12, color: '#64748b' }}>儲存合計 <span style={{ color: '#e2e8f0', marginLeft: 4 }}>{h.storageTotal}</span></div>
                </div>
              </Card>
            ))}
          </div>
          <Card title="主機資源趨勢（過去 24 小時）" icon={<Icon.activity />}>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24 }}>
              {HOSTS.map(h => (
                <div key={h.name}>
                  <div className="chart-label">{h.name} · CPU</div>
                  <Sparkline data={Array.from({length:24}, (_,i) => Math.round(h.cpu * (0.8 + Math.sin(i*0.5)*0.2 + Math.random()*0.1))).map(v=>Math.min(v,100))} color={h.cpu > 75 ? '#f59e0b' : '#22d3ee'} height={56} width={300} />
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
              <option value="KHFACVS01">KHFACVS01</option>
              <option value="KHFACVS02">KHFACVS02</option>
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
                  <th>Tier</th>
                  <th>狀態</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map(vm => (
                  <React.Fragment key={vm.name}>
                    <tr onClick={() => setExpandedVm(expandedVm === vm.name ? null : vm.name)}>
                      <td style={{ fontWeight: 600 }}>
                        <span style={{ marginRight: 8, color: '#475569', fontSize: 11 }}>{expandedVm === vm.name ? '▼' : '▶'}</span>
                        <Dot kind={vm.cpu >= 85 ? 'err' : vm.cpu >= 75 ? 'warn' : 'ok'} />
                        {vm.name}
                      </td>
                      <td className="td-mono">{vm.host}</td>
                      <td className="td-center td-mono">{vm.vcpu}</td>
                      <td><ProgressBar pct={vm.cpu} /></td>
                      <td><ProgressBar pct={vm.ram} /></td>
                      <td className="td-mono">{vm.net}</td>
                      <td><Pill kind={vm.tier === 1 ? 'err' : 'info'}>Tier {vm.tier}</Pill></td>
                      <td><Pill kind="ok">RUNNING</Pill></td>
                    </tr>
                    {expandedVm === vm.name && (
                      <tr>
                        <td colSpan="8" style={{ padding: 0 }}>
                          <div className="vm-expand">
                            <div>
                              <div className="chart-label">CPU 趨勢（過去 7 天）</div>
                              <Sparkline data={vm.cpuHistory} color={vm.cpu >= 85 ? '#ef4444' : '#22d3ee'} height={72} width={400} />
                              <div className="chart-stats">
                                <div className="chart-stat"><span className="lbl">P95 </span><span className="val">{Math.round(Math.max(...vm.cpuHistory))}%</span></div>
                                <div className="chart-stat"><span className="lbl">平均 </span><span className="val">{Math.round(vm.cpuHistory.reduce((a,b)=>a+b,0)/vm.cpuHistory.length)}%</span></div>
                              </div>
                              <div className="chart-label" style={{ marginTop: 16 }}>記憶體壓力趨勢</div>
                              <Sparkline data={vm.ramHistory} color={vm.ram >= 80 ? '#ef4444' : vm.ram >= 70 ? '#f59e0b' : '#22c55e'} height={72} width={400} />
                            </div>
                            <div style={{ display: 'flex', flexDirection: 'column', gap: 12, minWidth: 180 }}>
                              <div className="card-ui" style={{ padding: '14px 16px' }}>
                                <div style={{ fontSize: 11, color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 8 }}>VM 規格</div>
                                <div style={{ fontFamily: 'var(--font-mono)', fontSize: 12, lineHeight: 2 }}>
                                  <div>vCPU：<span style={{ color: '#e2e8f0' }}>{vm.vcpu} 核</span></div>
                                  <div>RAM：<span style={{ color: '#e2e8f0' }}>{vm.ramVal}</span></div>
                                  <div>網路：<span style={{ color: '#e2e8f0' }}>{vm.net}</span></div>
                                  <div>主機：<span style={{ color: '#e2e8f0' }}>{vm.host}</span></div>
                                </div>
                              </div>
                              {vm.cpu >= 85 && (
                                <div className="card-ui" style={{ padding: '14px 16px', borderColor: 'rgba(239,68,68,0.4)', background: 'rgba(239,68,68,0.05)' }}>
                                  <div style={{ fontSize: 11, color: '#ef4444', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 6 }}>建議</div>
                                  <div style={{ fontSize: 12, color: '#94a3b8', lineHeight: 1.6 }}>CPU 持續高負載<br/>建議擴增至 <span style={{ color: '#e2e8f0', fontWeight: 600 }}>6 vCPU</span></div>
                                </div>
                              )}
                            </div>
                          </div>
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

window.PageResources = PageResources;

// Page: 備份 / HA
const { useState: useStateBk } = React;

function PageBackup() {
  const [tab, setTab] = useStateBk('backup');
  const { data, loading, error } = useFetch('/api/backup');

  if (loading) return <LoadingCard />;
  if (error)   return <ErrorCard msg={error} />;

  const { items: backupJobs, replication, success_count, total_count, success_rate_pct } = data;

  const failCount = backupJobs.filter(j => j.result === 'Failed').length;
  const warnCount = backupJobs.filter(j => j.result === 'Warning').length;
  const repOk     = replication.filter(r => r.replication_health === 'Normal').length;
  const repErr    = replication.filter(r => r.replication_health !== 'Normal').length;

  const fmtTime = (iso) => {
    if (!iso) return '—';
    const d = new Date(iso);
    const now = new Date();
    const diffMin = Math.round((now - d) / 60000);
    if (diffMin < 60)  return `${diffMin} 分鐘前`;
    if (diffMin < 1440) return `${Math.floor(diffMin/60)} 小時前`;
    return `昨日 ${d.getHours().toString().padStart(2,'0')}:${d.getMinutes().toString().padStart(2,'0')}`;
  };

  return (
    <>
      {failCount > 0 && (
        <Banner kind="err"
          title={`備份失敗 · ${failCount} 台 VM`}
          msg={`${backupJobs.filter(j=>j.result==='Failed').map(j=>j.vm_name).join('、')} 備份失敗，RPO 超標，請立即檢查 Veeam Job 狀態`}
        />
      )}
      {repErr > 0 && (
        <Banner kind="err"
          title={`複寫中斷 · ${replication.filter(r=>!r.rpo_met).map(r=>r.vm_name).join('、')}`}
          msg="異地複寫已中斷，DR 站點資料落後，延遲超過 RPO 門檻"
        />
      )}

      <div className="metrics-4" style={{ marginBottom: 20 }}>
        <Metric title="備份成功率" icon={<Icon.backup />}
          value={`${success_rate_pct}%`}
          delta={`${success_count} 成功 · ${failCount} 失敗 · ${warnCount} 警告`}
          deltaColor={failCount > 0 ? '#ef4444' : warnCount > 0 ? '#f59e0b' : '#22c55e'}
          active={failCount > 0} />
        <Metric title="備份失敗" icon={<Icon.x />} value={String(failCount)}
          delta="需立即處理" deltaColor="#ef4444" active={failCount > 0} />
        <Metric title="複寫正常" icon={<Icon.repeat />} value={`${repOk}/${replication.length}`}
          delta={`${repErr} 台中斷`} deltaColor={repErr > 0 ? '#ef4444' : '#22c55e'} active={repErr > 0} />
        <Metric title="DR 站點健康" icon={<Icon.shield />} value={repErr > 0 ? '警告' : '正常'}
          delta={repErr > 0 ? `${repErr} 台複寫中斷` : '全部同步正常'}
          deltaColor={repErr > 0 ? '#ef4444' : '#22c55e'} />
      </div>

      <div className="ctabs">
        <div className={`ctab ${tab === 'backup' ? 'active' : ''}`} onClick={() => setTab('backup')}>
          <Icon.backup style={{ width: 15, height: 15 }} />備份狀態（Veeam）
        </div>
        <div className={`ctab ${tab === 'rep' ? 'active' : ''}`} onClick={() => setTab('rep')}>
          <Icon.repeat style={{ width: 15, height: 15 }} />異地 HA 複寫
        </div>
      </div>

      {tab === 'backup' && (
        <Card title="備份工作狀態" icon={<Icon.backup />}
          actions={<Btn variant="ghost" size="sm" icon={<Icon.download />}>匯出報告</Btn>}>
          <div className="tbl-wrap">
            <table>
              <thead>
                <tr>
                  <th>VM 名稱</th>
                  <th className="td-center">關鍵性</th>
                  <th>上次備份時間</th>
                  <th className="td-center">備份結果</th>
                  <th>RPO</th>
                  <th className="td-center">RPO 達標</th>
                </tr>
              </thead>
              <tbody>
                {backupJobs.map(j => (
                  <tr key={j.vm_name}>
                    <td style={{ fontWeight: 600 }}>
                      <Dot kind={j.result_status} />{j.vm_name}
                    </td>
                    <td className="td-center">
                      <Pill kind={j.tier === 'Tier1' ? 'err' : 'info'}>{j.tier}</Pill>
                    </td>
                    <td className="td-mono">{fmtTime(j.last_backup_time)}</td>
                    <td className="td-center">
                      <Pill kind={j.result_status}>
                        {j.result === 'Success' ? '成功' : j.result === 'Warning' ? '警告' : j.result === 'Failed' ? '失敗' : '無資料'}
                      </Pill>
                    </td>
                    <td className="td-mono">{j.rpo_label}</td>
                    <td className="td-center">
                      <span style={{ fontFamily: 'var(--font-mono)', fontSize: 13, color: j.rpo_met ? '#22c55e' : '#ef4444', fontWeight: 600 }}>
                        {j.rpo_met ? '✓ 達標' : '✗ 超標'}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {tab === 'rep' && (
        <Card title="異地複寫狀態" icon={<Icon.repeat />}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 16, marginBottom: 20, padding: '12px 16px', background: 'var(--bg-1)', borderRadius: 8, border: '1px solid var(--border-1)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <Dot kind="ok" />
              <span style={{ fontFamily: 'var(--font-mono)', fontSize: 12 }}>主站：KHFACVS01（本地）</span>
            </div>
            <div style={{ flex: 1, height: 2, background: 'var(--border-1)', position: 'relative' }}>
              <div style={{ position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%,-50%)', background: 'var(--bg-1)', padding: '0 8px', fontFamily: 'var(--font-mono)', fontSize: 11, color: '#475569' }}>→ 複寫 →</div>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <Dot kind={repErr > 0 ? 'warn' : 'ok'} />
              <span style={{ fontFamily: 'var(--font-mono)', fontSize: 12 }}>備援站：DR-SITE{repErr > 0 ? '（部分異常）' : ''}</span>
            </div>
          </div>

          <div className="tbl-wrap">
            <table>
              <thead>
                <tr>
                  <th>VM 名稱</th>
                  <th className="td-center">複寫狀態</th>
                  <th>上次同步</th>
                  <th>延遲</th>
                  <th>RPO 目標</th>
                  <th className="td-center">RPO 達標</th>
                </tr>
              </thead>
              <tbody>
                {replication.map(r => (
                  <tr key={r.vm_name}>
                    <td style={{ fontWeight: 600 }}>
                      <Dot kind={r.rpo_met ? 'ok' : 'err'} />{r.vm_name}
                    </td>
                    <td className="td-center">
                      <Pill kind={r.replication_health === 'Normal' ? 'ok' : 'err'}>
                        {r.replication_state === 'Normal' ? '正常' : '中斷'}
                      </Pill>
                    </td>
                    <td className="td-mono">{fmtTime(r.last_replication_time)}</td>
                    <td className="td-mono" style={{ color: r.rpo_met ? '#22c55e' : '#ef4444' }}>
                      {r.lag_minutes >= 60 ? `${Math.floor(r.lag_minutes/60)} hr ${r.lag_minutes%60} min` : `${r.lag_minutes} min`}
                    </td>
                    <td className="td-mono">{r.rpo_minutes} min</td>
                    <td className="td-center">
                      <span style={{ fontFamily: 'var(--font-mono)', fontSize: 13, color: r.rpo_met ? '#22c55e' : '#ef4444', fontWeight: 600 }}>
                        {r.rpo_met ? '✓' : '✗ 超標'}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <Card title="站點健康度" icon={<Icon.server />} style={{ marginTop: 20 }}>
            {[
              { label: '本地站點 · KHFACVS01', pct: 100,             kind: 'ok' },
              { label: 'DR 站點',              pct: repErr > 0 ? 75 : 100, kind: repErr > 0 ? 'warn' : 'ok' },
            ].map(s => (
              <div key={s.label} className="host-bar">
                <div className="host-bar-label" style={{ fontSize: 13 }}>{s.label}</div>
                <ProgressBar pct={s.pct} kind={s.kind} />
                <div className="host-bar-val" style={{ color: s.kind === 'ok' ? '#22c55e' : '#f59e0b', fontSize: 12 }}>
                  {s.pct === 100 ? '正常' : '警告'}
                </div>
              </div>
            ))}
          </Card>
        </Card>
      )}
    </>
  );
}

window.PageBackup = PageBackup;

// Page: 備份 / HA
const { useState: useStateBk } = React;

const BACKUP_JOBS = [
  { vm: 'KHTWXDB',          tier: 1, rpo: '≤4hr',  lastBackup: '今日 02:00', result: 'ok',   rpoMet: true },
  { vm: 'KHTWXAR',          tier: 1, rpo: '≤4hr',  lastBackup: '今日 02:00', result: 'ok',   rpoMet: true },
  { vm: 'KHTWIOTPWR',       tier: 1, rpo: '≤4hr',  lastBackup: '昨日 02:00', result: 'err',  rpoMet: false },
  { vm: 'KHTWIOTVIB',       tier: 2, rpo: '≤24hr', lastBackup: '今日 03:00', result: 'ok',   rpoMet: true },
  { vm: 'KHTWXFD',          tier: 2, rpo: '≤24hr', lastBackup: '今日 03:00', result: 'ok',   rpoMet: true },
  { vm: 'KHTWXML',          tier: 2, rpo: '≤24hr', lastBackup: '今日 03:00', result: 'warn', rpoMet: true },
  { vm: 'FACCENTRALJUMP01', tier: 2, rpo: '≤24hr', lastBackup: '今日 03:30', result: 'ok',   rpoMet: true },
  { vm: 'FACCENTRALJUMP02', tier: 2, rpo: '≤24hr', lastBackup: '今日 03:30', result: 'ok',   rpoMet: true },
];

const REPLICATION = [
  { vm: 'KHTWXDB',    src: 'KHFACVS01', dst: 'DR-SITE', status: 'ok',   lastSync: '15 分鐘前', lag: 15,  rpo: 15,  rpoMet: true },
  { vm: 'KHTWXAR',    src: 'KHFACVS01', dst: 'DR-SITE', status: 'ok',   lastSync: '15 分鐘前', lag: 15,  rpo: 15,  rpoMet: true },
  { vm: 'KHTWIOTPWR', src: 'KHFACVS01', dst: 'DR-SITE', status: 'err',  lastSync: '3 小時前',  lag: 180, rpo: 15,  rpoMet: false },
  { vm: 'KHTWXFD',    src: 'KHFACVS01', dst: 'DR-SITE', status: 'ok',   lastSync: '15 分鐘前', lag: 15,  rpo: 60,  rpoMet: true },
];

function PageBackup() {
  const [tab, setTab] = useStateBk('backup');

  const successCount = BACKUP_JOBS.filter(j => j.result === 'ok').length;
  const failCount    = BACKUP_JOBS.filter(j => j.result === 'err').length;
  const warnCount    = BACKUP_JOBS.filter(j => j.result === 'warn').length;
  const repOk        = REPLICATION.filter(r => r.status === 'ok').length;
  const repErr       = REPLICATION.filter(r => r.status === 'err').length;
  const successRate  = Math.round((successCount / BACKUP_JOBS.length) * 100);

  return (
    <>
      {failCount > 0 && (
        <Banner kind="err"
          title={`備份失敗 · ${failCount} 台 VM`}
          msg="KHTWIOTPWR 上次備份為昨日 02:00，RPO 超標，請立即檢查 Veeam Job 狀態"
        />
      )}
      {repErr > 0 && (
        <Banner kind="err"
          title="複寫中斷 · KHTWIOTPWR"
          msg="異地複寫已中斷 3 小時，DR 站點資料落後，延遲遠超 RPO 15 分鐘門檻"
        />
      )}

      <div className="metrics-4" style={{ marginBottom: 20 }}>
        <Metric title="備份成功率" icon={<Icon.backup />}
          value={`${successRate}%`}
          delta={`${successCount} 成功 · ${failCount} 失敗 · ${warnCount} 警告`}
          deltaColor={failCount > 0 ? '#ef4444' : '#f59e0b'} active={failCount > 0} />
        <Metric title="備份失敗" icon={<Icon.x />} value={failCount}
          delta="需立即處理" deltaColor="#ef4444" active={failCount > 0} />
        <Metric title="複寫正常" icon={<Icon.repeat />} value={`${repOk}/${REPLICATION.length}`}
          delta={`${repErr} 台中斷`} deltaColor={repErr > 0 ? '#ef4444' : '#22c55e'} active={repErr > 0} />
        <Metric title="DR 站點健康" icon={<Icon.shield />} value={repErr > 0 ? '警告' : '正常'}
          delta={repErr > 0 ? '1 台複寫中斷' : '全部同步正常'} deltaColor={repErr > 0 ? '#ef4444' : '#22c55e'} />
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
        <>
          <Card title="備份工作狀態（過去 7 天）" icon={<Icon.backup />}
            actions={<Btn variant="ghost" size="sm" icon={<Icon.download />}>匯出報告</Btn>}>
            <div className="tbl-wrap">
              <table>
                <thead>
                  <tr>
                    <th>VM 名稱</th>
                    <th className="td-center">關鍵性</th>
                    <th>上次備份時間</th>
                    <th className="td-center">備份結果</th>
                    <th>RPO 目標</th>
                    <th className="td-center">RPO 達標</th>
                  </tr>
                </thead>
                <tbody>
                  {BACKUP_JOBS.map(j => (
                    <tr key={j.vm}>
                      <td style={{ fontWeight: 600 }}>
                        <Dot kind={j.result === 'ok' ? 'ok' : j.result === 'warn' ? 'warn' : 'err'} />{j.vm}
                      </td>
                      <td className="td-center">
                        <Pill kind={j.tier === 1 ? 'err' : 'info'}>Tier {j.tier}</Pill>
                      </td>
                      <td className="td-mono">{j.lastBackup}</td>
                      <td className="td-center">
                        <Pill kind={j.result === 'ok' ? 'ok' : j.result === 'warn' ? 'warn' : 'err'}>
                          {j.result === 'ok' ? '成功' : j.result === 'warn' ? '警告' : '失敗'}
                        </Pill>
                      </td>
                      <td className="td-mono">{j.rpo}</td>
                      <td className="td-center">
                        <span style={{ fontFamily: 'var(--font-mono)', fontSize: 13, color: j.rpoMet ? '#22c55e' : '#ef4444', fontWeight: 600 }}>
                          {j.rpoMet ? '✓ 達標' : '✗ 超標'}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>

          {/* 7-day summary bars */}
          <Card title="過去 7 天備份成功率趨勢" icon={<Icon.activity />} style={{ marginTop: 20 }}>
            <div style={{ display: 'flex', gap: 6, alignItems: 'flex-end', height: 80, padding: '0 4px' }}>
              {['週一','週二','週三','週四','週五','週六','週日'].map((d, i) => {
                const rates = [100, 100, 87.5, 100, 100, 87.5, 90];
                const pct = rates[i];
                const color = pct < 90 ? '#ef4444' : pct < 100 ? '#f59e0b' : '#22c55e';
                return (
                  <div key={d} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 6 }}>
                    <div style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: '#64748b' }}>{pct}%</div>
                    <div style={{ width: '100%', background: 'var(--bg-1)', borderRadius: 3, overflow: 'hidden', height: 48 }}>
                      <div style={{ width: '100%', height: `${pct}%`, background: color, borderRadius: 3, marginTop: `${100 - pct}%` }}></div>
                    </div>
                    <div style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: '#64748b' }}>{d}</div>
                  </div>
                );
              })}
            </div>
          </Card>
        </>
      )}

      {tab === 'rep' && (
        <>
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
                    <th>來源主機</th>
                    <th>目標站點</th>
                    <th className="td-center">複寫狀態</th>
                    <th>上次同步</th>
                    <th>延遲</th>
                    <th className="td-center">RPO 達標</th>
                  </tr>
                </thead>
                <tbody>
                  {REPLICATION.map(r => (
                    <tr key={r.vm}>
                      <td style={{ fontWeight: 600 }}>
                        <Dot kind={r.status === 'ok' ? 'ok' : 'err'} />{r.vm}
                      </td>
                      <td className="td-mono">{r.src}</td>
                      <td className="td-mono">{r.dst}</td>
                      <td className="td-center">
                        <Pill kind={r.status === 'ok' ? 'ok' : 'err'}>
                          {r.status === 'ok' ? '正常' : '中斷'}
                        </Pill>
                      </td>
                      <td className="td-mono">{r.lastSync}</td>
                      <td className="td-mono" style={{ color: r.rpoMet ? '#22c55e' : '#ef4444' }}>
                        {r.lag >= 60 ? `${Math.floor(r.lag/60)} hr ${r.lag%60} min` : `${r.lag} min`}
                      </td>
                      <td className="td-center">
                        <span style={{ fontFamily: 'var(--font-mono)', fontSize: 13, color: r.rpoMet ? '#22c55e' : '#ef4444', fontWeight: 600 }}>
                          {r.rpoMet ? '✓' : '✗ 超標'}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>

          {/* Site health bars */}
          <Card title="站點健康度" icon={<Icon.server />} style={{ marginTop: 20 }}>
            {[
              { label: '本地站點 · KHFACVS01', pct: 100, kind: 'ok' },
              { label: 'DR 站點',              pct: 75,  kind: 'warn' },
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
        </>
      )}
    </>
  );
}

window.PageBackup = PageBackup;

"""HVM Email HTML 模板。

提供三種格式：
  - alert_html()       即時告警（嚴重 / 警告）
  - summary_html()     每小時警告彙整
  - daily_report_html() 每日健康報告
"""
from datetime import datetime


# ── 共用樣式 ─────────────────────────────────────────────────

_BASE_STYLE = """
  body { margin:0; padding:0; background:#0f172a; font-family:Inter,Arial,sans-serif; }
  .wrap { max-width:640px; margin:0 auto; padding:24px 16px; }
  .header { background:#0f172a; border-bottom:2px solid {accent}; padding:20px 24px; border-radius:8px 8px 0 0; }
  .header-brand { display:flex; align-items:center; gap:12px; }
  .brand-box {{ background:#172033; border:1.5px solid {accent}40; border-radius:8px;
               width:40px; height:40px; display:flex; align-items:center; justify-content:center;
               font-weight:800; font-size:13px; color:#e6edf7; letter-spacing:-0.03em; }}
  .brand-title {{ color:#e6edf7; font-size:15px; font-weight:700; }}
  .brand-sub {{ color:{accent}; font-size:10px; font-family:monospace; letter-spacing:0.12em; text-transform:uppercase; }}
  .timestamp {{ color:#475569; font-size:12px; font-family:monospace; margin-top:4px; }}
  .body {{ background:#0f172a; padding:24px; border-radius:0 0 8px 8px; border:1px solid #1e293b; border-top:none; }}
  .sev-banner {{ padding:14px 18px; border-radius:8px; margin-bottom:20px; display:flex; align-items:flex-start; gap:12px; }}
  .sev-err  {{ background:rgba(239,68,68,0.08); border-left:4px solid #ef4444; }}
  .sev-warn {{ background:rgba(245,158,11,0.08); border-left:4px solid #f59e0b; }}
  .sev-ok   {{ background:rgba(34,197,94,0.08);  border-left:4px solid #22c55e; }}
  .sev-icon {{ font-size:20px; line-height:1; flex-shrink:0; margin-top:2px; }}
  .sev-body h2 {{ margin:0 0 4px; font-size:16px; font-weight:700; color:#e2e8f0; }}
  .sev-body p  {{ margin:0; font-size:13px; color:#94a3b8; line-height:1.6; }}
  table.data {{ width:100%; border-collapse:collapse; margin:16px 0; font-size:13px; }}
  table.data th {{ background:#172033; color:#64748b; font-weight:600; font-size:11px;
                   text-transform:uppercase; letter-spacing:0.06em; padding:8px 12px; text-align:left; }}
  table.data td {{ padding:10px 12px; border-bottom:1px solid #1e293b; color:#e2e8f0; vertical-align:top; }}
  table.data tr:last-child td {{ border-bottom:none; }}
  .pill-err  {{ display:inline-block; padding:2px 8px; border-radius:999px; background:#ef444430;
                color:#ef4444; font-size:11px; font-weight:600; }}
  .pill-warn {{ display:inline-block; padding:2px 8px; border-radius:999px; background:#f59e0b30;
                color:#f59e0b; font-size:11px; font-weight:600; }}
  .pill-ok   {{ display:inline-block; padding:2px 8px; border-radius:999px; background:#22c55e30;
                color:#22c55e; font-size:11px; font-weight:600; }}
  .pill-info {{ display:inline-block; padding:2px 8px; border-radius:999px; background:#3b82f630;
                color:#3b82f6; font-size:11px; font-weight:600; }}
  .section-title {{ font-size:11px; font-weight:600; text-transform:uppercase; letter-spacing:0.1em;
                    color:#64748b; margin:20px 0 8px; }}
  .footer {{ text-align:center; color:#334155; font-size:11px; font-family:monospace;
             margin-top:20px; padding-top:16px; border-top:1px solid #1e293b; }}
  .mono {{ font-family:monospace; }}
  .action-box {{ background:#172033; border:1px solid #1e293b; border-radius:6px;
                 padding:14px 16px; margin-top:16px; font-size:13px; color:#94a3b8; line-height:1.8; }}
"""

_SEV_LABEL = {"err": "嚴重告警", "warn": "警告通知", "ok": "復歸通知"}
_SEV_ACCENT = {"err": "#ef4444", "warn": "#f59e0b", "ok": "#22c55e"}
_SEV_ICON = {"err": "🔴", "warn": "🟡", "ok": "🟢"}


def _header(accent: str) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return f"""
    <div class="header">
      <div class="header-brand">
        <div class="brand-box">HVM</div>
        <div>
          <div class="brand-title">Hyper-V Monitor</div>
          <div class="brand-sub">Alert Notification</div>
        </div>
      </div>
      <div class="timestamp">產生時間：{now}</div>
    </div>"""


def _footer(dashboard_url: str = "") -> str:
    link = f'<a href="{dashboard_url}" style="color:#22d3ee;">開啟 Dashboard</a>' if dashboard_url else ""
    return f"""
    <div class="footer">
      Hyper-V Monitor · 自動產生，請勿直接回覆<br>
      {link}
    </div>"""


def _style(accent: str) -> str:
    return "<style>" + _BASE_STYLE.replace("{accent}", accent) + "</style>"


# ── 即時告警 ─────────────────────────────────────────────────

def alert_html(
    severity: str,            # err / warn / ok
    title: str,
    description: str,
    source: str,
    details: list[tuple[str, str]],   # [(欄位名, 值), ...]
    action: str = "",
    dashboard_url: str = "",
) -> str:
    """
    即時告警郵件（嚴重 / 警告 / 復歸）。

    details 範例：
      [("VM 名稱", "KHTWXDB"), ("CPU 使用率", "92%"), ("門檻", "85%")]
    """
    accent = _SEV_ACCENT.get(severity, "#22d3ee")
    icon   = _SEV_ICON.get(severity, "ℹ️")
    label  = _SEV_LABEL.get(severity, "通知")

    rows = "".join(
        f"<tr><td class='mono' style='color:#64748b;width:140px'>{k}</td><td>{v}</td></tr>"
        for k, v in details
    )
    action_block = f'<div class="action-box">💡 建議動作：{action}</div>' if action else ""

    return f"""<!DOCTYPE html><html lang="zh-Hant"><head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
{_style(accent)}
</head><body><div class="wrap">
{_header(accent)}
<div class="body">
  <div class="sev-banner sev-{severity}">
    <div class="sev-icon">{icon}</div>
    <div class="sev-body">
      <h2>[{label}] {title}</h2>
      <p>{description}</p>
    </div>
  </div>

  <div class="section-title">事件來源</div>
  <div class="mono" style="color:#94a3b8;font-size:13px;padding:4px 0">{source}</div>

  <div class="section-title">詳細資訊</div>
  <table class="data"><tbody>{rows}</tbody></table>

  {action_block}
</div>
{_footer(dashboard_url)}
</div></body></html>"""


# ── 每小時警告彙整 ────────────────────────────────────────────

def summary_html(
    events: list[dict],
    period_label: str = "過去 1 小時",
    dashboard_url: str = "",
) -> str:
    """
    每小時警告彙整郵件。

    events 每筆格式：
      {"severity": "warn", "source": "KHTWXDB", "title": "CPU 過高",
       "description": "CPU 88%，超過門檻 75%", "occurred_at": "14:05:32"}
    """
    err_count  = sum(1 for e in events if e.get("severity") == "err")
    warn_count = sum(1 for e in events if e.get("severity") == "warn")
    accent = "#ef4444" if err_count else "#f59e0b"

    rows = ""
    for e in events:
        sev = e.get("severity", "warn")
        pill = f'<span class="pill-{sev}">{_SEV_LABEL.get(sev, sev)}</span>'
        rows += f"""<tr>
          <td class="mono" style="white-space:nowrap;color:#64748b">{e.get('occurred_at','')}</td>
          <td class="mono">{e.get('source','')}</td>
          <td>{pill}</td>
          <td style="color:#94a3b8">{e.get('title','')}：{e.get('description','')}</td>
        </tr>"""

    return f"""<!DOCTYPE html><html lang="zh-Hant"><head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
{_style(accent)}
</head><body><div class="wrap">
{_header(accent)}
<div class="body">
  <div class="sev-banner sev-{'err' if err_count else 'warn'}">
    <div class="sev-icon">{'🔴' if err_count else '🟡'}</div>
    <div class="sev-body">
      <h2>告警彙整・{period_label}</h2>
      <p>共 <strong>{len(events)}</strong> 筆告警：嚴重 <strong>{err_count}</strong> 筆・警告 <strong>{warn_count}</strong> 筆</p>
    </div>
  </div>

  <div class="section-title">告警明細</div>
  <table class="data">
    <thead><tr>
      <th>時間</th><th>來源</th><th>類型</th><th>說明</th>
    </tr></thead>
    <tbody>{rows}</tbody>
  </table>
</div>
{_footer(dashboard_url)}
</div></body></html>"""


# ── 每日健康報告 ──────────────────────────────────────────────

def daily_report_html(
    report_date: str,
    health_pct: int,
    host_count: int,
    vm_count: int,
    sections: list[dict],
    top_alerts: list[dict],
    dashboard_url: str = "",
) -> str:
    """
    每日系統健康報告。

    sections 每筆格式：
      {"title": "資源監控", "status": "warn",
       "summary": "1 台 VM CPU > 90%", "count": 2}

    top_alerts 每筆格式：
      {"severity": "err", "source": "KHTWXDB", "message": "CPU 持續 >90%"}
    """
    health_color = "#22c55e" if health_pct >= 80 else "#f59e0b" if health_pct >= 60 else "#ef4444"
    accent = health_color

    section_rows = ""
    for s in sections:
        pill_cls = {"ok": "ok", "warn": "warn", "err": "err"}.get(s.get("status", "ok"), "ok")
        pill_txt = {"ok": "正常", "warn": "警告", "err": "異常"}.get(s.get("status", "ok"), "—")
        section_rows += f"""<tr>
          <td style="font-weight:600">{s.get('title','')}</td>
          <td><span class="pill-{pill_cls}">{pill_txt}</span></td>
          <td style="color:#94a3b8">{s.get('summary','')}</td>
        </tr>"""

    alert_rows = ""
    for a in top_alerts:
        sev = a.get("severity", "warn")
        icon = _SEV_ICON.get(sev, "ℹ️")
        alert_rows += f"""<tr>
          <td style="width:24px">{icon}</td>
          <td class="mono" style="color:#64748b;white-space:nowrap">{a.get('source','')}</td>
          <td style="color:#94a3b8">{a.get('message','')}</td>
        </tr>"""

    return f"""<!DOCTYPE html><html lang="zh-Hant"><head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
{_style(accent)}
</head><body><div class="wrap">
{_header(accent)}
<div class="body">
  <!-- 健康度 KPI -->
  <table style="width:100%;margin-bottom:20px">
    <tr>
      <td style="text-align:center;padding:16px;background:#172033;border-radius:8px;border:1px solid #1e293b">
        <div style="font-size:11px;color:#64748b;text-transform:uppercase;letter-spacing:0.1em;margin-bottom:6px">系統健康度</div>
        <div style="font-size:40px;font-weight:800;font-family:monospace;color:{health_color}">{health_pct}%</div>
        <div style="font-size:12px;color:#475569;margin-top:4px">{report_date}</div>
      </td>
      <td style="width:16px"></td>
      <td style="vertical-align:top;padding:16px;background:#172033;border-radius:8px;border:1px solid #1e293b">
        <div style="font-size:11px;color:#64748b;text-transform:uppercase;letter-spacing:0.1em;margin-bottom:12px">環境概況</div>
        <div style="font-family:monospace;font-size:13px;line-height:2.2;color:#94a3b8">
          實體主機：<span style="color:#e2e8f0;font-weight:600">{host_count} 台</span><br>
          虛擬機器：<span style="color:#e2e8f0;font-weight:600">{vm_count} 台</span>
        </div>
      </td>
    </tr>
  </table>

  <!-- 各視角狀態 -->
  <div class="section-title">各視角狀態</div>
  <table class="data">
    <thead><tr><th>視角</th><th>狀態</th><th>摘要</th></tr></thead>
    <tbody>{section_rows}</tbody>
  </table>

  <!-- 待處理事項 -->
  {'<div class="section-title">待處理事項</div><table class="data"><tbody>' + alert_rows + '</tbody></table>' if top_alerts else ''}
</div>
{_footer(dashboard_url)}
</div></body></html>"""

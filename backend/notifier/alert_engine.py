"""告警規則評估引擎：評估閾值並觸發 Email / Webhook 通知。"""
import logging
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func

log = logging.getLogger(__name__)

# 同一規則 + 來源的發送冷卻時間（分鐘），避免短時間內重複告警
COOLDOWN_MINUTES = 60
_last_sent: dict[tuple, datetime] = {}


def _cooling(rule_id: int, source: str) -> bool:
    key = (rule_id, source)
    last = _last_sent.get(key)
    return bool(last and (datetime.utcnow() - last).total_seconds() < COOLDOWN_MINUTES * 60)


def _mark(rule_id: int, source: str):
    _last_sent[(rule_id, source)] = datetime.utcnow()


def _get_cfg(db: Session):
    """取得通知設定（DB 優先，fallback .env）。"""
    from database import settings as env
    from models import AppSetting

    def g(key: str, default: str = "") -> str:
        row = db.query(AppSetting).filter_by(key=key).first()
        return row.value if row else default

    def b(key: str, env_val: bool) -> bool:
        v = g(key)
        return v.lower() in ("1", "true") if v else env_val

    return {
        "smtp_host":         g("smtp_host") or env.smtp_host,
        "smtp_port":         int(g("smtp_port") or env.smtp_port),
        "smtp_sender_email": g("smtp_sender_email") or env.smtp_sender_email,
        "smtp_sender_name":  g("smtp_sender_name") or env.smtp_sender_name,
        "email_it":          g("alert_email_it") or env.alert_email_it,
        "email_mgr":         g("alert_email_manager") or env.alert_email_manager,
        "dashboard_url":     env.dashboard_url,
        "webhook_enable":    b("webhook_enable", env.webhook_enable),
        "webhook_url":       g("webhook_url") or env.webhook_url,
        "webhook_token":     g("webhook_token") or env.webhook_token,
        "webhook_body_template": g("webhook_body_template") or env.webhook_body_template,
        "webhook_use_proxy": b("webhook_use_proxy", env.webhook_use_proxy),
        "webhook_proxy_url": g("webhook_proxy_url") or env.webhook_proxy_url,
    }


def evaluate_and_notify(db: Session):
    """評估所有啟用的告警規則，若觸發則發送通知。"""
    from models import AlertRule, VM, VMMetric, VMSnapshot, VMReplication, SecurityEvent
    from notifier.email_service import EmailService
    from notifier.templates import alert_html, summary_html
    from notifier.webhook_service import WebhookService

    rules = db.query(AlertRule).filter_by(enabled=True).all()
    if not rules:
        return

    cfg = _get_cfg(db)
    now = datetime.utcnow()
    triggered: list[dict] = []

    for rule in rules:
        if not rule.notify_immediate:
            continue

        if rule.category == "resource":
            _eval_resource(db, rule, triggered)
        elif rule.category == "snapshot":
            _eval_snapshot(db, rule, now, triggered)
        elif rule.category == "backup":
            _eval_backup(db, rule, now, triggered)
        elif rule.category == "security":
            _eval_security(db, rule, now, triggered)

    # 過濾冷卻中的告警
    new_alerts = [t for t in triggered if not _cooling(t["rule_id"], t["source"])]
    if not new_alerts:
        return

    log.info("告警引擎：觸發 %d 件告警", len(new_alerts))

    it_addrs  = [e.strip() for e in cfg["email_it"].split(",")  if e.strip()]
    mgr_addrs = [e.strip() for e in cfg["email_mgr"].split(",") if e.strip()]

    # Email
    if cfg["smtp_host"] and cfg["smtp_sender_email"] and it_addrs:
        svc = EmailService(
            cfg["smtp_host"], cfg["smtp_port"],
            cfg["smtp_sender_email"], cfg["smtp_sender_name"],
        )
        err_alerts = [t for t in new_alerts if t["severity"] == "err"]

        # IT 群組：所有告警
        events_for_email = [
            {"severity": t["severity"], "source": t["source"],
             "title": t["rule_name"], "description": t["message"],
             "occurred_at": now.strftime("%H:%M")}
            for t in new_alerts
        ]
        html = summary_html(events_for_email, "最新採樣週期", cfg["dashboard_url"])
        svc.send_alert_email(it_addrs, f"[HVM 告警] {len(new_alerts)} 件需處理", html)

        # 主管群組：僅嚴重告警
        if err_alerts and mgr_addrs:
            err_events = [
                {"severity": t["severity"], "source": t["source"],
                 "title": t["rule_name"], "description": t["message"],
                 "occurred_at": now.strftime("%H:%M")}
                for t in err_alerts
            ]
            err_html = summary_html(err_events, "最新採樣週期", cfg["dashboard_url"])
            svc.send_alert_email(mgr_addrs, f"[HVM 嚴重告警] {len(err_alerts)} 件需立即處理", err_html)

    # Webhook
    if cfg["webhook_enable"] and cfg["webhook_url"]:
        wh = WebhookService(
            cfg["webhook_url"], cfg["webhook_token"], cfg["webhook_body_template"],
            enable=True, use_proxy=cfg["webhook_use_proxy"], proxy_url=cfg["webhook_proxy_url"] or None,
        )
        for t in new_alerts:
            vars_ = wh.build_variables(t["rule_name"], t["severity"], t["source"], t["message"])
            wh.send(vars_, device_name=t["source"])

    for t in new_alerts:
        _mark(t["rule_id"], t["source"])


def _eval_resource(db, rule, triggered):
    from models import VM, VMMetric
    threshold = rule.threshold_value or 0
    for vm in db.query(VM).all():
        m = (db.query(VMMetric).filter_by(vm_id=vm.id)
             .order_by(VMMetric.collected_at.desc()).first())
        if not m:
            continue
        if "CPU" in rule.rule_name and m.cpu_pct >= threshold:
            triggered.append({
                "rule_id": rule.id, "source": vm.name, "severity": rule.severity,
                "rule_name": rule.rule_name,
                "message": f"CPU {m.cpu_pct:.1f}%（門檻 {threshold:.0f}%）",
            })
        elif "記憶體" in rule.rule_name and m.ram_pressure_pct and m.ram_pressure_pct >= threshold:
            triggered.append({
                "rule_id": rule.id, "source": vm.name, "severity": rule.severity,
                "rule_name": rule.rule_name,
                "message": f"記憶體壓力 {m.ram_pressure_pct:.1f}%（門檻 {threshold:.0f}%）",
            })


def _eval_snapshot(db, rule, now, triggered):
    from models import VM, VMSnapshot
    threshold = int(rule.threshold_value or 7)
    for vm in db.query(VM).all():
        snaps = db.query(VMSnapshot).filter_by(vm_id=vm.id).all()
        if not snaps:
            continue
        if vm.is_sql:
            triggered.append({
                "rule_id": rule.id, "source": vm.name, "severity": "err",
                "rule_name": rule.rule_name,
                "message": f"SQL Server VM 有快照（即違規）",
            })
        else:
            oldest = min(snaps, key=lambda s: s.created_at)
            age = (now - oldest.created_at).days
            if age > threshold:
                triggered.append({
                    "rule_id": rule.id, "source": vm.name, "severity": rule.severity,
                    "rule_name": rule.rule_name,
                    "message": f"快照已 {age} 天（門檻 {threshold} 天）",
                })


def _eval_backup(db, rule, now, triggered):
    from models import VM, VMReplication
    for vm in db.query(VM).all():
        r = (db.query(VMReplication).filter_by(vm_id=vm.id)
             .order_by(VMReplication.collected_at.desc()).first())
        if r and r.replication_health in ("Critical", "Warning"):
            lag = (int((now - r.last_replication_time).total_seconds() / 60)
                   if r.last_replication_time else 0)
            triggered.append({
                "rule_id": rule.id, "source": vm.name,
                "severity": "err" if r.replication_health == "Critical" else "warn",
                "rule_name": rule.rule_name,
                "message": f"複寫狀態 {r.replication_health}，落後 {lag} 分鐘",
            })


def _eval_security(db, rule, now, triggered):
    from models import SecurityEvent
    if "暴力破解" not in rule.rule_name:
        return
    threshold = int(rule.threshold_value or 5)
    since = now - timedelta(minutes=10)
    rows = (
        db.query(SecurityEvent.account, func.count(SecurityEvent.id).label("cnt"))
        .filter(SecurityEvent.event_type == "login_fail", SecurityEvent.occurred_at >= since)
        .group_by(SecurityEvent.account)
        .having(func.count(SecurityEvent.id) >= threshold)
        .all()
    )
    for account, cnt in rows:
        triggered.append({
            "rule_id": rule.id, "source": account, "severity": rule.severity,
            "rule_name": rule.rule_name,
            "message": f"帳號 {account} 10 分鐘內登入失敗 {cnt} 次",
        })

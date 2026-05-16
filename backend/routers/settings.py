"""系統設定 API：通知設定（SMTP / Webhook）的 GET/PATCH + 測試發送。"""
from datetime import datetime
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from database import get_db, settings as env_settings
from models import AppSetting, Host, VM

router = APIRouter(prefix="/api/settings", tags=["settings"])


def _get(db: Session, key: str, default: str = "") -> str:
    row = db.query(AppSetting).filter_by(key=key).first()
    return row.value if row else default


def _set(db: Session, key: str, value: str):
    row = db.query(AppSetting).filter_by(key=key).first()
    if row:
        row.value = value
        row.updated_at = datetime.utcnow()
    else:
        db.add(AppSetting(key=key, value=value, updated_at=datetime.utcnow()))


class NotifyConfig(BaseModel):
    smtp_host: str = ""
    smtp_port: int = 25
    smtp_sender_email: str = ""
    smtp_sender_name: str = "Hyper-V Monitor"
    alert_email_it: str = ""
    alert_email_manager: str = ""
    daily_report_time: str = "08:00"
    webhook_enable: bool = False
    webhook_url: str = ""
    webhook_token: str = ""
    webhook_body_template: str = '{"token":"{{$token}}","content":"{{$message}}"}'
    webhook_use_proxy: bool = False
    webhook_proxy_url: str = ""


class TestNotifyRequest(BaseModel):
    recipient: str = ""


def _load_config(db: Session) -> NotifyConfig:
    def _bool(key: str, env_val: bool) -> bool:
        v = _get(db, key)
        if v:
            return v.lower() in ("1", "true")
        return env_val

    return NotifyConfig(
        smtp_host=_get(db, "smtp_host") or env_settings.smtp_host,
        smtp_port=int(_get(db, "smtp_port") or env_settings.smtp_port),
        smtp_sender_email=_get(db, "smtp_sender_email") or env_settings.smtp_sender_email,
        smtp_sender_name=_get(db, "smtp_sender_name") or env_settings.smtp_sender_name,
        alert_email_it=_get(db, "alert_email_it") or env_settings.alert_email_it,
        alert_email_manager=_get(db, "alert_email_manager") or env_settings.alert_email_manager,
        daily_report_time=_get(db, "daily_report_time") or "08:00",
        webhook_enable=_bool("webhook_enable", env_settings.webhook_enable),
        webhook_url=_get(db, "webhook_url") or env_settings.webhook_url,
        webhook_token=_get(db, "webhook_token") or env_settings.webhook_token,
        webhook_body_template=_get(db, "webhook_body_template") or env_settings.webhook_body_template,
        webhook_use_proxy=_bool("webhook_use_proxy", env_settings.webhook_use_proxy),
        webhook_proxy_url=_get(db, "webhook_proxy_url") or env_settings.webhook_proxy_url,
    )


@router.get("/notify", response_model=NotifyConfig)
def get_notify_config(db: Session = Depends(get_db)):
    return _load_config(db)


@router.patch("/notify", response_model=NotifyConfig)
def update_notify_config(body: NotifyConfig, db: Session = Depends(get_db)):
    _set(db, "smtp_host", body.smtp_host)
    _set(db, "smtp_port", str(body.smtp_port))
    _set(db, "smtp_sender_email", body.smtp_sender_email)
    _set(db, "smtp_sender_name", body.smtp_sender_name)
    _set(db, "alert_email_it", body.alert_email_it)
    _set(db, "alert_email_manager", body.alert_email_manager)
    _set(db, "daily_report_time", body.daily_report_time)
    _set(db, "webhook_enable", str(body.webhook_enable).lower())
    _set(db, "webhook_url", body.webhook_url)
    _set(db, "webhook_token", body.webhook_token)
    _set(db, "webhook_body_template", body.webhook_body_template)
    _set(db, "webhook_use_proxy", str(body.webhook_use_proxy).lower())
    _set(db, "webhook_proxy_url", body.webhook_proxy_url)
    db.commit()
    return _load_config(db)


@router.post("/notify/test")
def test_notify(body: TestNotifyRequest, db: Session = Depends(get_db)):
    cfg = _load_config(db)
    recipient = body.recipient or cfg.alert_email_it
    if not cfg.smtp_host:
        return {"ok": False, "error": "未設定 SMTP 主機"}
    if not cfg.smtp_sender_email:
        return {"ok": False, "error": "未設定寄件人信箱"}
    if not recipient:
        return {"ok": False, "error": "未設定收件人"}
    from notifier.email_service import EmailService
    svc = EmailService(cfg.smtp_host, cfg.smtp_port, cfg.smtp_sender_email, cfg.smtp_sender_name)
    ok = svc.send_alert_email(
        recipient,
        "[HVM] 測試郵件",
        "<p>這是來自 <strong>Hyper-V Monitor</strong> 的測試郵件，表示 SMTP 設定正確。</p>",
    )
    return {"ok": ok, "error": "" if ok else "郵件發送失敗，請確認 SMTP 設定"}


@router.get("/system")
def get_system_info(db: Session = Depends(get_db)):
    cfg = _load_config(db)
    db_type = "PostgreSQL" if "postgresql" in env_settings.database_url else "SQLite"
    return {
        "host_count": db.query(Host).count(),
        "vm_count": db.query(VM).count(),
        "db_type": db_type,
        "winrm_user": env_settings.winrm_user,
        "hv_hosts": env_settings.hv_hosts,
        "smtp_configured": bool(cfg.smtp_host and cfg.smtp_sender_email),
        "smtp_host": cfg.smtp_host,
        "collection_interval_vm": 15,
        "collection_interval_sec": 5,
        "dashboard_url": env_settings.dashboard_url,
        "webhook_configured": cfg.webhook_enable and bool(cfg.webhook_url),
    }

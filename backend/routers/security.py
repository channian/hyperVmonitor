from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from database import get_db
from schemas import SecurityResponse, SecurityEventItem, SecuritySummaryCard

router = APIRouter(prefix="/api/security", tags=["security"])

_TODAY = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

_MOCK_EVENTS = [
    SecurityEventItem(occurred_at=_TODAY + timedelta(hours=3, minutes=42), source_host="KHTWXDB",   event_type="login_fail",   event_id=4625, account="administrator", description="連續登入失敗 8 次（暴力破解偵測）", severity="err"),
    SecurityEventItem(occurred_at=_TODAY + timedelta(hours=3, minutes=43), source_host="KHTWXDB",   event_type="lockout",      event_id=4740, account="administrator", description="帳號鎖定，超過失敗門檻",             severity="err"),
    SecurityEventItem(occurred_at=_TODAY + timedelta(hours=14, minutes=22), source_host="AD-01",    event_type="group_change",  event_id=4728, account="jsmith-adm",   description="加入 HV-Admins 群組",             severity="err"),
    SecurityEventItem(occurred_at=_TODAY + timedelta(hours=9, minutes=5),  source_host="KHTWXFD",   event_type="login_success", event_id=4624, account="svc-backup",   description="服務帳號互動式登入（非排程）",    severity="warn"),
    SecurityEventItem(occurred_at=_TODAY - timedelta(hours=2),             source_host="KHTWXML",   event_type="login_fail",   event_id=4625, account="khtwxml-adm",  description="登入失敗 2 次",                   severity="warn"),
]


@router.get("", response_model=SecurityResponse)
def get_security(period: str = Query("today", pattern="^(today|week|month)$"), db: Session = Depends(get_db)):
    err_events   = [e for e in _MOCK_EVENTS if e.severity == "err"]
    warn_events  = [e for e in _MOCK_EVENTS if e.severity == "warn"]
    login_fails  = [e for e in _MOCK_EVENTS if e.event_type == "login_fail"]
    lockouts     = [e for e in _MOCK_EVENTS if e.event_type == "lockout"]
    group_change = [e for e in _MOCK_EVENTS if e.event_type == "group_change"]

    return SecurityResponse(
        period=period,
        summary_cards=[
            SecuritySummaryCard(category="login",        label="登入異常",   count=len(login_fails),  status="err"  if login_fails  else "ok"),
            SecuritySummaryCard(category="account",      label="帳號事件",   count=len(lockouts) + len(group_change), status="err" if (lockouts or group_change) else "ok"),
            SecuritySummaryCard(category="network",      label="流量異常",   count=0,                 status="ok"),
            SecuritySummaryCard(category="vm_operation", label="VM 操作稽核", count=0,                status="ok"),
            SecuritySummaryCard(category="ot",           label="OT 通訊狀態", count=0,               status="ok"),
        ],
        events=sorted(_MOCK_EVENTS, key=lambda e: e.occurred_at, reverse=True),
    )

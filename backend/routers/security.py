from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from database import get_db
from models import SecurityEvent
from schemas import SecurityResponse, SecurityEventItem, SecuritySummaryCard

router = APIRouter(prefix="/api/security", tags=["security"])


def _period_start(period: str) -> datetime:
    now = datetime.utcnow()
    if period == "today":
        return now.replace(hour=0, minute=0, second=0, microsecond=0)
    if period == "week":
        return now - timedelta(days=7)
    return now - timedelta(days=30)  # month


@router.get("", response_model=SecurityResponse)
def get_security(
    period: str = Query("today", pattern="^(today|week|month)$"),
    db: Session = Depends(get_db),
):
    since = _period_start(period)
    events = (
        db.query(SecurityEvent)
        .filter(SecurityEvent.occurred_at >= since)
        .order_by(SecurityEvent.occurred_at.desc())
        .all()
    )

    login_fails  = [e for e in events if e.event_type == "login_fail"]
    lockouts     = [e for e in events if e.event_type == "lockout"]
    group_changes = [e for e in events if e.event_type in ("group_change", "group_member_add")]

    event_items = [
        SecurityEventItem(
            occurred_at=e.occurred_at,
            source_host=e.source_host,
            event_type=e.event_type,
            event_id=e.event_id,
            account=e.account,
            description=e.description,
            severity=e.severity,
        )
        for e in events
    ]

    account_count = len(lockouts) + len(group_changes)
    return SecurityResponse(
        period=period,
        summary_cards=[
            SecuritySummaryCard(
                category="login",
                label="登入異常",
                count=len(login_fails),
                status="err" if login_fails else "ok",
            ),
            SecuritySummaryCard(
                category="account",
                label="帳號事件",
                count=account_count,
                status="err" if (lockouts or group_changes) else "ok",
            ),
            SecuritySummaryCard(category="network",      label="流量異常",    count=0, status="ok"),
            SecuritySummaryCard(category="vm_operation", label="VM 操作稽核", count=0, status="ok"),
            SecuritySummaryCard(category="ot",           label="OT 通訊狀態", count=0, status="ok"),
        ],
        events=event_items,
    )

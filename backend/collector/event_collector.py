"""安全事件收集器：Windows Event Log（每 5 分鐘）"""
import json
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from .winrm_client import WinRMClient
from .utils import parse_ps_datetime
from models import SecurityEvent

# 收集 4624/4625/4728/4732/4740 等關鍵事件，往回看 10 分鐘（避免重複）
_PS_GET_EVENTS = r"""
$since = (Get-Date).ToUniversalTime().AddMinutes(-10)
$ids   = @(4624, 4625, 4728, 4732, 4740)
$events = Get-WinEvent -FilterHashtable @{
    LogName   = 'Security'
    Id        = $ids
    StartTime = $since
} -ErrorAction SilentlyContinue
if (-not $events) { '[]'; return }
$events | ForEach-Object {
    $xml  = [xml]$_.ToXml()
    $data = @{}
    $xml.Event.EventData.Data | ForEach-Object { $data[$_.Name] = $_.'#text' }
    [PSCustomObject]@{
        EventId      = $_.Id
        TimeCreated  = $_.TimeCreated.ToUniversalTime().ToString('o')
        AccountName  = $data['TargetUserName']
        IpAddress    = $data['IpAddress']
        LogonType    = $data['LogonType']
        MemberName   = $data['MemberName']
        GroupName    = $data['TargetUserName']
    }
} | ConvertTo-Json -Compress
"""

_EVENT_TYPE_MAP = {
    4624: "login_success",
    4625: "login_fail",
    4728: "group_change",
    4732: "group_change",
    4740: "lockout",
}

_SEVERITY_MAP = {
    4624: "info",
    4625: "warn",
    4728: "err",
    4732: "err",
    4740: "err",
}


def collect_security_events(client: WinRMClient, db: Session, source_host: str):
    raw = client.run_ps(_PS_GET_EVENTS).strip()
    if not raw or raw in ("null", "[]"):
        return

    items = json.loads(raw)
    if isinstance(items, dict):
        items = [items]

    cutoff = datetime.utcnow() - timedelta(minutes=11)

    for item in items:
        event_id = int(item["EventId"])
        occurred_at = parse_ps_datetime(item["TimeCreated"])

        if occurred_at < cutoff:
            continue

        duplicate = db.query(SecurityEvent).filter(
            SecurityEvent.source_host == source_host,
            SecurityEvent.event_id == event_id,
            SecurityEvent.occurred_at == occurred_at,
        ).first()
        if duplicate:
            continue

        account = item.get("AccountName") or item.get("MemberName") or "unknown"
        description = _build_description(item, event_id)

        db.add(SecurityEvent(
            source_host=source_host,
            event_id=event_id,
            event_type=_EVENT_TYPE_MAP.get(event_id, "unknown"),
            account=account,
            description=description,
            severity=_SEVERITY_MAP.get(event_id, "info"),
            occurred_at=occurred_at,
        ))

    db.commit()


def _build_description(item: dict, event_id: int) -> str:
    if event_id == 4625:
        return f"登入失敗，來源 IP：{item.get('IpAddress', 'N/A')}"
    if event_id == 4624:
        logon_type = item.get("LogonType", "?")
        return f"登入成功，類型 {logon_type}"
    if event_id in (4728, 4732):
        return f"加入群組：{item.get('GroupName', 'N/A')}"
    if event_id == 4740:
        return "帳號被鎖定"
    return ""

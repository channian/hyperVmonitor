"""複寫狀態收集器：Get-VMReplication（每 15 分鐘）"""
import json
from datetime import datetime
from sqlalchemy.orm import Session
from .winrm_client import WinRMClient
from .utils import parse_ps_datetime
from models import VM, VMReplication

_PS_GET_REPLICATION = """
Get-VMReplication | Select-Object VMName, State, Health,
    @{N='LastReplicationTimeUTC';E={
        if ($_.LastReplicationTime) {
            $_.LastReplicationTime.ToUniversalTime().ToString('o')
        } else { $null }
    }},
    ReplicationFrequencySec |
    ConvertTo-Json -Compress
"""


def collect_replication(client: WinRMClient, db: Session):
    now = datetime.utcnow()
    raw = client.run_ps(_PS_GET_REPLICATION).strip()

    if not raw or raw == "null":
        return

    items = json.loads(raw)
    if isinstance(items, dict):
        items = [items]

    for item in items:
        vm_name = item["VMName"].upper()
        vm = db.query(VM).filter_by(name=vm_name).first()
        if vm is None:
            continue

        last_time = parse_ps_datetime(item.get("LastReplicationTimeUTC"))

        rpo_minutes = max(1, int(item.get("ReplicationFrequencySec", 900)) // 60)

        db.add(VMReplication(
            vm_id=vm.id,
            replication_state=item.get("State", "Unknown"),
            replication_health=item.get("Health", "Unknown"),
            last_replication_time=last_time,
            rpo_minutes=rpo_minutes,
            collected_at=now,
        ))

    db.commit()

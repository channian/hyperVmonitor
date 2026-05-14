"""快照收集器：Get-VMSnapshot（每 15 分鐘）"""
import json
from datetime import datetime
from sqlalchemy.orm import Session
from .winrm_client import WinRMClient
from .utils import parse_ps_datetime
from models import VM, VMSnapshot

_PS_GET_SNAPSHOTS = """
Get-VMSnapshot -VMName * |
    Select-Object VMName, Name,
        @{N='CreationTimeUTC';E={$_.CreationTime.ToUniversalTime().ToString('o')}} |
    ConvertTo-Json -Compress
"""


def collect_snapshots(client: WinRMClient, db: Session):
    now = datetime.utcnow()
    raw = client.run_ps(_PS_GET_SNAPSHOTS).strip()

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

        created_at = parse_ps_datetime(item["CreationTimeUTC"])
        snap_name  = item["Name"]

        exists = db.query(VMSnapshot).filter_by(
            vm_id=vm.id, snapshot_name=snap_name
        ).first()
        if not exists:
            db.add(VMSnapshot(
                vm_id=vm.id,
                snapshot_name=snap_name,
                created_at=created_at,
                detected_at=now,
            ))

    db.commit()

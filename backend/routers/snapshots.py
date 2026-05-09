from datetime import datetime
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
from schemas import SnapshotResponse, SnapshotItem

router = APIRouter(prefix="/api/snapshots", tags=["snapshots"])

_MOCK_SNAPSHOTS = [
    SnapshotItem(vm_name="KHTWXDB",          snapshot_count=2, oldest_snapshot_date=datetime(2024, 3, 15), age_days=397, compliance_status="err", compliance_label="嚴重違規", is_sql=True),
    SnapshotItem(vm_name="KHTWXAR",          snapshot_count=2, oldest_snapshot_date=datetime(2024, 3, 15), age_days=397, compliance_status="err", compliance_label="嚴重違規", is_sql=False),
    SnapshotItem(vm_name="KHTWXML",          snapshot_count=3, oldest_snapshot_date=datetime(2024, 8, 15), age_days=248, compliance_status="err", compliance_label="違規",     is_sql=False),
    SnapshotItem(vm_name="KHTWXFD",          snapshot_count=2, oldest_snapshot_date=datetime(2024, 11, 1), age_days=170, compliance_status="err", compliance_label="違規",     is_sql=False),
    SnapshotItem(vm_name="KHTWIOTPWR",       snapshot_count=1, oldest_snapshot_date=datetime(2024, 6, 20), age_days=300, compliance_status="err", compliance_label="違規",     is_sql=False),
    SnapshotItem(vm_name="KHTWIOTVIB",       snapshot_count=1, oldest_snapshot_date=datetime(2024, 6, 20), age_days=300, compliance_status="err", compliance_label="違規",     is_sql=False),
    SnapshotItem(vm_name="FACCENTRALJUMP01", snapshot_count=1, oldest_snapshot_date=datetime(2025, 1, 10), age_days=95,  compliance_status="err", compliance_label="違規",     is_sql=False),
    SnapshotItem(vm_name="FACCENTRALJUMP02", snapshot_count=1, oldest_snapshot_date=datetime(2025, 1, 10), age_days=95,  compliance_status="err", compliance_label="違規",     is_sql=False),
]


@router.get("", response_model=SnapshotResponse)
def get_snapshots(db: Session = Depends(get_db)):
    violations = [s for s in _MOCK_SNAPSHOTS if s.compliance_status != "ok"]
    compliant  = [s for s in _MOCK_SNAPSHOTS if s.compliance_status == "ok"]
    return SnapshotResponse(
        compliance_count=len(compliant),
        violation_count=len(violations),
        total_count=len(_MOCK_SNAPSHOTS),
        items=sorted(_MOCK_SNAPSHOTS, key=lambda x: x.age_days, reverse=True),
    )

from datetime import datetime
from pydantic import BaseModel


# ── Overview ──────────────────────────────────────────────────

class ActionItem(BaseModel):
    severity: str          # err / warn
    source: str
    message: str

class SectionCard(BaseModel):
    id: str
    title: str
    status: str            # ok / warn / err
    summary: str
    detail: str
    counts: list[dict]

class OverviewResponse(BaseModel):
    host_count: int
    vm_count: int
    alert_count: int
    snapshot_violation_count: int
    health_pct: int
    section_cards: list[SectionCard]
    action_items: list[ActionItem]
    last_updated: datetime


# ── Resources ────────────────────────────────────────────────

class HostSummary(BaseModel):
    name: str
    ip: str
    online: bool
    cpu_pct: float
    ram_used_gb: float
    ram_total_gb: float
    storage_used_tb: float
    storage_total_tb: float

class VMSummary(BaseModel):
    name: str
    host: str
    vcpu: int
    cpu_pct: float
    ram_used_gb: float
    ram_pressure_pct: float | None
    net_in_kbps: float
    net_out_kbps: float
    state: str
    cpu_status: str        # ok / warn / err
    ram_status: str        # ok / warn / err

class VMHistory(BaseModel):
    collected_at: datetime
    cpu_pct: float
    ram_pressure_pct: float | None

class VMDetailResponse(BaseModel):
    vm: VMSummary
    history: list[VMHistory]
    cpu_p95: float
    cpu_avg: float
    recommended_vcpu: int | None

class ResourcesResponse(BaseModel):
    hosts: list[HostSummary]
    vms: list[VMSummary]


# ── Snapshots ────────────────────────────────────────────────

class SnapshotItem(BaseModel):
    vm_name: str
    snapshot_count: int
    oldest_snapshot_date: datetime | None
    age_days: int
    compliance_status: str   # ok / warn / err
    compliance_label: str    # 合規 / 警告 / 違規 / 嚴重違規
    is_sql: bool

class SnapshotResponse(BaseModel):
    compliance_count: int
    violation_count: int
    total_count: int
    items: list[SnapshotItem]


# ── Backup / HA ──────────────────────────────────────────────

class BackupItem(BaseModel):
    vm_name: str
    tier: str
    last_backup_time: datetime | None
    result: str              # Success / Failed / Warning / NoData
    result_status: str       # ok / err / warn
    rpo_met: bool
    rpo_label: str

class ReplicationItem(BaseModel):
    vm_name: str
    replication_state: str
    replication_health: str
    last_replication_time: datetime | None
    lag_minutes: int
    rpo_minutes: int
    rpo_met: bool

class BackupResponse(BaseModel):
    success_count: int
    total_count: int
    success_rate_pct: float
    items: list[BackupItem]
    replication: list[ReplicationItem]


# ── Security ─────────────────────────────────────────────────

class SecurityEventItem(BaseModel):
    occurred_at: datetime
    source_host: str
    event_type: str
    event_id: int
    account: str
    description: str
    severity: str

class SecuritySummaryCard(BaseModel):
    category: str
    label: str
    count: int
    status: str

class SecurityResponse(BaseModel):
    summary_cards: list[SecuritySummaryCard]
    events: list[SecurityEventItem]
    period: str


# ── Alerts ───────────────────────────────────────────────────

class AlertRuleItem(BaseModel):
    id: int
    rule_name: str
    category: str
    enabled: bool
    severity: str
    threshold_value: float | None
    threshold_unit: str | None
    notify_immediate: bool
    description: str

class AlertRuleUpdate(BaseModel):
    enabled: bool | None = None
    threshold_value: float | None = None
    notify_immediate: bool | None = None

from datetime import datetime
from sqlalchemy import Integer, String, Float, DateTime, Boolean, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database import Base


class OwnerGroup(Base):
    """主機擁有者群組（如 CIM、IT）"""
    __tablename__ = "owner_groups"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    hosts: Mapped[list["Host"]] = relationship("Host", back_populates="owner_group")


class HvmRole(Base):
    """HVM 儀表板使用者角色（admin / user）"""
    __tablename__ = "hvm_roles"

    username: Mapped[str] = mapped_column(String(64), primary_key=True)
    role: Mapped[str] = mapped_column(String(16), default="user")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Host(Base):
    """實體 Hyper-V 主機"""
    __tablename__ = "hosts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    ip: Mapped[str] = mapped_column(String(64))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    host_type: Mapped[str] = mapped_column(String(16), default="hyperv")
    owner_group_id: Mapped[int | None] = mapped_column(ForeignKey("owner_groups.id"), nullable=True)
    online: Mapped[bool] = mapped_column(Boolean, default=True)
    collected_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    vms: Mapped[list["VM"]] = relationship("VM", back_populates="host")
    metrics: Mapped[list["HostMetric"]] = relationship("HostMetric", back_populates="host")
    owner_group: Mapped["OwnerGroup | None"] = relationship("OwnerGroup", back_populates="hosts")


class HostMetric(Base):
    """實體主機資源使用量（每 15 分鐘採樣）"""
    __tablename__ = "host_metrics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    host_id: Mapped[int] = mapped_column(ForeignKey("hosts.id"), index=True)
    cpu_pct: Mapped[float] = mapped_column(Float)
    ram_used_gb: Mapped[float] = mapped_column(Float)
    ram_total_gb: Mapped[float] = mapped_column(Float)
    storage_used_tb: Mapped[float] = mapped_column(Float)
    storage_total_tb: Mapped[float] = mapped_column(Float)
    collected_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

    host: Mapped["Host"] = relationship("Host", back_populates="metrics")


class VM(Base):
    """虛擬機清單（Get-VM）"""
    __tablename__ = "vms"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    host_id: Mapped[int] = mapped_column(ForeignKey("hosts.id"))
    vcpu: Mapped[int] = mapped_column(Integer)
    ram_gb: Mapped[float] = mapped_column(Float)
    tier: Mapped[str] = mapped_column(String(16), default="Tier2")   # Tier1 / Tier2
    is_sql: Mapped[bool] = mapped_column(Boolean, default=False)      # SQL Server VM 快照即違規
    state: Mapped[str] = mapped_column(String(32), default="Running")

    host: Mapped["Host"] = relationship("Host", back_populates="vms")
    metrics: Mapped[list["VMMetric"]] = relationship("VMMetric", back_populates="vm")
    snapshots: Mapped[list["VMSnapshot"]] = relationship("VMSnapshot", back_populates="vm")
    replication: Mapped[list["VMReplication"]] = relationship("VMReplication", back_populates="vm")
    backup_jobs: Mapped[list["BackupJob"]] = relationship("BackupJob", back_populates="vm")


class VMMetric(Base):
    """VM 資源使用量（每 15 分鐘採樣）"""
    __tablename__ = "vm_metrics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    vm_id: Mapped[int] = mapped_column(ForeignKey("vms.id"), index=True)
    cpu_pct: Mapped[float] = mapped_column(Float)
    ram_used_gb: Mapped[float] = mapped_column(Float)
    ram_pressure_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    net_in_kbps: Mapped[float] = mapped_column(Float, default=0)
    net_out_kbps: Mapped[float] = mapped_column(Float, default=0)
    collected_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

    vm: Mapped["VM"] = relationship("VM", back_populates="metrics")


class VMSnapshot(Base):
    """快照紀錄（Get-VMSnapshot，每 15 分鐘）"""
    __tablename__ = "vm_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    vm_id: Mapped[int] = mapped_column(ForeignKey("vms.id"), index=True)
    snapshot_name: Mapped[str] = mapped_column(String(256))
    created_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    detected_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    vm: Mapped["VM"] = relationship("VM", back_populates="snapshots")


class VMReplication(Base):
    """複寫狀態（Get-VMReplication，每 15 分鐘）"""
    __tablename__ = "vm_replication"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    vm_id: Mapped[int] = mapped_column(ForeignKey("vms.id"), index=True)
    replication_state: Mapped[str] = mapped_column(String(64))   # Normal / Error / Suspended
    replication_health: Mapped[str] = mapped_column(String(64))  # Normal / Warning / Critical
    last_replication_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    rpo_minutes: Mapped[int] = mapped_column(Integer, default=15)
    collected_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

    vm: Mapped["VM"] = relationship("VM", back_populates="replication")


class BackupJob(Base):
    """備份 Job 結果（Veeam API，每 30 分鐘）"""
    __tablename__ = "backup_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    vm_id: Mapped[int] = mapped_column(ForeignKey("vms.id"), index=True)
    job_name: Mapped[str] = mapped_column(String(128))
    result: Mapped[str] = mapped_column(String(32))        # Success / Failed / Warning
    start_time: Mapped[datetime] = mapped_column(DateTime)
    end_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    collected_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

    vm: Mapped["VM"] = relationship("VM", back_populates="backup_jobs")


class SecurityEvent(Base):
    """安全事件（Windows Event Log，每 5 分鐘）"""
    __tablename__ = "security_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_host: Mapped[str] = mapped_column(String(64), index=True)
    event_id: Mapped[int] = mapped_column(Integer, index=True)
    event_type: Mapped[str] = mapped_column(String(64))       # login_fail / login_success / group_change / lockout
    account: Mapped[str] = mapped_column(String(128))
    description: Mapped[str] = mapped_column(Text, default="")
    severity: Mapped[str] = mapped_column(String(16), default="warn")  # err / warn / info
    occurred_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    collected_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class AlertRule(Base):
    """告警規則設定"""
    __tablename__ = "alert_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    rule_name: Mapped[str] = mapped_column(String(128), unique=True)
    category: Mapped[str] = mapped_column(String(64))          # resource / snapshot / backup / security
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    severity: Mapped[str] = mapped_column(String(16))          # err / warn
    threshold_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    threshold_unit: Mapped[str | None] = mapped_column(String(32), nullable=True)
    notify_immediate: Mapped[bool] = mapped_column(Boolean, default=True)
    description: Mapped[str] = mapped_column(Text, default="")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class AppSetting(Base):
    """應用程式設定鍵值儲存（可覆蓋 .env）"""
    __tablename__ = "app_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    key: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    value: Mapped[str] = mapped_column(Text, default="")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

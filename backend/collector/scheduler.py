"""APScheduler 排程主程式。
獨立執行：python -m collector.scheduler
或透過 Windows Task Scheduler 呼叫。
"""
import logging
from apscheduler.schedulers.blocking import BlockingScheduler
from sqlalchemy.orm import Session
from database import SessionLocal, engine, Base, settings
from models import Host
from .winrm_client import WinRMClient
from .vm_collector import collect_vm_metrics, collect_host_metrics_only
from .snapshot_collector import collect_snapshots
from .replication_collector import collect_replication
from .event_collector import collect_security_events

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

# 確保資料表存在（無論是直接執行或被 import 啟動都需要）
Base.metadata.create_all(bind=engine)

# 從 .env 讀取設定（透過 pydantic-settings，與 FastAPI 共用同一份設定）
WINRM_USER     = settings.winrm_user
WINRM_PASSWORD = settings.winrm_password
HOSTS          = [h.strip() for h in settings.hv_hosts.split(",") if h.strip()]
WS_HOSTS = [h.strip() for h in settings.ws_hosts.split(",") if h.strip()]

# VM 直連帳密：留空時自動沿用宿主機帳密
VM_WINRM_USER     = settings.vm_winrm_user     or WINRM_USER
VM_WINRM_PASSWORD = settings.vm_winrm_password or WINRM_PASSWORD


def _get_or_create_host(db: Session, name: str, ip: str, host_type: str = "hyperv") -> Host:
    host = db.query(Host).filter_by(name=name.upper()).first()
    if host is None:
        host = Host(name=name.upper(), ip=ip, host_type=host_type)
        db.add(host)
        db.commit()
        db.refresh(host)
    return host


def _collect_all():
    if not HOSTS and not WS_HOSTS:
        log.warning("HV_HOSTS 與 WS_HOSTS 均未設定，跳過採樣")
        return

    db: Session = SessionLocal()
    try:
        # 確保 .env 設定的主機都存在於 DB
        for host_ip in HOSTS:
            _get_or_create_host(db, host_ip, host_ip, host_type="hyperv")
        for host_ip in WS_HOSTS:
            _get_or_create_host(db, host_ip, host_ip, host_type="windows")

        # 從 DB 取所有主機（含從 UI 手動新增的非 HV 主機）
        all_hosts = db.query(Host).all()
        for host_record in all_hosts:
            log.info("開始採樣主機：%s（%s）", host_record.ip, host_record.host_type)
            try:
                client = WinRMClient(host_record.ip, WINRM_USER, WINRM_PASSWORD)

                if host_record.host_type == "hyperv":
                    collect_vm_metrics(client, db, host_record, VM_WINRM_USER, VM_WINRM_PASSWORD)
                    collect_snapshots(client, db)
                    collect_replication(client, db)
                    collect_security_events(client, db, host_record.ip)
                else:
                    collect_host_metrics_only(client, db, host_record)
                    collect_security_events(client, db, host_record.ip)

                log.info("主機 %s 採樣完成", host_record.ip)
            except Exception as e:
                log.error("主機 %s 採樣失敗：%s", host_record.ip, e)

        # 告警規則評估 + 通知
        try:
            from notifier.alert_engine import evaluate_and_notify
            evaluate_and_notify(db)
        except Exception as e:
            log.error("告警引擎執行失敗：%s", e)
    finally:
        db.close()


def _collect_security_only():
    db: Session = SessionLocal()
    try:
        all_hosts = db.query(Host).all()
        for host_record in all_hosts:
            try:
                client = WinRMClient(host_record.ip, WINRM_USER, WINRM_PASSWORD)
                collect_security_events(client, db, host_record.ip)
            except Exception as e:
                log.error("主機 %s 安全事件採樣失敗：%s", host_record.ip, e)
    finally:
        db.close()


if __name__ == "__main__":
    log.info("Collector 排程啟動，目標主機：%s", HOSTS)

    scheduler = BlockingScheduler(timezone="Asia/Taipei")
    scheduler.add_job(_collect_all, "interval", minutes=15, id="vm_metrics",   max_instances=1)
    # 安全事件採用較短間隔
    scheduler.add_job(
        _collect_security_only,
        "interval",
        minutes=5,
        id="security_events",
        max_instances=1,
    )

    _collect_all()  # 啟動時立即執行一次
    scheduler.start()

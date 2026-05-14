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
from .vm_collector import collect_vm_metrics
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


def _get_or_create_host(db: Session, name: str, ip: str) -> Host:
    host = db.query(Host).filter_by(name=name.upper()).first()
    if host is None:
        host = Host(name=name.upper(), ip=ip)
        db.add(host)
        db.commit()
        db.refresh(host)
    return host


def _collect_all():
    if not HOSTS:
        log.warning("HV_HOSTS 未設定，跳過採樣")
        return

    db: Session = SessionLocal()
    try:
        for host_ip in HOSTS:
            log.info("開始採樣主機：%s", host_ip)
            try:
                client = WinRMClient(host_ip, WINRM_USER, WINRM_PASSWORD)
                host_record = _get_or_create_host(db, host_ip, host_ip)

                collect_vm_metrics(client, db, host_record)
                collect_snapshots(client, db)
                collect_replication(client, db)
                collect_security_events(client, db, host_ip)

                log.info("主機 %s 採樣完成", host_ip)
            except Exception as e:
                log.error("主機 %s 採樣失敗：%s", host_ip, e)
    finally:
        db.close()


if __name__ == "__main__":
    log.info("Collector 排程啟動，目標主機：%s", HOSTS)

    scheduler = BlockingScheduler(timezone="Asia/Taipei")
    scheduler.add_job(_collect_all, "interval", minutes=15, id="vm_metrics",   max_instances=1)
    # 安全事件採用較短間隔
    scheduler.add_job(
        lambda: [
            collect_security_events(
                WinRMClient(h, WINRM_USER, WINRM_PASSWORD),
                SessionLocal(),
                h,
            )
            for h in HOSTS
        ],
        "interval",
        minutes=5,
        id="security_events",
        max_instances=1,
    )

    _collect_all()  # 啟動時立即執行一次
    scheduler.start()

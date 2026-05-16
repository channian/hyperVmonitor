from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "sqlite:///./hv_metrics.db"

    # WinRM / Collector
    winrm_user: str = "administrator"
    winrm_password: str = ""
    hv_hosts: str = ""          # 逗號分隔，如 "10.10.22.187,10.10.22.188"

    # VM 直連帳密（IS 故障時 fallback 用，帳密與宿主機不同時填入）
    vm_winrm_user: str = ""     # 留空則沿用 winrm_user
    vm_winrm_password: str = "" # 留空則沿用 winrm_password

    # Email
    smtp_host: str = ""
    smtp_port: int = 25
    smtp_sender_email: str = ""
    smtp_sender_name: str = "Hyper-V Monitor"
    alert_email_it: str = ""
    alert_email_manager: str = ""
    dashboard_url: str = ""

    # Webhook
    webhook_enable: bool = False
    webhook_url: str = ""
    webhook_token: str = ""
    webhook_body_template: str = '{"token":"{{$token}}","content":"{{$message}}"}'
    webhook_use_proxy: bool = False
    webhook_proxy_url: str = ""

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

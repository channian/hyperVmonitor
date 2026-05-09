from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy.orm import Session
from database import get_db
from models import AlertRule
from schemas import AlertRuleItem, AlertRuleUpdate

router = APIRouter(prefix="/api/alerts", tags=["alerts"])

_DEFAULT_RULES = [
    dict(rule_name="暴力破解偵測",       category="security", enabled=True,  severity="err",  threshold_value=5,   threshold_unit="次/10min",  notify_immediate=True,  description="同一帳號 10 分鐘內登入失敗 ≥ 5 次"),
    dict(rule_name="非上班時段管理員登入", category="security", enabled=True,  severity="warn", threshold_value=None, threshold_unit=None,       notify_immediate=True,  description="管理員帳號於 22:00–07:00 登入成功"),
    dict(rule_name="特權群組新增成員",    category="security", enabled=True,  severity="err",  threshold_value=None, threshold_unit=None,       notify_immediate=True,  description="HV-Admins / Domain Admins 有新成員加入"),
    dict(rule_name="服務帳號互動式登入",  category="security", enabled=True,  severity="err",  threshold_value=None, threshold_unit=None,       notify_immediate=True,  description="svc-* 帳號出現互動式登入（非服務啟動）"),
    dict(rule_name="網路流量突增",        category="security", enabled=True,  severity="warn", threshold_value=3,   threshold_unit="倍基線P95", notify_immediate=False, description="任一 VM 網路流量超過基線 P95 的 3 倍"),
    dict(rule_name="OT 非預期對外連線",   category="security", enabled=True,  severity="err",  threshold_value=None, threshold_unit=None,       notify_immediate=True,  description="Kepware VM 出現 OT-DMZ 以外的連線"),
    dict(rule_name="VM 非預期關機",       category="security", enabled=True,  severity="warn", threshold_value=None, threshold_unit=None,       notify_immediate=True,  description="Running 狀態的 VM 被關機（非排程維護）"),
    dict(rule_name="新快照建立",          category="snapshot", enabled=True,  severity="warn", threshold_value=None, threshold_unit=None,       notify_immediate=False, description="任一 VM 出現新快照"),
    dict(rule_name="快照超過 7 天",       category="snapshot", enabled=True,  severity="err",  threshold_value=7,   threshold_unit="天",        notify_immediate=True,  description="快照存在超過 7 天（SQL Server VM 即違規）"),
    dict(rule_name="CPU 使用率過高",      category="resource", enabled=True,  severity="err",  threshold_value=85,  threshold_unit="%",         notify_immediate=True,  description="VM CPU 持續超過 85%"),
    dict(rule_name="記憶體壓力警告",      category="resource", enabled=True,  severity="warn", threshold_value=70,  threshold_unit="%",         notify_immediate=False, description="VM 記憶體壓力超過 70%"),
    dict(rule_name="備份失敗通知",        category="backup",   enabled=True,  severity="err",  threshold_value=None, threshold_unit=None,       notify_immediate=True,  description="Veeam 備份 Job 失敗立即通知"),
    dict(rule_name="複寫延遲超過 RPO",    category="backup",   enabled=True,  severity="err",  threshold_value=None, threshold_unit=None,       notify_immediate=True,  description="VM 複寫延遲超過設定 RPO 門檻"),
]


def _seed_rules(db: Session):
    if db.query(AlertRule).count() == 0:
        for r in _DEFAULT_RULES:
            db.add(AlertRule(**r, updated_at=datetime.utcnow()))
        db.commit()


@router.get("", response_model=list[AlertRuleItem])
def get_alert_rules(db: Session = Depends(get_db)):
    _seed_rules(db)
    rules = db.query(AlertRule).order_by(AlertRule.category, AlertRule.id).all()
    return [AlertRuleItem(
        id=r.id, rule_name=r.rule_name, category=r.category,
        enabled=r.enabled, severity=r.severity,
        threshold_value=r.threshold_value, threshold_unit=r.threshold_unit,
        notify_immediate=r.notify_immediate, description=r.description,
    ) for r in rules]


@router.patch("/{rule_id}", response_model=AlertRuleItem)
def update_alert_rule(
    rule_id: int = Path(...),
    body: AlertRuleUpdate = ...,
    db: Session = Depends(get_db),
):
    rule = db.get(AlertRule, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    if body.enabled is not None:
        rule.enabled = body.enabled
    if body.threshold_value is not None:
        rule.threshold_value = body.threshold_value
    if body.notify_immediate is not None:
        rule.notify_immediate = body.notify_immediate
    rule.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(rule)
    return AlertRuleItem(
        id=rule.id, rule_name=rule.rule_name, category=rule.category,
        enabled=rule.enabled, severity=rule.severity,
        threshold_value=rule.threshold_value, threshold_unit=rule.threshold_unit,
        notify_immediate=rule.notify_immediate, description=rule.description,
    )

from datetime import datetime
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
from schemas import OverviewResponse, ActionItem, SectionCard

router = APIRouter(prefix="/api/overview", tags=["overview"])


def _mock_overview() -> OverviewResponse:
    return OverviewResponse(
        host_count=2,
        vm_count=8,
        alert_count=6,
        snapshot_violation_count=8,
        health_pct=52,
        last_updated=datetime.utcnow(),
        section_cards=[
            SectionCard(
                id="resources", title="資源監控", status="warn",
                summary="2 台主機正常",
                detail="1 台 VM CPU > 90%・1 台記憶體接近門檻",
                counts=[{"label": "實體主機", "v": 2, "k": "ok"}, {"label": "警告 VM", "v": 2, "k": "warn"}],
            ),
            SectionCard(
                id="snapshots", title="快照合規", status="err",
                summary="合規率 0 / 8",
                detail="8 台 VM 皆有快照，最舊已 397 天",
                counts=[{"label": "違規", "v": 8, "k": "err"}, {"label": "合規", "v": 0, "k": "ok"}],
            ),
            SectionCard(
                id="backup", title="備份 / HA", status="err",
                summary="備份成功率 90%",
                detail="1 台備份失敗・1 台複寫中斷 3hr",
                counts=[{"label": "備份失敗", "v": 1, "k": "err"}, {"label": "複寫中斷", "v": 1, "k": "err"}],
            ),
            SectionCard(
                id="security", title="資安監控", status="err",
                summary="今日 3 件異常",
                detail="暴力破解偵測・帳號鎖定・群組異動",
                counts=[{"label": "嚴重", "v": 3, "k": "err"}, {"label": "警告", "v": 1, "k": "warn"}],
            ),
        ],
        action_items=[
            ActionItem(severity="err", source="KHTWXDB", message="CPU 持續 >90%，建議擴增 vCPU（目前 4 核）"),
            ActionItem(severity="err", source="全部 VM（8台）", message="快照未清理，合規率 0/8，需排定維護視窗"),
            ActionItem(severity="err", source="KHTWIOTPWR", message="備份連續失敗，上次備份昨日 02:00，RPO 超標"),
            ActionItem(severity="err", source="KHTWIOTPWR", message="複寫中斷 3 小時，DR 站點同步異常"),
            ActionItem(severity="warn", source="KHTWIOTPWR", message="記憶體壓力 79%，接近門檻 80%"),
            ActionItem(severity="err", source="KHTWXDB", message="今日 03:42 偵測到連續登入失敗 × 8（暴力破解）"),
        ],
    )


@router.get("", response_model=OverviewResponse)
def get_overview(db: Session = Depends(get_db)):
    # TODO: 從 DB 彙整真實資料後回傳；目前回傳 mock
    return _mock_overview()

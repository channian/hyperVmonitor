"""Collector 共用工具函式。"""
import re
from datetime import datetime


def parse_ps_datetime(s: str | None) -> datetime | None:
    """
    解析 PowerShell ToString('o') 輸出的 datetime 字串。

    .NET 'o' 格式含 7 位小數秒：2021-10-15T14:30:45.1234567+00:00
    Python 3.10 fromisoformat 最多支援 6 位，多餘位數直接截斷。
    回傳不含 tzinfo 的 UTC datetime（SQLite 儲存用）。
    """
    if not s:
        return None
    # 截斷超過 6 位的小數秒（7 位 → 6 位）
    s = re.sub(r"(\.\d{6})\d+", r"\1", s)
    return datetime.fromisoformat(s.replace("Z", "+00:00")).replace(tzinfo=None)

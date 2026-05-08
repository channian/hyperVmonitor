import os
import shutil
import logging

logger = logging.getLogger("backup_sys")


def run_backup(source_dir: str, rules: list[dict]) -> list[str]:
    """
    掃描 source_dir 最上層，依 rules 比對關鍵字後搬移檔案。
    rules 格式: [{"keyword": "報表", "dest": "D:\\Backup\\報表"}, ...]
    回傳本次執行的訊息清單（供 GUI 顯示）。
    """
    messages = []

    def log(level: str, msg: str):
        messages.append(msg)
        getattr(logger, level)(msg)

    if not os.path.isdir(source_dir):
        log("warning", f"來源資料夾不存在或無效：{source_dir}")
        return messages

    try:
        entries = list(os.scandir(source_dir))
    except PermissionError as e:
        log("error", f"無法讀取來源資料夾：{e}")
        return messages

    for entry in entries:
        if not entry.is_file():
            continue

        filename = entry.name
        matched_rule = None
        for rule in rules:
            keyword = rule.get("keyword", "").strip()
            if keyword and keyword in filename:
                matched_rule = rule
                break

        if matched_rule is None:
            continue

        dest_dir = matched_rule.get("dest", "").strip()
        if not dest_dir:
            log("warning", f"規則關鍵字「{matched_rule['keyword']}」的目標路徑為空，略過 {filename}")
            continue

        try:
            os.makedirs(dest_dir, exist_ok=True)
        except OSError as e:
            log("error", f"無法建立目標資料夾 {dest_dir}：{e}")
            continue

        dest_path = os.path.join(dest_dir, filename)
        if os.path.exists(dest_path):
            log("warning", f"目標已存在，略過：{dest_path}")
            continue

        try:
            shutil.move(entry.path, dest_path)
            log("info", f"已搬移：{filename} → {dest_dir}")
        except (OSError, PermissionError, shutil.Error) as e:
            log("error", f"搬移失敗 {filename}：{e}")

    if not messages:
        msg = "掃描完成，無符合條件的檔案。"
        messages.append(msg)
        logger.info(msg)

    return messages

import configparser
import logging
import os
import threading

import customtkinter as ctk
from tkinter import filedialog
from apscheduler.schedulers.background import BackgroundScheduler
from PIL import Image
import pystray

from core import run_backup

# ── 日誌設定 ─────────────────────────────────────────────────────────────────

LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backup_sys.log")

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.FileHandler(LOG_FILE, encoding="utf-8")],
)
logger = logging.getLogger("backup_sys")

CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.ini")

# ── 全域色彩 ─────────────────────────────────────────────────────────────────

ACCENT       = "#4A9EFF"
CARD_BG      = "#1E2130"
HEADER_BG    = "#151824"
BTN_SAVE     = ("#3A3A3A", "#3A3A3A")
BTN_RUN      = ("#1A5FA8", "#1A5FA8")
BTN_RUN_HOV  = "#2272C3"
BTN_START    = "#1A7A1A"
BTN_START_H  = "#239123"
BTN_STOP     = "#8B1A1A"
BTN_STOP_H   = "#B22222"
BTN_DEL      = "#7A1A1A"
BTN_DEL_H    = "#A02020"
LOG_INFO     = "#7ec8e3"
LOG_OK       = "#5cb85c"
LOG_WARN     = "#f0a500"
LOG_ERR      = "#e05252"
LOG_DIM      = "#777788"

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

MAX_LOG_LINES = 50

_DAY_NAMES = ["一", "二", "三", "四", "五", "六", "日"]


# ── 輔助：區塊卡片 ────────────────────────────────────────────────────────────

def make_card(parent) -> ctk.CTkFrame:
    return ctk.CTkFrame(parent, fg_color=CARD_BG, corner_radius=10)


def section_header(card: ctk.CTkFrame, title: str) -> ctk.CTkFrame:
    hdr = ctk.CTkFrame(card, fg_color="transparent")
    hdr.pack(fill="x", padx=14, pady=(12, 6))

    accent_bar = ctk.CTkFrame(hdr, width=4, height=18, fg_color=ACCENT, corner_radius=2)
    accent_bar.pack(side="left", padx=(0, 8))
    accent_bar.pack_propagate(False)

    ctk.CTkLabel(hdr, text=title,
                 font=ctk.CTkFont(size=13, weight="bold"),
                 text_color=ACCENT).pack(side="left")
    return hdr


# ── 規則列元件（單條規則）────────────────────────────────────────────────────

class RuleRow(ctk.CTkFrame):
    def __init__(self, parent, on_delete, keyword="", dest=""):
        super().__init__(parent, fg_color="#252840", corner_radius=6)

        self.keyword_var = ctk.StringVar(value=keyword)
        self.dest_var    = ctk.StringVar(value=dest)

        ctk.CTkEntry(self, textvariable=self.keyword_var,
                     placeholder_text="關鍵字", width=130,
                     border_color="#3A3D5C").pack(side="left", padx=(8, 4), pady=6)

        ctk.CTkEntry(self, textvariable=self.dest_var,
                     placeholder_text="目標資料夾路徑",
                     border_color="#3A3D5C").pack(side="left", fill="x", expand=True,
                                                  padx=(0, 4), pady=6)

        ctk.CTkButton(self, text="瀏覽", width=58, height=28,
                      fg_color="#2A4A7A", hover_color="#3A5A9A",
                      font=ctk.CTkFont(size=12),
                      command=self._browse_dest).pack(side="left", padx=(0, 4), pady=6)

        ctk.CTkButton(self, text="✕", width=30, height=28,
                      fg_color=BTN_DEL, hover_color=BTN_DEL_H,
                      font=ctk.CTkFont(size=12),
                      command=on_delete).pack(side="left", padx=(0, 8), pady=6)

    def _browse_dest(self):
        path = filedialog.askdirectory()
        if path:
            self.dest_var.set(path)

    def get(self) -> dict:
        return {"keyword": self.keyword_var.get(), "dest": self.dest_var.get()}


# ── 群組子規則列 ──────────────────────────────────────────────────────────────

class SubRuleRow(ctk.CTkFrame):
    def __init__(self, parent, on_delete, keyword="", subfolder=""):
        super().__init__(parent, fg_color="#1A1D2A", corner_radius=4)

        self.keyword_var   = ctk.StringVar(value=keyword)
        self.subfolder_var = ctk.StringVar(value=subfolder)

        ctk.CTkEntry(self, textvariable=self.keyword_var,
                     placeholder_text="關鍵字", width=130, height=28,
                     border_color="#3A3D5C").pack(side="left", padx=(8, 4), pady=4)

        ctk.CTkLabel(self, text="→", text_color="#556677",
                     font=ctk.CTkFont(size=13)).pack(side="left", padx=4)

        ctk.CTkEntry(self, textvariable=self.subfolder_var,
                     placeholder_text="子資料夾名稱", height=28,
                     border_color="#3A3D5C").pack(side="left", fill="x", expand=True,
                                                  padx=(0, 4), pady=4)

        ctk.CTkButton(self, text="✕", width=28, height=24,
                      fg_color=BTN_DEL, hover_color=BTN_DEL_H,
                      font=ctk.CTkFont(size=11),
                      command=on_delete).pack(side="left", padx=(0, 8), pady=4)

    def get(self) -> tuple[str, str]:
        return self.keyword_var.get(), self.subfolder_var.get()


# ── 規則群組元件 ──────────────────────────────────────────────────────────────

class RuleGroup(ctk.CTkFrame):
    def __init__(self, parent, on_delete, source="", base="", sub_rules=None):
        super().__init__(parent, fg_color="#1A1D2E", corner_radius=8,
                         border_width=1, border_color="#3A4060")

        self._sub_rows: list[SubRuleRow] = []

        # ── Header 標題列 ─────────────────────────────────────────────────────
        title_row = ctk.CTkFrame(self, fg_color="#252840", corner_radius=6)
        title_row.pack(fill="x", padx=6, pady=(6, 2))

        ctk.CTkLabel(title_row, text="群組", font=ctk.CTkFont(size=11, weight="bold"),
                     text_color=ACCENT, width=36).pack(side="left", padx=(8, 4), pady=6)

        ctk.CTkButton(title_row, text="✕ 刪除群組", width=90, height=28,
                      fg_color=BTN_DEL, hover_color=BTN_DEL_H,
                      font=ctk.CTkFont(size=11),
                      command=on_delete).pack(side="right", padx=(0, 6), pady=6)

        # ── 來源資料夾 ────────────────────────────────────────────────────────
        src_row = ctk.CTkFrame(self, fg_color="transparent")
        src_row.pack(fill="x", padx=8, pady=(4, 2))

        ctk.CTkLabel(src_row, text="來源：", font=ctk.CTkFont(size=11),
                     text_color="#AABBCC", width=40).pack(side="left")
        self._source_var = ctk.StringVar(value=source)
        ctk.CTkEntry(src_row, textvariable=self._source_var,
                     placeholder_text="來源資料夾路徑",
                     border_color="#3A3D5C", height=30).pack(
                         side="left", fill="x", expand=True, padx=(0, 4))
        ctk.CTkButton(src_row, text="瀏覽", width=52, height=28,
                      fg_color="#2A4A7A", hover_color="#3A5A9A",
                      font=ctk.CTkFont(size=11),
                      command=self._browse_source).pack(side="left")

        # ── 目標母資料夾 ──────────────────────────────────────────────────────
        dest_row = ctk.CTkFrame(self, fg_color="transparent")
        dest_row.pack(fill="x", padx=8, pady=(2, 4))

        ctk.CTkLabel(dest_row, text="目標：", font=ctk.CTkFont(size=11),
                     text_color="#AABBCC", width=40).pack(side="left")
        self._base_var = ctk.StringVar(value=base)
        ctk.CTkEntry(dest_row, textvariable=self._base_var,
                     placeholder_text="目標母資料夾路徑（子規則填子資料夾名稱）",
                     border_color="#3A3D5C", height=30).pack(
                         side="left", fill="x", expand=True, padx=(0, 4))
        ctk.CTkButton(dest_row, text="瀏覽", width=52, height=28,
                      fg_color="#2A4A7A", hover_color="#3A5A9A",
                      font=ctk.CTkFont(size=11),
                      command=self._browse_base).pack(side="left")

        # ── 欄位標題 ─────────────────────────────────────────────────────────
        col_hdr = ctk.CTkFrame(self, fg_color="transparent")
        col_hdr.pack(fill="x", padx=14, pady=(2, 0))
        ctk.CTkLabel(col_hdr, text="關鍵字", font=ctk.CTkFont(size=10),
                     text_color="#8899AA", width=138, anchor="w").pack(side="left")
        ctk.CTkLabel(col_hdr, text="子資料夾名稱", font=ctk.CTkFont(size=10),
                     text_color="#8899AA", anchor="w").pack(side="left", padx=(20, 0))

        # ── 子規則列表 ───────────────────────────────────────────────────────
        self._sub_frame = ctk.CTkFrame(self, fg_color="transparent")
        self._sub_frame.pack(fill="x", padx=6, pady=(0, 2))

        if sub_rules:
            for kw, sub in sub_rules:
                self._add_sub_row(kw, sub)

        # ── 新增子規則按鈕 ───────────────────────────────────────────────────
        ctk.CTkButton(self, text="＋ 新增子規則", width=110, height=26,
                      fg_color="#2A3A50", hover_color="#3A4A60",
                      font=ctk.CTkFont(size=11),
                      command=lambda: self._add_sub_row()).pack(
                          anchor="w", padx=14, pady=(2, 8))

    def _browse_source(self):
        path = filedialog.askdirectory()
        if path:
            self._source_var.set(path)

    def _browse_base(self):
        path = filedialog.askdirectory()
        if path:
            self._base_var.set(path)

    def _add_sub_row(self, keyword="", subfolder=""):
        row = SubRuleRow(self._sub_frame,
                         on_delete=lambda r=None: self._delete_sub(row),
                         keyword=keyword, subfolder=subfolder)
        row.pack(fill="x", pady=2)
        self._sub_rows.append(row)

    def _delete_sub(self, row: SubRuleRow):
        row.pack_forget()
        row.destroy()
        self._sub_rows.remove(row)

    def get_rules(self) -> list[dict]:
        base = self._base_var.get().strip()
        rules = []
        for r in self._sub_rows:
            kw, sub = r.get()
            dest = os.path.join(base, sub.strip()) if sub.strip() else base
            rules.append({"keyword": kw, "dest": dest})
        return rules


# ── 主應用程式 ────────────────────────────────────────────────────────────────

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("檔案自動備份系統")
        self.geometry("800x800")
        self.minsize(700, 640)
        self.resizable(True, True)
        self.configure(fg_color=HEADER_BG)

        self._rule_rows: list[RuleRow]   = []
        self._rule_groups: list[RuleGroup] = []
        self._scheduler = BackgroundScheduler()
        self._scheduler_running = False
        self._tray_icon = None
        self._tags_ready = False

        self._build_ui()
        self._load_config()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ── UI 建構 ───────────────────────────────────────────────────────────────

    def _build_ui(self):
        self._build_header()

        scroll_root = ctk.CTkScrollableFrame(self, fg_color=HEADER_BG,
                                             scrollbar_button_color="#3A3D5C")
        scroll_root.pack(fill="both", expand=True, padx=0, pady=0)

        P = {"fill": "x", "padx": 16, "pady": 6}

        self._build_source_section(scroll_root, P)
        self._build_rules_section(scroll_root, P)
        self._build_schedule_section(scroll_root, P)
        self._build_action_bar(scroll_root, P)
        self._build_log_section(scroll_root, P)

    def _build_header(self):
        hdr = ctk.CTkFrame(self, fg_color="#0D1120", height=56, corner_radius=0)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)

        ctk.CTkLabel(hdr, text="  檔案自動備份系統",
                     font=ctk.CTkFont(size=18, weight="bold"),
                     text_color="#FFFFFF").pack(side="left", padx=16)

        self._status_dot = ctk.CTkLabel(hdr, text="●", font=ctk.CTkFont(size=14),
                                         text_color="#555566")
        self._status_dot.pack(side="right", padx=(0, 4))
        self._status_lbl = ctk.CTkLabel(hdr, text="排程未啟動",
                                         font=ctk.CTkFont(size=12),
                                         text_color="#777788")
        self._status_lbl.pack(side="right", padx=(0, 2))

    # ── 來源資料夾 ────────────────────────────────────────────────────────────

    def _build_source_section(self, parent, P):
        card = make_card(parent)
        card.pack(**P)

        section_header(card, "來源資料夾")

        row = ctk.CTkFrame(card, fg_color="transparent")
        row.pack(fill="x", padx=14, pady=(0, 12))

        self._source_var = ctk.StringVar()
        ctk.CTkEntry(row, textvariable=self._source_var,
                     placeholder_text="選擇或輸入要監控的資料夾路徑",
                     height=36, border_color="#3A3D5C").pack(side="left", fill="x",
                                                              expand=True, padx=(0, 8))
        ctk.CTkButton(row, text="瀏覽資料夾", width=100, height=36,
                      fg_color="#2A4A7A", hover_color="#3A5A9A",
                      command=self._browse_source).pack(side="left")

    # ── 分類規則 ──────────────────────────────────────────────────────────────

    def _build_rules_section(self, parent, P):
        card = make_card(parent)
        card.pack(**P)

        hdr = section_header(card, "分類規則")
        ctk.CTkButton(hdr, text="＋  新增群組", width=110, height=28,
                      fg_color="#2A4A50", hover_color="#3A5A60",
                      font=ctk.CTkFont(size=12),
                      command=self._add_rule_group).pack(side="right", padx=(0, 6))
        ctk.CTkButton(hdr, text="＋  新增規則", width=110, height=28,
                      fg_color="#1A5FA8", hover_color=BTN_RUN_HOV,
                      font=ctk.CTkFont(size=12),
                      command=self._add_rule_row).pack(side="right")

        self._rules_scroll = ctk.CTkScrollableFrame(card, height=200,
                                                     fg_color="#181B2A",
                                                     corner_radius=6,
                                                     scrollbar_button_color="#3A3D5C")
        self._rules_scroll.pack(fill="x", padx=14, pady=(0, 12))

        self._empty_lbl = ctk.CTkLabel(
            self._rules_scroll,
            text="尚未新增任何規則，點擊「＋ 新增規則」或「＋ 新增群組」開始設定",
            text_color="#555566",
            font=ctk.CTkFont(size=12))
        self._empty_lbl.pack(pady=30)

    # ── 排程設定 ──────────────────────────────────────────────────────────────

    def _build_schedule_section(self, parent, P):
        card = make_card(parent)
        card.pack(**P)

        section_header(card, "排程設定")

        self._mode_var = ctk.StringVar(value="interval")

        # 第一列：每隔 / 每天
        row1 = ctk.CTkFrame(card, fg_color="transparent")
        row1.pack(fill="x", padx=14, pady=(0, 6))

        ctk.CTkRadioButton(row1, text="每隔",
                           variable=self._mode_var, value="interval",
                           command=self._on_mode_change,
                           radiobutton_width=16, radiobutton_height=16).pack(side="left")
        self._interval_var   = ctk.StringVar(value="2")
        self._interval_entry = ctk.CTkEntry(row1, textvariable=self._interval_var,
                                             width=52, height=32, border_color="#3A3D5C",
                                             justify="center")
        self._interval_entry.pack(side="left", padx=6)
        ctk.CTkLabel(row1, text="小時執行一次", text_color="#AABBCC").pack(side="left")

        ctk.CTkFrame(row1, width=1, height=24, fg_color="#3A3D5C").pack(side="left", padx=20)

        ctk.CTkRadioButton(row1, text="每天",
                           variable=self._mode_var, value="daily",
                           command=self._on_mode_change,
                           radiobutton_width=16, radiobutton_height=16).pack(side="left")
        self._daily_var   = ctk.StringVar(value="23:00")
        self._daily_entry = ctk.CTkEntry(row1, textvariable=self._daily_var,
                                          width=70, height=32, border_color="#3A3D5C",
                                          justify="center", placeholder_text="HH:MM")
        self._daily_entry.pack(side="left", padx=6)
        ctk.CTkLabel(row1, text="執行", text_color="#AABBCC").pack(side="left")

        # 第二列：每週
        row2 = ctk.CTkFrame(card, fg_color="transparent")
        row2.pack(fill="x", padx=14, pady=(0, 14))

        ctk.CTkRadioButton(row2, text="每週",
                           variable=self._mode_var, value="weekly",
                           command=self._on_mode_change,
                           radiobutton_width=16, radiobutton_height=16).pack(side="left")

        self._weekly_day_vars: list[ctk.IntVar] = [ctk.IntVar(value=0) for _ in range(7)]
        self._weekly_checkboxes: list[ctk.CTkCheckBox] = []
        for i, lbl in enumerate(_DAY_NAMES):
            cb = ctk.CTkCheckBox(row2, text=lbl,
                                 variable=self._weekly_day_vars[i],
                                 checkbox_width=16, checkbox_height=16,
                                 width=46, font=ctk.CTkFont(size=12))
            cb.pack(side="left", padx=2)
            self._weekly_checkboxes.append(cb)

        ctk.CTkFrame(row2, width=1, height=20, fg_color="#3A3D5C").pack(side="left", padx=10)

        self._weekly_time_var   = ctk.StringVar(value="23:00")
        self._weekly_time_entry = ctk.CTkEntry(row2, textvariable=self._weekly_time_var,
                                                width=70, height=32, border_color="#3A3D5C",
                                                justify="center", placeholder_text="HH:MM")
        self._weekly_time_entry.pack(side="left", padx=6)
        ctk.CTkLabel(row2, text="執行", text_color="#AABBCC").pack(side="left")

        self._on_mode_change()

    # ── 操作按鈕列 ────────────────────────────────────────────────────────────

    def _build_action_bar(self, parent, P):
        bar = ctk.CTkFrame(parent, fg_color="#111420", corner_radius=10)
        bar.pack(**P)

        inner = ctk.CTkFrame(bar, fg_color="transparent")
        inner.pack(padx=14, pady=10)

        ctk.CTkButton(inner, text="儲存設定", width=120, height=38,
                      fg_color="#2A2D40", hover_color="#363A55",
                      font=ctk.CTkFont(size=13),
                      command=self._save_config).pack(side="left", padx=(0, 10))

        ctk.CTkButton(inner, text="▶  立即執行", width=130, height=38,
                      fg_color=BTN_RUN[0], hover_color=BTN_RUN_HOV,
                      font=ctk.CTkFont(size=13, weight="bold"),
                      command=self._run_now).pack(side="left", padx=(0, 10))

        self._sched_btn = ctk.CTkButton(inner, text="啟動排程", width=130, height=38,
                                         fg_color=BTN_START, hover_color=BTN_START_H,
                                         font=ctk.CTkFont(size=13, weight="bold"),
                                         command=self._toggle_scheduler)
        self._sched_btn.pack(side="left")

    # ── 執行記錄 ──────────────────────────────────────────────────────────────

    def _build_log_section(self, parent, P):
        card = make_card(parent)
        card.pack(fill="both", expand=True, padx=16, pady=(6, 16))

        hdr = section_header(card, "執行記錄")
        ctk.CTkLabel(hdr, text=f"→ {LOG_FILE}",
                     font=ctk.CTkFont(size=10), text_color="#555566").pack(side="right")

        self._log_box = ctk.CTkTextbox(
            card, height=200,
            fg_color="#0D1018",
            border_color="#252840",
            border_width=1,
            corner_radius=6,
            font=ctk.CTkFont(family="Courier New", size=12),
            state="disabled",
        )
        self._log_box.pack(fill="both", expand=True, padx=14, pady=(0, 12))

    # ── 路徑瀏覽 ──────────────────────────────────────────────────────────────

    def _browse_source(self):
        path = filedialog.askdirectory()
        if path:
            self._source_var.set(path)

    # ── 規則管理 ──────────────────────────────────────────────────────────────

    def _is_all_empty(self) -> bool:
        return not self._rule_rows and not self._rule_groups

    def _add_rule_row(self, keyword="", dest=""):
        if hasattr(self, "_empty_lbl") and self._empty_lbl.winfo_ismapped():
            self._empty_lbl.pack_forget()

        row = RuleRow(self._rules_scroll,
                      on_delete=lambda r=None: self._delete_rule(row),
                      keyword=keyword, dest=dest)
        row.pack(fill="x", pady=3)
        self._rule_rows.append(row)

    def _delete_rule(self, row: RuleRow):
        row.pack_forget()
        row.destroy()
        self._rule_rows.remove(row)
        if self._is_all_empty():
            self._empty_lbl.pack(pady=30)

    def _add_rule_group(self, source="", base="", sub_rules=None):
        if hasattr(self, "_empty_lbl") and self._empty_lbl.winfo_ismapped():
            self._empty_lbl.pack_forget()

        group = RuleGroup(self._rules_scroll,
                          on_delete=lambda g=None: self._delete_rule_group(group),
                          source=source, base=base, sub_rules=sub_rules)
        group.pack(fill="x", pady=4)
        self._rule_groups.append(group)

    def _delete_rule_group(self, group: RuleGroup):
        group.pack_forget()
        group.destroy()
        self._rule_groups.remove(group)
        if self._is_all_empty():
            self._empty_lbl.pack(pady=30)

    def _get_rules(self) -> list[dict]:
        rules = [r.get() for r in self._rule_rows]
        for g in self._rule_groups:
            rules.extend(g.get_rules())
        return rules

    # ── 排程模式切換 ──────────────────────────────────────────────────────────

    def _on_mode_change(self):
        mode = self._mode_var.get()
        self._interval_entry.configure(state="normal" if mode == "interval" else "disabled")
        self._daily_entry.configure(state="normal"    if mode == "daily"    else "disabled")
        weekly_state = "normal" if mode == "weekly" else "disabled"
        for cb in self._weekly_checkboxes:
            cb.configure(state=weekly_state)
        self._weekly_time_entry.configure(state=weekly_state)

    # ── 設定檔 I/O ────────────────────────────────────────────────────────────

    def _save_config(self):
        cfg = configparser.ConfigParser()
        cfg["general"] = {"source_dir": self._source_var.get()}
        cfg["schedule"] = {
            "mode":           self._mode_var.get(),
            "interval_hours": self._interval_var.get(),
            "daily_time":     self._daily_var.get(),
            "weekly_days":    ",".join(
                str(i) for i, v in enumerate(self._weekly_day_vars) if v.get()),
            "weekly_time":    self._weekly_time_var.get(),
        }

        rules = [r.get() for r in self._rule_rows]
        cfg["rules"] = {"rule_count": str(len(rules))}
        for i, rule in enumerate(rules):
            cfg["rules"][f"keyword_{i}"] = rule["keyword"]
            cfg["rules"][f"dest_{i}"]    = rule["dest"]

        cfg["groups"] = {"group_count": str(len(self._rule_groups))}
        for i, group in enumerate(self._rule_groups):
            sub_rules = [r.get() for r in group._sub_rows]
            cfg["groups"][f"source_{i}"]    = group._source_var.get()
            cfg["groups"][f"base_{i}"]      = group._base_var.get()
            cfg["groups"][f"sub_count_{i}"] = str(len(sub_rules))
            for j, (kw, sub) in enumerate(sub_rules):
                cfg["groups"][f"keyword_{i}_{j}"] = kw
                cfg["groups"][f"sub_{i}_{j}"]     = sub

        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            cfg.write(f)

        self._append_log("設定已儲存。", "ok")

    def _load_config(self):
        if not os.path.exists(CONFIG_FILE):
            return

        cfg = configparser.ConfigParser()
        cfg.read(CONFIG_FILE, encoding="utf-8")

        if "general" in cfg:
            self._source_var.set(cfg["general"].get("source_dir", ""))

        if "schedule" in cfg:
            self._mode_var.set(cfg["schedule"].get("mode", "interval"))
            self._interval_var.set(cfg["schedule"].get("interval_hours", "2"))
            self._daily_var.set(cfg["schedule"].get("daily_time", "23:00"))

            weekly_days_str = cfg["schedule"].get("weekly_days", "")
            if weekly_days_str:
                selected = {int(d) for d in weekly_days_str.split(",") if d.strip()}
                for i, v in enumerate(self._weekly_day_vars):
                    v.set(1 if i in selected else 0)

            self._weekly_time_var.set(cfg["schedule"].get("weekly_time", "23:00"))
            self._on_mode_change()

        if "rules" in cfg:
            count = int(cfg["rules"].get("rule_count", "0"))
            for i in range(count):
                self._add_rule_row(
                    keyword=cfg["rules"].get(f"keyword_{i}", ""),
                    dest=cfg["rules"].get(f"dest_{i}", ""),
                )

        if "groups" in cfg:
            count = int(cfg["groups"].get("group_count", "0"))
            for i in range(count):
                source    = cfg["groups"].get(f"source_{i}", "")
                base      = cfg["groups"].get(f"base_{i}", "")
                sub_count = int(cfg["groups"].get(f"sub_count_{i}", "0"))
                sub_rules = []
                for j in range(sub_count):
                    kw  = cfg["groups"].get(f"keyword_{i}_{j}", "")
                    sub = cfg["groups"].get(f"sub_{i}_{j}", "")
                    sub_rules.append((kw, sub))
                self._add_rule_group(source=source, base=base, sub_rules=sub_rules)

    # ── 立即執行 ──────────────────────────────────────────────────────────────

    def _run_now(self):
        self._append_log("手動觸發備份...", "info")
        threading.Thread(target=self._do_backup, daemon=True).start()

    def _do_backup(self):
        all_msgs: list[str] = []

        # 獨立規則：使用全域來源資料夾
        simple_rules = [r.get() for r in self._rule_rows]
        if simple_rules:
            all_msgs += run_backup(self._source_var.get(), simple_rules)

        # 群組規則：各自使用群組來源資料夾
        for g in self._rule_groups:
            grp_rules = g.get_rules()
            if grp_rules:
                all_msgs += run_backup(g._source_var.get(), grp_rules)

        if not all_msgs:
            all_msgs = ["掃描完成，無符合條件的檔案。"]

        for msg in all_msgs:
            tag = ("ok"   if "已搬移" in msg else
                   "warn" if "略過"   in msg or "無效" in msg or "不存在" in msg else
                   "err"  if "失敗"   in msg or "無法" in msg else
                   "dim"  if "無符合" in msg else "info")
            self.after(0, self._append_log, msg, tag)

    # ── 排程 ──────────────────────────────────────────────────────────────────

    def _toggle_scheduler(self):
        if self._scheduler_running:
            self._stop_scheduler()
        else:
            self._start_scheduler()

    def _start_scheduler(self):
        self._scheduler.remove_all_jobs()
        mode = self._mode_var.get()
        try:
            if mode == "interval":
                hours = float(self._interval_var.get())
                if hours <= 0:
                    raise ValueError
                self._scheduler.add_job(self._do_backup, "interval", hours=hours)
                self._append_log(f"排程已啟動：每 {hours} 小時執行一次。", "ok")

            elif mode == "daily":
                time_str = self._daily_var.get().strip()
                h, m = map(int, time_str.split(":"))
                self._scheduler.add_job(self._do_backup, "cron", hour=h, minute=m)
                self._append_log(f"排程已啟動：每天 {time_str} 執行。", "ok")

            else:  # weekly
                selected = [i for i, v in enumerate(self._weekly_day_vars) if v.get()]
                if not selected:
                    self._append_log("請至少選擇一個星期幾。", "warn")
                    return
                time_str = self._weekly_time_var.get().strip()
                h, m = map(int, time_str.split(":"))
                days_str = ",".join(str(d) for d in selected)
                self._scheduler.add_job(self._do_backup, "cron",
                                        day_of_week=days_str, hour=h, minute=m)
                days_display = "、".join(_DAY_NAMES[d] for d in selected)
                self._append_log(f"排程已啟動：每週{days_display} {time_str} 執行。", "ok")

        except (ValueError, TypeError):
            self._append_log("排程設定無效，請確認時間格式。", "warn")
            return

        if not self._scheduler.running:
            self._scheduler.start()

        self._scheduler_running = True
        self._sched_btn.configure(text="停止排程",
                                   fg_color=BTN_STOP, hover_color=BTN_STOP_H)
        self._status_dot.configure(text_color="#2EC82E")
        self._status_lbl.configure(text="排程運行中", text_color="#2EC82E")

    def _stop_scheduler(self):
        self._scheduler.remove_all_jobs()
        self._scheduler_running = False
        self._sched_btn.configure(text="啟動排程",
                                   fg_color=BTN_START, hover_color=BTN_START_H)
        self._status_dot.configure(text_color="#555566")
        self._status_lbl.configure(text="排程未啟動", text_color="#777788")
        self._append_log("排程已停止。", "warn")

    # ── Log UI ────────────────────────────────────────────────────────────────

    def _ensure_log_tags(self):
        if self._tags_ready:
            return
        tb = self._log_box._textbox
        tb.tag_configure("info", foreground=LOG_INFO)
        tb.tag_configure("ok",   foreground=LOG_OK)
        tb.tag_configure("warn", foreground=LOG_WARN)
        tb.tag_configure("err",  foreground=LOG_ERR)
        tb.tag_configure("dim",  foreground=LOG_DIM)
        self._tags_ready = True

    def _append_log(self, msg: str, tag: str = "info"):
        self._ensure_log_tags()
        tb = self._log_box._textbox

        self._log_box.configure(state="normal")
        tb.insert("end", msg + "\n", tag)

        lines = self._log_box.get("1.0", "end").splitlines()
        if len(lines) > MAX_LOG_LINES:
            self._log_box.delete("1.0", f"{len(lines) - MAX_LOG_LINES + 1}.0")

        self._log_box.configure(state="disabled")
        self._log_box.see("end")

    # ── 系統匣 ────────────────────────────────────────────────────────────────

    def _on_close(self):
        self.withdraw()
        if self._tray_icon is None:
            self._start_tray()

    def _start_tray(self):
        img  = Image.new("RGB", (64, 64), color=(26, 95, 168))
        menu = pystray.Menu(
            pystray.MenuItem("顯示視窗", self._show_window, default=True),
            pystray.MenuItem("結束程式", self._quit_app),
        )
        self._tray_icon = pystray.Icon("backup_sys", img, "檔案備份系統", menu)
        threading.Thread(target=self._tray_icon.run, daemon=True).start()

    def _show_window(self, icon=None, item=None):
        self.after(0, self.deiconify)
        self.after(0, self.lift)

    def _quit_app(self, icon=None, item=None):
        if self._tray_icon:
            self._tray_icon.stop()
        if self._scheduler.running:
            self._scheduler.shutdown(wait=False)
        self.after(0, self.destroy)


# ── 進入點 ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app = App()
    app.mainloop()

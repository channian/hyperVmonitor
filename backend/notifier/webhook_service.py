import json
import re
import logging
from datetime import datetime

import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

log = logging.getLogger(__name__)


class WebhookService:
    """
    Webhook 推播服務。
    - 支援 {{$variable}} 模板替換（變數名可含底線）
    - Token 由 BodyTemplate 控制（用 {{$token}} 引用）
    - 預設直連模式（不走 Proxy），適用於公司內網 API
    """

    def __init__(
        self,
        url: str,
        token: str,
        body_template: str,
        enable: bool = True,
        timeout: int = 10,
        verify_ssl: bool = False,
        use_proxy: bool = False,
        proxy_url: str | None = None,
    ):
        self.url = url
        self.token = token
        self.body_template = body_template
        self.enable = enable
        self.timeout = timeout
        self.verify_ssl = verify_ssl

        if use_proxy and proxy_url:
            self.proxies = {"http": proxy_url, "https": proxy_url}
        elif use_proxy:
            self.proxies = None  # 系統預設 Proxy
        else:
            self.proxies = {"http": None, "https": None}  # 強制直連

    # ── 公開方法 ──────────────────────────────────────────────

    def send(
        self,
        variables: dict,
        device_name: str = "",
        server_name: str = "",
        is_recovery: bool = False,
    ) -> bool:
        """發送 Webhook 推播，回傳是否成功。"""
        if not self.enable or not self.url:
            return False

        variables = {**variables, "token": self.token}
        body_str = self._render_template(self.body_template, variables)

        try:
            post_data = json.loads(body_str)
        except json.JSONDecodeError as e:
            log.warning("Webhook Body 模板解析失敗：%s\n內容：%s", e, body_str[:300])
            return False

        raw_body = json.dumps(post_data, ensure_ascii=False)
        headers = {"Content-Type": "application/json; charset=utf-8"}

        log.info("Webhook 送出 → %s | Body: %s", self.url, raw_body[:300])

        try:
            resp = requests.post(
                self.url,
                data=raw_body.encode("utf-8"),
                headers=headers,
                verify=self.verify_ssl,
                proxies=self.proxies,
                timeout=(5, self.timeout),
            )
            is_success = 200 <= resp.status_code < 300

            # 部分 API 回 HTTP 200 但 body status=false 視為失敗
            if is_success:
                try:
                    body_json = resp.json()
                    if isinstance(body_json, dict) and body_json.get("status") is False:
                        is_success = False
                except (ValueError, KeyError):
                    pass

            log_fn = log.info if is_success else log.warning
            log_fn("Webhook 回應 ← %s HTTP %s | %s", device_name, resp.status_code, resp.text[:200])
            return is_success

        except requests.exceptions.ConnectTimeout:
            log.warning("Webhook 連線逾時：%s - %s", device_name, self.url)
        except requests.exceptions.ReadTimeout:
            log.warning("Webhook 讀取逾時：%s - %s", device_name, self.url)
        except requests.exceptions.ConnectionError as e:
            log.warning("Webhook 連線失敗：%s - %s", device_name, e)
        except Exception as e:
            log.warning("Webhook 推播錯誤：%s - %s", device_name, e)

        return False

    def build_variables(
        self,
        title: str,
        severity: str,
        source: str,
        message: str,
        is_recovery: bool = False,
    ) -> dict:
        """建立 HVM 標準模板變數。"""
        status = "復歸" if is_recovery else ("嚴重" if severity == "err" else "警告")
        return {
            "title": title,
            "severity": severity,
            "status": status,
            "source": source,
            "message": message,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "is_recovery": str(is_recovery).lower(),
        }

    def test_send(self) -> tuple[bool, str]:
        """送一筆測試訊息，回傳 (success, detail)。"""
        variables = self.build_variables(
            title="測試推播",
            severity="warn",
            source="HVM 測試",
            message="這是一則來自 Hyper-V Monitor 的測試推播訊息",
        )
        variables["token"] = self.token
        body_str = self._render_template(self.body_template, variables)

        try:
            post_data = json.loads(body_str)
        except json.JSONDecodeError as e:
            return False, f"Body 模板解析失敗：{e}\n原始內容：{body_str[:300]}"

        raw_body = json.dumps(post_data, ensure_ascii=False)
        headers = {"Content-Type": "application/json; charset=utf-8"}
        detail_lines = [
            f"URL: {self.url}",
            f"Body: {raw_body}",
            f"verify_ssl: {self.verify_ssl}",
            f"proxies: {self.proxies}",
            "",
        ]

        try:
            resp = requests.post(
                self.url,
                data=raw_body.encode("utf-8"),
                headers=headers,
                verify=self.verify_ssl,
                proxies=self.proxies,
                timeout=(5, self.timeout),
            )
            detail_lines += [
                f"HTTP {resp.status_code}",
                f"Response: {resp.text[:500]}",
            ]
            ok = 200 <= resp.status_code < 300
            return ok, "\n".join(detail_lines)
        except Exception as e:
            detail_lines.append(f"Exception: {type(e).__name__}: {e}")
            return False, "\n".join(detail_lines)

    # ── 內部方法 ──────────────────────────────────────────────

    @staticmethod
    def _render_template(template: str, variables: dict) -> str:
        """替換 {{$variable}} 或 {{$_variable}} 為對應值，並跳脫 JSON 特殊字元。"""
        def replacer(match: re.Match) -> str:
            value = str(variables.get(match.group(1), ""))
            return (
                value
                .replace("\\", "\\\\")
                .replace('"', '\\"')
                .replace("\n", "\\n")
                .replace("\r", "\\r")
                .replace("\t", "\\t")
            )
        return re.sub(r"\{\{\$(_?\w+)\}\}", replacer, template)

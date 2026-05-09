"""WinRM 連線封裝，處理 cp950 編碼與錯誤重試。"""
import winrm
from winrm.exceptions import WinRMError


class WinRMClient:
    def __init__(self, host: str, username: str, password: str, port: int = 5985):
        self.host = host
        self.session = winrm.Session(
            f"http://{host}:{port}/wsman",
            auth=(username, password),
            transport="ntlm",
        )

    def run_ps(self, script: str) -> str:
        """執行 PowerShell 指令，回傳 stdout 字串（cp950 解碼）。"""
        result = self.session.run_ps(script)
        if result.status_code != 0:
            stderr = result.std_err.decode("cp950", errors="replace").strip()
            raise WinRMError(f"PowerShell 執行失敗 [{self.host}]: {stderr}")
        return result.std_out.decode("cp950", errors="replace")

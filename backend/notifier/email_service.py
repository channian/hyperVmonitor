import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

log = logging.getLogger(__name__)


class EmailService:
    def __init__(self, smtp_server: str, smtp_port: int,
                 sender_email: str, sender_name: str = "Hyper-V Monitor"):
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.sender_email = sender_email
        self.sender_name = sender_name

    def send_alert_email(
        self,
        to_addresses: str | list[str],
        subject: str,
        html_body: str,
        cc_addresses: str | list[str] | None = None,
    ) -> bool:
        """發送告警郵件，支援多收件人與副本。"""
        try:
            message = MIMEMultipart("alternative")
            message["From"] = f"{self.sender_name} <{self.sender_email}>"

            if isinstance(to_addresses, str):
                message["To"] = to_addresses
                to_list = [to_addresses]
            else:
                message["To"] = ", ".join(to_addresses)
                to_list = list(to_addresses)

            cc_list: list[str] = []
            if cc_addresses:
                if isinstance(cc_addresses, str):
                    message["Cc"] = cc_addresses
                    cc_list = [cc_addresses]
                else:
                    message["Cc"] = ", ".join(cc_addresses)
                    cc_list = list(cc_addresses)

            message["Subject"] = subject
            message.attach(MIMEText(html_body, "html", "utf-8"))

            with smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=30) as server:
                server.sendmail(
                    self.sender_email,
                    to_list + cc_list,
                    message.as_string(),
                )

            log.info("郵件發送成功：%s → %s", subject, to_list)
            return True

        except Exception as e:
            log.error("郵件發送失敗：%s", e)
            return False

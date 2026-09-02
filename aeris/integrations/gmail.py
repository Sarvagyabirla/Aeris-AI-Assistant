from __future__ import annotations

import base64
import json
from email.message import EmailMessage
from email.utils import parseaddr
from pathlib import Path
from typing import Any

from ..models import ActionResult

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
]


class GmailClient:
    def __init__(self, credentials_file: Path, keyring_service: str = "Aeris-Gmail"):
        self.credentials_file = credentials_file
        self.keyring_service = keyring_service
        self.keyring_user = "oauth-token"
        self._gmail: Any = None

    def _service(self) -> Any:
        if self._gmail is not None:
            return self._gmail
        try:
            import keyring
            from google.auth.transport.requests import Request
            from google.oauth2.credentials import Credentials
            from google_auth_oauthlib.flow import InstalledAppFlow
            from googleapiclient.discovery import build
        except ImportError as exc:
            raise RuntimeError("Install Aeris with the gmail extra first.") from exc

        credentials = None
        stored = keyring.get_password(self.keyring_service, self.keyring_user)
        if stored:
            credentials = Credentials.from_authorized_user_info(json.loads(stored), SCOPES)
        if credentials and credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
        if not credentials or not credentials.valid:
            if not self.credentials_file.exists():
                raise RuntimeError(
                    f"Gmail OAuth file not found: {self.credentials_file}. See docs/GMAIL_SETUP.md."
                )
            flow = InstalledAppFlow.from_client_secrets_file(str(self.credentials_file), SCOPES)
            credentials = flow.run_local_server(port=0)
        keyring.set_password(self.keyring_service, self.keyring_user, credentials.to_json())
        self._gmail = build("gmail", "v1", credentials=credentials, cache_discovery=False)
        return self._gmail

    @staticmethod
    def _headers(payload: dict[str, Any]) -> dict[str, str]:
        return {item.get("name", "").lower(): item.get("value", "") for item in payload.get("headers", [])}

    def list_recent(self, arguments: dict[str, object]) -> ActionResult:
        count = max(1, min(int(arguments.get("count", 5)), 20))
        service = self._service()
        listing = service.users().messages().list(userId="me", maxResults=count).execute()
        summaries = []
        for item in listing.get("messages", []):
            message = (
                service.users()
                .messages()
                .get(
                    userId="me", id=item["id"], format="metadata", metadataHeaders=["From", "Subject", "Date"]
                )
                .execute()
            )
            headers = self._headers(message.get("payload", {}))
            summaries.append(
                {
                    "id": item["id"],
                    "from": headers.get("from", ""),
                    "subject": headers.get("subject", "(no subject)"),
                    "date": headers.get("date", ""),
                    "snippet": message.get("snippet", ""),
                }
            )
        return ActionResult(True, f"Loaded {len(summaries)} recent emails.", data={"emails": summaries})

    def read_latest(self, arguments: dict[str, object]) -> ActionResult:
        result = self.list_recent({"count": 1})
        if not result.success or not result.data.get("emails"):
            return ActionResult(False, "No recent email was found.", error="email_not_found")
        return ActionResult(True, "Loaded the latest email.", data={"email": result.data["emails"][0]})

    def send_email(self, arguments: dict[str, object]) -> ActionResult:
        recipient = str(arguments["to"]).strip()
        subject = str(arguments["subject"]).strip()
        body = str(arguments["body"])
        _, address = parseaddr(recipient)
        if not address or "@" not in address:
            return ActionResult(
                False, "A valid recipient email address is required.", error="invalid_recipient"
            )
        message = EmailMessage()
        message["To"] = address
        message["Subject"] = subject
        message.set_content(body)
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode("ascii")
        sent = self._service().users().messages().send(userId="me", body={"raw": raw}).execute()
        message_id = sent.get("id")
        if not message_id:
            return ActionResult(False, "Gmail did not return a message ID.", error="send_unverified")
        return ActionResult(True, f"Email sent to {address}.", data={"message_id": message_id, "to": address})

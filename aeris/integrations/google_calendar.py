from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..models import ActionResult

SCOPES = [
    "https://www.googleapis.com/auth/calendar.readonly",
]


class GoogleCalendarClient:
    def __init__(self, credentials_file: Path, keyring_service: str = "Aeris-Calendar"):
        self.credentials_file = credentials_file
        self.keyring_service = keyring_service
        self.keyring_user = "oauth-token"
        self._calendar: Any = None

    def _service(self) -> Any:
        if self._calendar is not None:
            return self._calendar
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
                    f"Google OAuth file not found: {self.credentials_file}. See docs/GMAIL_SETUP.md."
                )
            flow = InstalledAppFlow.from_client_secrets_file(str(self.credentials_file), SCOPES)
            credentials = flow.run_local_server(port=0)
        keyring.set_password(self.keyring_service, self.keyring_user, credentials.to_json())
        self._calendar = build("calendar", "v3", credentials=credentials, cache_discovery=False)
        return self._calendar

    def list_events(self, arguments: dict[str, object]) -> ActionResult:
        count = max(1, min(int(arguments.get("count", 10)), 50))
        try:
            service = self._service()
            now = datetime.now(timezone.utc).isoformat()
            
            events_result = service.events().list(
                calendarId='primary', timeMin=now,
                maxResults=count, singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            summaries = []
            
            for event in events:
                start = event['start'].get('dateTime', event['start'].get('date'))
                summaries.append({
                    "id": event.get("id"),
                    "summary": event.get("summary", "(no summary)"),
                    "start": start,
                    "link": event.get("htmlLink", "")
                })
                
            return ActionResult(True, f"Loaded {len(summaries)} upcoming events.", data={"events": summaries})
        except Exception as e:
            return ActionResult(False, f"Failed to list events: {str(e)}", error="calendar_error")

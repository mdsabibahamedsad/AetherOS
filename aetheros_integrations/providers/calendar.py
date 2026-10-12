"""AetherOS Integrations — calendar engine adapters.

Google Calendar, Microsoft Outlook calendar (Graph), and CalDAV. Events,
tasks, scheduling, availability, reminders.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from urllib.parse import quote

import httpx
import requests

from aetheros_integrations.models import AuthMethod, HealthStatus, IntegrationCategory, ProviderDefinition
from aetheros_integrations.providers.base import RESTProvider, register_provider

logger = logging.getLogger(__name__)


@register_provider
class GoogleCalendarProvider(RESTProvider):
    definition = ProviderDefinition(
        key="google_calendar",
        category=IntegrationCategory.CALENDAR,
        display_name="Google Calendar",
        description="Google Calendar API: events, availability, reminders.",
        auth_method=AuthMethod.OAUTH2,
        base_url="https://www.googleapis.com/calendar/v3",
        scopes=["https://www.googleapis.com/auth/calendar"],
        capabilities=["list_events", "create_event", "availability", "reminders"],
    )

    def _calendar_id(self) -> str:
        return self.config.get("calendar_id", "primary")

    def ping(self) -> HealthStatus:
        token = self.config.get("_auth_header", {}).get("Authorization", "")
        if not token:
            return HealthStatus.UNAVAILABLE
        try:
            resp = httpx.get(f"{self.definition.base_url}/users/me/calendarList", headers=self._headers(), params={"maxResults": 1}, timeout=10)
            return HealthStatus.HEALTHY if resp.status_code == 200 else HealthStatus.UNHEALTHY
        except (httpx.HTTPError, OSError):
            return HealthStatus.DEGRADED

    def list_events(self, max_results: int = 10, time_min: str = "", time_max: str = "", **kwargs) -> List[Dict[str, Any]]:
        token = self.config.get("_auth_header", {}).get("Authorization", "")
        if not token:
            return []
        params = {"maxResults": max_results, "singleEvents": True, "orderBy": "startTime"}
        if time_min:
            params["timeMin"] = time_min
        if time_max:
            params["timeMax"] = time_max
        resp = httpx.get(f"{self.definition.base_url}/calendars/{quote(self._calendar_id())}/events", headers=self._headers(), params=params, timeout=15)
        if resp.status_code != 200:
            return []
        return resp.json().get("items", [])

    def create_event(self, summary: str, start: str, end: str, **kwargs) -> Dict[str, Any]:
        token = self.config.get("_auth_header", {}).get("Authorization", "")
        if not token:
            return {"success": False, "error": "no calendar credential"}
        body = {
            "summary": summary,
            "start": {"dateTime": start, "timeZone": self.config.get("timezone", "UTC")},
            "end": {"dateTime": end, "timeZone": self.config.get("timezone", "UTC")},
        }
        if kwargs.get("description"):
            body["description"] = kwargs["description"]
        resp = httpx.post(f"{self.definition.base_url}/calendars/{quote(self._calendar_id())}/events", headers={**self._headers(), "Content-Type": "application/json"}, json=body, timeout=15)
        return {"success": resp.status_code == 200, "status": resp.status_code, "data": resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}}

    def availability(self, time_min: str, time_max: str, **kwargs) -> List[Dict[str, Any]]:
        return self.list_events(time_min=time_min, time_max=time_max, max_results=500)


@register_provider
class OutlookCalendarProvider(RESTProvider):
    definition = ProviderDefinition(
        key="outlook_calendar",
        category=IntegrationCategory.CALENDAR,
        display_name="Microsoft Outlook Calendar",
        description="Outlook calendar via Graph API.",
        auth_method=AuthMethod.OAUTH2,
        base_url="https://graph.microsoft.com/v1.0",
        scopes=["Calendars.ReadWrite"],
        capabilities=["list_events", "create_event", "availability", "reminders"],
    )

    def ping(self) -> HealthStatus:
        token = self.config.get("_auth_header", {}).get("Authorization", "")
        if not token:
            return HealthStatus.UNAVAILABLE
        return HealthStatus.HEALTHY if token.startswith("Bearer") else HealthStatus.UNHEALTHY

    def list_events(self, max_results: int = 10, time_min: str = "", time_max: str = "", **kwargs) -> List[Dict[str, Any]]:
        token = self.config.get("_auth_header", {}).get("Authorization", "")
        if not token:
            return []
        params = {"$top": max_results, "$select": "id,subject,start,end"}
        if time_min and time_max:
            params["$filter"] = f"start/dateTime ge '{time_min}' and end/dateTime le '{time_max}'"
        resp = httpx.get(f"{self.definition.base_url}/me/events", headers=self._headers(), params=params, timeout=15)
        return resp.json().get("value", []) if resp.status_code == 200 else []

    def create_event(self, summary: str, start: str, end: str, **kwargs) -> Dict[str, Any]:
        token = self.config.get("_auth_header", {}).get("Authorization", "")
        if not token:
            return {"success": False, "error": "no calendar credential"}
        body = {"subject": summary, "start": {"dateTime": start, "timeZone": self.config.get("timezone", "UTC")}, "end": {"dateTime": end, "timeZone": self.config.get("timezone", "UTC")}}
        resp = httpx.post(f"{self.definition.base_url}/me/events", headers={**self._headers(), "Content-Type": "application/json"}, json=body, timeout=15)
        return {"success": resp.status_code in (200, 201), "status": resp.status_code}


@register_provider
class CalDAVProvider(RESTProvider):
    definition = ProviderDefinition(
        key="caldav",
        category=IntegrationCategory.CALENDAR,
        display_name="CalDAV",
        description="CalDAV calendar (Radicale, Nextcloud, iCloud, etc.).",
        auth_method=AuthMethod.BASIC,
        base_url="",
        capabilities=["list_events", "create_event"],
    )

    def _base(self) -> str:
        return self.config.get("dav_url", "")

    def _auth(self):
        return (self.config.get("dav_user", ""), self.config.get("dav_password", ""))

    def ping(self) -> HealthStatus:
        base = self._base()
        if not base:
            return HealthStatus.UNAVAILABLE
        try:
            resp = requests.request("PROPFIND", base.rstrip("/") + "/", auth=self._auth(), timeout=10)
            return HealthStatus.HEALTHY if resp.status_code in (200, 207) else HealthStatus.UNHEALTHY
        except (requests.RequestException, OSError):
            return HealthStatus.DEGRADED

    def list_events(self, calendar_path: str = "", max_results: int = 20, **kwargs) -> List[Dict[str, Any]]:
        base = self._base()
        if not base:
            return []
        target = (base.rstrip("/") + "/" + calendar_path.strip("/")) if calendar_path else base
        resp = requests.request("REPORT", target.rstrip("/") + "/", auth=self._auth(), data=REPORT_BODY, headers={"Content-Type": "application/xml; charset=utf-8", "Depth": "1"}, timeout=20)
        if resp.status_code not in (200, 207):
            return []
        events = []
        for href in _iter_hrefs(resp.text):
            events.append({"href": href, "calendar": calendar_path or "default"})
        return events[:max_results]

    def create_event(self, summary: str, start: str, end: str, **kwargs) -> Dict[str, Any]:
        base = self._base()
        if not base:
            return {"success": False, "error": "no caldav url"}
        import uuid

        calendar_path = kwargs.get("calendar_path", "")
        target = base.rstrip("/") + "/" + calendar_path.strip("/").rstrip("/") + "/" + f"{uuid.uuid4().hex}.ics" if calendar_path else base.rstrip("/") + "/" + f"{uuid.uuid4().hex}.ics"
        ics = f"BEGIN:VCALENDAR\r\nVERSION:2.0\r\nPRODID:-//AetherOS//EN\r\nBEGIN:VEVENT\r\nUID:{uuid.uuid4().hex}@aetheros\r\nSUMMARY:{summary}\r\nDTSTART:{_ical_dt(start)}\r\nDTEND:{_ical_dt(end)}\r\nEND:VEVENT\r\nEND:VCALENDAR\r\n"
        resp = requests.put(target, auth=self._auth(), data=ics.encode(), headers={"Content-Type": "text/calendar; charset=utf-8"}, timeout=15)
        return {"success": resp.status_code in (200, 201, 204), "status": resp.status_code}


REPORT_BODY = (
    "<?xml version='1.0' encoding='utf-8'?>"
    "<C:calendar-query xmlns:C='urn:ietf:params:xml:ns:caldav'>"
    "<D:prop xmlns:D='DAV:'><D:getetag/></D:prop>"
    "<C:filter><C:comp-filter name='VCALENDAR'/></C:filter>"
    "</C:calendar-query>"
)


def _iter_hrefs(xml_text: str) -> List[str]:
    import re

    return re.findall(r"<D:href[^>]*>([^<]+)</D:href>", xml_text)


def _ical_dt(value: str) -> str:
    """Convert ISO 8601 to iCal basic format (YYYYMMDDTHHMMSSZ)."""
    cleaned = value.replace("-", "").replace(":", "").replace(" ", "T")
    return cleaned[:15]

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional


@dataclass
class ContactLink:
    provider: str
    account_id: str
    username: str = ""
    display_name: str = ""
    avatar_url: str = ""
    last_interaction: Optional[datetime] = None


@dataclass
class UnifiedContact:
    id: str
    name: str
    email: str = ""
    phone: str = ""
    photo_url: str = ""
    organization: str = ""
    tags: list[str] = field(default_factory=list)
    notes: str = ""
    links: list[ContactLink] = field(default_factory=list)
    conversation_count: int = 0
    last_message_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    confidence: float = 1.0


class ContactManager:
    def __init__(self, storage_path: Optional[Path] = None):
        self._storage_path = storage_path or Path.home() / ".aetheros" / "automation" / "communications"
        self._storage_path.mkdir(parents=True, exist_ok=True)
        self._contacts: dict[str, UnifiedContact] = {}
        self._load()

    def _path(self) -> Path:
        return self._storage_path / "contacts.json"

    def _load(self):
        if self._path().exists():
            try:
                data = json.loads(self._path().read_text())
                for item in data:
                    contact = self._deserialize(item)
                    self._contacts[contact.id] = contact
            except (json.JSONDecodeError, KeyError):
                pass

    def _save(self):
        data = [self._serialize(c) for c in self._contacts.values()]
        self._path().write_text(json.dumps(data, indent=2, default=str))

    def _serialize(self, contact: UnifiedContact) -> dict:
        return {
            "id": contact.id,
            "name": contact.name,
            "email": contact.email,
            "phone": contact.phone,
            "photo_url": contact.photo_url,
            "organization": contact.organization,
            "tags": contact.tags,
            "notes": contact.notes,
            "links": [l.__dict__ for l in contact.links],
            "conversation_count": contact.conversation_count,
            "last_message_at": contact.last_message_at.isoformat() if contact.last_message_at else None,
            "created_at": contact.created_at.isoformat(),
            "updated_at": contact.updated_at.isoformat(),
            "confidence": contact.confidence,
        }

    def _deserialize(self, data: dict) -> UnifiedContact:
        links = []
        for l in data.get("links", []):
            lm = None
            if l.get("last_interaction"):
                try:
                    lm = datetime.fromisoformat(l["last_interaction"])
                except (ValueError, TypeError):
                    pass
            links.append(ContactLink(
                provider=l["provider"],
                account_id=l["account_id"],
                username=l.get("username", ""),
                display_name=l.get("display_name", ""),
                avatar_url=l.get("avatar_url", ""),
                last_interaction=lm,
            ))
        lma = None
        if data.get("last_message_at"):
            try:
                lma = datetime.fromisoformat(data["last_message_at"])
            except (ValueError, TypeError):
                pass
        return UnifiedContact(
            id=data["id"],
            name=data["name"],
            email=data.get("email", ""),
            phone=data.get("phone", ""),
            photo_url=data.get("photo_url", ""),
            organization=data.get("organization", ""),
            tags=data.get("tags", []),
            notes=data.get("notes", ""),
            links=links,
            conversation_count=data.get("conversation_count", 0),
            last_message_at=lma,
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.now(),
            updated_at=datetime.fromisoformat(data["updated_at"]) if data.get("updated_at") else datetime.now(),
            confidence=data.get("confidence", 1.0),
        )

    def add_contact(self, contact: UnifiedContact):
        self._contacts[contact.id] = contact
        self._save()

    def update_contact(self, contact_id: str, **kwargs) -> bool:
        contact = self._contacts.get(contact_id)
        if not contact:
            return False
        for key, value in kwargs.items():
            if hasattr(contact, key):
                setattr(contact, key, value)
        contact.updated_at = datetime.now()
        self._save()
        return True

    def get_contact(self, contact_id: str) -> Optional[UnifiedContact]:
        return self._contacts.get(contact_id)

    def remove_contact(self, contact_id: str) -> bool:
        if contact_id in self._contacts:
            del self._contacts[contact_id]
            self._save()
            return True
        return False

    def list_contacts(self) -> list[UnifiedContact]:
        return sorted(self._contacts.values(), key=lambda c: c.name.lower())

    def search_contacts(self, query: str) -> list[UnifiedContact]:
        pattern = re.compile(re.escape(query), re.IGNORECASE)
        return [c for c in self._contacts.values() if
                pattern.search(c.name) or pattern.search(c.email) or
                pattern.search(c.phone) or pattern.search(c.organization) or
                any(pattern.search(l.username) for l in c.links)]

    def find_by_provider_account(self, provider: str, account_id: str) -> Optional[UnifiedContact]:
        for contact in self._contacts.values():
            for link in contact.links:
                if link.provider == provider and link.account_id == account_id:
                    return contact
        return None

    def add_link_to_contact(self, contact_id: str, link: ContactLink) -> bool:
        contact = self._contacts.get(contact_id)
        if not contact:
            return False
        for existing in contact.links:
            if existing.provider == link.provider and existing.account_id == link.account_id:
                existing.username = link.username or existing.username
                existing.display_name = link.display_name or existing.display_name
                existing.avatar_url = link.avatar_url or existing.avatar_url
                existing.last_interaction = link.last_interaction or existing.last_interaction
                contact.updated_at = datetime.now()
                self._save()
                return True
        contact.links.append(link)
        contact.updated_at = datetime.now()
        self._save()
        return True

    def merge_contacts(self, target_id: str, source_id: str) -> Optional[UnifiedContact]:
        target = self._contacts.get(target_id)
        source = self._contacts.get(source_id)
        if not target or not source:
            return None
        target.links.extend(source.links)
        target.conversation_count += source.conversation_count
        if not target.email and source.email:
            target.email = source.email
        if not target.phone and source.phone:
            target.phone = source.phone
        if not target.photo_url and source.photo_url:
            target.photo_url = source.photo_url
        target.tags = list(set(target.tags + source.tags))
        if source.notes and source.notes not in target.notes:
            target.notes = f"{target.notes}\n{source.notes}".strip()
        target.confidence = min(1.0, target.confidence + source.confidence * 0.1)
        target.updated_at = datetime.now()
        del self._contacts[source_id]
        self._save()
        return target

    def get_contacts_by_tag(self, tag: str) -> list[UnifiedContact]:
        return [c for c in self._contacts.values() if tag in c.tags]

    def get_contacts_by_provider(self, provider: str) -> list[UnifiedContact]:
        return [c for c in self._contacts.values() if any(l.provider == provider for l in c.links)]

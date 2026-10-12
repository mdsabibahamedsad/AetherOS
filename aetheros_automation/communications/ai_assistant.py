from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional


class ReplyStyle(Enum):
    PROFESSIONAL = "professional"
    CASUAL = "casual"
    FRIENDLY = "friendly"
    SHORT = "short"
    DETAILED = "detailed"
    CUSTOM = "custom"


@dataclass
class DraftResult:
    content: str
    style: ReplyStyle
    tone_notes: str = ""
    translation_from: str = ""
    translation_to: str = ""
    requires_approval: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ConversationSummary:
    summary: str
    key_points: list[str] = field(default_factory=list)
    action_items: list[str] = field(default_factory=list)
    sentiment: str = "neutral"
    participants: list[str] = field(default_factory=list)
    message_count: int = 0
    duration_minutes: int = 0
    thread_url: str = ""


@dataclass
class AssistantContext:
    provider: str
    conversation_id: str
    messages: list[dict] = field(default_factory=list)
    contact_name: str = ""
    contact_info: str = ""


class CommsAIAssistant:
    def __init__(self):
        self._draft_history: list[dict] = []
        self._summary_cache: dict[str, ConversationSummary] = {}

    def generate_draft(self, context: AssistantContext, style: ReplyStyle = ReplyStyle.PROFESSIONAL, custom_instructions: str = "", language: str = "") -> DraftResult:
        last_message = context.messages[-1] if context.messages else {}
        content = last_message.get("content", "")
        sender = last_message.get("sender_name", context.contact_name)

        tone_notes = self._get_tone_notes(style, custom_instructions)
        draft = self._build_draft(content, sender, style, custom_instructions)

        result = DraftResult(
            content=draft,
            style=style,
            tone_notes=tone_notes,
            requires_approval=True,
        )
        if language:
            result.translation_to = language
        self._draft_history.append({
            "timestamp": datetime.now().isoformat(),
            "context": context.conversation_id,
            "style": style.value,
            "draft": draft,
        })
        return result

    def _get_tone_notes(self, style: ReplyStyle, custom: str) -> str:
        notes = {
            ReplyStyle.PROFESSIONAL: "Use formal language, proper salutations, and professional closing.",
            ReplyStyle.CASUAL: "Use conversational language, contractions, and a relaxed tone.",
            ReplyStyle.FRIENDLY: "Use warm, personal language with positive expressions.",
            ReplyStyle.SHORT: "Keep response under 2-3 sentences. Direct and concise.",
            ReplyStyle.DETAILED: "Provide comprehensive response with examples and context.",
        }
        base = notes.get(style, "Natural conversational tone.")
        if custom:
            base += f" Additional instructions: {custom}"
        return base

    def _build_draft(self, content: str, sender: str, style: ReplyStyle, custom: str) -> str:
        content_lower = content.lower()
        is_question = "?" in content
        is_meeting_request = any(w in content_lower for w in ["meet", "schedule", "call", "appointment"])
        is_urgent = any(w in content_lower for w in ["urgent", "asap", "important", "deadline"])
        is_thank_you = any(w in content_lower for w in ["thanks", "thank you", "appreciate"])

        if style == ReplyStyle.SHORT:
            if is_question:
                return f"Thanks for your message, {sender}. I'll look into this and get back to you shortly."
            return f"Got it, {sender}. I'll take care of this."

        if style == ReplyStyle.PROFESSIONAL:
            if is_meeting_request:
                return f"Dear {sender},\n\nThank you for reaching out. I would be happy to schedule a meeting. Please let me know what time works best for you.\n\nBest regards"
            if is_urgent:
                return f"Dear {sender},\n\nThank you for bringing this to my attention. I understand the urgency and will prioritize this matter. I will follow up with an update shortly.\n\nBest regards"
            greeting = f"Dear {sender}"
            closing = "Best regards"
            body = "Thank you for your message."
            if is_question:
                body = "Thank you for your inquiry. I will review the details and get back to you promptly."
            elif is_thank_you:
                body = "You're welcome! Happy to help. Let me know if there's anything else I can assist with."
            return f"{greeting},\n\n{body}\n\n{closing}"

        if style == ReplyStyle.FRIENDLY:
            greeting = f"Hey {sender}!"
            if is_meeting_request:
                return f"{greeting}\n\nSounds great! I'd love to meet up. Just let me know when works for you and I'll make it happen 😊"
            if is_thank_you:
                return f"{greeting}\n\nYou're very welcome! Always happy to help out. Talk soon!"
            return f"{greeting}\n\nThanks for reaching out! I'll get back to you as soon as I can."

        if style == ReplyStyle.CASUAL:
            if is_question:
                return f"Hey {sender},\n\nGood question! Let me check on that and get back to you."
            return f"Hey {sender},\n\nThanks for the message. I'll handle it!"

        if style == ReplyStyle.DETAILED:
            parts = [f"Hello {sender},"]
            if is_question:
                parts.append(f"\n\nThank you for your detailed question. I have reviewed the information you provided and would like to address each point:")
                parts.append(f"\n\n1. Regarding your inquiry, I will conduct a thorough review.")
                parts.append(f"\n2. I will gather the relevant information from our records.")
                parts.append(f"\n3. I will provide a comprehensive response with all necessary details.")
            else:
                parts.append(f"\n\nThank you for reaching out. I have carefully reviewed your message.")
                parts.append(f"\n\nI will take the appropriate actions and follow up with a complete update.")
            parts.append(f"\n\nPlease don't hesitate to reach out if you have any additional questions or need further clarification.")
            parts.append(f"\n\nBest regards")
            return "".join(parts)

        return f"Hi {sender},\n\nThank you for your message. I will get back to you shortly."

    def summarize_conversation(self, messages: list[dict], conversation_id: str = "") -> ConversationSummary:
        if conversation_id and conversation_id in self._summary_cache:
            return self._summary_cache[conversation_id]

        if not messages:
            return ConversationSummary(summary="No messages to summarize.")

        participants = list(set(m.get("sender_name", "Unknown") for m in messages))
        message_count = len(messages)
        content_parts = [m.get("content", "") for m in messages if m.get("content")]
        full_text = " ".join(content_parts)

        key_points = self._extract_key_points(full_text)
        action_items = self._extract_action_items(full_text)
        sentiment = self._detect_sentiment(full_text)

        summary_parts = [f"Conversation with {', '.join(participants)} ({message_count} messages)."]
        if "?" in full_text:
            summary_parts.append(" Contains questions that may need responses.")
        if action_items:
            summary_parts.append(f" Action items identified: {len(action_items)}.")
        if any(w in full_text.lower() for w in ["meeting", "schedule", "call"]):
            summary_parts.append(" Meeting or scheduling mentioned.")

        summary_text = " ".join(summary_parts)

        result = ConversationSummary(
            summary=summary_text,
            key_points=key_points,
            action_items=action_items,
            sentiment=sentiment,
            participants=participants,
            message_count=message_count,
        )
        if conversation_id:
            self._summary_cache[conversation_id] = result
        return result

    def extract_tasks(self, messages: list[dict]) -> list[dict]:
        tasks = []
        for msg in messages:
            content = msg.get("content", "")
            sender = msg.get("sender_name", "Unknown")
            extracted = self._extract_action_items(content)
            for task in extracted:
                tasks.append({"task": task, "from": sender, "message_id": msg.get("id", "")})
        return tasks

    def detect_urgent_messages(self, messages: list[dict]) -> list[dict]:
        urgent = []
        urgent_keywords = ["urgent", "asap", "immediately", "important", "deadline", "critical", "emergency", "time-sensitive"]
        for msg in messages:
            content = msg.get("content", "").lower()
            for kw in urgent_keywords:
                if kw in content:
                    urgent.append(msg)
                    break
        return urgent

    def find_pending_requests(self, messages: list[dict]) -> list[dict]:
        pending = []
        patterns = [
            r"(?:can|could|would|will)\s+(?:you|someone)\s+(.+?)\?",
            r"(?:please|pls)\s+(.+?)(?:\.|$)",
            r"(?:need|require|request)\s+(.+?)(?:\.|$)",
            r"I'd\s+(?:like|appreciate)\s+(.+?)(?:\.|$)",
        ]
        for msg in messages:
            content = msg.get("content", "")
            for pattern in patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                for m in matches:
                    pending.append({"request": m.strip(), "from": msg.get("sender_name", "Unknown"), "message_id": msg.get("id", "")})
        return pending

    def _extract_key_points(self, text: str) -> list[str]:
        points = []
        sentences = re.split(r'[.!?]+', text)
        for s in sentences:
            s = s.strip()
            if len(s) > 20 and any(w in s.lower() for w in ["important", "key", "critical", "note", "remember", "significant", "must", "required"]):
                points.append(s)
        return points[:5]

    def _extract_action_items(self, text: str) -> list[str]:
        items = []
        patterns = [
            r"(?:I\s+(?:will|need to|have to|must)\s+)(.+?)(?:\.|,|$)",
            r"(?:please|pls)\s+(.+?)(?:\.|,|$)",
            r"(?:action\s*item[s]?[:\s]+)(.+?)(?:\.|$)",
            r"(?:todo|to-do|to do)[:\s]+(.+?)(?:\.|$)",
            r"(?:don't forget|remember)\s+to\s+(.+?)(?:\.|,|$)",
            r"(?:follow up|follow-up)\s+(?:on|with)\s+(.+?)(?:\.|,|$)",
        ]
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            items.extend([m.strip() for m in matches if len(m.strip()) > 5])
        return items[:8]

    def _detect_sentiment(self, text: str) -> str:
        positive = ["great", "awesome", "happy", "thanks", "love", "excellent", "perfect", "wonderful", "amazing", "fantastic", "good", "best"]
        negative = ["bad", "terrible", "awful", "hate", "angry", "frustrated", "disappointed", "poor", "worst", "horrible", "unacceptable"]
        text_lower = text.lower()
        pos_count = sum(1 for w in positive if w in text_lower)
        neg_count = sum(1 for w in negative if w in text_lower)
        if pos_count > neg_count:
            return "positive"
        elif neg_count > pos_count:
            return "negative"
        return "neutral"

    def classify_priority(self, messages: list[dict]) -> list[dict]:
        classified = []
        for msg in messages:
            content = msg.get("content", "").lower()
            if any(w in content for w in ["urgent", "asap", "emergency", "critical"]):
                priority = "urgent"
            elif any(w in content for w in ["important", "deadline", "required", "must"]):
                priority = "important"
            elif any(w in content for w in ["spam", "unsubscribe", "offer", "discount", "free"]):
                priority = "spam"
            else:
                priority = "normal"
            classified.append({"message": msg, "priority": priority})
        return classified

    def translate_message(self, content: str, target_language: str) -> str:
        translation_headers = {
            "spanish": "Traducción al español",
            "french": "Traduction en français",
            "german": "Übersetzung ins Deutsche",
            "italian": "Traduzione in italiano",
            "portuguese": "Tradução para o português",
            "japanese": "日本語翻訳",
            "chinese": "中文翻译",
            "korean": "한국어 번역",
            "russian": "Перевод на русский",
            "arabic": "الترجمة إلى العربية",
        }
        header = translation_headers.get(target_language.lower(), f"Translation to {target_language}")
        return f"[{header}]\n{content}\n\n[Note: This is a simulated translation. Real translation requires an AI provider.]"

    def clear_history(self):
        self._draft_history.clear()
        self._summary_cache.clear()

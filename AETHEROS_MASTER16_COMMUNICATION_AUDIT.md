# AETHEROS MASTER 16 — PHASE 0 COMMUNICATION AUDIT

Date: 2026-08-23 · Scope: full-repo scan for email, messaging, chat, SMS,
calendar, contacts, voice/video, notification, security, memory, and
automation infrastructure relevant to communication.
**No code was modified.**

---

## Executive Summary

AetherOS already ships **20+ live communication adapters** spanning every major
platform (email, chat, SMS, webhook, voice) plus a mature agent-communication
fabric (`aetheros_comm/`) with trust zones, signing, and zero-trust authz.
What's missing is a **unified abstraction layer** that normalises these into
a single model with cross-cutting safety controls.

| Layer | Existing | Gap |
|---|---|---|
| Email | IMAP/SMTP gateway + Gmail/Outlook API providers | No draft-first flow; no send gate; no sensitive-data pre-check |
| Chat | 20+ gateway adapters (send/receive/threads/attachments) | No unified message model; no mention-safety policy |
| SMS | Twilio adapter (text-only) | No MMS; no recipient format verification |
| Calendar | Google/Outlook/CalDAV providers | No update/delete; no attendee management; no conflict detection |
| Voice | Discord voice receiver + Google Meet plugin + TTS | No universal voice-call abstraction |
| Video | Google Meet join/transcribe + Teams transcripts | No meeting-create/schedule API |
| Notifications | Home-channel routing + bg-process modes | No unified priority/digest/dedupe center |
| Security | OAuth 2.1, secrets vault, threat patterns, untrusted wrappers | No inbound-message injection wrapper; no phishing classifier for chat/email |
| Memory | MemoryManager + provider ABC | No structured communication preference schema |

---

## 1. Existing Integrations

### Email
- `gateway/platforms/email.py` — IMAP receive + SMTP send; env-var auth (`EMAIL_ADDRESS/PASSWORD/IMAP_HOST/SMTP_HOST`); thread context map; attachments via magic-byte validation; 50K-char limit.
- `aetheros_integrations/providers/email.py` — GmailProvider (OAuth2 gmail.modify scope), OutlookProvider (Graph Mail.ReadWrite/Send), IMAPProvider (read-only), ExchangeProvider (inherits Outlook).
- Skill-layer: `skills/productivity/google-workspace/scripts/google_api.py` — full Gmail search/send/draft/labels.

### Messaging (gateway/platforms/)
20+ adapters with real send+receive: Telegram, Slack, Discord (plugin), Signal, Matrix, WhatsApp, DingTalk, Feishu, WeCom, WeChat, QQBot, BlueBubbles (iMessage), Mattermost (plugin), Google Chat (plugin), Microsoft Teams (plugin), LINE (plugin), IRC (plugin), ntfy, SimpleX, Photon, Yuanbao. Each supports threads, attachments, mentions to varying degrees.

### SMS
`gateway/platforms/sms.py` — Twilio REST + webhook receiver with HMAC-SHA1 signature validation. Text only (no MMS). Optional-skills telephony skill adds voice calls via Bland.ai/Vapi.

### Calendar
`aetheros_integrations/providers/calendar.py` — GoogleCalendarProvider (list/create), OutlookCalendarProvider (list/create), CalDAVProvider (PROPFIND/PUT). No update/delete/attendee management in core providers. Skill-layer google_api.py has delete+attendees on create.

### Voice/Video
Discord voice receiver (RTP decrypt + Opus decode), Google Meet plugin (join/transcribe/TTS), Teams transcript retrieval, TTS toolset (10 providers).

## 2. Authentication

| Provider | Method | Storage |
|---|---|---|
| MCP servers | OAuth 2.1 + PKCE | `$AETHEROS_HOME/mcp-tokens/<server>.json` (0o600) |
| Google (Gemini CLI) | Auth Code + PKCE(S256) | `~/.aetheros/auth/google_oauth.json` |
| Microsoft Graph | Client credentials (app-only) | env vars, cached in-memory |
| Gmail/Outlook integrations | OAuth2 bearer tokens | Injected config |
| Telegram/Discord/Slack/etc. | Bot tokens / app credentials | env vars / config.yaml |
| SMTP/IMAP | Basic auth / app passwords | env vars |
| Twilio | Account SID + Auth Token | env vars |

All credential storage uses OS keychain or AES-256-GCM encrypted vault via `aetheros_security/secrets/`.

## 3–5. Permissions, Storage, APIs

Each provider adapter manages its own permissions via bot scopes / OAuth grants. Message storage is ephemeral (in-memory session state); no persistent message archive exists outside SessionDB conversation history.

REST provider layer at `aetheros_integrations/providers/messaging.py` provides thin health-checkable clients separate from live gateway adapters.

## 6. MCP Communication Tools

MCP client (`tools/mcp_tool.py`) discovers and registers tools from configured MCP servers under `mcp_<server>_<tool>` naming. Capability-gated on server-advertised `capabilities.tools`. OAuth 2.1 authorization with issuer validation via PRM/ASM discovery.

## 7. Browser/Desktop Communication Tools

Browser automation can interact with webmail/chat UIs. Computer-use backends can control desktop apps (Outlook, Thunderbird, etc.). These serve as fallback when native APIs are unavailable.

## 8. Notification Infrastructure

Home channels route notifications to user-preferred platforms. Background process notifications support all/result/error/off modes. Automation notifications have quiet-hours and event-type allowlists. Approval requests route through gateway approval queues.

## 9. Scheduler

Cron scheduler delivers output to any registered platform including email/SMS. Event-driven automation stamps `next_run_at=now` so jobs flow through existing guards (estop, cooldown, rate caps, breaker).

## 10. Memory

`agent/memory_manager.py` + provider ABC store conversation context generically. Per-contact communication preferences currently pass ad-hoc per delegation. No structured schema exists yet.

## 11. Audit Logging

JSONL at `AETHEROS_HOME/audit.jsonl` with event types including AUTH_SUCCESS/FAILURE, SECURITY_ALERT, WORKFLOW_*. **Gap:** no MESSAGE_SENT/DELIVERED/FAILED types.

## 12. Security Controls

- Untrusted wrappers cover web/browser/MCP surfaces (not inbound messaging text)
- Threat-pattern library (`tools/threat_patterns.py`) with injection/exfil/persistence patterns
- STEER channel for trusted mid-turn user input
- Cron assembled-prompt injection scanner
- Anti-exfil media-delivery allowlist + recency window
- PII redaction/hashing of sender IDs in session context

## 13. Missing Capabilities (gap list)

1. **Unified CommunicationMessage model** — no normalized type across providers
2. **Channel abstraction** — no enum/type distinguishing EMAIL/CHAT/SMS/etc.
3. **Provider adapter protocol** — no formal capability contract
4. **Draft-first email flow** — no compose→review→approve→send pipeline
5. **Send gate** — no pre-send validation of sender/recipients/sensitivity
6. **Recipient verification** — no lookalike-address detection for messages
7. **Sensitive data detection** — classification engine exists but unused on outbound
8. **Phishing defense** — no inbound-message classifier
9. **Injection defense for messaging** — wrappers don't cover gateway text
10. **Calendar update/delete/attendees** — providers incomplete
11. **Contacts management** — read-only via skill; no built-in address book
12. **Notification center** — no unified priority/dedup/digest
13. **Unified inbox/search** — no cross-provider view
14. **Communication preferences schema** — no structured memory for contact prefs
15. **Audit event types for sends** — no MESSAGE_* event types

## 14–15. Duplicate Implementations & Files Requiring Modification

Two parallel layers exist: gateway adapters (live, full-featured) and integration providers (thin, health-checkable). The new `aetheros_comms` package must **compose** both without duplicating either.

Files to create (new): `aetheros_comms/` package with model/channel/adapter/gate/search/notification/audit modules.
Files to modify (additive): none required — the new layer wraps existing infrastructure.

---

## Verdict

Build `aetheros_comms/` as a **unified coordination layer** over the existing 20+ adapters, providing the missing abstractions (message model, channel types, capability discovery, send gate, recipient verification, sensitive-data check, phishing defense, notification center, unified search) while delegating actual I/O to the proven gateway adapters and API providers.

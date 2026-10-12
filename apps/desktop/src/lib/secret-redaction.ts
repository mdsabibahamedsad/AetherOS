/**
 * Secret redaction for renderer surfaces (logs, errors, notifications,
 * terminal/tool output previews). Defense-in-depth: the backend owns
 * enforcement, but the UI must never amplify a leaked credential by
 * persisting or displaying it verbatim.
 *
 * Conservative by design: only well-formed secret shapes are masked;
 * ordinary prose, paths, and identifiers pass through untouched.
 */

const PATTERNS: { name: string; re: RegExp }[] = [
  // PEM / OpenSSH private key blocks (multiline).
  { name: 'private-key', re: /-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----[\s\S]*?-----END [A-Z0-9 ]*PRIVATE KEY-----/g },
  // OpenAI-style + generic long bearer-ish tokens.
  { name: 'api-key', re: /\bsk-[A-Za-z0-9_-]{16,}\b/g },
  { name: 'github-pat', re: /\bgh[pousr]_[A-Za-z0-9_]{16,}\b/g },
  { name: 'slack-token', re: /\bxox[baprs]-[A-Za-z0-9-]{8,}\b/g },
  { name: 'aws-key', re: /\bAKIA[0-9A-Z]{16}\b/g },
  // Explicit bearer/basic auth headers.
  { name: 'bearer', re: /\b(Bearer|Basic)\s+[A-Za-z0-9\-._~+/=]{12,}/g },
  // JWT access/id tokens (header.payload.signature). The shape requirement
  // (eyJ head + two dots + bounded length) keeps base64 data-URLs and
  // random dotted strings out; data-URL payloads are excluded explicitly.
  {
    name: 'jwt',
    re: /(?<!data:[^;]*;base64,)\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b/g,
  },
  // key=value assignments whose NAME looks secret-bearing.
  {
    name: 'secret-assignment',
    re: /\b(api[_-]?key|api[_-]?secret|secret|password|passwd|pwd|token|auth[_-]?token|access[_-]?token|private[_-]?key|client[_-]?secret)\b\s*[:=]\s*['"]?[^\s'"]{4,}['"]?/gi,
  },
]

const MASK = '[redacted]'

export function redactSecrets(text: string): string {
  let out = text

  for (const { re } of PATTERNS) {
    out = out.replace(re, MASK)
  }

  return out
}

/** True when redaction changed the text (a secret shape was present). */
export function containsSecret(text: string): boolean {
  return redactSecrets(text) !== text
}

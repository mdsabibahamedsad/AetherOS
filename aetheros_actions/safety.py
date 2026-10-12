"""Safety policy for computer-use actions (Steps 24-27, 31).

Encapsulates the deterministic safety rules that are *policy* — independent of
any backend or permission system:

* Download security — executable/payload extensions are flagged; never
  auto-executed.
* Upload security — sensitive uploads and ambiguous destinations require
  confirmation.
* Clipboard security — reads/writes are gated; sensitive clipboard
  transcripts are never surfaced to the model.
* Password-field protection — password/secret targets are surfaced as
  ``"PASSWORD FIELD"``, never the actual value.
* Filesystem security — path traversal and protected-directory writes are
  blocked (credential dirs, SSH keys, browser profiles).
"""

from __future__ import annotations

import re
from pathlib import PurePath
from typing import Dict, List, Tuple

# ── Executable / payload content (Step 24) ──────────────────────────────

EXECUTABLE_EXTENSIONS = frozenset({
    ".exe", ".msi", ".bat", ".cmd", ".ps1", ".sh", ".js", ".vbs", ".dmg",
    ".pkg", ".app", ".jar", ".deb", ".rpm", ".apk", ".scr", ".com",
})

SCRIPT_SEQUENCES = (
    ("curl", "|", "bash"),
    ("curl", "|", "sh"),
    ("wget", "|", "sh"),
    ("wget", "|", "bash"),
    ("powershell", "-executionpolicy", "bypass"),
    ("iwr", "|", "iex"),
    ("invoke-expression",),
)

_ARCHIVE_EXTENSIONS = frozenset({
    ".zip", ".tar", ".gz", ".tgz", ".bz2", ".7z", ".rar",
})

_SENSITIVE_UPLOAD_TERMS = re.compile(
    r"\b(password|secret|api[_-]?key|token|credentials?|private|key\.pem|"
    r"\.env|ssh|passport|ssn|card|bank)\b",
    re.IGNORECASE,
)

# Filesystem protections (Step 31).
_DENIED_PATH_PARTS = (
    ".ssh", "id_rsa", "id_ed25519", ".gnupg", "secring", "keyring",
    "auth.json", "credentials", ".aws/credentials", "wp-config.php",
    "apikey", "api_key", ".env", "browser profile", "profile/default",
    "cookies.sqlite", "login_data",
)
_DENIED_ENV_DIRS = ("/etc", "/var/run", "/proc", "/sys", "/dev", "C:\\Windows")
# Private-key file suffixes — any path segment ending in one of these is
# treated as a credential file and never a safe target.
_PRIVATE_KEY_SUFFIXES = (".pem", ".key", ".p12", ".pfx", ".ppk", ".asc",
                         ".gpg", ".p8", ".jks")


class SafetyPolicy:
    """Deterministic safety rules shared by the risk/permission pipeline.

    All methods are pure (no I/O). Misconfigured or empty inputs fail
    *closed* — an unknown extension or a traversal-prone path is unsafe.
    """

    def __init__(
        self,
        executable_extensions: frozenset[str] = EXECUTABLE_EXTENSIONS,
        script_sequences: Tuple[Tuple[str, ...], ...] = SCRIPT_SEQUENCES,
    ) -> None:
        self.executable_extensions = frozenset(executable_extensions)
        self.script_sequences = script_sequences

    # ── Download security ─────────────────────────────────────────────

    def is_executable(self, filename: str) -> bool:
        """True when ``filename`` carries an executable/payload extension."""
        name = (filename or "").strip().lower()
        if not name:
            return True  # unknown download destination → treat as unsafe
        return PurePath(name).suffix in self.executable_extensions

    def executable_payload_warning(self, filename: str) -> str:
        return (
            f"'{filename}' is executable content. AetherOS refuses to "
            "auto-run downloaded executables; execution requires explicit "
            "user authorization."
        )

    # ── Upload security (Step 25) ─────────────────────────────────────

    def is_sensitive_upload(self, filename: str, content_sample: str = "") -> bool:
        """True when the upload may contain or be named as a secret."""
        haystack = f"{filename}\n{content_sample}"
        return bool(_SENSITIVE_UPLOAD_TERMS.search(haystack))

    def _is_archive(self, filename: str) -> bool:
        name = (filename or "").strip().lower()
        if "." not in name:
            return False
        ext = PurePath(name).suffix
        return ext in _ARCHIVE_EXTENSIONS or name.endswith(".tar.gz")

    def upload_requires_confirmation(
        self, filename: str, destination: str, content_sample: str = ""
    ) -> bool:
        """Sensitive/archive content or an unknown destination ⇒ confirmation.

        * sensitive name or content sample → confirm (may contain secrets);
        * archives → confirm (can bundle secrets/configs — treat as opaque);
        * empty filename → confirm (we can't judge what we're uploading);
        * empty destination → confirm (must show where it goes).
        """
        if self.is_sensitive_upload(filename, content_sample):
            return True
        if self._is_archive(filename):
            return True
        dest = (destination or "").strip()
        return not filename or not dest

    # ── Clipboard security (Step 26) ──────────────────────────────────

    def clipboard_text_for_model(self, text: str, *, authorized: bool) -> str:
        """Return the text the model is allowed to see.

        Never surfaces clipboard contents unless ``authorized``.
        """
        if authorized:
            return text
        return "(clipboard access denied — content withheld)"

    # ── Password-field protection (Step 27) ───────────────────────────

    PASSWORD_FIELD_MARKER = "PASSWORD FIELD"

    def mask_secret_input(self, value: str) -> str:
        """Never leak a secret value; replace with a marker."""
        return self.PASSWORD_FIELD_MARKER

    def is_password_like_target(self, target: str, parameters: Dict[str, object]) -> bool:
        hay = " ".join(str(v) for v in (target, *parameters.values()))
        return bool(_SENSITIVE_UPLOAD_TERMS.search(hay))

    # ── Filesystem security (Step 31) ─────────────────────────────────

    def _lower_parts(self, path: str) -> List[str]:
        p = (path or "").strip()
        try:
            pure = PurePath(p)
            parts = [part.lower() for part in pure.parts]
        except Exception:
            parts = p.lower().replace("\\", "/").split("/")
        return parts

    def has_traversal(self, path: str) -> bool:
        p = (path or "").replace("\\", "/")
        return ".." in [seg for seg in p.split("/") if seg]

    def is_denied_path(self, path: str) -> bool:
        parts = self._lower_parts(path)
        if any(part in _DENIED_PATH_PARTS for part in parts):
            return True
        # Credential files: any final segment carrying a private-key suffix.
        if parts:
            last = parts[-1]
            if any(last.endswith(suffix) for suffix in _PRIVATE_KEY_SUFFIXES):
                return True
        # Normalize to forward slashes so absolute-path prefixes are
        # detected regardless of OS (e.g. "/etc/shadow" on Windows).
        norm = (path or "").replace("\\", "/").strip().lower()
        for denied in _DENIED_ENV_DIRS:
            d = denied.replace("\\", "/").lower()
            if norm == d or norm.startswith(d + "/"):
                return True
        return False

    def is_safe_path(self, path: str) -> bool:
        """False when a path is traversable, denied, or empty."""
        p = (path or "").strip()
        if not p:
            return False
        if self.has_traversal(p):
            return False
        if self.is_denied_path(p):
            return False
        return True
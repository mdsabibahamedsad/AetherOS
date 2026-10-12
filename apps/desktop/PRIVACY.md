# AetherOS Desktop Privacy Policy

## Data Collection

### What We Collect

**Required (always collected for app function):**
- Application version and build number
- Operating system type and version
- CPU architecture
- System locale/language

**Optional (opt-in via Settings → Privacy):**
- Anonymous usage statistics (features used, session duration, error counts)
- Crash reports (stack traces, system state at crash)
- Performance metrics (startup time, memory usage, frame rates)

**Never Collected:**
- Personal files or documents
- Keystrokes or input content
- Screen captures
- Network traffic content
- Credentials or tokens
- Location data
- Contacts or address book

### How We Collect
- Usage data is aggregated and anonymized
- Crash reports are sent to Sentry (or self-hosted alternative)
- No third-party analytics SDKs
- No tracking cookies or fingerprinting

## Data Storage

### Local Storage
- **Configuration:** `~/.config/aetheros/` (JSON files)
- **Workspace Data:** User-specified directory
- **Cache:** `~/.cache/aetheros/`
- **Logs:** `~/.config/aetheros/logs/` (7-day retention)

### Sensitive Data
- **Tokens:** Encrypted in OS keychain (Credential Manager, Keychain, secret-service)
- **No plaintext secrets** are stored on disk

## Data Sharing

### We Do NOT Share:
- Personal data with third parties
- Usage data with advertisers
- Crash reports without consent
- File contents or workspace data

### We May Share (with consent or legal requirement):
- Anonymized aggregate statistics in public reports
- Information as required by law enforcement (with valid legal process)
- Crash reports with Sentry (if enabled) for crash analysis

## User Rights

### You Can:
- **View** collected data in Settings → Privacy
- **Export** your data (Settings → Privacy → Export Data)
- **Delete** all local data by uninstalling the application
- **Opt out** of telemetry and crash reporting at any time
- **Disable** automatic updates

### Data Retention
- Local data persists until you uninstall or clear app data
- Telemetry data is retained for 90 days
- Crash reports are retained for 180 days
- Anonymized aggregate statistics may be retained indefinitely

## Third-Party Services

### Updates
- Update checks contact `updates.aetheros.dev` over HTTPS
- No personal data transmitted
- Update server records: IP address, timestamp, version

### Telemetry (if enabled)
- Sentry for error tracking
- Self-hosted analytics endpoint
- Both configured to strip personally identifiable information

## Compliance

### GDPR
- Lawful basis: Consent for telemetry, Legitimate Interest for app function
- Data Processing Agreement available on request
- EU representative contact: privacy@aetheros.dev
- Supervisory authority: [Relevant EU Data Protection Authority]

### CCPA
- No sale of personal information
- Right to know, delete, and opt out
- Contact: privacy@aetheros.dev

### SOC 2
- Audit logging covers authentication and configuration changes
- Access controls for administrative functions
- Regular security assessments

## Changes to This Policy
We will notify users of material changes via:
1. In-app notification on next launch
2. Updated policy on our website
3. Release notes for the update

## Contact
- **Privacy Questions:** privacy@aetheros.dev
- **Data Protection Officer:** dpo@aetheros.dev
- **Report a Concern:** https://github.com/aetheros/aetheros/security

## Version History
| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-Q3 | Initial privacy policy for v1 release |

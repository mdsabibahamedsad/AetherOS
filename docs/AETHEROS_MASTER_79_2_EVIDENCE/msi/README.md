# Verbose msiexec logs (CI-only)

`msiexec /i ... /L*v msi-install.log` and `msiexec /x ... /L*v msi-uninstall.log`
from `.github/workflows/windows-desktop-certification.yml` are stored here
after a real CI run. No CI run has executed yet (gh auth invalid on dev host;
manual `gh workflow run` or GitHub UI dispatch required), so this directory
is intentionally empty. Do NOT fabricate logs.

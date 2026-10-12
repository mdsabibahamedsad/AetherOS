# AETHEROS MASTER 78A — Final Certification

## AETHEROS_WINDOWS_DESKTOP_BLOCKED

Rationale (§55, applied literally): clean-VM validation could not occur on this host — no clean VM
exists, so installer INSTALL/LAUNCH/SMOKE/UNINSTALL/REINSTALL for NSIS, MSI, and portable are all
BLOCKED, as is SIGNING (no credentials). A BETA label was considered (§54: all artifacts exist, no
P0 remains) but §55 names unoccurrable clean-VM validation an explicit BLOCKED trigger, and this run
does not override that hierarchy.

What IS complete and proven by real command execution:
- NSIS BUILD PASS, MSI BUILD PASS (LGHT0103 root-caused and fixed via short-root build), PORTABLE BUILD PASS
- All three artifacts HEAD_BOUND (commit 2bdfbfd8, dirty-tree caveat recorded), SHA-256 recorded
- Artifact validator: VALID (7/7 cross-checked)
- win-unpacked runtime: PROCESS_STARTED + PROCESS_STABLE + GUI_VISIBLE (observed HWND + title), 0 orphans
- Electron platform tests 176/176, typecheck PASS, full `npm run build` PASS

To lift BLOCKED: provision (a) a clean Windows VM, (b) a code-signing certificate. Then execute:
install → launch → smoke → uninstall → reinstall for each of the three artifacts in
`apps/desktop/dist-packaged/` (hashes in `AETHEROS_MASTER_78A_WINDOWS_ARTIFACT_CHECKSUMS.txt`),
and re-certify. No rebuild is required unless the source commit moves.

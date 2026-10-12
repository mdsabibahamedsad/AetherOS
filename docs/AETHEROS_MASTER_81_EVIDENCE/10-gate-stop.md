# Exact failed gate (§Final Instruction)

STOP at A01: RELEASE_BUILD_BLOCKED_DIRTY_TREE (2783 changed paths).
Per §92 the guard was NOT weakened; per §4/§5 no reset/clean/stash/commit was
performed without authorization. Stages §13–§30 (clean output → rebuild → install/
runtime/VM) never started because the pipeline fails fast (§44). The authoritative
RC build, CI build, and all downstream gates inherit this STOP.

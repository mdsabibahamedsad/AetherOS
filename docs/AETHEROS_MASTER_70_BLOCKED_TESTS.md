# AETHEROS Master 70 — Blocked Test Register

| Test | Platform | Reason | Required environment | Priority | Next action |
|---|---|---|---|---|---|
| J01–J44 journeys | all | no runnable clients/servers/devices | staging + device lab + VMs | P1 | Master 70 follow-up |
| Xcode/Swift | iOS | no macOS | macos-runner | P1 | run ios-platform.yml |
| Gradle/Kotlin | Android | no JDK/SDK | linux-runner + SDK | P1 | implement app, run android-platform.yml |
| Docker/K8s | server | no daemon | linux-runner + docker | P1 | compose up + drills |
| Browser matrix | web | no Playwright browsers | ci-playwright | P2 | install + matrix |
| Signing/notarization | desktop | no credentials | secrets + runners | P0 for release | provision |
| Clean VMs | desktop | no hypervisor images | VM lab | P0 for release | harness + runs |
| Pen-test/live auth | server | no staging | staging env | P0 for release | schedule |
| Backup/restore drill | server | no disposable env | staging env | P0 for release | drill + measure RTO/RPO |
| Perf benchmarks | all | no hardware rig | perf lab | P2 | Master 71 |

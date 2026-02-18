# mcar Release Gate Run (2026-02-18_10-03-08)

- Root: /Users/xiaorain/code/mcar
- Output: docs/verification/run-2026-02-18_10-03-08

## Results
- PASS | Gate P | node_version | v24.13.1
- PASS | Gate P | python_version | Python 3.12.11
- PASS | Gate P | env_file | .ai_pet_env present
- PASS | Gate P | gemini_key | configured
- PASS | Gate P | picovoice_key | configured
- PASS | Gate P | data_backup | created docs/verification/.../data-backup.tgz
- PASS | GateA | core_npm_install | ok (log: docs/verification/run-2026-02-18_10-03-08/GateA_core_npm_install.log)
- PASS | GateA | core_build | ok (log: docs/verification/run-2026-02-18_10-03-08/GateA_core_build.log)
- PASS | GateA | core_test | ok (log: docs/verification/run-2026-02-18_10-03-08/GateA_core_test.log)
- PASS | GateA | core_coverage_plugin | ok (log: docs/verification/run-2026-02-18_10-03-08/GateA_core_coverage_plugin.log)
- PASS | GateA | core_test_coverage | ok (log: docs/verification/run-2026-02-18_10-03-08/GateA_core_test_coverage.log)
- PASS | GateA | modules_install | ok (log: docs/verification/run-2026-02-18_10-03-08/GateA_modules_install.log)
- PASS | GateA | modules_pytest | ok (log: docs/verification/run-2026-02-18_10-03-08/GateA_modules_pytest.log)
- PASS | Gate B | service_start | service reachable at /api/status
- PASS | Gate B | api_status | 200 OK
- PASS | Gate B | api_modules | 200 OK
- PASS | Gate B | api_capabilities | 200 OK
- PASS | Gate B | api_health | 200 OK
- PASS | Gate B | api_watchdog | 200 OK
- PASS | Gate B | api_metrics | 200 OK
- PASS | Gate B | api_audit | 200 OK
- PASS | Gate B | api_sessions | 200 OK
- PASS | Gate B | api_rules/status | 200 OK
- PASS | Gate B | negative_invalid_capability | rejected as expected
- PASS | Gate B | negative_invalid_input | rejected as expected
- PASS | Gate B | watchdog_stability | no permanentlyFailed=true
- NA | Gate C | raspberry_pi_full_validation | N/A-HW-MISSING in local environment

## Summary

- PASS: 26
- FAIL: 0
- NA: 1
- BLOCKED: 0

**Decision: GO**

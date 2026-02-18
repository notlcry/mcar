# mcar Release Gate Run (2026-02-18_09-46-35)

- Root: /Users/xiaorain/code/mcar
- Output: docs/verification/run-2026-02-18_09-46-35

## Results
- PASS | Gate P | node_version | v24.13.1
- PASS | Gate P | python_version | Python 3.12.11
- PASS | Gate P | env_file | .ai_pet_env present
- PASS | Gate P | gemini_key | configured
- PASS | Gate P | picovoice_key | configured
- PASS | Gate P | data_backup | created docs/verification/.../data-backup.tgz
- PASS | GateA | core_npm_install | ok (log: docs/verification/run-2026-02-18_09-46-35/GateA_core_npm_install.log)
- PASS | GateA | core_build | ok (log: docs/verification/run-2026-02-18_09-46-35/GateA_core_build.log)
- FAIL | GateA | core_test | rc=1 (log: docs/verification/run-2026-02-18_09-46-35/GateA_core_test.log)
- PASS | GateA | core_coverage_plugin | ok (log: docs/verification/run-2026-02-18_09-46-35/GateA_core_coverage_plugin.log)
- FAIL | GateA | core_test_coverage | rc=1 (log: docs/verification/run-2026-02-18_09-46-35/GateA_core_test_coverage.log)
- PASS | GateA | modules_install | ok (log: docs/verification/run-2026-02-18_09-46-35/GateA_modules_install.log)
- PASS | GateA | modules_pytest | ok (log: docs/verification/run-2026-02-18_09-46-35/GateA_modules_pytest.log)
- FAIL | Gate B | service_start | service did not become ready
- NA | Gate C | raspberry_pi_full_validation | N/A-HW-MISSING in local environment

## Summary

- PASS: 11
- FAIL: 3
- NA: 1
- BLOCKED: 0

**Decision: NO-GO**

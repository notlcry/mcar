# mcar Release Gate Run (2026-02-17_18-19-30)

- Root: /Users/xiaorain/code/mcar
- Output: docs/verification/run-2026-02-17_18-19-30

## Results
- PASS | Gate P | node_version | v19.8.1
- PASS | Gate P | python_version | Python 3.12.11
- PASS | Gate P | env_file | .ai_pet_env present
- PASS | Gate P | gemini_key | configured
- PASS | Gate P | picovoice_key | configured
- NA | Gate P | data_backup | N/A-DATA-MISSING
- FAIL | GateA | core_npm_install | rc=1 (log: docs/verification/run-2026-02-17_18-19-30/GateA_core_npm_install.log)
- FAIL | GateA | core_build | rc=127 (log: docs/verification/run-2026-02-17_18-19-30/GateA_core_build.log)
- FAIL | GateA | core_test | rc=127 (log: docs/verification/run-2026-02-17_18-19-30/GateA_core_test.log)
- FAIL | GateA | core_test_coverage | rc=127 (log: docs/verification/run-2026-02-17_18-19-30/GateA_core_test_coverage.log)
- FAIL | GateA | modules_install | rc=1 (log: docs/verification/run-2026-02-17_18-19-30/GateA_modules_install.log)
- FAIL | GateA | modules_pytest | rc=2 (log: docs/verification/run-2026-02-17_18-19-30/GateA_modules_pytest.log)
- BLOCKED | Gate B | service_start | blocked by Gate A (core install/build)
- NA | Gate C | raspberry_pi_full_validation | N/A-HW-MISSING in local environment

## Summary

- PASS: 5
- FAIL: 6
- NA: 2
- BLOCKED: 1

**Decision: NO-GO**

# mcar Release Gate Run (2026-02-17_18-08-58)

- Root: /Users/xiaorain/code/mcar
- Output: docs/verification/run-2026-02-17_18-08-58

## Results
- PASS | Gate P | node_version | v19.8.1
- FAIL | Gate P | python_version | python >=3.11 required, got Python 3.10.9
- PASS | Gate P | env_file | .ai_pet_env present
- FAIL | Gate P | gemini_key | missing or template value
- NA | Gate P | picovoice_key | N/A-KEY-MISSING
- NA | Gate P | data_backup | N/A-DATA-MISSING
- FAIL | GateA | core_npm_install | rc=1 (log: docs/verification/run-2026-02-17_18-08-58/GateA_core_npm_install.log)
- FAIL | GateA | core_build | rc=127 (log: docs/verification/run-2026-02-17_18-08-58/GateA_core_build.log)
- FAIL | GateA | core_test | rc=127 (log: docs/verification/run-2026-02-17_18-08-58/GateA_core_test.log)
- FAIL | GateA | core_test_coverage | rc=127 (log: docs/verification/run-2026-02-17_18-08-58/GateA_core_test_coverage.log)
- FAIL | GateA | modules_install | rc=1 (log: docs/verification/run-2026-02-17_18-08-58/GateA_modules_install.log)
- FAIL | GateA | modules_pytest | rc=2 (log: docs/verification/run-2026-02-17_18-08-58/GateA_modules_pytest.log)
- BLOCKED | Gate B | service_start | blocked by Gate A (core install/build)
- NA | Gate C | raspberry_pi_full_validation | N/A-HW-MISSING in local environment

## Summary

- PASS: 2
- FAIL: 8
- NA: 3
- BLOCKED: 1

**Decision: NO-GO**

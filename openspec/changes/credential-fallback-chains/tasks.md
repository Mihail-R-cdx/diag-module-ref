## 1. Credential provider and schema

- [x] 1.1 Add backward-compatible plural credential resolution and request-scoped source priority.
- [x] 1.2 Support and atomically validate ordered device-profile mappings of arbitrary length.

## 2. GUI composition and retry integration

- [x] 2.1 Convert all resolved candidates to handler kwargs and use them in request credential storage.
- [x] 2.2 Verify every production worker path receives the existing retry context and preserves safe attempt reporting.

## 3. Documentation and regression coverage

- [x] 3.1 Update the synthetic example configuration for legacy and long ordered mappings.
- [x] 3.2 Add provider, composition, and retry regression tests for ordered chains and redaction.

## 4. Validation findings and evidence

- [x] 4.1 Fix device/IP credential-index isolation, invalid-index recovery, and partial-result caching.
- [x] 4.2 Redact TE20 and Extron terminal errors at the GUI public boundary.
- [x] 4.3 Add cross-IP, parameterized production retry, and terminal-redaction regression coverage.
- [x] 4.4 Rerun required focused and full offline tests, strict OpenSpec validation, and Git hygiene checks.
- [x] 4.5 Record factual implementation and verification evidence for independent validation.

## 5. Independent-validation retry-ownership corrections

- [x] 5.1 Define the GUI/application layer as the sole credential-fallback owner and distinguish credential fallback from protocol fallback.
- [x] 5.2 Remove internal credential iteration, wrap-around, and index mutation from the TE20 worker.
- [x] 5.3 Remove internal credential iteration, wrap-around, index mutation, and success-index caching from the Bar 310 worker.
- [x] 5.4 Preserve monotonic GUI retry from a saved index and terminate the chain after non-authentication failures or exhaustion.
- [x] 5.5 Add worker-level TE20 retry-ownership, transport, single-outcome, and redaction tests.
- [x] 5.6 Add worker-level Bar 310 retry-ownership, single-outcome, and redaction tests.
- [x] 5.7 Expand GUI retry coverage to all production paths, arbitrary chain length, duplicate/stale callbacks, and saved-index exhaustion.
- [x] 5.8 Rerun required focused and full offline tests, strict OpenSpec validation, and Git hygiene checks.
- [x] 5.9 Update factual implementation evidence for independent re-validation.
- [x] 5.10 Remove the remaining internal credential fallback from the Biamp and Aten production workers and add regression coverage.

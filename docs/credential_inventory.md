# Credential-flow and tracked-material inventory

This inventory intentionally records paths and categories only. It must never
contain a credential value, token, session identifier, or authentication
header.

## Production flow

| Component | Path | Authentication mode | Handoff boundary |
| --- | --- | --- | --- |
| GUI composition | `gui/main_window.py` | selected JSON profile or explicit caller input | resolves request-scoped credentials before worker construction |
| TE20 worker | `core/te20_worker.py` | username/password | explicit worker arguments to `HuaweiTE20Handler` |
| General workers | `core/worker.py` | device-specific username/password | explicit worker arguments to Huawei, Polycom, Extron, Aten, and Biamp handlers |
| Protocol factory | `core/factory.py` | credential contract supplied by caller | explicit handler constructor keyword arguments |
| Huawei handlers | `handlers/huawei/` | username/password | HTTP/session authentication boundary |
| Polycom handler | `handlers/polycom/rpg310.py` | username/password | HTTPS/SSH authentication boundary |
| Extron handler | `handlers/extron/in1804.py` | username/password | SSH/Telnet authentication boundary |
| Aten handler | `handlers/aten/pdu.py` | username/password | HTTPS authentication boundary |
| Biamp handler | `handlers/biamp/tesira_forte_ci.py` | device-specific contract | handler connection boundary |

## Finding classification and remediation

| Area | Category / risk | Removal and rotation handling |
| --- | --- | --- |
| GUI and workers | Operational credential defaults; high source-control and runtime disclosure risk | Removed from production fallback paths; rotate through incident process if prior use is confirmed. |
| Protocol handlers and factory | Username/password substitution defaults; high accidental-network-access risk | Replaced with explicit inputs and precondition errors. |
| Tests and fixtures | Synthetic test data; low risk when plainly synthetic | Retain only where needed, never copy operational material. |
| Tools, reference drivers, logs, docs, serialized outputs | Historical/generated or diagnostic material; medium-to-high disclosure risk | Review separately with path-only scan; redact/remediate confirmed material and keep hardware tools opt-in. |

## Safe verification procedure

Use `git ls-files` with a path-only scanner (for example `rg -l`) and report
only file paths, categories, and pass/fail. Review Git history only under
approved incident guidance. Confirmed operational exposure requires rotation;
any history rewrite needs separate approval.

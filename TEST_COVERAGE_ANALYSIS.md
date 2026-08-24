I traced every step against `tests.py`, the two Squish `test.py` suites, `remote_runner.py`, `system_metadata.py`, and the object maps. Summary: **13 fully implemented, 5 partial, 12 not implemented** out of 30.

| # | Procedure step | Status | Notes |
|---|---|---|---|
| 1 | Install nightly build via Ansible | ❌ Not implemented | No install/deploy step anywhere — only a version *read* exists |
| 2 | Check install version | ✅ Implemented | `system_metadata.py` → Ansible `apt list \| grep polaris`, stamped into the report |
| 3 | Check system in prod mode | ❌ Not implemented | No "prod mode" concept anywhere in code |
| 4 | Check monitors on | ⚠️ Partial | QA-T1127 checks cart/assistant/surgeon GUI windows visible (auto) + Lindir 3D TV (manual popup) |
| 5 | bootcheck3.0 on 3 PCs | ⚠️ Partial | QA-T1128 runs it via SSH on Cart + Cockpit only — only 2 hosts configured, no third (Tech) PC |
| 6 | Assistant GUI await login | ✅ Implemented | QA-T1132, `agui_prelogin_verify` |
| 7 | Cart GUI login screen | ✅ Implemented | QA-T1129, `cgui_prelogin_verify` |
| 8 | Surgeon GUI await login | ✅ Implemented | QA-T1133, `sgui_prelogin_verify` |
| 9 | Login Cart GUI (user/horizon) | ✅ Implemented | `cgui_login()` — credentials are hardcoded, not parameterized |
| 10 | Other screens grayed-out after login | ⚠️ Partial | QA-T1130 checks a label becomes visible on aGUI/sGUI — doesn't actually verify a "grayed-out" visual state |
| 11 | Case setup: ID / laterality / surgeon | ⚠️ Partial | `cart_gui_case_setup()` hardcodes case ID `"123"`, laterality `OS` only, surgeon `Dr. Smith` — not random/parametric as the procedure implies |
| 12 | Verify 'Move to Draping' enabled | ❌ Not implemented | Code clicks it directly; never checks `enabled` state first |
| 13 | Click 'Move to Draping' | ✅ Implemented | Same function as #11 |
| 14 | Rviz sim on Tech PC / aGUI Init button / cGUI ready message | ⚠️ Partial | aGUI/cGUI text checks implemented (QA-T1156 steps 1-2); Rviz/Tech PC check is entirely absent |
| 15 | aGUI click 'Initialize Case' | ✅ Implemented | `agui_click_ini_case` |
| 16 | "Ready for surgery, waiting for surgeon" | ✅ Implemented | Implemented against **Cart GUI**, not Assistant GUI as the procedure states (`verify_cgui_surgeon_control`) |
| 17 | sGUI 'Start Surgery' button appears | ✅ Implemented | `verify_start_surgery_popup` |
| 18 | sGUI click 'Start Surgery' | ✅ Implemented | `click_start_surgery` |
| 19 | sGUI 'Apply docking to operative eye' | ✅ Implemented | `verify_docking_confirmation` |
| 20 | sGUI click 'Confirm' | ✅ Implemented | `sgui_docking_confirm` |
| 21 | sGUI transitions to enabled screen | ❌ Not implemented | `sgui_docking_confirm` only clicks confirm — never verifies the resulting enabled/non-grayed screen |
| 22 | Verify screens (QA-T1131) | ✅ Implemented | Full 3-step case-setup verification across cart/assistant/surgeon GUIs |
| 23 | Surgical timer starts at 0, 5-min consistency check | ❌ Not implemented | No timer logic anywhere |
| 24 | OCT on surgeon GUI + 3D TV | ❌ Not implemented | No OCT references in code or object maps |
| 25 | QA-T1135 OCT color overlay, live image | ❌ Not implemented | Test case QA-T1135 doesn't exist in `tests.py` |
| 26 | Side camera on surgeon GUI | ❌ Not implemented | — |
| 27 | Wide camera on surgeon GUI | ❌ Not implemented | — |
| 28 | Telecentric camera on assistant GUI | ❌ Not implemented | — |
| 29 | Color overlay on Telecentric view | ❌ Not implemented | — |
| 30 | data_recorder / Perception process check | ❌ Not implemented | No such SSH/shell steps defined; `remote_runner.py` supports arbitrary shell commands, so this is easy to add but isn't wired up |

**Takeaway:** the framework fully covers the login → case-setup → start-surgery → docking-confirm handshake (steps 6–20, 22, plus the boot-check/version/display checks). Everything past "surgery enabled" — the timer, OCT, all camera views, and the data_recorder/Perception process check (steps 21, 23–30) — has no code at all, and steps 1 (install), 3 (prod mode), and 12 (button-enabled check) are also missing. Step 5 only targets 2 of the 3 PCs the procedure calls for.

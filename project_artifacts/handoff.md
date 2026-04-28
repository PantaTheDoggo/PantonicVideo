# Handoff — PantonicVideo

This file is the single source of truth for cross-sprint pending items.
Every agent reads it **before any implementation work** and decides whether each open item falls within the current sprint scope.

---

## How to use

| Action | Rule |
|---|---|
| Start of sprint | Read this file; for each **open** item, decide: in scope → resolve; out of scope → leave |
| New pending item found | Add it here as **open** before stopping |
| Sprint closes an item | Change status to **done** and move its spec to `project_artifacts/history/done/` |
| New development needed | Create a spec under `project_artifacts/history/<spec_name>.md` first; then add an entry here as **open** |

---

## Open items

### OPEN — `open_file_request` consumer

| Field | Value |
|---|---|
| **Status** | open |
| **Opened** | 2026-04-28 |
| **Opened by** | plugin-extender Sprint 2 |
| **Owner** | plugin-extender (next sprint) |
| **Spec** | not yet written — required before coding starts |

**Description:**  
`project_folder` publishes `app_state_service.state_set("open_file_request", path)` when the user double-clicks or presses Enter on a file. No plugin currently subscribes to this key. Until a subscriber exists, the signal is silently dropped.

**Acceptance criteria for closure:**  
- A new plugin (or an extension to an existing one) observes `"open_file_request"` via `state_observe` and opens/previews the file.
- A spec exists in `project_artifacts/history/` before any coding starts.
- All floor tests remain green.

---

## Done items

_(none yet)_

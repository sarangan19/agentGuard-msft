# AgentGuard — Task Execution Rules

These rules apply whenever Claude is working through a task list (e.g. `PROGRESS.MD`, `PLAN.MD`, or any numbered list of changes the user has given).

---

## Rule 1 — One Task at a Time

**Do not move to the next task without explicit user approval.**

After completing a task, stop. Post the status report (see Rule 2) and wait for the user to say yes, proceed, or equivalent before touching the next item.

**Exception — subtasks:** If a task requires sub-steps to be completed as a unit (e.g. "create file X and wire it into file Y"), complete all sub-steps before stopping. The one-at-a-time rule applies to parent tasks in the list, not to the internal steps needed to finish one parent task correctly.

**Example of correct behaviour:**
- PROGRESS.MD has 7 tasks.
- Claude completes task 1, posts status report, waits.
- User says "yes" → Claude does task 2, posts status report, waits.
- Claude does NOT run through tasks 1–7 in a single response.

---

## Rule 2 — Status Report After Every Task

After completing a task, always post a structured status report before stopping. The report must cover:

### Status Report Format

**Task:** [name or number of the task just completed]

**Result:** [Done / Partially done / Blocked — one line]

**What was implemented:**
A concise description of exactly what was built or changed. Name the files and functions touched. Be specific enough that the user can verify without reading the diff.

**New findings or discoveries:**
Anything learned during implementation that wasn't known before — interface mismatches discovered, undocumented dependencies found, design decisions that had to be made on the spot, etc. If nothing notable, write "None."

**Problems encountered and resolved:**
Any issue that came up during the task and how it was handled. If nothing notable, write "None."

**Problems not yet resolved / things to watch:**
Any open question, risk, or follow-on issue the user should know about before the next task begins.

**Ready for next task?** Yes / No — [brief reason if No]

---

## Rule 3 — Update PROGRESS.MD After Every Task

After completing a task and before posting the status report, update the task's entry in `PROGRESS.MD`:
- Status: "Not started" → "In progress" → "Done"
- Add a one-line note summarising what was done and which files were touched

This ensures PROGRESS.MD is always accurate at the moment the user reads the status report.

---

## Rule 4 — Do Not Batch

Even if the next task looks trivial or closely related, do not start it. The user may want to review the implementation, test it, redirect the approach, or change the plan entirely before proceeding. Batching removes that opportunity.

---

## When These Rules Apply

These rules are active whenever:
- The user says "start the next task", "implement [task name]", "proceed", "go ahead", or similar
- The session begins and PROGRESS.MD has tasks marked "Not started" or "In progress"
- The user pastes a numbered list of things to implement

These rules are **not** active for:
- One-off questions or explanations
- Strategic discussions or brainstorming
- Single isolated fixes not part of a tracked task list

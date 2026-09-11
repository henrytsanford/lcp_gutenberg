# Tasks

Lightweight issue board for tracking work across sessions/agents. No DB —
just this file.

**Usage:**
- Claim a task by moving it to **In Progress** and adding
  `(owner: <name>, started: YYYY-MM-DD)`.
- Finish a task by moving it into `TASKS_ARCHIVE.md` under **Done**, with
  `(completed: YYYY-MM-DD)` and a summary of what actually changed.
- Add new tasks to **Backlog** with the next unused ID (check both this file
  and `TASKS_ARCHIVE.md` for the highest one used). IDs are never reused,
  even if a task is dropped.

## In Progress

## Backlog

## Done

Completed tasks are archived in `TASKS_ARCHIVE.md` (currently through T012).

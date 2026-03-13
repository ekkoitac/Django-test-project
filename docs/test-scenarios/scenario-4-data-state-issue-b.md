# Test Scenario 4 — Data/State Issue B (Category A)

**What this tests:** A second Category A scenario. The agent must classify the
crash as a *data/state issue* (Axis 1, Axis 2 = unexpected null from missing
FK / corrupt record), skip opening a pull request, apply label
`ops-remediation-needed`, and post a detailed ops-remediation comment. No
code change is needed. No regression should be detected.

---

## Background — the planted data state

The `task_detail` view calls `Task.objects.get(id=task_id)` and then renders:

```python
task = Task.objects.get(id=task_id)
return render(request, 'tasks/task_detail.html', {'task': task})
```

The template references `{{ task.title }}` and `{{ task.created_at }}`.
This path is normally safe. However, a direct SQLite edit was performed in
production to bulk-delete old tasks using:

```sql
DELETE FROM tasks_task WHERE id < 20;
```

Several users bookmarked direct task URLs (e.g. `/task/7/`, `/task/12/`).
When they visit those URLs now, Django tries to load a task that no longer
exists and raises `Task.DoesNotExist`.

> Note: `task_detail` uses raw `.get()` instead of `get_object_or_404`,
> which means the error surfaces as a 500 rather than a 404. However the root
> cause of the crash spike is the missing rows in the database, not the
> missing guard — fixing the guard would turn 500s into 404s but the broken
> bookmarks issue would remain. This is a data/state issue (Category A):
> the operations team must communicate to users that old tasks were removed,
> and/or restore the deleted rows from backup.

The code defect (missing `get_object_or_404`) is a **secondary observation**
and must NOT be the basis for opening a PR in this triage scenario.

---

## Simulated GitHub Issue Body (Path A — Sentry bot format)

### Issue title (exact)
```
Task.DoesNotExist: Task matching query does not exist.
```

### Issue body (paste verbatim)

```markdown
## Overview

**`Task.DoesNotExist: Task matching query does not exist.`**

| | |
|--|--|
| **Culprit** | `tasks.views in task_detail` |
| **Last seen** | 2026-03-12T15:44:00Z |
| **First seen** | 2026-03-12T14:20:00Z |
| **Times seen** | 31 |
| **Users affected** | 18 |
| **Assigned** | Unassigned |

## Stack Trace

```
File "tasks/views.py", line 91, in task_detail
    task = Task.objects.get(id=task_id)

  File "django/db/models/manager.py", line 85, in manager_method
    return getattr(self.get_queryset(), name)(*args, **kwargs)

  File "django/db/models/query.py", line 496, in get
    raise self.model.DoesNotExist(

tasks.models.Task.DoesNotExist: Task matching query does not exist.
```

## Context

Crash began at 14:20 UTC immediately after a database maintenance window.
During maintenance, tasks with id < 20 were bulk-deleted from the SQLite
database using a direct SQL DELETE statement to purge old test data.
Multiple users had bookmarked direct task detail URLs (e.g. /task/7/).
All requests to detail pages for deleted tasks now produce a 500.
The index, search, add, toggle and delete views all work correctly.
New tasks can be created and viewed without issue.

Severity: error

https://sentry.io/organizations/demo-org/issues/99004/events/112233445566/
```

---

## Path B equivalent (GitHub Issue Form)

Use the **Manual Triage Request** form. Fill in the fields as follows:

| Field | Value |
|-------|-------|
| **Issue Type** | Data Issue |
| **Exception / Error** | `Task.DoesNotExist: Task matching query does not exist.` |
| **Culprit** | `tasks/views.py in task_detail` |
| **Severity** | error |
| **Affected Instance** | production |
| **Description** | Tasks with id < 20 were bulk-deleted directly in SQLite during maintenance. Users with bookmarked task detail URLs (e.g. /task/7/) now hit 500s because those rows no longer exist. The index page works fine. |
| **Stack Trace** | *(paste the stack trace from above)* |

---

## Expected Agent Behaviour — Verification Checklist

After the agent runs, verify each item:

### Classification
- [ ] Agent correctly identifies **Axis 1 = Data/state issue** (rows deleted from DB)
- [ ] Agent correctly identifies **Axis 2 = Corrupt or missing record** (bulk DELETE removed task rows that users still reference)
- [ ] Agent classifies as **Category A — no code PR needed**
- [ ] Agent may note the secondary observation that `get_object_or_404` would improve the UX (500 → 404), but does NOT open a PR for it in this triage run

### Labels
- [ ] Label `ops-remediation-needed` applied to the issue
- [ ] Label `sentry-triage-code-fix` is **NOT** applied
- [ ] Label `potential-regression` is **NOT** applied

### No PR
- [ ] Agent does **NOT** open a pull request
- [ ] Agent does **NOT** modify any source file

### Impact Analysis comment
- [ ] Comment posted with `## Impact Analysis` header
- [ ] Impact level stated as **Medium** (secondary view `task_detail` broken; core views unaffected)
- [ ] Affected endpoint listed: `GET /task/<id>/` → `task_detail`
- [ ] Background tasks: "none"
- [ ] Tests: agent found `tasks/tests.py` (empty) or reported "none found"

### Ops Remediation comment
- [ ] Comment posted with `## Automated Triage Analysis` header
- [ ] Root Cause Axis 1 and Axis 2 clearly stated
- [ ] "No code change required" stated
- [ ] Remediation steps include **at least one** of:
  - Restore the deleted rows from a database backup
  - Inform affected users that the task URLs are no longer valid
  - Optionally: patch `task_detail` to use `get_object_or_404` to improve error UX (framed as a follow-up, not as the fix)
- [ ] Confidence level stated (should be **High** — all fields present)

### Not expected
- [ ] No test file created or modified
- [ ] No `tasks/views.py` changes

---

## Why Category A and not Category B?

The crash is caused by missing rows in the database, not by incorrect code.
The `task_detail` view correctly attempts to load a task by ID. The rows simply
do not exist because they were deleted. Fixing the code to use
`get_object_or_404` would change a 500 into a 404, which is a valid improvement,
but it does not restore the data or fix the bookmarks — it is a separate,
lower-priority code cleanup that belongs in a different PR. The immediate
operational problem is data absence, making this Category A.

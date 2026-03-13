# Test Scenario 5 — Code Fix B (Category B)

**What this tests:** A second Category B scenario. The agent must classify the
crash as a *code defect*, open a draft PR with the fix, generate regression
tests, post an impact analysis comment, and apply the correct label. No
regression should be detected (the bug was present from the start).

---

## Background — the planted bug

`tasks/views.py` → `task_detail` view uses a raw `.get()` call:

```python
# Committed as part of initial code — raises Task.DoesNotExist on invalid IDs
task = Task.objects.get(id=task_id)
```

Visiting `/task/99999/` (or any non-existent task ID) raises an unhandled
`Task.DoesNotExist` exception, returning a 500 to the client instead of a
proper 404. The fix is `get_object_or_404(Task, id=task_id)`.

> This is a code defect scenario — the bug is triggered by a valid code path
> with any non-existent ID, not by missing data from a bulk delete or other
> operational issue. The ID supplied by the test user is intentionally invalid.

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
| **Last seen** | 2026-03-12T09:30:00Z |
| **First seen** | 2026-03-10T11:00:00Z |
| **Times seen** | 52 |
| **Users affected** | 27 |
| **Assigned** | Unassigned |

## Stack Trace

```
File "tasks/views.py", line 91, in task_detail
    task = Task.objects.get(id=task_id)

  File "django/db/models/query.py", line 496, in get
    raise self.model.DoesNotExist(

tasks.models.Task.DoesNotExist: Task matching query does not exist.
```

## Context

Users typing task IDs directly into the URL bar, clicking broken links, or
following URLs from shared messages that reference deleted or never-created
task IDs all hit this 500. There is no data integrity problem — the IDs
simply do not exist in the database. The view is missing the standard Django
guard: it calls Task.objects.get() directly instead of get_object_or_404(),
so an invalid ID raises Task.DoesNotExist as an unhandled exception rather
than returning a proper 404 Not Found response.
All other views work correctly. Only task detail pages for invalid IDs crash.

Severity: error

https://sentry.io/organizations/demo-org/issues/99005/events/aabbcc998877/
```

---

## Path B equivalent (GitHub Issue Form)

Use the **Manual Triage Request** form. Fill in the fields as follows:

| Field | Value |
|-------|-------|
| **Issue Type** | Bug |
| **Exception / Error** | `Task.DoesNotExist: Task matching query does not exist.` |
| **Culprit** | `tasks/views.py in task_detail` |
| **Severity** | error |
| **Affected Instance** | *(leave blank)* |
| **Description** | Visiting /task/<id>/ with any non-existent task ID returns a 500. The view uses Task.objects.get() instead of get_object_or_404(). All other views are unaffected. |
| **Stack Trace** | *(paste the stack trace from above)* |

---

## Expected Agent Behaviour — Verification Checklist

After the agent runs, verify each item:

### Classification
- [ ] Agent correctly identifies **Axis 1 = Code defect** (missing `get_object_or_404` guard)
- [ ] Agent classifies as **Category B — code PR needed**
- [ ] Agent does **NOT** classify as data issue (the data is fine; the code is missing a guard)

### Labels
- [ ] Label `sentry-triage-code-fix` applied to the issue
- [ ] Label `ops-remediation-needed` is **NOT** applied
- [ ] Label `potential-regression` is **NOT** applied (this was present from the start)

### Regression detection
- [ ] Agent does NOT set `REGRESSION_DETECTED=true`
- [ ] `## Regression Detection` section is **absent** from the PR description

### Impact Analysis comment
- [ ] Comment posted with `## Impact Analysis` header before any code changes
- [ ] Impact level stated as **Medium** (secondary view `task_detail` broken; core views unaffected)
- [ ] Endpoint `GET /task/<id>/` → `task_detail` listed as affected
- [ ] Background tasks: "none"
- [ ] Tests: agent found `tasks/tests.py` or reported "none found"

### Code fix (tasks/views.py)
- [ ] `task = Task.objects.get(id=task_id)` replaced with `task = get_object_or_404(Task, id=task_id)`
- [ ] `get_object_or_404` is already imported at the top of the file — no import change required
- [ ] No other lines changed in `tasks/views.py`
- [ ] No other files modified except `tasks/tests.py`

### Draft PR
- [ ] PR opened as a **draft**
- [ ] Branch named `fix/sentry-task-doesnotexist-<run_id>` (or similar slug)
- [ ] PR title: `fix: Task.DoesNotExist: Task matching query does not exist. (Sentry auto-triage)`
- [ ] `Closes #<issue_number>` present in PR body
- [ ] Sentry URL present in PR body
- [ ] `## Tests Added` section present listing the test file

### Test generation (tasks/tests.py)
The agent must add at minimum these three tests to `tasks/tests.py`:

| Test | What it verifies |
|------|-----------------|
| Crash scenario | `GET /task/99999/` returns 500 **before** the fix (document the bug) |
| Fix scenario | `GET /task/99999/` returns 404 **after** the fix |
| Edge case | `GET /task/<valid_id>/` returns 200 for an existing task |

Check that:
- [ ] Tests use `django.test.TestCase` (not pytest)
- [ ] Tests use `self.client.get(reverse('task_detail', args=[...]))`
- [ ] Each test has a one-line docstring
- [ ] Tests do NOT test model internals directly — only HTTP behaviour

---

## Why Category B and not Category A?

The database is fine. The crash happens on any request to `/task/<id>/` where
the ID does not exist in the database — which is a normal and expected
occurrence (typo in URL, stale bookmark, deleted task). The view should return
a 404, not a 500. This is a textbook code defect: a missing `get_object_or_404`
guard that has been in the code from the start.

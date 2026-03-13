# Test Scenario 6 — Regression B (Category B + Regression Detection)

**What this tests:** A second regression scenario. The agent must classify the
crash as a *code defect introduced by a specific recent commit*, set
`REGRESSION_DETECTED=true`, include the `## Regression Detection` section in
the PR description, apply label `potential-regression`, request review from the
regression author in addition to `ramya-co/ops-team`, generate tests, and post
an impact analysis comment.

---

## Background — the planted regression

A new branch `feat/search-completed-filter` adds a completion-status filter to
the `search_tasks` view in `tasks/views.py`.

The commit on that branch introduces:

```python
# Bug: direct dict access raises KeyError when ?completed= is absent
completed_filter = request.GET['completed']
if completed_filter == 'true':
    results = results.filter(completed=True)
elif completed_filter == 'false':
    results = results.filter(completed=False)
```

After this branch is merged to `main`, any visit to `GET /search/` (including
the default search with no `?completed=` param) raises:

```
KeyError: 'completed'
```

The fix is `completed_filter = request.GET.get('completed', '')`.

Prior to the merge, `GET /search/` worked correctly. This is a clean regression
introduced by the feature commit.

---

## How to set up this test

1. The branch `feat/search-completed-filter` has been pushed to the repository
   with the regression commit already on it.
2. Open a PR from `feat/search-completed-filter` → `main` and merge it.
3. After merging, create a GitHub issue using the **Manual Triage Request** form
   (or let the Sentry bot create one) with the details below.
4. The agent should detect the regression by inspecting `git log` and the
   recent merge commit.

---

## Simulated GitHub Issue Body (Path A — Sentry bot format)

### Issue title (exact)
```
KeyError: 'completed'
```

### Issue body (paste verbatim)

```markdown
## Overview

**`KeyError: 'completed'`**

| | |
|--|--|
| **Culprit** | `tasks.views in search_tasks` |
| **Last seen** | 2026-03-12T20:15:00Z |
| **First seen** | 2026-03-12T19:45:00Z |
| **Times seen** | 47 |
| **Users affected** | 23 |
| **Assigned** | Unassigned |

## Stack Trace

```
File "tasks/views.py", in search_tasks
    completed_filter = request.GET['completed']
KeyError: 'completed'
```

## Context

Every visit to /search/ — with or without a search query — now returns a 500.
This started approximately 30 minutes ago and coincides with a merge of
feat/search-completed-filter into main. Prior to the merge, the search page
worked correctly. The crash occurs because the new completion filter code
accesses request.GET['completed'] directly instead of using .get() with a
default, so any request without ?completed= in the query string raises KeyError.

Severity: error

https://sentry.io/organizations/demo-org/issues/99006/events/ffeeddccbbaa/
```

---

## Path B equivalent (GitHub Issue Form)

Use the **Manual Triage Request** form. Fill in the fields as follows:

| Field | Value |
|-------|-------|
| **Issue Type** | Bug |
| **Exception / Error** | `KeyError: 'completed'` |
| **Culprit** | `tasks/views.py in search_tasks` |
| **Severity** | error |
| **Affected Instance** | *(leave blank)* |
| **Description** | Every request to /search/ raises KeyError: 'completed'. Started after merging feat/search-completed-filter. The new completion filter uses direct dict access on request.GET instead of .get() with a default. |
| **Stack Trace** | *(paste the stack trace from above)* |

---

## Expected Agent Behaviour — Verification Checklist

After the agent runs, verify each item:

### Classification
- [ ] Agent correctly identifies **Axis 1 = Code defect** (missing `.get()` fallback on `request.GET`)
- [ ] Agent classifies as **Category B — code PR needed**
- [ ] Agent does **NOT** classify as data issue

### Regression detection
- [ ] Agent runs `git log --oneline -15 -- tasks/views.py` and identifies the merge commit from `feat/search-completed-filter`
- [ ] Agent sets `REGRESSION_DETECTED=true`
- [ ] `## Regression Detection` section is **present** in the PR description
- [ ] Introducing commit hash, author username, date, and associated PR number are all recorded
- [ ] Label `potential-regression` applied to the issue

### Labels
- [ ] Label `sentry-triage-code-fix` applied to the issue
- [ ] Label `potential-regression` applied to the issue
- [ ] Label `ops-remediation-needed` is **NOT** applied

### Impact Analysis comment
- [ ] Comment posted with `## Impact Analysis` header
- [ ] Impact level stated as **High** (search view completely broken for all users)
- [ ] Endpoint `GET /search/` → `search_tasks` listed as affected
- [ ] Background tasks: "none"
- [ ] Tests: agent found `tasks/tests.py` or reported "none found"

### Code fix (tasks/views.py)
- [ ] `completed_filter = request.GET['completed']` replaced with `completed_filter = request.GET.get('completed', '')`
- [ ] No other lines changed in `tasks/views.py`
- [ ] No other files modified except `tasks/tests.py`

### Draft PR
- [ ] PR opened as a **draft**
- [ ] Branch named `fix/sentry-keyerror-completed-<run_id>` (or similar slug)
- [ ] PR title: `fix: KeyError: 'completed' (Sentry auto-triage)`
- [ ] `Closes #<issue_number>` present in PR body
- [ ] Sentry URL present in PR body
- [ ] `## Regression Detection` section present with introducing commit details
- [ ] `## Tests Added` section present listing the test file
- [ ] Reviewer requested from `@<regression_author>` AND `ramya-co/ops-team`

### Reviewer assignment
- [ ] Review requested from `ramya-co/ops-team`
- [ ] Review ALSO requested from the individual author of the regression commit

### Test generation (tasks/tests.py)
The agent must add at minimum these three tests to `tasks/tests.py`:

| Test | What it verifies |
|------|-----------------|
| Crash scenario | `GET /search/` (no ?completed=) returns 500 before the fix |
| Fix scenario | `GET /search/` returns 200 after the fix |
| Edge case | `GET /search/?completed=true` returns 200 (filter works when param present) |

Check that:
- [ ] Tests use `django.test.TestCase` (not pytest)
- [ ] Tests use `self.client.get(reverse('search_tasks'))` and variants
- [ ] Each test has a one-line docstring
- [ ] Tests do NOT test `request.GET` internals directly — only HTTP behaviour

---

## Why REGRESSION_DETECTED=true?

The `git log` for `tasks/views.py` will show a recent commit from
`feat/search-completed-filter` that introduced the direct `request.GET['completed']`
access. Prior to that commit, `search_tasks` had no `completed_filter` code and
worked correctly. The regression was introduced by the feature branch merge,
making this a clear regression with a traceable introducing commit.

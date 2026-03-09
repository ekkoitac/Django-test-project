# Sentry Crash Triage — Copilot Agent Playbook

> **You are the Copilot coding agent.** A production crash has been detected.
> Your job is to find the root cause, apply the minimal correct fix, and open a
> **draft Pull Request** for human review. You must **never** auto-merge.
> You must **never** open a GitHub Issue as your output.

---

## 1 · Project Map

```
Django-test-project/
├── manage.py
├── requirements.txt
├── .env                        ← local secrets (git-ignored)
├── todoproject/                ← project config
│   ├── settings.py             ← Django settings; SENTRY_DSN loaded here
│   ├── urls.py                 ← root URL router  (admin/ + tasks/)
│   ├── wsgi.py
│   └── asgi.py
└── tasks/                      ← the Todo-list application
    ├── models.py               ← Task(id, title:str, completed:bool, created_at:datetime)
    ├── views.py                ← index, add_task, toggle_task, delete_task, export_tasks_csv
    ├── urls.py                 ← '', 'add/', 'toggle/<id>/', 'delete/<id>/', 'export/'
    ├── admin.py
    ├── migrations/
    └── templates/tasks/        ← base.html, index.html
```

**Framework & versions:** Django 6.x · SQLite · Python 3.x  
**No frontend framework** — plain Django templates.  
**Crash detection:** Sentry SDK via `SENTRY_DSN`; the Sentry GitHub integration creates a GitHub Issue which triggers this triage workflow.

---

## 2 · Reading the Sentry Culprit Field

Sentry sets `culprit` in one of these formats:

| Format | Example | Meaning |
|--------|---------|---------|
| `module.path in function` | `tasks.views in delete_task` | `tasks/views.py`, function `delete_task` |
| `module.path` | `tasks.models` | `tasks/models.py`, module-level code |
| `package.module in Class.method` | `tasks.views in TaskViewSet.destroy` | `tasks/views.py`, method `destroy` on `TaskViewSet` |

**Conversion rule:** replace every `.` with `/`, append `.py`, then strip the `in …` suffix for the file path.
---

## 2a · Extracting Crash Details from the GitHub Issue Body

Crash details now arrive as a GitHub Issue created by Sentry's native GitHub
integration (bot login: `sentry-io[bot]`). The structured `workflow_dispatch`
inputs no longer exist — you must parse the relevant fields from free text.

### Crash title
Use the **GitHub issue title** verbatim. It is set by Sentry to the exception
type and message, e.g. `KeyError: 'pending'`.

### Sentry URL
Scan the issue body for the first URL that matches `https://sentry.io/`.
This is the direct link to the Sentry issue's event detail page.

### Severity level
Look for one of the words `fatal`, `error`, or `warning` (case-insensitive)
in the issue body. If none is found, default to `error`.

### Culprit file and function
The culprit typically appears in the issue body in one of these forms:

| Pattern in body | Extraction |
|-----------------|------------|
| `tasks/views.py in delete_task` | file = `tasks/views.py`, fn = `delete_task` |
| `tasks.views in delete_task` | apply dot→slash + `.py` rule from §2 |
| A code block or stack trace line like `File "tasks/views.py", line 42, in delete_task` | file = `tasks/views.py`, fn = `delete_task` |

Steps:
1. Search the body for a line containing `in <identifier>` near a file path or module path.
2. Apply the conversion rule from §2 to obtain the file path and function name.
3. Verify the file exists in the repository (`ls <file_path>`).

### Fallback — culprit cannot be identified
If after the steps above you still cannot confidently identify the culprit file:
1. Extract the **exception type** from the crash title (e.g. `KeyError`, `ZeroDivisionError`).
2. Search the codebase: `grep -rn "raise \|except " tasks/ --include="*.py"` and look for code that could raise that exception type.
3. Cross-reference with the Sentry URL (open it if possible) for the full stack trace.
4. Narrow to the most plausible function, state your reasoning in the PR description, and proceed with the fix.
---

## 3 · Investigation Checklist — Complete Every Step

### Step 1 — Locate the culprit

1. Extract crash details from the GitHub issue body using the guidance in **§2a**.
2. Parse the culprit using the table in **§2** to get `<file_path>` and `<function_name>`.
3. Read the entire file (`cat <file_path>`).
4. Find the exact function/method.  If the function is not in that file, search: `grep -rn "def <function_name>" .`

### Step 2 — Understand the crash

Answer all three questions before writing a single line of code:

- **What is the operation?** (database query, attribute access, arithmetic, HTTP call, …)
- **What is the failure mode?** (KeyError, AttributeError, ZeroDivisionError, DoesNotExist, …)
- **What guard is missing or what assumption is violated?**

### Step 3 — Check git history

```bash
git log --oneline -20 -- <file_path>
```

- Identify commits that touched the crash site.
- Note any commit that removed a guard, changed a default, or altered the function signature.

### Step 4 — Check for related open issues / PRs

Search open issues for keywords from the crash title and culprit module.

- If a **duplicate** already has an open PR — add a comment to that PR with the new Sentry crash URL and **stop here**.
- If a duplicate issue has **no PR** — continue and reference that issue in your PR.

### Step 5 — Apply the fix

Rules:
- Make the **smallest correct change** possible.
- Match the existing code style exactly (see §4 below).
- Do NOT add new packages unless absolutely necessary; if you must, add them to `requirements.txt` with a pinned version.
- Do NOT modify unrelated files, refactor unrelated code, or change formatting outside the fix.

### Step 6 — Verify locally (mental or shell check)

- Trace through the fixed code path with the inputs that caused the crash.
- Confirm the guard/fix prevents the exception.
- Check that normal (non-crashing) inputs still work correctly.

---

## 4 · Code Style Reference

This project follows standard Django conventions. Match what you see:

```python
# views.py pattern — all task views follow this shape:
@require_POST
def action_name(request, task_id):
    task = get_object_or_404(Task, id=task_id)
    # … minimal logic …
    return redirect('index')
```

- Use `get_object_or_404` when looking up by primary key — never raw `.get()` without a try/except.
- Single blank line between top-level functions.
- Docstrings: `"""One-line description."""` format (matches existing views).
- No f-strings with complex expressions — keep them simple.

---

## 5 · PR Requirements (Mandatory)

### Branch name
```
fix/sentry-<slugified-crash-title>
```
Example: `fix/sentry-zerodivisionerror-delete-task`  
Slugify rule: lowercase, replace spaces and special chars with `-`, max 60 chars.

### PR must be a **draft** PR
Set `draft: true` in the API call. The human reviewer will mark it ready for review.

### PR title
```
fix: <crash title> (Sentry auto-triage)
```

### PR description — use this exact template

```markdown
## 🔴 Sentry Crash Fix

| Field | Value |
|-------|-------|
| **Crash title** | <title from GitHub issue> |
| **Culprit** | `<culprit extracted from issue body>` |
| **Severity** | <level extracted from issue body> |
| **Sentry URL** | [View crash](PASTE_FULL_SENTRY_HTTPS_URL_HERE_NO_ANGLE_BRACKETS) |
| **Triage issue** | Closes #<GitHub issue number that triggered this workflow> |

> **IMPORTANT for Sentry URL**: Replace `PASTE_FULL_SENTRY_HTTPS_URL_HERE_NO_ANGLE_BRACKETS` with the raw full URL exactly as extracted, e.g. `https://demo3n.sentry.io/organizations/...`. Do NOT wrap it in angle brackets `<>`. The format must be exactly `[View crash](https://...)` with no extra parentheses or brackets.

---

## Root Cause

<One clear paragraph: what went wrong, what input triggered it, what assumption was violated.>

## Fix Summary

<One paragraph: what exactly was changed and why it prevents the crash.>

## Changed Files

- `<file_path>` — <one-line description of the change>

## Code Diff Explanation

```<language>
# Before
<original code>

# After
<fixed code>
```

## Risk Assessment

- **Side effects:** <none / describe if any>
- **Edge cases covered:** <list them>
- **Edge cases NOT covered (requires follow-up):** <list or "none">

## Testing

To reproduce the original crash (before this fix):
```
<curl or Django shell command that triggers the crash>
```

To verify the fix:
```
<command that shows the crash no longer occurs>
```
```

---

## 6 · Hard Rules

| Rule | Detail |
|------|--------|
| ❌ No auto-merge | The PR must be a **draft**. Never mark it ready or merge it. |
| ❌ No issue as output | Do not open a new GitHub Issue. The issue that triggered you is the task brief — your only output is a draft PR. |
| ❌ No unrelated changes | If you notice other bugs while reading the code, do not fix them in this PR. |
| ❌ No new migration without a note | If your fix requires a schema change, call it out explicitly in the PR description and label it `needs-migration-review`. |
| ✅ Always reference Sentry URL | Include the Sentry URL (extracted from the issue body) in the PR description so the reviewer can see the real stack trace. |
| ✅ Always reference the triggering issue | Use `Closes #<N>` in the PR body so the GitHub issue is auto-closed when the PR merges. |

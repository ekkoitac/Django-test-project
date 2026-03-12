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
    ├── views.py                ← index, add_task, toggle_task, delete_task,
    │                              search_tasks, task_detail, export_tasks_csv
    ├── urls.py                 ← '', 'add/', 'toggle/<id>/', 'delete/<id>/'
    │                              'search/', 'task/<id>/', 'export/'
    ├── admin.py
    ├── migrations/
    └── templates/tasks/        ← base.html, index.html, search.html, task_detail.html
```

**Framework & versions:** Django 4.2 · SQLite · Python 3.x  
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

---

## 7 · Manual Issue Template

Human engineers may open a triage issue manually when a crash is not reported
by the Sentry bot. The **preferred and only supported method** is to use the
GitHub Issue Form at `.github/ISSUE_TEMPLATE/manual-triage.yml`. When someone
clicks **New Issue → Manual Triage Request** in the repository, GitHub renders
a structured form with dropdowns and text inputs and writes the submitted values
into the issue body automatically in a consistent format.

> ⚠️ The old raw markdown template (with `Type:`, `Exception:`, `Culprit:`
> inline markers) is **no longer in use**. The GitHub Issue Form replaces it.
> Do not look for those inline markers when parsing Path B issues.

### Issue Form output format

When the GitHub Issue Form is submitted, the body looks like this:

```markdown
### Issue Type

Bug

### Exception / Error

KeyError: 'popular'

### Culprit

tasks/views.py in index

### Severity

error

### Affected Instance

_No response_

### Description

Any request with ?sort=popular raises a KeyError...

### Stack Trace

\`\`\`python
File "tasks/views.py", line 17, in index
    order_field = sort_map[sort]
KeyError: 'popular'
\`\`\`
```

### Field extraction rules

Parse each field by locating its `### {Field Label}` heading and reading the
content that follows it (up to the next `###` heading or end of body):

| Field heading | Extracted value | Notes |
|---------------|-----------------|-------|
| `### Issue Type` | Dropdown value | One of: Bug, Crash, Data Issue, Config Issue |
| `### Exception / Error` | Single line | Full exception class and message |
| `### Culprit` | Single line | `file_path in function_name` format; may be `_No response_` if skipped |
| `### Severity` | Dropdown value | One of: fatal, error, warning |
| `### Affected Instance` | Single line or `_No response_` | Tenant/environment identifier |
| `### Description` | Multi-line text | All text between this heading and the next `###` |
| `### Stack Trace` | Code block | Python code block; may be absent |

**Detection:** Path B triage activates when the issue has the `manual-triage`
label (applied automatically by the form frontmatter) **or** when the body
contains all three of `### Exception / Error`, `### Issue Type`, and
`### Severity` headings.

**Partial-data handling:** If any field value is `_No response_` or absent,
triage proceeds with reduced confidence. The agent must explicitly state:
- Which fields were missing
- What assumptions were made to fill the gaps
- The overall confidence level (High / Medium / Low) per the rules in Step 2

---

## 8 · Fix Action Classification

After root cause analysis, classify the crash on two axes before deciding
whether to open a PR or post a remediation comment.

### Axis 1 — Root cause category

| Category | Description | Fix action |
|----------|-------------|------------|
| **Code defect** | Missing guard, wrong logic, unhandled exception path, type error, off-by-one, bad default | **Category B** — open a code PR |
| **Data/state issue** | Corrupt record, unexpected null, missing FK, stale cache, bad migration data | **Category A** — ops remediation |
| **Race condition** | Concurrent requests, missing lock, non-atomic multi-step operation | **Category A** — ops remediation |
| **External dependency failure** | Third-party API down, DB connection refused, storage error | **Category A** — ops remediation |

### Axis 2 — Data/state sub-cause (apply when Axis 1 = Data/state issue)

| Sub-cause | Remediation approach |
|-----------|---------------------|
| Corrupt or missing record | Run a data-repair script |
| Stale cache entry | Flush specific cache key or namespace |
| Bad migration data | Run a one-off data migration or fixup script |
| Unexpected null from external sync | Re-trigger sync job or patch record |

### Label to apply

| Category | GitHub label |
|----------|-------------|
| Category A | `ops-remediation-needed` |
| Category B | `sentry-triage-code-fix` |

---

## 9 · Impact Level Classification

Use these criteria when writing the Impact Analysis comment (Step 7 of the
workflow):

| Level | Criteria |
|-------|----------|
| **Critical** | Crash affects task creation, CSV export, or overall data integrity of the task list |
| **High** | Crash affects a core view: `index`, `add_task`, `toggle_task`, `delete_task`, or `export_tasks_csv` |
| **Medium** | Crash affects a secondary view (`search_tasks`, `task_detail`) or an edge-case input to a core view |
| **Low** | Crash affects a rare code path, a cosmetic issue, or an admin-only operation |

Always state which criterion was matched and why.

---

## 10 · Deduplication Check Instructions

Run all three checks **before** performing any root cause analysis.

### Check 1 — Open issue deduplication
Search open issues using the exception class name from the crash title as the
query string. Compare title and culprit module:
- **Exact match** (same exception class + same module): post a duplicate comment
  and stop.
- **Partial match** (same exception class, different module): continue triage
  but note the related issue in the impact analysis comment.

### Check 2 — Open PR deduplication
Search open pull requests for any PR whose branch or title references the
**culprit file** (`<file_path>`) or the **culprit function** (`<function_name>`).
Also search for open `fix/sentry-` branches.

If an open PR already exists that touches the crashing function:
- Post a comment on the new issue:
  ```
  ## Fix Already In Progress

  An open pull request already addresses this crash: #<pr_number>
  **PR:** #<pr_number> — <pr_title>

  Please review and merge that PR rather than opening a duplicate fix.
  If this crash has a different root cause, reopen with additional context.
  ```
- **Stop immediately.** Do not open a second PR.

### Check 3 — Recently merged PR → regression trigger
Search merged pull requests (last 30 days) whose **changed files** include the
culprit file (`<file_path>`) or whose title/branch references the culprit
function name.

For each matching merged PR:
1. Check whether that PR **introduced the crashing line** by running
   `git show <merge_commit_hash> -- <culprit_file>` and looking for the
   exact code that is now crashing (e.g. the direct `request.GET['key']`
   access, the unguarded lookup, the removed `.get()` call).
2. If the crashing line **was added or modified** by that merge:
   - This is a **regression** — set `REGRESSION_DETECTED=true`.
   - Record the PR number, commit hash, author, and date.
   - Continue to full triage (do NOT stop here).
3. If the merged PR **fixed** the crashing code (i.e. it removed or guarded
   the problematic line) but the crash is happening again:
   - Note in the impact analysis comment that a prior fix may not be
     deployed or may have been reverted.
   - Reduce triage confidence by one level (High → Medium, Medium → Low).
   - Continue to full triage.

---

## 11 · Regression Detection Instructions

A regression is defined as: a crash whose crashing line was **introduced or
modified by a recently merged Pull Request**. The introducing PR is the source
of truth — not just the raw git commit.

### Detection procedure

1. Run `git log --oneline -15 -- <culprit_file>` to get recent commits that
   touched the culprit file.
2. For each commit that touched the crashing function, run:
   ```bash
   git show <hash> -- <culprit_file>
   ```
   Find the commit whose diff **introduced or last modified the crashing line**
   (the line that raises the exception). "Introduced" includes:
   - Adding a direct dictionary lookup (`dict['key']`, `request.GET['key']`,
     `request.POST['key']`) with no `.get()` fallback
   - Adding new code that assumes a parameter or attribute is always present
   - Removing an existing `try/except`, `.get()` fallback, or `if` guard
   - Changing a default value or method signature in a breaking way
3. Once the introducing commit is identified, find the merged PR that contains
   it:
   ```bash
   gh pr list --state merged --search "<commit_hash>" --json number,title,mergedAt,author
   ```
   If the PR is found and was merged within the last 30 days:
   - Set `REGRESSION_DETECTED=true`.
   - Record the PR number, commit hash, merge date, and PR author.
4. If the introducing commit is **not** found in any merged PR (e.g. it was a
   direct push), treat the commit itself as the regression source and set
   `REGRESSION_DETECTED=true` using the commit author.
5. If the crashing line has existed unchanged for more than 30 commits and no
   recent PR introduced or modified it, `REGRESSION_DETECTED` remains `false` —
   this is an original bug, not a regression.

### Metadata to collect

```bash
git log --format="%H %ae %an %ad %s" --date=short -1 <hash>
```

Extract:
- `commit_hash` — full SHA
- `github_username` — derive from the author email if it is a
  `@users.noreply.github.com` address (format: `<id>+<username>@users.noreply.github.com`);
  otherwise use the author name as a best-effort handle
- `commit_date` — the author date in `YYYY-MM-DD` format
- `pr_number` — search merged PRs for the commit hash; if not found, write "not found"

### Effect on the PR

When `REGRESSION_DETECTED=true`:
1. Add label `potential-regression` to the **issue**.
2. Add label `potential-regression` to the **PR** as well.
3. Include the `## Regression Detection` section in the PR description (see
   Step 11 of the workflow).
4. Request review from `@{github_username}` in addition to `ramya-co/ops-team`.

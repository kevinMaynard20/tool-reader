# /list-tools

Scan the `.claude/` directory for task definition files and display them with their status.

## Usage

```
/list-tools
```

## What It Does

1. Scans the `.claude/` directory in the current project
2. Finds all `.md` files that contain task definitions
3. Parses each file to extract:
   - Title (from first `#` heading)
   - Description (first paragraph after title)
   - Checklist items (`[ ]` and `[x]` markers)
   - Completion percentage

## Output Format

```
## Task Files in .claude/

| File | Description | Status | Progress |
|------|-------------|--------|----------|
| PLUGIN_TASK.md | Create two plugins | IN_PROGRESS | 12/25 (48%) |
| AUTH_TASK.md | Add OAuth support | NOT_STARTED | 0/10 (0%) |
| DEPLOY.md | Deploy to production | COMPLETE | 5/5 (100%) |

Total: 3 task files
```

## Task Detection

A file is considered a task definition if it contains:
- At least one `[ ]` or `[x]` checkbox
- OR a section titled "## Checklist", "## Tasks", "## Steps", or "## TODO"

## Example

```
> /list-tools

Found 3 task files in .claude/:

1. **PLUGIN_TASK.md** - Plugin Creation & Deployment Task
   - Status: IN_PROGRESS
   - Progress: 12/25 (48%)

2. **AUTH_TASK.md** - Add OAuth Authentication
   - Status: NOT_STARTED
   - Progress: 0/10 (0%)

3. **DEPLOY.md** - Production Deployment
   - Status: COMPLETE
   - Progress: 5/5 (100%)
```

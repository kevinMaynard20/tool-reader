# /verify-tool

Check completion status of a task file without executing.

## Usage

```
/verify-tool <name>
```

Examples:
```
/verify-tool PLUGIN_TASK
/verify-tool auth-task
/verify-tool deploy
```

## What It Does

1. Reads `.claude/<name>.md`
2. Parses all checklist items
3. Counts completed (`[x]`) and uncompleted (`[ ]`) items
4. Reports status without making any changes

## Output Format

```
> /verify-tool PLUGIN_TASK

## Task Verification: PLUGIN_TASK.md

**Status**: IN_PROGRESS

| Metric | Count |
|--------|-------|
| Total Items | 25 |
| Completed | 12 |
| Remaining | 13 |
| Progress | 48% |

### Remaining Items:
1. [ ] Create tool-reader plugin structure
2. [ ] Implement /list-tools
3. [ ] Implement /run-tool
...
```

## Status Values

- **NOT_STARTED**: 0 items completed
- **IN_PROGRESS**: Some items completed, some remaining
- **COMPLETE**: All items completed (100%)

## Use Cases

1. **Check Progress**: See how much of a task is done
2. **Find Remaining Work**: List what still needs to be done
3. **Validate Completion**: Confirm all items are checked before marking complete

## Example

```
> /verify-tool DEPLOY

## Task Verification: DEPLOY.md

**Status**: COMPLETE

| Metric | Count |
|--------|-------|
| Total Items | 5 |
| Completed | 5 |
| Remaining | 0 |
| Progress | 100% |

All items completed!
```

## Notes

- This command is read-only and doesn't modify the task file
- Use `/run-tool` to actually execute uncompleted items
- Use `/list-tools` to see all available task files

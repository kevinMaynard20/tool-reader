# /run-tool

Execute a task definition from `.claude/<name>.md`.

## Usage

```
/run-tool <name>
```

Examples:
```
/run-tool PLUGIN_TASK
/run-tool auth-task
/run-tool deploy
```

## What It Does

1. Reads `.claude/<name>.md` (or `.claude/<name>` if already includes extension)
2. Parses the task file for checklist items
3. Identifies uncompleted items (`[ ]`)
4. Executes each item sequentially
5. Marks items as `[x]` when completed
6. Reports progress after each item

## Execution Flow

```
> /run-tool PLUGIN_TASK

Reading task: .claude/PLUGIN_TASK.md
Found 25 items (12 completed, 13 remaining)

Executing remaining items:

[13/25] Create tool-reader plugin structure
  - Creating directories...
  - Done!

[14/25] Implement /list-tools
  - Writing command file...
  - Done!

...

Task completed: 25/25 items done
```

## Task Item Format

The plugin recognizes these checklist formats:

```markdown
- [ ] Uncompleted item
- [x] Completed item
* [ ] Also works with asterisks
* [x] Completed with asterisk

| # | Task | Done |
|---|------|------|
| 1 | Task name | [ ] |
| 2 | Another task | [x] |
```

## Behavior

- **Sequential Execution**: Items are executed in order
- **Auto-Update**: The `.md` file is updated as items complete
- **Error Handling**: If an item fails, execution stops and status is reported
- **Resumable**: Run the command again to continue from where you left off

## Example Task File

```markdown
# My Task

## Checklist

- [ ] First step to complete
- [ ] Second step to complete
- [x] Already done step
- [ ] Final step
```

## Notes

- The `<name>` parameter should match the filename without `.md` extension
- If the file doesn't exist, an error is shown
- If all items are complete, a success message is shown

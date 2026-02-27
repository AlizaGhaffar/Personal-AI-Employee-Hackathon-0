# Skill: /ralph-loop

Run Claude autonomously in a loop until a multi-step task is fully complete. Stops when Claude signals `TASK_COMPLETE` or all files move to `Done/`. Safeguarded at 10 iterations max.

---

## Metadata

| Field      | Value                                            |
|------------|--------------------------------------------------|
| Command    | `/ralph-loop`                                    |
| Script     | `Ralph/ralph_loop.py`                            |
| Autonomy   | Fully autonomous — loops without human input     |
| Log        | `Logs/ralph_YYYY-MM-DD.log`                      |
| State file | `Ralph/state.json`                               |

---

## When to Use This Skill

- A task has multiple steps that can't be done in a single Claude pass
- User says "keep going until all files are processed"
- Needs_Action/ has a backlog that needs fully automated drain
- User wants Claude to self-correct and retry until the job is done
- Any task where "done" = files moved to Done/ or a clear completion signal

---

## How It Works (The Ralph Wiggum Pattern)

```
[1] Orchestrator starts Claude with the task prompt
[2] Claude works: reads files, calls tools, moves items
[3] Completion check:
     → Did Claude output TASK_COMPLETE?      → DONE ✓
     → Are new files in Done/ + queue empty? → DONE ✓
     → Needs_Action/ now empty?              → DONE ✓
     → None of the above                     → loop continues
[4] On loop: re-inject prompt + previous output (Claude sees its own work)
[5] Max 10 iterations → exit with warning if still incomplete
```

---

## Execution

### Run from terminal

```bash
python Ralph/ralph_loop.py "Process all files in Needs_Action/ and move to Done/"
python Ralph/ralph_loop.py "Triage all pending items" --max-iter 5
```

### From Claude (invoke the script)

```bash
python Ralph/ralph_loop.py "$TASK_DESCRIPTION"
```

---

## Completion Signals (checked in order)

| Priority | Signal                              | How                                          |
|----------|-------------------------------------|----------------------------------------------|
| 1st      | Promise-based                       | Claude outputs `TASK_COMPLETE` in response   |
| 2nd      | File movement + empty queue         | New files in `Done/` AND `Needs_Action/` empty |
| 3rd      | Queue cleared                       | `Needs_Action/` was non-empty, now empty     |

---

## Iteration Prompt Strategy

- **Iteration 1**: plain task + "output TASK_COMPLETE when done"
- **Iteration 2+**: task + last 1500 chars of previous output + "continue working"

Claude can see what it already tried, so it doesn't repeat the same steps.

---

## Logs & State

Every iteration appends to `Logs/ralph_YYYY-MM-DD.log`:
```
[2026-02-19 14:03:01] INFO | --- Iteration 1/10 ---
[2026-02-19 14:03:12] INFO | Output preview: Processed email_1.md → Done/
[2026-02-19 14:03:12] INFO | Not yet complete — continuing to iteration 2
[2026-02-19 14:03:24] INFO | ✓ TASK COMPLETE — Needs_Action/ is now empty
```

Current state saved to `Ralph/state.json` after every iteration.

---

## Safety

- Hard cap at `--max-iter` (default 10) — never infinite
- Each Claude call has a 5-minute timeout
- On Claude CLI failure: stops loop immediately, reports error
- Does not delete files — only moves through the standard pipeline
- On max iterations reached: logs warning with remaining file counts

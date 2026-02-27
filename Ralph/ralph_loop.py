#!/usr/bin/env python3
"""
Ralph Wiggum Loop
-----------------
Autonomous multi-step task executor for the Gold Tier AI Employee.

Runs Claude CLI in a loop until the task is complete or max iterations reached.

Completion Signals (checked in order):
  1. Promise-based  : Claude outputs TASK_COMPLETE in its response
  2. File movement  : New files appeared in Done/ AND Needs_Action/ is clear
  3. Empty queue    : Needs_Action/ has no remaining files

Reference: Hackathon Doc — Section 2D "Persistence (The Ralph Wiggum Loop)"

Usage:
  python Ralph/ralph_loop.py "Process all files in Needs_Action/"
  python Ralph/ralph_loop.py "Process all files" --max-iter 5
"""

import argparse
import json
import logging
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# ── Workspace Paths ────────────────────────────────────────────────────────────
WORKSPACE  = Path(__file__).resolve().parent.parent  # D:\hack0aliza-gold
DONE_DIR   = WORKSPACE / "Done"
NEEDS_DIR  = WORKSPACE / "Needs_Action"
LOGS_DIR   = WORKSPACE / "Logs"
RALPH_DIR  = WORKSPACE / "Ralph"

# ── Constants ──────────────────────────────────────────────────────────────────
COMPLETION_MARKER = "TASK_COMPLETE"
DEFAULT_MAX_ITER  = 10
CLAUDE_TIMEOUT    = 300  # seconds per iteration


# ── Logging ────────────────────────────────────────────────────────────────────

def setup_logging() -> logging.Logger:
    """Log to both console and Logs/ralph_YYYY-MM-DD.log"""
    LOGS_DIR.mkdir(exist_ok=True)
    log_file = LOGS_DIR / f"ralph_{datetime.now().strftime('%Y-%m-%d')}.log"

    logger = logging.getLogger("ralph")
    logger.setLevel(logging.DEBUG)

    fmt = logging.Formatter("[%(asctime)s] %(levelname)s | %(message)s", "%Y-%m-%d %H:%M:%S")

    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    ch = logging.StreamHandler(sys.stdout)
    ch.setFormatter(fmt)
    logger.addHandler(ch)

    return logger


# ── State Helpers ──────────────────────────────────────────────────────────────

def snapshot_dir(directory: Path) -> set[str]:
    """Return filenames in a directory (excludes hidden files)."""
    directory.mkdir(exist_ok=True)
    return {f.name for f in directory.iterdir() if f.is_file() and not f.name.startswith(".")}


def save_state(task: str, iteration: int, output: str) -> None:
    """Persist loop state to Ralph/state.json for debugging or resumption."""
    RALPH_DIR.mkdir(exist_ok=True)
    state = {
        "task":                 task,
        "iteration":            iteration,
        "timestamp":            datetime.now().isoformat(),
        "last_output_preview":  output[:500] if output else "",
    }
    (RALPH_DIR / "state.json").write_text(json.dumps(state, indent=2), encoding="utf-8")


# ── Claude Invocation ──────────────────────────────────────────────────────────

def run_claude(prompt: str, logger: logging.Logger) -> tuple[str, int]:
    """
    Call the Claude CLI in non-interactive (--print) mode.
    Returns (output_text, exit_code).
    exit_code < 0 means a local failure (timeout, not found, etc.)
    """
    try:
        result = subprocess.run(
            ["claude", "--print", prompt],
            capture_output=True,
            text=True,
            cwd=str(WORKSPACE),
            timeout=CLAUDE_TIMEOUT,
        )
        if result.stderr:
            logger.warning(f"Claude stderr: {result.stderr[:300]}")
        return result.stdout, result.returncode

    except subprocess.TimeoutExpired:
        logger.error(f"Claude timed out after {CLAUDE_TIMEOUT}s")
        return "", -1

    except FileNotFoundError:
        logger.error("'claude' not found in PATH. Is Claude Code installed?")
        return "", -2

    except Exception as exc:
        logger.error(f"Unexpected error running Claude: {exc}")
        return "", -3


# ── Completion Check ───────────────────────────────────────────────────────────

def check_completion(
    output: str,
    done_before: set[str],
    needs_before: set[str],
    logger: logging.Logger,
) -> tuple[bool, str]:
    """
    Return (is_complete, reason_string).

    Strategy 1 — Promise:     Claude printed TASK_COMPLETE
    Strategy 2 — File moved:  New files in Done/ AND Needs_Action/ now empty
    Strategy 3 — Queue clear: Needs_Action/ was non-empty, now fully empty
    """

    # 1. Promise-based
    if COMPLETION_MARKER in output:
        return True, "Claude signalled TASK_COMPLETE"

    done_now  = snapshot_dir(DONE_DIR)
    needs_now = snapshot_dir(NEEDS_DIR)
    new_done  = done_now - done_before

    # 2. Files moved AND queue empty
    if new_done and not needs_now:
        return True, f"{len(new_done)} file(s) moved to Done/ — Needs_Action/ is empty"

    # 3. Queue was non-empty at start, now empty (files may have moved elsewhere)
    if needs_before and not needs_now:
        return True, "Needs_Action/ is now empty"

    if new_done:
        logger.info(f"Partial progress — {len(new_done)} new in Done/, {len(needs_now)} still in Needs_Action/")

    return False, ""


# ── Build Prompt ───────────────────────────────────────────────────────────────

def build_prompt(task: str, iteration: int, previous_output: str) -> str:
    """
    Iteration 1:  Plain task + completion instruction.
    Iteration 2+: Append previous output so Claude can see what happened.
    """
    completion_instruction = (
        f"\n\nWhen ALL work is complete, output the exact text: {COMPLETION_MARKER}"
    )

    if iteration == 1:
        return task + completion_instruction

    context = (
        f"\n\n---\nPrevious attempt output (last 1500 chars):\n"
        f"{previous_output[-1500:].strip()}\n"
        f"---\n\n"
        f"Continue the task. Check Needs_Action/ for any remaining files."
    )
    return task + context + completion_instruction


# ── Main Loop ──────────────────────────────────────────────────────────────────

def ralph_loop(task: str, max_iterations: int = DEFAULT_MAX_ITER) -> bool:
    """
    Run Claude in a loop until task completion or max iterations.
    Returns True on success, False otherwise.
    """
    logger = setup_logging()

    logger.info("=" * 60)
    logger.info("RALPH WIGGUM LOOP — START")
    logger.info(f"Task        : {task}")
    logger.info(f"Max iters   : {max_iterations}")
    logger.info(f"Workspace   : {WORKSPACE}")
    logger.info("=" * 60)

    done_before  = snapshot_dir(DONE_DIR)
    needs_before = snapshot_dir(NEEDS_DIR)

    logger.info(f"Initial state — Done/: {len(done_before)} file(s) | Needs_Action/: {len(needs_before)} file(s)")

    if needs_before:
        logger.info(f"Files to process: {sorted(needs_before)}")

    previous_output = ""

    for iteration in range(1, max_iterations + 1):
        logger.info(f"--- Iteration {iteration}/{max_iterations} ---")

        prompt = build_prompt(task, iteration, previous_output)
        save_state(task, iteration, previous_output)

        output, exit_code = run_claude(prompt, logger)

        if exit_code < 0:
            logger.error(f"Claude invocation failed (code {exit_code}) — stopping loop")
            return False

        preview = output[:300].strip().replace("\n", " ")
        logger.info(f"Output preview: {preview}")

        complete, reason = check_completion(output, done_before, needs_before, logger)

        if complete:
            logger.info(f"✓ TASK COMPLETE — {reason}")
            logger.info(f"Finished in {iteration} iteration(s)")
            save_state(task, iteration, output)
            return True

        if iteration < max_iterations:
            logger.info(f"Not yet complete — continuing to iteration {iteration + 1}")
        previous_output = output

    # Max iterations exhausted
    done_final  = snapshot_dir(DONE_DIR)
    needs_final = snapshot_dir(NEEDS_DIR)
    logger.warning(f"MAX ITERATIONS ({max_iterations}) REACHED — task may be incomplete")
    logger.warning(f"Done/: {len(done_final)} file(s) | Needs_Action/: {len(needs_final)} file(s) remaining")
    logger.warning("Review Ralph/state.json and Logs/ for details")
    return False


# ── CLI Entry Point ────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Ralph Wiggum Loop — autonomous Claude task executor",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python Ralph/ralph_loop.py "Process all files in Needs_Action/ and move to Done/"
  python Ralph/ralph_loop.py "Triage inbox and create plans" --max-iter 5
        """,
    )
    parser.add_argument("task", help="Task description for Claude to execute autonomously")
    parser.add_argument(
        "--max-iter",
        type=int,
        default=DEFAULT_MAX_ITER,
        help=f"Maximum loop iterations (default: {DEFAULT_MAX_ITER})",
    )
    args = parser.parse_args()

    success = ralph_loop(args.task, args.max_iter)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

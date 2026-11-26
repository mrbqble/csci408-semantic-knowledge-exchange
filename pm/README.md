# Project management

- `backfill_board.py` created the milestones, the 50 issues and the Projects v2 board items on 26 Nov 2026 from the work the team actually did in fall 2026 (assignees, Start/End dates, status). It skips issues that already exist, so it is safe to re-run.
- `verify_board.py` checks the result (duplicates, assignees, Start/End, milestones).
- The September scripts `setup_project.py`, `share_project.py` and `clear_tasks.py` (repository root) set up the board, shared it with the team and removed the speculative issues created from the kickoff plan.

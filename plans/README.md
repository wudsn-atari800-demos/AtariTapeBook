# Plans

The plan files of the Atari Tape Book, one per batch of work, numbered in
the order they were created. A new plan takes the next free number and an
upper-case name (`NN_TOPIC_PLAN.md`), and gets a row in the table below.
Each plan carries its status in its first lines; this table is the overview.

| No. | Plan | Purpose | Status |
|---|---|---|---|
| 01 | [INTRO_DURING_LOADING_PLAN](01_INTRO_DURING_LOADING_PLAN.md) | Show the animated cassette intro while the tape loads: two-stage boot, intro in low memory protected by `MEMLO`, immediate VBI with double-buffered reel characters | Done 2026-11-14 |
| 02 | [LOADING_TEXT_PLAN](02_LOADING_TEXT_PLAN.md) | A "Loading" text with the name of the next section below the cassette: uppercase, digits and `.-:` at their standard OS font positions in the intro's font, no display list interrupt | Done 2026-11-14 |
| 03 | [BOOT_FADE_AND_TEXT_PLAN](03_BOOT_FADE_AND_TEXT_PLAN.md) | The pre-loader stops the motor, fades the boot screen to black and types `ATARI TAPE BOOK` (inverse) and `LOADING` before it continues loading the intro | Done 2026-11-14 |

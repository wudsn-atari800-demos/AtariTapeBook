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
| 04 | [SMALLER_BOOT_PLAN](04_SMALLER_BOOT_PLAN.md) | Make the records the OS loads smaller: BASIC entry points at a stable address below the font, show handling and finish code into the second stage, the title loaded by the pre-loader (1 boot record) | Done 2026-11-14 |
| 05 | [LOADER_MODULE_PLAN](05_LOADER_MODULE_PLAN.md) | Move the BASIC services (`loader_text`, `loader`, `syncer`) from `boot/Boot.asm` into a module `loader/Loader.asm`, as the intro is split; the jump table at 2042/2045 stays in `Boot.asm` | Done 2026-11-14 |

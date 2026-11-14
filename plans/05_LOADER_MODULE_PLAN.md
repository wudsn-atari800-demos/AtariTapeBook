# Plan: Move the chapter loader into its own module

Written 2026-11-14. Requested after plan 04, to split the code the BASIC
chapters call from the boot code, as the intro is split.

**Status: done 2026-11-14.**

## Current state

`boot/Boot.asm` holds two kinds of code:

| Kind | Code | Runs |
|---|---|---|
| Boot | header, `preloader`, `motor`, `wait`, `put_char`, `title`, `pause`, `show_intro`, `finish`, `booter`, `reset` | once, until BASIC starts (`reset` also after RESET) |
| BASIC services | `syncer` ($0770, 24 bytes, below the font), the jump table at $07FA, `loader_text` and `loader` (241 bytes, behind the intro) | whenever a chapter program calls USR 2042 or 2045 |

The services are the interface of the tape book for chapter programs and
will grow with the chapters. Their dependencies are small: `loader_text`
and `loader` use only `intro.on`, `intro.off`, `intro.set_text` and
`intro.loading_text`; `syncer` uses `motor` and `wait`.

## Proposal

1. **New module `loader/Loader.asm`** with `.local loader`, included by
   `boot/Boot.asm` behind `intro/Intro.asm`, where `loader_text` and
   `loader` are today. It holds the BASIC services without fixed
   addresses:
   - `load_text`, today's `loader_text`: USR 2042, reads the optional text
     and continues in `load`.
   - `load`, today's `loader`: types `CLOAD` and `RUN` through the E: hook,
     with its nested `read_char`.
   - `sync`, today's `syncer`: USR 2045, waits for the next cue.
   - A header comment like the intro's: what the module does, its entry
     points, what it needs from the boot file (`motor`, `wait`) and from
     the intro.
2. **The jump table stays in `boot/Boot.asm`.** Its fixed addresses are
   part of the memory layout, which `Boot.asm` describes, and an included
   file can be placed at only one address. It becomes `jmp
   loader.load_text` at `USR_LOADER` and `jmp loader.sync` at
   `USR_SYNCER`, with the `ert` checks for both addresses next to it.
3. **`syncer` moves into the module.** All BASIC services are then in one
   file. It costs about 24 bytes of BASIC memory, because `MEMLO` rises by
   the size of `sync`, and the space below $0800 grows to about 138 free
   bytes.
4. **`Boot.asm`'s header comment** describes the new memory order: boot
   record, second stage with the boot code and the jump table, intro,
   loader module.
5. **`.proc` conventions** as in the rest of the project: every
   self-contained routine is a proc, tail calls are `jmp`.

## Impact

- **`boot/Boot.asm`**: `syncer`, `loader_text` and `loader` go; the jump
  table targets change; `icl '../loader/Loader.asm'` behind the intro.
- **`loader/Loader.asm`**: new.
- **Unchanged**: the USR addresses 2042 and 2045, the BASIC programs, the
  tape format, `Bin2Wav.py`, `AtariTapeBookEquates.asm`, the boot records
  (still 1) and the pause record.
- **`TestChapters.py`**: it checks `basic_syncer` in `Boot.lab`; the label
  stays, so only references to `syncer` (if any) change.
- **Documentation**: the file list in the README, if it lists the sources.

## Costs and risks

- **Memory**: about 24 bytes less BASIC memory (point 3). Keeping `syncer`
  in `Boot.asm` avoids that, but splits the services across two files.
- **Naming**: "loader" next to "pre-loader". The pre-loader is part of the
  boot and stays in `Boot.asm`; the module's header comment makes the
  difference explicit. Alternatives: `chapter/Chapter.asm`,
  `basic/Basic.asm`.

## Test

- The boot records and the pause record are unchanged: 1 and 3.
- `test-chapters/TestChapters.bat` passes (syncer, LOADING text, colors).
- The real tape build passes its boot test.

## Decisions

Made 2026-11-14:

- `syncer` moves into the module (point 3).
- The module is `loader/Loader.asm`.

## Result

- `loader/Loader.asm` holds `load_text` ($163C), `load` ($16AB) and `sync`
  ($172D); `booter` calls `loader.load`, the jump table jumps to
  `loader.load_text` and `loader.sync`.
- `MEMLO` rose by 24 bytes, from $172D to $1745. The boot records (1), the
  pause record (3) and the USR addresses (2042, 2045) are unchanged.
- `test-chapters/TestChapters.bat` passes, and so does the boot test of the
  real tape build.

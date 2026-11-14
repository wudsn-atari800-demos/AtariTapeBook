# Plan: Reels that speed up and slow down with the motor

Written 2026-11-14. Requested after plan 05: the reels of the intro shall
slow down and speed up to the current speed instead of jumping between
standstill and full speed.

**Status: done 2026-11-14.**

## Current state

`intro.animate`, called by the immediate VBI after `intro.start`, counts
`delay` down from `SPEED/2` and copies one chunk of the next frame each
time it reaches 0: with `SPEED` = 2 one chunk per VBI, one step every 2
VBIs. The reels run at this speed from `intro.start` on, whether the motor
runs or not, for example also after the boot stops the motor and before
CLOAD starts it again.

## Decisions

Made 2026-11-14:

- The reels follow the motor: motor on, they speed up to full speed; motor
  off, they slow down to standstill.
- A ramp from standstill to full speed, or back, takes about 1 s.

## Proposal

1. **Motor state from `PACTL`.** The VBI reads bit 3 of `PACTL`
   (`START_MOTOR` = $34 has it clear, `STOP_MOTOR` = $3C set). The control
   bits of the PIA read back as written, so the OS, the boot code and the
   loader need no changes.
2. **Speed as a rate, accumulated per VBI.** `animate` keeps two bytes,
   `rate` (0 to `MAX_RATE`) and `sum`. Every VBI it adds `rate` to `sum`;
   when `sum` reaches `THRESHOLD`, it subtracts `THRESHOLD` and copies the
   next chunk, as today. With `THRESHOLD = MAX_RATE*SPEED/2`, full speed
   (`rate` = `MAX_RATE`) is exactly today's speed, and every lower rate is
   proportionally slower, down to standstill at 0.
3. **Ramp.** Every VBI `rate` goes 1 up while the motor runs (up to
   `MAX_RATE`) and 1 down while it is off (down to 0). `MAX_RATE` =
   `RAMP_VBIS` = 50 gives a ramp of 1 s at 50 Hz (0.83 s at 60 Hz).
4. **Start values.** `rate` and `sum` start at 0, so the reels stand still
   until the motor runs; `intro.start` changes nothing else. A frame that
   is half copied when the reels stop stays hidden until the next step
   switches sets, so nothing shows a torn frame.
5. **Settings.** `SPEED` stays the number of VBIs per step at full speed;
   `RAMP_VBIS` is new at the top of `Intro.asm`. An `ert` checks that
   `sum + rate` fits into a byte (`THRESHOLD + MAX_RATE <= 256`).
6. **Demo.** `Intro-Demo.asm` has no tape to follow, so it switches the
   motor itself: on for 4 s, off for 2 s, in a loop. That shows both ramps
   (and runs a connected recorder, as loading would).

## Impact

- **`intro/Intro.asm`**: `animate` with `rate` and `sum` instead of
  `delay`, `RAMP_VBIS`, the `ert`, the header comment on the animation.
- **`intro/Intro-Demo.asm`**: the motor loop.
- **`intro/README.md`**: the description of the animation and its settings.
- **Unchanged**: the boot records and the pause record (`animate` is in the
  intro's animation part, loaded last), the loader, the BASIC programs, the
  tape format.

## Costs and risks

- **VBI time.** About 30 cycles more per VBI, far below one bit at 600
  baud (1.67 ms, about 3000 cycles), which limits the VBI during tape I/O.
- **Memory.** About 30 bytes more behind the intro; `MEMLO` rises
  accordingly.
- **Reels at the end of the boot.** `finish` starts the animation and stops
  the motor right after it, so the reels stay still until CLOAD starts the
  motor, then speed up. That matches the tape.

## Test

- `test-chapters/TestChapters.bat` passes.
- The real tape build passes its boot test.
- A probe in AltirraBridge reads `rate` while the tape loads (full speed)
  and after the motor stops (0).
- The demo in Altirra shows both ramps.

## Result

- Implemented as proposed. In addition, `intro.off` sets `rate` to 0: it
  removes the VBI while the reels may run at full speed, and the next
  `intro.on` comes while the motor is off, so the reels would otherwise
  start at full speed and slow down before CLOAD starts the motor.
- `MOTOR_OFF_MASK` (`START_MOTOR^STOP_MOTOR`, $08) is new in
  `AtariTapeBookEquates.asm`.
- `MEMLO` rose by 43 bytes, from $1745 to $1770. The boot records (1) and
  the pause record (3) are unchanged.
- Probe on the tape: the reels stand still until the boot has loaded
  everything; CLOAD of each chapter starts the motor, and `rate` goes from
  0 to 50 in 1 s. On the tape the motor does not stop while the intro is
  shown, so the slowdown shows only in the demo, where `rate` goes from 50
  to 0 in 1 s after each motor stop.
- `test-chapters/TestChapters.bat` passes, and so does the boot test of the
  real tape build.

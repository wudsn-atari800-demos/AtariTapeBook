#!/usr/bin/env python3
"""End-to-end test of the sync co-track with the BASIC syncer of the boot code.

The test tape consists of the boot file, the load section C1 and the run
section C1A.  C1.BAS waits for three cues through basic_syncer:

    10 PRINT "SYNC TEST"
    20 FOR N=1 TO 3
    30 X=USR(1554)
    40 PRINT "CUE ";N
    50 NEXT N
    60 PRINT "DONE"

C1A.TXT holds three cues at 2.0, 6.5 and 11.0 s.  C1.WAV is played while
C1.BAS loads, a rising tone sequence.  C1A.WAV is the audio of the run
section, a short beep at every cue.  Both are 8-bit mono files at 22050 Hz
and part of the repository.  They are written again with --write-audio,
for example after changing the cues.

The test
1. assembles the boot code and checks that basic_syncer is still at 1554,
   the address C1.BAS calls,
2. builds the tape with Bin2Wav.py, which also runs its boot check,
3. plays the tape in the headless AltirraBridgeServer at real tape speed
   (SIO patch off) and reads the screen,
4. checks that exactly three cues and DONE appear, with the cue spacing
   of C1A.TXT.

The tape is kept as TestChapters.wav, so PlayChapters.bat can play it in Altirra.

mads, Java, TURGEN and AltirraBridgeServer must be in the PATH, see
Make-Settings.bat.

Usage:
    python test-chapters/TestChapters.py [--write-audio]
"""

import argparse
import math
import os
import re
import subprocess
import sys
import tempfile
import wave

TEST_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(TEST_DIR)
sys.path.insert(0, PROJECT_DIR)
import Bin2Wav  # noqa: E402

SYNCER_ADDRESS = 1554          # the address C1.BAS calls with USR
CUES = 3
AUDIO_SECONDS = 15.0
SPACING_TOLERANCE_S = 0.3
TAPE_MARGIN_S = 20             # emulated time after the end of the tape


def assemble_boot(tmp):
    sec, lab = os.path.join(tmp, "Boot.sec"), os.path.join(tmp, "Boot.lab")
    r = subprocess.run(["mads", os.path.join(PROJECT_DIR, "boot", "Boot.asm"), f"-o:{sec}", f"-t:{lab}"],
                       capture_output=True, text=True)
    if r.returncode != 0 or not os.path.exists(sec):
        sys.stderr.write(r.stdout + r.stderr)
        raise SystemExit("assembling boot/Boot.asm failed")
    with open(lab) as f:
        m = re.search(r"^\S+\s+([0-9A-F]{4})\s+BASIC_SYNCER\s*$", f.read(), re.MULTILINE | re.IGNORECASE)
    if not m:
        raise SystemExit("label basic_syncer not found in boot/Boot.asm")
    address = int(m.group(1), 16)
    if address != SYNCER_ADDRESS:
        raise SystemExit(f"basic_syncer is at {address}, but test-chapters/C1.BAS calls USR({SYNCER_ADDRESS})")
    return sec


def read_cues():
    return Bin2Wav.read_cues(os.path.join(TEST_DIR, "C1A.TXT"))


AUDIO_RATE = 22050
LOAD_AUDIO_SECONDS = 3.0


def write_audio(path, seconds, tones):
    """Write an 8-bit mono .wav with sine tones given as (start s, length s, frequency Hz)."""
    samples = [0.0] * int(seconds * AUDIO_RATE)
    for start, length, frequency in tones:
        first = int(start * AUDIO_RATE)
        for i in range(int(length * AUDIO_RATE)):
            samples[first + i] = 0.5 * math.sin(2 * math.pi * frequency * i / AUDIO_RATE)
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(1)
        w.setframerate(AUDIO_RATE)
        w.writeframes(bytes(128 + int(127 * v) for v in samples))


def write_test_audio(cues):
    # C1.WAV: four rising tones while C1.BAS loads.
    write_audio(os.path.join(TEST_DIR, "C1.WAV"), LOAD_AUDIO_SECONDS,
                [(0.5 * n, 0.4, 440 * 2 ** (n / 4)) for n in range(4)])
    # C1A.WAV: a 0.2 s beep at every cue.
    write_audio(os.path.join(TEST_DIR, "C1A.WAV"), AUDIO_SECONDS, [(t, 0.2, 880) for t in cues])


def build_tape(boot, output):
    r = subprocess.run([sys.executable, os.path.join(PROJECT_DIR, "Bin2Wav.py"), "--short-irg", "--short-leader",
                        boot, os.path.join(TEST_DIR, "C1"), os.path.join(TEST_DIR, "C1A"), output],
                       capture_output=True, text=True)
    sys.stdout.write("".join(line + "\n" for line in r.stdout.splitlines() if not line.startswith("  record")))
    if r.returncode != 0:
        sys.stderr.write(r.stderr)
        raise SystemExit("building the test tape failed")
    with wave.open(output) as w:
        return w.getnframes() / w.getframerate()


def screen_lines(a):
    savmsc = a.peek16(0x58)
    raw = a.peek(savmsc, 40 * 24)
    lines = []
    for row in range(24):
        chars = []
        for code in raw[row * 40:(row + 1) * 40]:
            code &= 0x7F
            code = code + 0x20 if code < 0x40 else (code - 0x40 if code < 0x60 else code)
            chars.append(chr(code) if 32 <= code < 127 else "?")
        lines.append("".join(chars).strip())
    return lines


def play_tape(tape, seconds):
    """Play the tape and return {screen line: emulated time of its first appearance}."""
    server_dir = Bin2Wav.folder_in_path("AltirraBridgeServer", "--server-dir")
    sys.path.insert(0, os.path.join(server_dir, "sdk", "python"))
    from altirra_bridge import AltirraBridge  # noqa: E402

    proc, token_file = Bin2Wav.start_server(server_dir)
    seen = {}
    try:
        with AltirraBridge.from_token_file(token_file) as a:
            a.config("basic", "on")
            a.config("casautoboot", "on")
            a.config("siopatch", "off")             # load at real tape speed
            a.boot(tape)
            fps = 50 if a.peek(0xD014, 1)[0] & 0x0E == 0 else 60
            step = 5
            for frame in range(0, int((seconds + TAPE_MARGIN_S) * fps), step):
                a.frame(step)
                for line in screen_lines(a):
                    if line and line not in seen:
                        seen[line] = (frame + step) / fps
                if "DONE" in seen:
                    break
            a.quit()
    finally:
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
    return seen


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--write-audio", action="store_true", help="write C1.WAV and C1A.WAV again before the test")
    args = p.parse_args()
    cues = read_cues()
    if len(cues) != CUES:
        raise SystemExit(f"test-chapters/C1A.TXT must contain {CUES} cues, found {len(cues)}")
    if args.write_audio:
        write_test_audio(cues)
    for name in ("C1.WAV", "C1A.WAV"):
        if not os.path.exists(os.path.join(TEST_DIR, name)):
            raise SystemExit(f"test-chapters/{name} is missing; write it with --write-audio")
    tape = os.path.join(TEST_DIR, "TestChapters.wav")     # kept for PlayChapters.bat
    with tempfile.TemporaryDirectory() as tmp:
        boot = assemble_boot(tmp)
        seconds = build_tape(boot, tape)
        seen = play_tape(tape, seconds)

    for line, t in sorted(seen.items(), key=lambda item: item[1]):
        print(f"  {t:6.1f} s: {line}")
    errors = []
    times = [seen.get(f"CUE {n}") for n in range(1, CUES + 1)]
    for n, t in enumerate(times, 1):
        if t is None:
            errors.append(f"CUE {n} did not appear")
    if f"CUE {CUES + 1}" in seen:
        errors.append(f"more than {CUES} cues were reported")
    if "DONE" not in seen:
        errors.append("DONE did not appear")
    if None not in times:
        for n in range(1, CUES):
            expected = cues[n] - cues[n - 1]
            actual = times[n] - times[n - 1]
            if abs(actual - expected) > SPACING_TOLERANCE_S:
                errors.append(f"CUE {n} to CUE {n + 1}: {actual:.2f} s, expected {expected:.2f} s")
    if errors:
        for e in errors:
            print("FAIL:", e)
        return 1
    print(f"PASS: {CUES} cues with the expected spacing, then DONE")
    return 0


if __name__ == "__main__":
    sys.exit(main())

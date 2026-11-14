#!/usr/bin/env python3
"""End-to-end test of the sync co-track with the BASIC syncer of the boot code.

The test tape consists of the boot file, the load section C1 and the run
section C1A.  C1.BAS prints the text of every section, which is spoken at
the same time, and waits for the section's cue through basic_syncer:

    10 PRINT "SYNC TEST"
    20 PRINT "This is the first section of the test."
    30 X=USR(1554):PRINT "CUE 1"
    40 PRINT "This is section two, which ends with the second cue."
    50 X=USR(1554):PRINT "CUE 2"
    60 PRINT "This is section three, which ends with the third cue."
    70 X=USR(1554):PRINT "CUE 3"
    80 PRINT "DONE"

C1A.TXT holds three cues at 3.0, 7.5 and 12.0 s, with the section texts as
labels; they must match the texts in C1.BAS.  C1.WAV is played while C1.BAS
loads, a spoken introduction.  C1A.WAV is the audio of the run section: the
label text of every cue is spoken before the cue and ends shortly before
its pulse, so the screen changes when the text has been spoken.  Both are
8-bit mono files at 22050 Hz and part of the repository.  They are written again
with --write-audio, for example after changing the cues, using the Windows
speech synthesizer.

The test
1. assembles the boot code and checks that basic_syncer is still at 1554,
   the address C1.BAS calls,
2. builds the tape with Bin2Wav.py, which also runs its boot check,
3. plays the tape in the headless AltirraBridgeServer at real tape speed
   (SIO patch off) and reads the screen,
4. checks that exactly three cues and DONE appear, with the cue spacing
   of C1A.TXT, and that the text of every section appears after the
   previous cue and before its own cue,
5. checks that the intro (intro/Intro.asm, loaded by the boot file) is on
   screen while C1.BAS loads, with the text LOADING below the cassette, and
   off when it runs.

The tape is kept as TestChapters.wav, so PlayChapters.bat can play it in Altirra.

mads, Java, TURGEN and AltirraBridgeServer must be in the PATH, see
Make-Settings.bat.

Usage:
    python test-chapters/TestChapters.py [--write-audio]
"""

import argparse
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
TEXT_PREFIX = 20               # characters of a section text compared on the screen
TAPE_MARGIN_S = 20             # emulated time after the end of the tape


def assemble_boot(tmp):
    sec, lab = os.path.join(tmp, "Boot.sec"), os.path.join(tmp, "Boot.lab")
    r = subprocess.run(["mads", os.path.join(PROJECT_DIR, "boot", "Boot.asm"), f"-o:{sec}", f"-t:{lab}"],
                       capture_output=True, text=True)
    if r.returncode != 0 or not os.path.exists(sec):
        sys.stderr.write(r.stdout + r.stderr)
        raise SystemExit("assembling boot/Boot.asm failed")
    labels = {}
    with open(lab) as f:
        for line in f:
            m = re.match(r"^\S+\s+([0-9A-F]{4})\s+(\S+)\s*$", line)
            if m:
                labels[m.group(2).upper()] = int(m.group(1), 16)
    for name in ("BASIC_SYNCER", "INTRO.DLIST", "INTRO.TEXT_LINE"):
        if name not in labels:
            raise SystemExit(f"label {name.lower()} not found in boot/Boot.asm")
    if labels["BASIC_SYNCER"] != SYNCER_ADDRESS:
        raise SystemExit(f"basic_syncer is at {labels['BASIC_SYNCER']}, "
                         f"but test-chapters/C1.BAS calls USR({SYNCER_ADDRESS})")
    return sec, labels["INTRO.DLIST"], labels["INTRO.TEXT_LINE"]


CUE_FILE = os.path.join(TEST_DIR, "C1A.TXT")
LOAD_SPEECH = "Sync test. The test program is loading. Then listen for the three cues."
AUDIO_RATE = 22050
SPEECH_GAP_S = 0.3             # silence between the end of a cue's speech and its pulse

# Windows speech synthesis, 8-bit mono at AUDIO_RATE, preferably with an English voice.
SPEAK_SCRIPT = f"""
Add-Type -AssemblyName System.Speech
$s = New-Object System.Speech.Synthesis.SpeechSynthesizer
$v = $s.GetInstalledVoices() | Where-Object {{ $_.Enabled -and $_.VoiceInfo.Culture.Name -like 'en-*' }} |
    Select-Object -First 1
if ($v) {{ $s.SelectVoice($v.VoiceInfo.Name) }}
$f = New-Object System.Speech.AudioFormat.SpeechAudioFormatInfo({AUDIO_RATE},
    [System.Speech.AudioFormat.AudioBitsPerSample]::Eight, [System.Speech.AudioFormat.AudioChannel]::Mono)
$s.SetOutputToWaveFile($env:SPEECH_FILE, $f)
$s.Speak($env:SPEECH_TEXT)
$s.Dispose()
"""


def read_cues():
    return Bin2Wav.read_cues(CUE_FILE)


def read_cue_labels():
    """Return (start time, label text) for every cue of the cue file."""
    labels = []
    with open(CUE_FILE, encoding="utf-8-sig") as f:
        for line in f:
            fields = line.strip().split("\t")
            if fields[0] and not fields[0].startswith("\\"):
                labels.append((float(fields[0]), fields[2] if len(fields) > 2 else ""))
    return sorted(labels)


def speak(text, tmp):
    """Return `text` spoken by the Windows speech synthesizer as 8-bit mono samples."""
    path = os.path.join(tmp, "speech.wav")
    r = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", SPEAK_SCRIPT],
                       env={**os.environ, "SPEECH_FILE": path, "SPEECH_TEXT": text},
                       capture_output=True, text=True)
    if r.returncode != 0 or not os.path.exists(path):
        sys.stderr.write(r.stdout + r.stderr)
        raise SystemExit(f"speech synthesis of '{text}' failed")
    with wave.open(path) as w:
        samples = w.readframes(w.getnframes())
    # Trim the silence the synthesizer puts before and after the speech.
    loud = [i for i, x in enumerate(samples) if abs(x - 128) > 4]
    return samples[loud[0]:loud[-1] + 1] if loud else samples


def write_speech(path, parts, seconds=0.0):
    """Write an 8-bit mono .wav with the speech samples of `parts` at their start times in seconds."""
    end = max([seconds] + [start + len(samples) / AUDIO_RATE + 0.5 for start, samples in parts])
    out = bytearray([128]) * int(end * AUDIO_RATE)
    for start, samples in parts:
        first = int(start * AUDIO_RATE)
        out[first:first + len(samples)] = samples
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(1)
        w.setframerate(AUDIO_RATE)
        w.writeframes(bytes(out))


def write_test_audio():
    with tempfile.TemporaryDirectory() as tmp:
        # C1.WAV: an introduction while C1.BAS loads.
        write_speech(os.path.join(TEST_DIR, "C1.WAV"), [(0.5, speak(LOAD_SPEECH, tmp))])
        # C1A.WAV: the label text of every cue, spoken before the cue so that it ends
        # SPEECH_GAP_S before the pulse; the screen changes when the text has been spoken.
        parts, section_start = [], 0.0
        for t, text in read_cue_labels():
            samples = speak(text, tmp)
            start = t - SPEECH_GAP_S - len(samples) / AUDIO_RATE
            if start < section_start:
                raise SystemExit(f"the speech '{text}' takes {len(samples) / AUDIO_RATE:.2f} s, but only "
                                 f"{t - SPEECH_GAP_S - section_start:.2f} s are free before the cue at {t:.2f} s")
            parts.append((start, samples))
            section_start = t + Bin2Wav.CUE_PULSE_S
        write_speech(os.path.join(TEST_DIR, "C1A.WAV"), parts, AUDIO_SECONDS)


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


def intro_text(a, text_line):
    """Return the intro's text line as a string, written in internal codes."""
    chars = []
    for code in a.peek(text_line, 40):
        code &= 0x7F
        code = code + 0x20 if code < 0x40 else (code - 0x40 if code < 0x60 else code)
        chars.append(chr(code) if 32 <= code < 127 else " ")
    return "".join(chars).strip()


def play_tape(tape, seconds, intro_dlist, text_line):
    """Play the tape and return {screen line: emulated time of its first appearance} and
    (emulated time, intro text) for every check at which the intro's display list was shown."""
    server_dir = Bin2Wav.folder_in_path("AltirraBridgeServer", "--server-dir")
    sys.path.insert(0, os.path.join(server_dir, "sdk", "python"))
    from altirra_bridge import AltirraBridge  # noqa: E402

    proc, token_file = Bin2Wav.start_server(server_dir)
    seen, intro_times = {}, []
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
                if a.peek16(0x230) == intro_dlist:      # SDLSTL
                    intro_times.append(((frame + step) / fps, intro_text(a, text_line)))
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
    return seen, intro_times


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--write-audio", action="store_true", help="write C1.WAV and C1A.WAV again before the test")
    args = p.parse_args()
    cues = read_cues()
    if len(cues) != CUES:
        raise SystemExit(f"test-chapters/C1A.TXT must contain {CUES} cues, found {len(cues)}")
    if args.write_audio:
        write_test_audio()
    for name in ("C1.WAV", "C1A.WAV"):
        if not os.path.exists(os.path.join(TEST_DIR, name)):
            raise SystemExit(f"test-chapters/{name} is missing; write it with --write-audio")
    tape = os.path.join(TEST_DIR, "TestChapters.wav")     # kept for PlayChapters.bat
    with tempfile.TemporaryDirectory() as tmp:
        boot, intro_dlist, text_line = assemble_boot(tmp)
        seconds = build_tape(boot, tape)
        seen, intro_times = play_tape(tape, seconds, intro_dlist, text_line)

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
        # Every section text appears between the previous cue and its own cue.  Long texts
        # wrap on the 40 column screen, so only their beginning is compared.
        previous = seen.get("SYNC TEST", 0.0)
        for n, (_, text) in enumerate(read_cue_labels(), 1):
            shown = [t for line, t in seen.items() if line.startswith(text[:TEXT_PREFIX])]
            if not shown:
                errors.append(f"the text of section {n}, '{text}', did not appear")
            elif not previous <= min(shown) <= times[n - 1]:
                errors.append(f"the text of section {n} appeared at {min(shown):.1f} s, "
                              f"not between {previous:.1f} s and CUE {n} at {times[n - 1]:.1f} s")
            previous = times[n - 1]
    # The intro is on screen while C1.BAS loads, between CLOAD and RUN, and off when it runs.
    if "CLOAD" in seen and "RUN" in seen:
        loading = [text for t, text in intro_times if seen["CLOAD"] < t < seen["RUN"]]
        if not loading:
            errors.append("the intro was not on screen while C1.BAS loaded")
        elif set(loading) != {"LOADING"}:
            errors.append(f"the intro's text while C1.BAS loaded was {sorted(set(loading))}, not LOADING")
    if "SYNC TEST" in seen and any(t >= seen["SYNC TEST"] for t, _ in intro_times):
        errors.append("the intro was still on screen while C1.BAS ran")
    if errors:
        for e in errors:
            print("FAIL:", e)
        return 1
    print(f"PASS: intro with LOADING shown while loading, {CUES} section texts and cues in order with the expected spacing, "
          f"then DONE")
    return 0


if __name__ == "__main__":
    sys.exit(main())

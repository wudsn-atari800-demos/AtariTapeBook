#!/usr/bin/env python3
"""Convert an Atari boot file, optionally followed by further files, to a
cassette .wav with TURGEN's GENCAS and verify the result with AltirraBridge.

GENCAS in plain mode writes a file exactly as the Atari OS cassette handler
does when a file is copied to C:: standard 600-baud FSK records
(0x55 0x55, control byte, 128 data bytes, checksum) behind a 20-second leader,
followed by an end-of-file record.  The first file is the boot file and gets
long (3 s) inter-record gaps like MyDOS writes them.  Every further file, for
example a tokenized BASIC program the boot loader CLOADs, is converted with
short gaps (CLOAD format) and appended after its own leader.  The OS skips
the boot file's end-of-file record because it waits nine seconds after
starting the motor before it reads.

The script also builds the .cas image to list the records, then boots the
.wav in the headless AltirraBridgeServer with a breakpoint on the boot file's
init vector and compares the memory at the load address with the file
content at that moment (before the boot code can modify itself).

An input can carry an audio file for the left (audio) channel of its tape
section, written as data=audio, e.g. C1.BAS=C1AUDIO.WAV.  The audio is
converted to the tape's sample rate and starts together with the section's
leader; if it outlasts the data, the section is extended with silence on the
data track.  The Atari plays this channel through the TV speaker while the
tape motor runs.  If the audio is longer than the data, the program must keep
the motor running (POKE 54018,52) until the audio has ended before it CLOADs
the next file; a CLOAD issued earlier times out (error 138) because the next
file's records are too far away.

If a cue file with the same name as the audio file and the extension .TXT
exists (e.g. C1.TXT next to C1.WAV), the data track under the rest of the
audio carries a sync co-track instead of silence: a continuous space tone
with a 335 ms mark pulse at every cue.  The program sees the pulses as bit 4
of SKSTAT (53775) changing from 0 to 1 while the motor runs.  The cue file is
an Audacity label export: one label per line, start time, end time and text
separated by tabs, times in seconds from the start of the audio file.  Only
the start time is used.  Cues must lie after the section's data records.

Usage:
    python Bin2Wav.py Boot.sec AtariTapeBook.wav
    python Bin2Wav.py Boot.sec program.bas AtariTapeBook.wav
    python Bin2Wav.py Boot.sec C1.BAS=C1AUDIO.WAV C2.BAS=C2AUDIO.WAV AtariTapeBook.wav
"""

import argparse
from array import array
import math
import os
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import threading
import wave


def folder_in_path(program, option):
    """Return the folder of a program found in the PATH, see Make-Settings.bat."""
    path = shutil.which(program)
    if not path:
        raise SystemExit(f"{program} not found in the PATH; add its folder in Make-Settings.bat or use {option}")
    return os.path.dirname(os.path.abspath(path))


# ----------------------------------------------------------------------
# GENCAS
# ----------------------------------------------------------------------

def gencas(turgen_dir, args):
    jar = os.path.join(turgen_dir, "dist", "turgen.jar")
    if not os.path.exists(jar):
        raise SystemExit(f"TURGEN not found: {jar}")
    cmd = ["java", "-cp", jar, "turgen.gencas.CLIGenCas", *args]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        sys.stderr.write(r.stdout + r.stderr)
        raise SystemExit(f"GENCAS failed with exit code {r.returncode}")


def cas_records(path):
    """Yield (control byte, data, gap_ms) for every data chunk of a .cas file."""
    with open(path, "rb") as f:
        image = f.read()
    i = 0
    while i + 8 <= len(image):
        tag = image[i:i + 4]
        length, aux = struct.unpack_from("<HH", image, i + 4)
        body = image[i + 8:i + 8 + length]
        if tag == b"data" and length >= 4:
            yield body[2], body[3:-1], aux
        i += 8 + length


def concat_wavs(parts, output):
    with wave.open(output, "wb") as out:
        for i, part in enumerate(parts):
            with wave.open(part, "rb") as w:
                if i == 0:
                    out.setparams(w.getparams())
                elif (w.getnchannels(), w.getsampwidth(), w.getframerate()) != \
                        (out.getnchannels(), out.getsampwidth(), out.getframerate()):
                    raise SystemExit(f"{part}: format differs from the first part")
                out.writeframes(w.readframes(w.getnframes()))


def read_audio_mono16(path, rate):
    """Read any 8/16-bit mono or stereo .wav as 16-bit mono samples at `rate`."""
    with wave.open(path, "rb") as w:
        channels, width, sr, n = w.getnchannels(), w.getsampwidth(), w.getframerate(), w.getnframes()
        raw = w.readframes(n)
    if width == 1:
        samples = array("h", ((b - 128) << 8 for b in raw))
    elif width == 2:
        samples = array("h")
        samples.frombytes(raw)
    else:
        raise SystemExit(f"{path}: only 8-bit and 16-bit .wav files are supported")
    if channels > 1:
        mono = array("h", bytes(2 * n))
        for ch in range(channels):
            part = samples[ch::channels]
            for i in range(n):
                mono[i] += part[i] // channels
        samples = mono
    if sr != rate:
        out_len = int(n * rate / sr)
        out = array("h", bytes(2 * out_len))
        step = sr / rate
        last = n - 1
        for i in range(out_len):
            pos = i * step
            j = int(pos)
            if j >= last:
                out[i] = samples[last]
            else:
                frac = pos - j
                out[i] = int(samples[j] + (samples[j + 1] - samples[j]) * frac)
        samples = out
    return samples


MARK_HZ = 5327
SPACE_HZ = 3995
CUE_PULSE_S = 0.335         # length of a cue pulse, as on the "Conversational" tapes
CUE_MIN_DISTANCE_S = 1.0    # closer cues are hard to see for a BASIC loop
CUE_SPIN_UP_S = 2.0         # keep the first cue away from the motor start after the data


def read_cues(path):
    """Read an Audacity label export and return the start times in seconds."""
    cues = []
    with open(path, encoding="utf-8-sig") as f:
        for n, line in enumerate(f, 1):
            line = line.strip()
            if not line or line.startswith("\\"):     # spectral selection lines of newer Audacity versions
                continue
            try:
                cues.append(float(line.split("\t")[0]))
            except ValueError:
                raise SystemExit(f"{path}:{n}: expected a start time in seconds, found '{line}'")
    return sorted(cues)


def check_cues(path, cues, data_seconds, audio_seconds):
    for t in cues:
        if t < data_seconds:
            raise SystemExit(f"{path}: cue at {t:.2f} s lies inside the data records, which end at {data_seconds:.2f} s")
        if t + CUE_PULSE_S > audio_seconds:
            raise SystemExit(f"{path}: cue at {t:.2f} s ends after the audio, which ends at {audio_seconds:.2f} s")
    if cues and cues[0] < data_seconds + CUE_SPIN_UP_S:
        print(f"warning: {path}: first cue at {cues[0]:.2f} s is less than {CUE_SPIN_UP_S:.0f} s "
              f"after the data records, the motor may still be spinning up")
    for a, b in zip(cues, cues[1:]):
        if b - a < CUE_MIN_DISTANCE_S:
            print(f"warning: {path}: cues at {a:.2f} s and {b:.2f} s are less than "
                  f"{CUE_MIN_DISTANCE_S:.0f} s apart")


def sync_cotrack(rate, start, end, cues, level):
    """Return a phase-continuous FSK signal from sample `start` to `end`: space tone with mark pulses."""
    pulses = [(int(t * rate), int((t + CUE_PULSE_S) * rate)) for t in cues]
    out = array("h", bytes(2 * (end - start)))
    phase, p = 0.0, 0
    mark_step, space_step = 2 * math.pi * MARK_HZ / rate, 2 * math.pi * SPACE_HZ / rate
    for i in range(start, end):
        while p < len(pulses) and i >= pulses[p][1]:
            p += 1
        mark = p < len(pulses) and pulses[p][0] <= i
        out[i - start] = int(level * math.sin(phase))
        phase += mark_step if mark else space_step
        if phase > 2 * math.pi:
            phase -= 2 * math.pi
    return out


def add_audio_track(data_wav, audio_wav, output, cues=None, cue_file=None):
    """Put `audio_wav` on the left channel of the stereo 16-bit data tape `data_wav`.

    With `cues`, the data track under the rest of the audio gets the sync co-track."""
    with wave.open(data_wav, "rb") as w:
        if (w.getnchannels(), w.getsampwidth()) != (2, 2):
            raise SystemExit(f"{data_wav}: expected a stereo 16-bit tape from GENCAS")
        rate = w.getframerate()
        frames = array("h")
        frames.frombytes(w.readframes(w.getnframes()))
    data = frames[1::2]
    audio = read_audio_mono16(audio_wav, rate)
    data_seconds, audio_seconds = len(data) / rate, len(audio) / rate
    n = max(len(data), len(audio))
    if cues:
        check_cues(cue_file, cues, data_seconds, audio_seconds)
        level = max(max(data), -min(data))
        data.extend(sync_cotrack(rate, len(data), n, cues, level))
    data.extend([0] * (n - len(data)))
    audio.extend([0] * (n - len(audio)))
    out = array("h", bytes(4 * n))
    out[0::2] = audio
    out[1::2] = data
    with wave.open(output, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(out.tobytes())
    return data_seconds, audio_seconds


def to_mono_8bit(path):
    """Rewrite a stereo 16-bit GENCAS .wav as 8-bit mono using the data track."""
    with wave.open(path, "rb") as w:
        channels, width, rate, n = w.getnchannels(), w.getsampwidth(), w.getframerate(), w.getnframes()
        raw = w.readframes(n)
    if channels == 1 and width == 1:
        return
    ch = channels - 1                       # data track is the right channel
    out = bytearray(n)
    for i in range(n):
        if width == 2:
            v = struct.unpack_from("<h", raw, (i * channels + ch) * 2)[0] >> 8
        else:
            v = raw[i * channels + ch] - 128
        out[i] = v + 128
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(1)
        w.setframerate(rate)
        w.writeframes(bytes(out))


# ----------------------------------------------------------------------
# Boot test with AltirraBridge
# ----------------------------------------------------------------------

def start_server(server_dir):
    exe = os.path.join(server_dir, "AltirraBridgeServer.exe")
    if not os.path.exists(exe):
        raise SystemExit(f"AltirraBridgeServer not found: {exe}")
    proc = subprocess.Popen([exe, "--bridge=tcp:127.0.0.1:0"],
                            stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
                            text=True, bufsize=1)
    token_file = None
    for line in proc.stderr:
        m = re.search(r"token-file:\s*(.+)$", line.strip(), re.IGNORECASE)
        if m:
            token_file = m.group(1).strip()
            break
        if proc.poll() is not None:
            break
    if not token_file:
        proc.kill()
        raise SystemExit("AltirraBridgeServer did not report a token file")
    threading.Thread(target=lambda: [None for _ in proc.stderr], daemon=True).start()
    return proc, token_file


def verify_boot(wav_path, content, server_dir):
    sys.path.insert(0, os.path.join(server_dir, "sdk", "python"))
    from altirra_bridge import AltirraBridge  # noqa: E402

    load_addr, init_addr = struct.unpack("<HH", content[2:6])
    proc, token_file = start_server(server_dir)
    ok = False
    try:
        with AltirraBridge.from_token_file(token_file) as a:
            a.config("basic", "on")
            a.config("casautoboot", "on")
            a.bp_set(init_addr)
            a.boot(os.path.abspath(wav_path))
            for _ in range(120):                   # up to 100 s of emulated time
                a.frame(50)
                if int(a.regs()["PC"].lstrip("$"), 16) == init_addr:
                    break
            else:
                print(f"boot test: init vector ${init_addr:04X} was never reached")
                a.quit()
                return False
            mem = a.peek(load_addr, len(content))
            ok = mem == content
            bad = [i for i in range(len(content)) if mem[i] != content[i]]
            print(f"boot test: at init ${init_addr:04X} the {len(content)} bytes at ${load_addr:04X} "
                  f"{'match the file' if ok else 'differ at offsets ' + str(bad[:10])}")
            a.quit()
    finally:
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
    return ok


# ----------------------------------------------------------------------

def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("files", nargs="+",
                   help="boot file, optional further files to chain, and optionally the output .wav last")
    p.add_argument("--short-irg", action="store_true",
                   help="short inter-record gaps for the boot file too (default: long, as MyDOS writes them)")
    p.add_argument("--short-leader", action="store_true",
                   help="14 s leader tone before each file instead of 20 s")
    p.add_argument("--cas", action="store_true", help="also keep the .cas image next to the .wav")
    p.add_argument("--mono", action="store_true", help="write 8-bit mono instead of GENCAS' stereo 16-bit")
    p.add_argument("--no-verify", action="store_true", help="skip the AltirraBridge boot test")
    p.add_argument("--turgen", help="TURGEN installation folder (default: the folder of gencas in the PATH)")
    p.add_argument("--server-dir",
                   help="folder containing AltirraBridgeServer.exe and sdk/ "
                        "(default: the folder of AltirraBridgeServer in the PATH)")
    args = p.parse_args()
    args.turgen = args.turgen or folder_in_path("gencas", "--turgen")

    inputs = list(args.files)
    output = inputs.pop() if len(inputs) > 1 and inputs[-1].lower().endswith(".wav") else None
    inputs = [(spec.split("=", 1) + [None])[:2] for spec in inputs]      # (data file, audio file or None)
    output = output or os.path.splitext(os.path.basename(inputs[0][0]))[0].title() + ".wav"
    if args.mono and any(audio for _, audio in inputs):
        raise SystemExit("--mono cannot be combined with audio tracks")
    with open(inputs[0][0], "rb") as f:
        boot = f.read()
    cas = os.path.splitext(output)[0] + ".cas" if args.cas else \
        os.path.join(tempfile.gettempdir(), os.path.splitext(os.path.basename(output))[0] + ".cas")

    parts = []
    sections = []
    with tempfile.TemporaryDirectory() as tmp:
        for i, (src, audio) in enumerate(inputs):
            gaps = [] if i or args.short_irg else ["-long"]
            if args.short_leader:
                gaps.append("-s")
            part = os.path.join(tmp, f"part{i}.wav")
            gencas(args.turgen, ["-mode:plain", "-r", *gaps, "-o:wav", src, part])
            gencas(args.turgen, ["-mode:plain", *(["-a"] if i else ["-r"]), *gaps, src, cas])
            if audio:
                mixed = os.path.join(tmp, f"mixed{i}.wav")
                cue_file = os.path.splitext(audio)[0] + ".TXT"
                cues = read_cues(cue_file) if os.path.exists(cue_file) else None
                data_s, audio_s = add_audio_track(part, audio, mixed, cues, cue_file)
                sections.append((src, data_s, audio, audio_s, cues))
                part = mixed
            else:
                with wave.open(part, "rb") as w:
                    sections.append((src, w.getnframes() / w.getframerate(), None, 0, None))
            parts.append(part)
        concat_wavs(parts, output)
    if args.mono:
        to_mono_8bit(output)

    with wave.open(output, "rb") as w:
        seconds = w.getnframes() / w.getframerate()
        fmt = f"{w.getframerate()} Hz, {w.getsampwidth() * 8}-bit, {'mono' if w.getnchannels() == 1 else 'stereo'}"
    print(f"{output}: {seconds:.1f} s, {fmt}, {len(inputs)} file(s)")
    start = 0.0
    for src, data_s, audio, audio_s, cues in sections:
        note = f", audio {os.path.basename(audio)} {audio_s:.1f} s on the left channel" if audio else ""
        if cues:
            note += f", {len(cues)} cue(s) from {cues[0]:.1f} s"
        print(f"  {start:6.1f} s: {os.path.basename(src)}, data {data_s:.1f} s{note}")
        start += max(data_s, audio_s)
    names = {0xFC: "data", 0xFA: "partial data", 0xFE: "EOF"}
    for n, (ctrl, _, gap) in enumerate(cas_records(cas), 1):
        print(f"  record {n}: {names.get(ctrl, f'${ctrl:02X}')}, {gap / 1000:.2f} s gap before it")
    if not args.cas:
        os.remove(cas)

    if args.no_verify:
        return 0
    if len(boot) < 6 or boot[1] == 0:
        print("first file does not look like a boot file, skipping the boot test")
        return 0
    server_dir = args.server_dir or folder_in_path("AltirraBridgeServer", "--server-dir")
    return 0 if verify_boot(output, boot, server_dir) else 1


if __name__ == "__main__":
    sys.exit(main())

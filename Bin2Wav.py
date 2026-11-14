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
.wav in the headless AltirraBridgeServer with a breakpoint at the boot file's
load address + 6, which the OS calls after loading the records announced in
the boot header, and compares those records in memory with the file content
at that moment (before the boot code can load more records or modify itself).

The tape is a sequence of sections, given in tape order.  The first one is
the boot file.  Every further section is given as a file or as a base name
without extension, and the files with that base name decide its type:

- Load section: a program file exists, either the given file or <base>.BAS.
  Its records are written by GENCAS.  An optional <base>.WAV is put on the
  left (audio) channel and starts together with the section's leader, so it
  plays while the program loads.  If it outlasts the records, the data track
  is extended with silence.
- Run section: no program file, but <base>.WAV exists.  It is played while
  the loaded program runs.  The audio starts after a lead-in of silence, so
  the motor can reach its speed first.  The data track carries the sync
  co-track: a continuous space tone with a 335 ms mark pulse at every cue
  from <base>.TXT.  Without a .TXT file there are no pulses.  The program
  sees the pulses as bit 4 of SKSTAT (53775) changing from 0 to 1.
  If the run section follows a load section, the data track of the load
  section is replaced by space tone from its end-of-file record on.  CLOAD
  does not read that record, and its data bits as well as the silence after
  it would otherwise be read as pulses when the program starts the motor.
- A load section must not have a .TXT file; cues belong to run sections.

If the boot file holds more records than its header announces (a two-stage
boot file, see boot/Boot.asm), the first header byte, which the OS ignores for
cassette boot, holds the record after which the pre-loader stops the motor and
restarts it before it reads on.  The gap after that record is extended by
BOOT_GAP_S of mark tone.  The boot section's .wav (for example boot/Boot.WAV
next to boot/Boot.sec) is the narration while the intro loads: it starts
NARRATION_DELAY_S into that gap, where the motor stops for the title, and
must end before the end of the boot section, see
plans/07_BOOT_NARRATION_PLAN.md.

The Atari plays the left channel through the TV speaker while the tape motor
runs.  The program must keep the motor running (POKE 54018,52) until the
audio has ended before it CLOADs the next file; a CLOAD issued earlier times
out (error 138) because the next file's records are too far away.

The cue file is an Audacity label export: one label per line, start time,
end time and text separated by tabs, times in seconds from the start of the
audio file.  Only the start time is used.

The .cas image only contains the records of the load sections.

Usage:
    python Bin2Wav.py Boot.sec AtariTapeBook.wav
    python Bin2Wav.py Boot.sec program.bas AtariTapeBook.wav
    python Bin2Wav.py boot/Boot.sec chapters/C1 chapters/C1A chapters/C2 AtariTapeBook.wav
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


RECORD_SIZE = 128           # data bytes of a cassette record, RECORD_SIZE in AtariTapeBookEquates.asm
MARK_HZ = 5327
SPACE_HZ = 3995
CUE_PULSE_S = 0.335         # length of a cue pulse, as on the "Conversational" tapes
CUE_MIN_DISTANCE_S = 1.0    # closer cues are hard to see for a BASIC loop
CUE_SPIN_UP_S = 2.0         # keep the first cue away from the motor start
AUDIO_LEAD_IN_S = 1.0       # silence before the audio of a run section, while the motor spins up
NARRATION_DELAY_S = 1.0     # start of the boot narration after the start of the pause gap
BOOT_GAP_S = 2.0            # extra mark tone where the pre-loader stops and restarts the motor (plan 03)


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


def check_cues(path, cues, audio_seconds):
    for t in cues:
        if t < 0:
            raise SystemExit(f"{path}: cue at {t:.2f} s lies before the start of the audio")
        if t + CUE_PULSE_S > audio_seconds:
            raise SystemExit(f"{path}: cue at {t:.2f} s ends after the audio, which ends at {audio_seconds:.2f} s")
    if cues and AUDIO_LEAD_IN_S + cues[0] < CUE_SPIN_UP_S:
        print(f"warning: {path}: first cue at {cues[0]:.2f} s is less than {CUE_SPIN_UP_S:.0f} s after the "
              f"motor start ({AUDIO_LEAD_IN_S:.0f} s lead-in included), the motor may still be spinning up")
    for a, b in zip(cues, cues[1:]):
        if b - a < CUE_MIN_DISTANCE_S:
            print(f"warning: {path}: cues at {a:.2f} s and {b:.2f} s are less than "
                  f"{CUE_MIN_DISTANCE_S:.0f} s apart")


def sync_cotrack(rate, n, cues, level, phase=0.0):
    """Return `n` samples of phase-continuous FSK, space tone with a mark pulse at each cue time,
    and the phase at the end."""
    pulses = [(int(t * rate), int((t + CUE_PULSE_S) * rate)) for t in cues]
    out = array("h", bytes(2 * n))
    p = 0
    mark_step, space_step = 2 * math.pi * MARK_HZ / rate, 2 * math.pi * SPACE_HZ / rate
    for i in range(n):
        while p < len(pulses) and i >= pulses[p][1]:
            p += 1
        mark = p < len(pulses) and pulses[p][0] <= i
        out[i] = int(level * math.sin(phase))
        phase += mark_step if mark else space_step
        if phase > 2 * math.pi:
            phase -= 2 * math.pi
    return out, phase


def data_track_format(data_wav):
    """Return the sample rate and the peak level of the data track of a GENCAS .wav."""
    with wave.open(data_wav, "rb") as w:
        rate, channels = w.getframerate(), w.getnchannels()
        frames = array("h")
        frames.frombytes(w.readframes(w.getnframes()))
    data = frames[channels - 1::channels]
    return rate, max(max(data), -min(data))


def write_stereo(output, rate, left, right):
    out = array("h", bytes(4 * len(left)))
    out[0::2] = left
    out[1::2] = right
    with wave.open(output, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(out.tobytes())


def make_run_section(audio_wav, cue_file, rate, level, output, phase=0.0):
    """Write a run section: lead-in plus audio on the left, the sync co-track on the right."""
    audio = read_audio_mono16(audio_wav, rate)
    audio_seconds = len(audio) / rate
    cues = read_cues(cue_file) if cue_file else []
    check_cues(cue_file, cues, audio_seconds)
    lead_in = int(AUDIO_LEAD_IN_S * rate)
    left = array("h", bytes(2 * lead_in)) + audio
    right, _ = sync_cotrack(rate, len(left), [AUDIO_LEAD_IN_S + t for t in cues], level, phase)
    write_stereo(output, rate, left, right)
    return len(left) / rate, audio_seconds, cues


def mark_gaps(data, rate, count=None, min_seconds=0.1):
    """Return the (start, end) samples of the mark tone stretches longer than `min_seconds`:
    the leader first, then the gap after each record. With `count`, the search stops after
    that many gaps, so only the start of the data is scanned."""
    split = rate / ((MARK_HZ + SPACE_HZ) / 2)
    gaps, start = [], None
    c0 = c1 = None                                           # the two previous zero crossings
    negative = data[0] < 0
    for i in range(1, len(data)):
        if (data[i] < 0) == negative:
            continue
        negative = not negative
        if c0 is not None:
            if i - c0 < split:                               # a full period of mark tone
                if start is None:
                    start = c0
            elif start is not None:
                if c1 - start > min_seconds * rate:
                    gaps.append((start, c1))
                    if count is not None and len(gaps) >= count:
                        break
                start = None
        c0, c1 = c1, i
    return gaps


def extend_gaps(load_wav, records, seconds):
    """Extend the gaps after the given records (counted from 1) of a GENCAS .wav by `seconds`
    of mark tone. The tone is continued by repeating whole periods of the gap's own tone,
    starting and ending at a rising zero crossing, so the signal stays continuous.
    Return {record: first sample of the gap after it} in the extended .wav."""
    with wave.open(load_wav, "rb") as w:
        rate = w.getframerate()
        frames = array("h")
        frames.frombytes(w.readframes(w.getnframes()))
    data = frames[1::2]
    gaps = mark_gaps(data, rate, max(records) + 1)        # up to the gap after the last record
    starts = {}
    for record in sorted(records, reverse=True):
        if record >= len(gaps):
            raise SystemExit(f"{load_wav}: no gap after record {record} found")
        start, end = gaps[record]
        rising = [i for i in range((start + end) // 2, end) if data[i - 1] < 0 <= data[i]]
        if len(rising) < 51:
            raise SystemExit(f"{load_wav}: the gap after record {record} is too short to extend")
        period = data[rising[0]:rising[50]]                   # 50 whole periods
        tone = period * (int(seconds * rate) // len(period) + 1)
        data = data[:rising[0]] + tone + data[rising[0]:]
        starts[record] = start                               # before every later insertion
    out = array("h", bytes(4 * len(data)))
    out[1::2] = data                                         # the left (audio) channel stays silent
    with wave.open(load_wav, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(out.tobytes())
    return starts


def silence_eof_record(load_wav, level):
    """Replace the data track of a load section from its end-of-file record on with space tone.

    CLOAD stops reading after the last data record, so the end-of-file record and the
    silence GENCAS writes after it are still on the tape when the program starts the motor
    for the following run section.  Their data bits and the noise Altirra and a real
    recorder decode from the silence would look like cue pulses.  The mark tone gap before
    the end-of-file record is kept; it passes while the program waits for the motor.
    Return the seconds replaced and the phase at the end, for the run section to continue."""
    with wave.open(load_wav, "rb") as w:
        rate = w.getframerate()
        frames = array("h")
        frames.frombytes(w.readframes(w.getnframes()))
    data = frames[1::2]
    # The end of the last record is the last sign change; GENCAS' silence is a constant offset.
    end = next((i for i in range(len(data) - 1, 0, -1) if (data[i - 1] < 0) != (data[i] < 0)), 0)
    # Going back from there, the gap before the end-of-file record is the last stretch of
    # mark tone (full periods below the split between mark and space) longer than 100 ms.
    split = rate / ((MARK_HZ + SPACE_HZ) / 2)
    crossings = [i for i in range(max(1, end - int(4 * rate)), end + 1) if (data[i - 1] < 0) != (data[i] < 0)]
    eof_start, run_end = None, None
    for k in range(len(crossings) - 3, -1, -1):
        is_mark = crossings[k + 2] - crossings[k] < split
        if is_mark and run_end is None:
            run_end = crossings[k + 2]
        elif not is_mark:
            if run_end is not None and run_end - crossings[k + 1] > 0.1 * rate:
                eof_start = run_end
                break
            run_end = None
    if eof_start is None:
        raise SystemExit(f"{load_wav}: the gap before the end-of-file record was not found")
    tone, phase = sync_cotrack(rate, len(data) - eof_start, [], level)
    frames[2 * eof_start + 1::2] = tone
    with wave.open(load_wav, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(frames.tobytes())
    return (len(data) - eof_start) / rate, phase


def add_audio_track(data_wav, audio_wav, output, offset_s=0.0, fit=False):
    """Put `audio_wav` on the left channel of the stereo 16-bit data tape `data_wav`,
    starting `offset_s` seconds into it.  With `fit`, the audio must end with the data;
    otherwise the data track is extended with silence."""
    with wave.open(data_wav, "rb") as w:
        if (w.getnchannels(), w.getsampwidth()) != (2, 2):
            raise SystemExit(f"{data_wav}: expected a stereo 16-bit tape from GENCAS")
        rate = w.getframerate()
        frames = array("h")
        frames.frombytes(w.readframes(w.getnframes()))
    data = frames[1::2]
    audio = read_audio_mono16(audio_wav, rate)
    data_seconds, audio_seconds = len(data) / rate, len(audio) / rate
    if fit and offset_s + audio_seconds > data_seconds:
        raise SystemExit(f"{audio_wav}: {audio_seconds:.1f} s, but only {data_seconds - offset_s:.1f} s "
                         f"are available from {offset_s:.1f} s to the end of the section; shorten it by "
                         f"{offset_s + audio_seconds - data_seconds:.1f} s")
    audio = array("h", bytes(2 * int(offset_s * rate))) + audio
    n = max(len(data), len(audio))
    data.extend([0] * (n - len(data)))
    audio.extend([0] * (n - len(audio)))
    write_stereo(output, rate, audio, data)
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

    load_addr = struct.unpack("<H", content[2:4])[0]
    loader_addr = load_addr + 6
    announced = content[:min(len(content), content[1] * RECORD_SIZE)]  # the records the OS loads itself
    proc, token_file = start_server(server_dir)
    ok = False
    try:
        with AltirraBridge.from_token_file(token_file) as a:
            a.config("basic", "on")
            a.config("casautoboot", "on")
            a.config("siopatch", "off")             # load at real tape speed, like the project's Altirra runs
            a.bp_set(loader_addr)
            a.boot(os.path.abspath(wav_path))
            for _ in range(120):                   # up to 120 s of emulated time
                a.frame(50)
                if int(a.regs()["PC"].lstrip("$"), 16) == loader_addr:
                    break
            else:
                print(f"boot test: load address + 6 (${loader_addr:04X}) was never reached")
                a.quit()
                return False
            mem = a.peek(load_addr, len(announced))
            ok = mem == announced
            bad = [i for i in range(len(announced)) if mem[i] != announced[i]]
            print(f"boot test: at ${loader_addr:04X} the {len(announced)} bytes of the announced boot records "
                  f"at ${load_addr:04X} {'match the file' if ok else 'differ at offsets ' + str(bad[:10])}")
            a.quit()
    finally:
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
    return ok


# ----------------------------------------------------------------------

def resolve_section(spec, first):
    """Return (program file, audio file, cue file) of a section, each None if absent."""
    def existing(path):
        return path if os.path.isfile(path) else None

    if os.path.isfile(spec):
        base, program = os.path.splitext(spec)[0], spec
    else:
        base, program = spec, existing(spec + ".BAS")
    audio, cues = existing(base + ".WAV"), existing(base + ".TXT")
    if first and not program:
        raise SystemExit(f"{spec}: the first section must be the boot file")
    if program and cues:
        raise SystemExit(f"{spec}: a load section ({program}) cannot have cues ({cues}); "
                         f"put the audio and the cues into a run section of their own")
    if not program and not audio:
        raise SystemExit(f"{spec}: neither a program (.BAS) nor audio (.WAV) found")
    return program, audio, cues


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("files", nargs="+",
                   help="boot file, further sections as files or base names, and optionally the output .wav last")
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

    specs = list(args.files)
    output = specs.pop() if len(specs) > 1 and specs[-1].lower().endswith(".wav") else None
    inputs = [resolve_section(spec, i == 0) for i, spec in enumerate(specs)]
    output = output or os.path.splitext(os.path.basename(inputs[0][0]))[0].title() + ".wav"
    if args.mono and any(audio for _, audio, _ in inputs):
        raise SystemExit("--mono cannot be combined with audio tracks")
    with open(inputs[0][0], "rb") as f:
        boot = f.read()
    cas = os.path.splitext(output)[0] + ".cas" if args.cas else \
        os.path.join(tempfile.gettempdir(), os.path.splitext(os.path.basename(output))[0] + ".cas")

    parts = []
    overview = []                      # (seconds, description)
    rate = level = None
    with tempfile.TemporaryDirectory() as tmp:
        for i, (program, audio, cue_file) in enumerate(inputs):
            part = os.path.join(tmp, f"part{i}.wav")
            if program:
                gaps = [] if i or args.short_irg else ["-long"]
                if args.short_leader:
                    gaps.append("-s")
                gencas(args.turgen, ["-mode:plain", "-r", *gaps, "-o:wav", program, part])
                gencas(args.turgen, ["-mode:plain", *(["-a"] if i else ["-r"]), *gaps, program, cas])
                extended = ""
                narration_s = None                     # start of the boot narration
                announced = boot[1] if len(boot) >= 6 else 0
                pause = boot[0] if len(boot) >= 6 else 0
                if i == 0 and 0 < announced and len(boot) > announced * RECORD_SIZE:
                    # Two-stage boot file: the pre-loader stops the motor after the record
                    # from the first header byte and restarts it before it reads the next one.
                    if not announced < pause < (len(boot) + RECORD_SIZE - 1) // RECORD_SIZE:
                        raise SystemExit(f"{program}: pause record {pause} in the first header byte "
                                         f"is not a record the pre-loader reads")
                    gap_start = extend_gaps(part, [pause], BOOT_GAP_S)[pause]
                    with wave.open(part, "rb") as w:
                        narration_s = gap_start / w.getframerate() + NARRATION_DELAY_S
                    extended = f", gap after record {pause} extended by {BOOT_GAP_S:.1f} s"
                if rate is None:
                    rate, level = data_track_format(part)
                if audio:
                    mixed = os.path.join(tmp, f"mixed{i}.wav")
                    data_s, audio_s = add_audio_track(part, audio, mixed, narration_s or 0.0, narration_s is not None)
                    part = mixed
                    if narration_s is None:
                        audio_note = f"audio {os.path.basename(audio)} {audio_s:.1f} s"
                    else:
                        audio_note = (f"narration {os.path.basename(audio)} {audio_s:.1f} s from {narration_s:.1f} s, "
                                      f"{data_s - narration_s - audio_s:.1f} s left")
                    overview.append((max(data_s, audio_s), f"load {os.path.basename(program)}, records {data_s:.1f} s"
                                                           f"{extended}, {audio_note}"))
                else:
                    with wave.open(part, "rb") as w:
                        data_s = w.getnframes() / w.getframerate()
                    overview.append((data_s, f"load {os.path.basename(program)}, records {data_s:.1f} s{extended}"))
            else:
                phase = 0.0
                if inputs[i - 1][0]:                   # follows a load section
                    replaced_s, phase = silence_eof_record(parts[-1], level)
                    overview[-1] = (overview[-1][0], overview[-1][1] +
                                    f", last {replaced_s:.1f} s of the data track replaced by space tone")
                section_s, audio_s, cues = make_run_section(audio, cue_file, rate, level, part, phase)
                cue_note = f"{len(cues)} cue(s) from {cues[0]:.1f} s" if cues else "no cues"
                overview.append((section_s, f"run {os.path.basename(audio)}, {AUDIO_LEAD_IN_S:.1f} s lead-in, "
                                            f"audio {audio_s:.1f} s, {cue_note}"))
            parts.append(part)
        concat_wavs(parts, output)
    if args.mono:
        to_mono_8bit(output)

    with wave.open(output, "rb") as w:
        seconds = w.getnframes() / w.getframerate()
        fmt = f"{w.getframerate()} Hz, {w.getsampwidth() * 8}-bit, {'mono' if w.getnchannels() == 1 else 'stereo'}"
    print(f"{output}: {seconds:.1f} s, {fmt}, {len(inputs)} section(s)")
    start = 0.0
    for section_s, description in overview:
        print(f"  {start:6.1f} s: {description}")
        start += section_s
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

#!/usr/bin/env python3
"""Extract the programs from a stereo Atari cassette .wav with A8CAS.

The data track of the .wav is written to a temporary mono .wav, because
a8cas-convert cannot select a channel.  a8cas-convert turns it into a .cas
tape image next to the .wav: standard records become "data" chunks and other
signals, such as the sync pulses played together with the audio track, become
"fsk" chunks.  The data records are then split into sections at long gaps.
Each section that starts with the header of a tokenized Atari BASIC file is
written as <prefix><n>.BAS, cut to the length given in the header; any other
section is written as <prefix><n>.BIN.

a8cas-convert must be in the PATH, see Make-Settings.bat.

Usage:
    python ExtractTape.py "Conversational GERMAN Unit 1 Side 1.wav" GERMAN1
"""

import argparse
from array import array
import os
import shutil
import struct
import subprocess
import sys
import tempfile
import wave

SECTION_GAP_MS = 5000          # a gap before a data record that starts a new section
CONTROL = {0xFC: "full", 0xFA: "partial", 0xFE: "end of file"}


def write_channel(wav_path, channel, mono_path):
    with wave.open(wav_path) as w:
        if w.getsampwidth() != 2:
            raise SystemExit(f"{wav_path}: only 16-bit WAV files are supported")
        channels, rate = w.getnchannels(), w.getframerate()
        raw = array("h")
        raw.frombytes(w.readframes(w.getnframes()))
    if channel >= channels:
        raise SystemExit(f"{wav_path} has {channels} channel(s), channel {channel} does not exist")
    with wave.open(mono_path, "wb") as o:
        o.setnchannels(1)
        o.setsampwidth(2)
        o.setframerate(rate)
        o.writeframes(raw[channel::channels].tobytes())
    return len(raw) // channels / rate


def a8cas_convert(mono_path, cas_path):
    exe = shutil.which("a8cas-convert")
    if not exe:
        raise SystemExit("a8cas-convert not found in the PATH; run Make-Setup.bat and call Make-Settings.bat first")
    r = subprocess.run([exe, mono_path, cas_path], capture_output=True, text=True)
    if r.returncode != 0 or not os.path.exists(cas_path):
        sys.stderr.write(r.stdout + r.stderr)
        raise SystemExit(f"a8cas-convert failed with exit code {r.returncode}")


def read_cas(cas_path):
    """Return the chunks of a .cas file as (start time in s, id, aux, data)."""
    b = open(cas_path, "rb").read()
    pos, t, baud, chunks = 0, 0.0, 600, []
    while pos + 8 <= len(b):
        cid = b[pos:pos + 4].decode("latin1")
        length, aux = struct.unpack("<HH", b[pos + 4:pos + 8])
        data = b[pos + 8:pos + 8 + length]
        pos += 8 + length
        if cid == "baud":
            baud = aux
        elif cid == "data":
            t += aux / 1000
            chunks.append((t, cid, aux, data))
            t += len(data) * 10 / baud
        elif cid == "fsk ":
            t += aux / 1000
            chunks.append((t, cid, aux, data))
            t += sum(struct.unpack(f"<{len(data) // 2}H", data)) / 10000
    return chunks


def is_standard(record):
    if len(record) != 132 or record[:2] != b"\x55\x55":
        return False
    c = 0
    for x in record[:131]:
        c += x
        if c > 255:
            c -= 255
    return c == record[131]


def sections(chunks):
    result, current = [], None
    for t, cid, aux, data in chunks:
        if cid != "data":
            continue
        if current is None or aux > SECTION_GAP_MS:
            current = {"start": t, "records": []}
            result.append(current)
        current["records"].append(data)
    return result


def section_data(records):
    data, standard, other = bytearray(), 0, 0
    for r in records:
        if not is_standard(r):
            other += 1
            continue
        standard += 1
        if r[2] == 0xFC:
            data += r[3:131]
        elif r[2] == 0xFA:
            data += r[3:3 + r[130]]
    return bytes(data), standard, other


def basic_length(data):
    """Return the length of a tokenized Atari BASIC file, or None."""
    if len(data) < 14:
        return None
    lomem, vntp, vntd, vvtp, stmtab, stmcur, starp = struct.unpack("<7H", data[:14])
    if lomem != 0 or not vntp <= vntd <= vvtp <= stmtab <= stmcur <= starp:
        return None
    length = 14 + starp - vntp
    return length if length <= len(data) + 1 else None


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("wav", help="stereo or mono cassette .wav")
    p.add_argument("prefix", help="file name prefix of the extracted programs, e.g. GERMAN1")
    p.add_argument("--channel", type=int, default=1, help="channel with the data track (default: 1 = right)")
    args = p.parse_args()

    out_dir = os.path.dirname(os.path.abspath(args.wav))
    cas_path = os.path.splitext(os.path.abspath(args.wav))[0] + ".cas"
    fd, mono_path = tempfile.mkstemp(suffix=".wav")
    os.close(fd)
    try:
        seconds = write_channel(args.wav, args.channel, mono_path)
        a8cas_convert(mono_path, cas_path)
    finally:
        os.remove(mono_path)

    chunks = read_cas(cas_path)
    fsk = sum(1 for c in chunks if c[1] == "fsk ")
    print(f"{args.wav}: {seconds:.1f} s -> {os.path.basename(cas_path)}, "
          f"{sum(1 for c in chunks if c[1] == 'data')} data chunks, {fsk} fsk chunks")
    for n, s in enumerate(sections(chunks), 1):
        data, standard, other = section_data(s["records"])
        length = basic_length(data)
        if length is not None:
            name, data = f"{args.prefix}{n}.BAS", data[:length]
        else:
            name = f"{args.prefix}{n}.BIN"
        with open(os.path.join(out_dir, name), "wb") as f:
            f.write(data)
        kind = "Atari BASIC program" if length is not None else "data"
        note = f", {other} non-standard record(s) skipped" if other else ""
        print(f"  section {n} at {s['start']:7.1f} s: {standard} records{note} -> {name}, {kind}, {len(data)} bytes")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Pack the boot image: write the boot file with the intro ZX0-compressed.

MADS assembles boot/Boot.asm into the plain image Boot.bin, which starts at
the load address.  The boot file holds, in this order (labels from the .lab
file, see plans/08_ZX0_INTRO_PLAN.md):

1. load_address to pack_start: the boot record and the second stage,
   as they are,
2. unpack_start to unpack_end: the decompressor, as it is, padded to
   whole records,
3. pack_start to pack_end: the intro and the loader module, compressed with
   Zx0.py, decompressed by unpack while it is loaded.

The script decompresses part 3 again and compares it with the image.

Usage:
    python Pack.py boot/Boot.bin boot/Boot.lab boot/Boot.sec
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import Zx0  # noqa: E402

RECORD_SIZE = 128           # RECORD_SIZE in AtariTapeBookEquates.asm


def read_labels(path):
    labels = {}
    with open(path) as f:
        for line in f:
            m = re.match(r"^\S+\s+([0-9A-F]{4})\s+(\S+)\s*$", line)
            if m:
                labels[m.group(2).upper()] = int(m.group(1), 16)
    return labels


def pack(image, labels):
    """Return the boot file and a description of its parts."""
    names = ("LOAD_ADDRESS", "PACK_START", "PACK_END", "UNPACK_START", "UNPACK_END")
    missing = [n for n in names if n not in labels]
    if missing:
        raise SystemExit(f"labels {', '.join(n.lower() for n in missing)} not found")
    load, pack_start, pack_end, unpack_start, unpack_end = (labels[n] for n in names)
    if (pack_start - load) % RECORD_SIZE or (unpack_end - unpack_start) % RECORD_SIZE:
        raise SystemExit("the raw parts must end at record boundaries")

    def part(start, end):
        data = image[start - load:end - load]
        return data + bytes(end - start - len(data))    # the image ends with the decompressor's code

    raw = part(load, pack_start)
    unpack = part(unpack_start, unpack_end)
    plain = part(pack_start, pack_end)
    packed = Zx0.compress(plain)
    if Zx0.decompress(packed) != plain:
        raise SystemExit("the ZX0 round trip failed")
    records = [len(raw) // RECORD_SIZE, len(unpack) // RECORD_SIZE, -(-len(packed) // RECORD_SIZE)]
    description = (f"records 1-{records[0]}: ${load:04X}-${pack_start - 1:04X}, "
                   f"{records[0] + 1}-{records[0] + records[1]}: decompressor ${unpack_start:04X}-${unpack_end - 1:04X}, "
                   f"{records[0] + records[1] + 1}-{sum(records)}: ${pack_start:04X}-${pack_end - 1:04X} "
                   f"{len(plain)} -> {len(packed)} bytes")
    return raw + unpack + packed, description


def main():
    if len(sys.argv) != 4:
        raise SystemExit(__doc__.split("Usage:")[1])
    image_path, lab_path, output = sys.argv[1:]
    with open(image_path, "rb") as f:
        image = f.read()
    boot, description = pack(image, read_labels(lab_path))
    with open(output, "wb") as f:
        f.write(boot)
    print(f"{output}: {len(boot)} bytes, {description}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

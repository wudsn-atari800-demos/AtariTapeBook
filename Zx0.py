#!/usr/bin/env python3
"""ZX0 compressor and decompressor, format v2, forward.

The compressor is a port of optimize.c and compress.c of ZX0 by Einar Saukas,
https://github.com/einar-saukas/ZX0, under its license:

    BSD 3-Clause License

    Copyright (c) 2021, Einar Saukas
    All rights reserved.

    Redistribution and use in source and binary forms, with or without
    modification, are permitted provided that the following conditions are met:

    1. Redistributions of source code must retain the above copyright notice, this
       list of conditions and the following disclaimer.

    2. Redistributions in binary form must reproduce the above copyright notice,
       this list of conditions and the following disclaimer in the documentation
       and/or other materials provided with the distribution.

    3. Neither the name of the copyright holder nor the names of its
       contributors may be used to endorse or promote products derived from
       this software without specific prior written permission.

    THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
    AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
    IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
    DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
    FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
    DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
    SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
    CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
    OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
    OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

The stream is the same as "zx0" (2.x) writes without options.  The 6502
decompressor is zx0/Zx0.asm.  Pack.py uses compress(); decompress() checks
the result.

Usage:
    python Zx0.py input.bin [output.zx0]
"""
import sys

INITIAL_OFFSET = 1
MAX_OFFSET = 32640


def elias_gamma_bits(value):
    bits = 1
    while value > 1:
        value >>= 1
        bits += 2
    return bits


def optimize(data, offset_limit=MAX_OFFSET):
    """Return the optimal chain of blocks [bits, index, offset, chain]."""
    n = len(data)
    max_offset = min(max(n - 1, INITIAL_OFFSET), offset_limit)
    last_literal = [None] * (max_offset + 1)
    last_match = [None] * (max_offset + 1)
    optimal = [None] * n
    match_length = [0] * (max_offset + 1)
    best_length = [0] * max(n, 3)
    if n > 2:
        best_length[2] = 2
    last_match[INITIAL_OFFSET] = (-1, -1, INITIAL_OFFSET, None)
    eg = [elias_gamma_bits(v) if v else 0 for v in range(max(n, 300) + 2)]
    for index in range(n):
        best_length_size = 2
        mo = min(max(index, INITIAL_OFFSET), offset_limit)
        cur = data[index]
        for offset in range(1, mo + 1):
            if index != 0 and index >= offset and cur == data[index - offset]:
                ll = last_literal[offset]
                if ll:
                    bits = ll[0] + 1 + eg[index - ll[1]]
                    last_match[offset] = (bits, index, offset, ll)
                    if optimal[index] is None or optimal[index][0] > bits:
                        optimal[index] = last_match[offset]
                match_length[offset] += 1
                ml = match_length[offset]
                if ml > 1:
                    if best_length_size < ml:
                        bits = optimal[index - best_length[best_length_size]][0] + eg[best_length[best_length_size] - 1]
                        while True:
                            best_length_size += 1
                            bits2 = optimal[index - best_length_size][0] + eg[best_length_size - 1]
                            if bits2 <= bits:
                                best_length[best_length_size] = best_length_size
                                bits = bits2
                            else:
                                best_length[best_length_size] = best_length[best_length_size - 1]
                            if best_length_size >= ml:
                                break
                    length = best_length[ml]
                    bits = optimal[index - length][0] + 8 + eg[(offset - 1) // 128 + 1] + eg[length - 1]
                    lm = last_match[offset]
                    if lm is None or lm[1] != index or lm[0] > bits:
                        last_match[offset] = (bits, index, offset, optimal[index - length])
                        if optimal[index] is None or optimal[index][0] > bits:
                            optimal[index] = last_match[offset]
            else:
                match_length[offset] = 0
                lm = last_match[offset]
                if lm:
                    length = index - lm[1]
                    bits = lm[0] + 1 + eg[length] + length * 8
                    last_literal[offset] = (bits, index, 0, lm)
                    if optimal[index] is None or optimal[index][0] > bits:
                        optimal[index] = last_literal[offset]
    return optimal[n - 1]


class _Writer:
    def __init__(self):
        self.out = bytearray()
        self.bit_index = 0
        self.bit_mask = 0
        self.backtrack = True

    def byte(self, value):
        self.out.append(value)

    def bit(self, value):
        if self.backtrack:
            if value:
                self.out[-1] |= 1
            self.backtrack = False
        else:
            if not self.bit_mask:
                self.bit_mask = 128
                self.bit_index = len(self.out)
                self.byte(0)
            if value:
                self.out[self.bit_index] |= self.bit_mask
            self.bit_mask >>= 1

    def elias(self, value, invert=False):
        i = 2
        while i <= value:
            i <<= 1
        i >>= 1
        while True:
            i >>= 1
            if not i:
                break
            self.bit(0)
            self.bit((not (value & i)) if invert else (value & i))
        self.bit(1)


def compress(data):
    """Compress `data` (at least 1 byte) to a ZX0 v2 stream."""
    data = bytes(data)
    block = optimize(data)
    chain = []
    while block is not None:
        chain.append(block)
        block = block[3]
    chain.reverse()                     # chain[0] is the fake start block
    w = _Writer()
    last_offset = INITIAL_OFFSET
    pos = 0
    for prev, blk in zip(chain, chain[1:]):
        length = blk[1] - prev[1]
        offset = blk[2]
        if not offset:
            w.bit(0)
            w.elias(length)
            for _ in range(length):
                w.byte(data[pos])
                pos += 1
        elif offset == last_offset:
            w.bit(0)
            w.elias(length)
            pos += length
        else:
            w.bit(1)
            w.elias((offset - 1) // 128 + 1, invert=True)
            w.byte((127 - (offset - 1) % 128) << 1)
            w.backtrack = True
            w.elias(length - 1)
            pos += length
            last_offset = offset
    w.bit(1)
    w.elias(256, invert=True)
    return bytes(w.out)


def decompress(stream):
    """Decompress a ZX0 v2 stream."""
    out = bytearray()
    it = iter(stream)
    state = {"mask": 0, "byte": 0, "backtrack": False, "last": 0}

    def get_byte():
        b = next(it)
        state["last"] = b
        return b

    def bit():
        if state["backtrack"]:
            state["backtrack"] = False
            return state["last"] & 1
        if not state["mask"]:
            state["mask"] = 128
            state["byte"] = get_byte()
        b = 1 if state["byte"] & state["mask"] else 0
        state["mask"] >>= 1
        return b

    def elias(invert=False):
        value = 1
        while not bit():
            value = (value << 1) | (bit() ^ (1 if invert else 0))
        return value

    last_offset = INITIAL_OFFSET
    while True:                         # literals
        for _ in range(elias()):
            out.append(get_byte())
        if not bit():                   # copy from last offset
            length = elias()
            for _ in range(length):
                out.append(out[-last_offset])
            if not bit():
                continue
        while True:                     # copy from new offset
            msb = elias(invert=True)
            if msb == 256:
                return bytes(out)
            last_offset = msb * 128 - (get_byte() >> 1)
            state["backtrack"] = True
            length = elias() + 1
            for _ in range(length):
                out.append(out[-last_offset])
            if not bit():
                break


def main():
    if len(sys.argv) not in (2, 3):
        raise SystemExit(__doc__.split("Usage:")[1])
    data = open(sys.argv[1], "rb").read()
    packed = compress(data)
    if decompress(packed) != data:
        raise SystemExit(f"{sys.argv[1]}: the round trip failed")
    if len(sys.argv) == 3:
        open(sys.argv[2], "wb").write(packed)
    print(f"{sys.argv[1]}: {len(data)} -> {len(packed)} bytes")
    return 0


if __name__ == "__main__":
    sys.exit(main())

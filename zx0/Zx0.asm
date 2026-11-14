;
;	@com.wudsn.ide.lng.mainsourcefile=../boot/Boot.asm
;
; THE ATARI TAPE BOOK - ZX0 decompressor, see plans/08_ZX0_INTRO_PLAN.md
;
; Decompresses a ZX0 stream, format v2, forward, as Zx0.py and "zx0" 2.x
; without options write it. A compact version of our own, 172 bytes.
;
; Call:   set zx0.dst to the destination, then jsr zx0. Returns after the
;         end marker, with zx0.dst after the last byte written.
; Needs:  ZP_ZX0, 9 zero page bytes; ZX0_GET_BYTE, a procedure that
;         returns the next byte of the stream in A. It must keep the carry
;         and may change X and Y.
;
; The offset is kept negated, so the copy source is dst+offs. One routine,
; "put", stores, advances and counts for literals and copies alike: byte by
; byte instead of page-wise loops, which costs speed, not size.

	.proc zx0
dst	= ZP_ZX0		; 2 bytes, destination
src	= ZP_ZX0+2		; 2 bytes, copy source
len	= ZP_ZX0+4		; 2 bytes, length of a literal run or copy
offs	= ZP_ZX0+6		; 2 bytes, negated offset of the last copy
bitbuf	= ZP_ZX0+8		; bits not yet read, followed by a marker bit

	lda #$80		; empty bit buffer: only the marker bit
	sta bitbuf
	lda #$ff		; last offset 1
	sta offs
	sta offs+1

literals
	jsr elias
copy_literal
	jsr ZX0_GET_BYTE
	jsr put
	bne copy_literal
	jsr getbit
	bcs new_offset

	jsr elias		; copy from the last offset
	jsr copy
	jsr getbit
	bcc literals

new_offset
	jsr getbit		; MSB, Elias gamma with inverted bits:
	ldy #$fe		; from $FE, the raw bits give -MSB-1
	jsr elias.with_carry
	inc len			; -MSB, 0 is the end marker
	beq done
	lda len
	sec			; offs+1 = $80 | (-MSB >> 1)
	ror @
	sta offs+1
	jsr ZX0_GET_BYTE	; offs = (-MSB bit 0) << 7 | (LSB >> 1)
	ror @
	sta offs
	ldy #1			; length-1, its first bit is bit 0 of the LSB, in the carry
	jsr elias.with_carry
	inc len
	bne length_ok
	inc len+1
length_ok
	jsr copy
	jsr getbit
	bcs new_offset
	bcc literals
done	rts

; Read an Elias gamma value into len. "with_carry" takes the first bit
; from the carry and the start value from Y.
	.proc elias
	jsr getbit
	ldy #1
with_carry
	sty len
	ldy #0
	sty len+1
	bcs elias_done
elias_loop
	jsr getbit
	rol len
	rol len+1
	jsr getbit
	bcc elias_loop
elias_done
	rts
	.endp

; Read the next bit of the stream into the carry.
	.proc getbit
	asl bitbuf
	bne getbit_done
	jsr ZX0_GET_BYTE	; the carry holds the marker bit
	rol @
	sta bitbuf
getbit_done
	rts
	.endp

; Copy len bytes from dst+offs.
	.proc copy
	lda dst
	clc
	adc offs
	sta src
	lda dst+1
	adc offs+1
	sta src+1
copy_byte
	ldy #0
	lda (src),y
	inc src
	bne src_ok
	inc src+1
src_ok	jsr put
	bne copy_byte
	rts
	.endp

; Store A at dst, advance dst and count len down; Z set when len is 0.
	.proc put
	ldy #0
	sta (dst),y
	inc dst
	bne dst_ok
	inc dst+1
dst_ok	lda len
	bne len_ok
	dec len+1
len_ok	dec len
	lda len
	ora len+1
	rts
	.endp
	.endp

#!/usr/bin/env python3
"""Speak a text file into a 16-bit mono .wav with the Windows speech synthesizer.

Used for the narration while the intro loads (plans/07_BOOT_NARRATION_PLAN.md):
boot/Make-Narration.bat speaks boot/Narration.txt into boot/Boot.WAV, which
Bin2Wav.py puts on the audio channel of the boot section.  A real recording
can replace the .wav under the same name.

Paragraphs are separated by blank lines; the synthesizer pauses between them.
Voice, language and rate are pinned, so the .wav has the same length on every
computer: the voice is Microsoft David (the voice the narration's length was
fitted with) or the one given with --voice, and it must speak the language
given with --culture (default en-US). The prompt carries that language and
voice too; without them, the synthesizer would follow the language of
Windows and switch, for example, to a German voice on a German Windows. The
rate is 0, the normal rate, unless given. If the voice is not installed, the
script stops and lists the installed voices of the language.

Usage:
    python Speak.py boot/Narration.txt boot/Boot.WAV
    python Speak.py --voice "Microsoft Zira Desktop" --rate 1 boot/Narration.txt boot/Boot.WAV
"""
import argparse
import os
import subprocess
import sys
import wave

RATE = 22050
DEFAULT_VOICE = "Microsoft David Desktop"

SPEAK_SCRIPT = f"""
Add-Type -AssemblyName System.Speech
$s = New-Object System.Speech.Synthesis.SpeechSynthesizer
$voices = $s.GetInstalledVoices() | Where-Object {{ $_.Enabled -and $_.VoiceInfo.Culture.Name -eq $env:SPEAK_CULTURE }}
$v = $voices | Where-Object {{ $_.VoiceInfo.Name -eq $env:SPEAK_VOICE }} | Select-Object -First 1
if (-not $v) {{
    $names = ($voices | ForEach-Object {{ $_.VoiceInfo.Name }}) -join ', '
    if (-not $names) {{ $names = 'none' }}
    [Console]::Error.WriteLine("voice '$env:SPEAK_VOICE' ($env:SPEAK_CULTURE) is not installed; installed $env:SPEAK_CULTURE voices: $names")
    exit 1
}}
$s.SelectVoice($v.VoiceInfo.Name)
$s.Rate = [int]$env:SPEAK_RATE
$f = New-Object System.Speech.AudioFormat.SpeechAudioFormatInfo({RATE},
    [System.Speech.AudioFormat.AudioBitsPerSample]::Sixteen, [System.Speech.AudioFormat.AudioChannel]::Mono)
$s.SetOutputToWaveFile($env:SPEAK_OUTPUT, $f)
$p = New-Object System.Speech.Synthesis.PromptBuilder($v.VoiceInfo.Culture)
$p.StartVoice($v.VoiceInfo)
foreach ($paragraph in ($env:SPEAK_TEXT -split "`n`n")) {{
    $p.AppendText($paragraph.Trim())
    $p.AppendBreak([System.Speech.Synthesis.PromptBreak]::Large)
}}
$p.EndVoice()
$s.Speak($p)
$s.Dispose()
Write-Output $v.VoiceInfo.Name
"""


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("text", help="text file, UTF-8, paragraphs separated by blank lines")
    p.add_argument("output", help="output .wav, 16-bit mono")
    p.add_argument("--voice", default=DEFAULT_VOICE, help=f"name of the voice (default {DEFAULT_VOICE})")
    p.add_argument("--culture", default="en-US", help="language of the voice and the text (default en-US)")
    p.add_argument("--rate", type=int, default=0, help="speaking rate from -10 to 10 (default 0, normal)")
    args = p.parse_args()

    with open(args.text, encoding="utf-8-sig") as f:
        paragraphs = [" ".join(block.split()) for block in f.read().replace("\r", "").split("\n\n")]
    text = "\n\n".join(block for block in paragraphs if block)
    r = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", SPEAK_SCRIPT],
                       env={**os.environ, "SPEAK_TEXT": text, "SPEAK_OUTPUT": os.path.abspath(args.output),
                            "SPEAK_VOICE": args.voice, "SPEAK_CULTURE": args.culture, "SPEAK_RATE": str(args.rate)},
                       capture_output=True, text=True)
    if r.returncode != 0 or not os.path.exists(args.output):
        sys.stderr.write(r.stdout + r.stderr)
        raise SystemExit(f"speaking {args.text} failed")
    with wave.open(args.output) as w:
        seconds = w.getnframes() / w.getframerate()
    print(f"{args.output}: {seconds:.1f} s, voice {r.stdout.strip()} ({args.culture}), rate {args.rate}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

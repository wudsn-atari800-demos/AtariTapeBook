#!/usr/bin/env python3
"""Speak a text file into a 16-bit mono .wav with the Windows speech synthesizer.

Used for the narration while the intro loads (plans/07_BOOT_NARRATION_PLAN.md):
boot/Make-Narration.bat speaks boot/Narration.txt into boot/Boot.WAV, which
Bin2Wav.py puts on the audio channel of the boot section.  A real recording
can replace the .wav under the same name.

Paragraphs are separated by blank lines; the synthesizer pauses between them.
The voice is the first enabled one of the given culture (default en-US), or
the one given by name.

Usage:
    python Speak.py boot/Narration.txt boot/Boot.WAV
    python Speak.py --voice "Microsoft David Desktop" boot/Narration.txt boot/Boot.WAV
"""
import argparse
import os
import subprocess
import sys
import wave

RATE = 22050

SPEAK_SCRIPT = f"""
Add-Type -AssemblyName System.Speech
$s = New-Object System.Speech.Synthesis.SpeechSynthesizer
$voices = $s.GetInstalledVoices() | Where-Object {{ $_.Enabled }}
if ($env:SPEAK_VOICE) {{
    $v = $voices | Where-Object {{ $_.VoiceInfo.Name -eq $env:SPEAK_VOICE }} | Select-Object -First 1
}} else {{
    $v = $voices | Where-Object {{ $_.VoiceInfo.Culture.Name -like $env:SPEAK_CULTURE }} | Select-Object -First 1
}}
if (-not $v) {{ Write-Error 'no matching voice installed'; exit 1 }}
$s.SelectVoice($v.VoiceInfo.Name)
$f = New-Object System.Speech.AudioFormat.SpeechAudioFormatInfo({RATE},
    [System.Speech.AudioFormat.AudioBitsPerSample]::Sixteen, [System.Speech.AudioFormat.AudioChannel]::Mono)
$s.SetOutputToWaveFile($env:SPEAK_OUTPUT, $f)
$p = New-Object System.Speech.Synthesis.PromptBuilder
foreach ($paragraph in ($env:SPEAK_TEXT -split "`n`n")) {{
    $p.AppendText($paragraph.Trim())
    $p.AppendBreak([System.Speech.Synthesis.PromptBreak]::Large)
}}
$s.Speak($p)
$s.Dispose()
Write-Output $v.VoiceInfo.Name
"""


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("text", help="text file, UTF-8, paragraphs separated by blank lines")
    p.add_argument("output", help="output .wav, 16-bit mono")
    p.add_argument("--voice", help="name of the voice, e.g. 'Microsoft Zira Desktop'")
    p.add_argument("--culture", default="en-US", help="culture of the voice if no name is given (default en-US)")
    args = p.parse_args()

    with open(args.text, encoding="utf-8-sig") as f:
        paragraphs = [" ".join(block.split()) for block in f.read().replace("\r", "").split("\n\n")]
    text = "\n\n".join(block for block in paragraphs if block)
    r = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", SPEAK_SCRIPT],
                       env={**os.environ, "SPEAK_TEXT": text, "SPEAK_OUTPUT": os.path.abspath(args.output),
                            "SPEAK_VOICE": args.voice or "", "SPEAK_CULTURE": args.culture},
                       capture_output=True, text=True)
    if r.returncode != 0 or not os.path.exists(args.output):
        sys.stderr.write(r.stdout + r.stderr)
        raise SystemExit(f"speaking {args.text} failed")
    with wave.open(args.output) as w:
        seconds = w.getnframes() / w.getframerate()
    print(f"{args.output}: {seconds:.1f} s, voice {r.stdout.strip()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

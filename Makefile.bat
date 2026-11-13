mads -o:Boot.sec Boot.asm
python Bin2Wav.py --short-irg --short-leader Boot.sec Chapter1.bas=Chapter1.wav Chapter2.bas=Chapter2.wav AtariTapeBook.wav
C:\jac\system\Atari800\Tools\EMU\Altirra\Altirra.exe /basic /casautoboot /tape AtariTapeBook.wav

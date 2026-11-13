mads -o:boot/Boot.sec boot/Boot.asm
python Bin2Wav.py --short-irg --short-leader boot/Boot.sec chapters/Chapter1.bas=chapters/Chapter1.wav chapters/Chapter2.bas=chapters/Chapter2.wav AtariTapeBook.wav
C:\jac\system\Atari800\Tools\EMU\Altirra\Altirra.exe /basic /casautoboot /tape AtariTapeBook.wav

mads -o:boot/Boot.sec boot/Boot.asm
python Bin2Wav.py --short-irg --short-leader boot/Boot.sec chapters/CHAPTER1.BAS=chapters/CHAPTER1.WAV chapters/CHAPTER2.BAS=chapters/CHAPTER2.WAV AtariTapeBook.wav
C:\jac\system\Atari800\Tools\EMU\Altirra\Altirra.exe /basic /casautoboot /tape AtariTapeBook.wav

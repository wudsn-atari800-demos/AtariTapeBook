mads -o:Boot.sec Boot.asm
python Bin2Wav.py --short-irg --short-leader Boot.sec Book1.bas=Book1.wav Book2.bas=Book2.wav Boot.wav
C:\jac\system\Atari800\Tools\EMU\Altirra\Altirra.exe /basic /casautoboot /tape Boot.wav

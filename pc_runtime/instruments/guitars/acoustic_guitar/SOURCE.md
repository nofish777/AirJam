# Acoustic Guitar SoundFont

Put the acoustic guitar `.sf2` file for the MaixCAM2 acoustic guitar mode in this folder.

Default filename expected by `pc_instrument_server.py`:

```text
FSS-SteelStringGuitar-20200521.sf2
```

You can also pass a custom path when starting the PC server:

```powershell
python pc_instrument_server.py --acoustic-guitar-sf2 "D:\path\to\your\acoustic.sf2"
```

The acoustic guitar mode uses pre-rendered up/down strum WAV files for lower latency:

```text
strums/C_down.wav
strums/C_up.wav
strums/G_down.wav
strums/G_up.wav
strums/Am_down.wav
strums/Am_up.wav
strums/F_down.wav
strums/F_up.wav
strums/D_down.wav
strums/D_up.wav
strums/Em_down.wav
strums/Em_up.wav
strums/A_down.wav
strums/A_up.wav
strums/E_down.wav
strums/E_up.wav
```

Generate them from the default SoundFont with:

```powershell
python pc_generate_guitar_strum_wavs.py --instrument acoustic_guitar
```

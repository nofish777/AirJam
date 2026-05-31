# Electric Guitar SoundFont

Put Bread Breads Distortion Guitar files in this folder.

Default filename expected by `pc_instrument_server.py`:

```text
Bread Breads Distortion Guitar v2.1.sf2
```

Electric guitar mode uses pre-rendered up/down power-chord strum WAV files for lower latency and clearer direction differences:

```text
strums/C5_down.wav
strums/C5_up.wav
strums/D5_down.wav
strums/D5_up.wav
strums/E5_down.wav
strums/E5_up.wav
strums/F5_down.wav
strums/F5_up.wav
strums/G5_down.wav
strums/G5_up.wav
strums/A5_down.wav
strums/A5_up.wav
strums/Bb5_down.wav
strums/Bb5_up.wav
strums/B5_down.wav
strums/B5_up.wav
```

Generate them from the default SoundFont with:

```powershell
python pc_generate_guitar_strum_wavs.py --instrument electric_guitar
```

# Salamander Grand Piano

The current piano mode uses:

```text
SalamanderGrandPiano-V3+20200602.sf2
```

The PC server plays pre-rendered WAV notes first:

```text
samples/036.wav
...
samples/095.wav
```

Those 60 samples cover five selectable octaves. Regenerate them with:

```powershell
python pc_generate_piano_wavs.py
```

# Shino Drums Snare

The current snare mode uses the Shino Drums snare SoundFont:

```text
02_Shino_Snare.sf2
```

`02_Shino_Snare.sf2` exposes the snare preset at:

```text
bank=0
preset=2
note=40
```

The PC server plays pre-rendered velocity layers first:

```text
snare_samples/ghost.wav
snare_samples/normal.wav
snare_samples/accent.wav
```

Regenerate them with:

```powershell
python pc_generate_snare_wavs.py
```

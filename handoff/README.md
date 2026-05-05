# Local amapiano track analyser

`analyze.py` runs entirely on your Mac — your audio file never leaves the
machine. It produces a small bundle of analysis artefacts (numbers + pictures
+ generated reference loops) which you can then paste into a Claude chat to
get a detailed amapiano-specific feedback report.

## One-time setup

```bash
brew install ffmpeg
pip3 install librosa numpy scipy matplotlib soundfile pyloudnorm mido demucs
```

Demucs will download a ~250 MB model the first time you run with stems.

If `pip3 install` hits build errors on your system Python, use a venv:

```bash
python3 -m venv ~/amapiano-venv
~/amapiano-venv/bin/pip install -U pip setuptools wheel
~/amapiano-venv/bin/pip install librosa numpy scipy matplotlib soundfile pyloudnorm mido demucs
# then prefix all later python3 calls with the venv binary:
~/amapiano-venv/bin/python analyze.py "path/to/your.mp3"
```

## Run it

```bash
python3 analyze.py "/Users/hom/Downloads/Telegram Desktop/тамбов.mp3"
```

Flags:
- `--no-stems`    skip Demucs (much faster, ~10s instead of a few minutes)
- `--no-samples`  skip generating log-drum / hat / chord reference loops

## What it produces

Output goes into `<basename>_analysis/` next to the input file:

```
тамбов_analysis/
├── metrics.json          # all numeric features (BPM, key, LUFS, swing, ...)
├── plots/
│   ├── waveform.png
│   ├── melspec.png       # full mel-spectrogram
│   ├── chroma.png        # chromagram (pitch content over time)
│   ├── onset.png         # onset envelope (rhythmic density)
│   ├── structure.png     # waveform with detected section boundaries
│   └── stems/            # if --no-stems wasn't passed
│       ├── drums_melspec.png
│       ├── bass_melspec.png
│       ├── vocals_melspec.png
│       └── other_melspec.png
└── samples/
    ├── logdrum_<bpm>_<key>.wav   # 4-bar pitched-sub log-drum loop
    ├── hats_<bpm>.wav            # 4-bar 16th-note hat shuffle + claps
    ├── hats.mid                  # same pattern as MIDI
    ├── chords_v1.mid             # i-VI-III-VII (or I-vi-IV-V if major)
    └── chords_v2.mid             # i-iv-VII-III (or I-V-vi-IV)
```

## Getting the feedback report

Drag these into a Claude chat:

1. `metrics.json`
2. The five PNGs in `plots/`
3. (Optional) the four PNGs in `plots/stems/`

…and ask: *"using these analysis outputs, write the amapiano feedback report
per the plan."*

You don't need to share the audio. The spectrograms are heatmaps of frequency
content — they're useful for diagnosis but can't be turned back into your
track. The MIDI/WAV samples in `samples/` are reference starting points to
audition in your DAW.

## Honest limitations

- Key estimation uses Krumhansl-Schmuckler on mean chroma. On dense full-mix
  tracks it's usually right; on percussion-heavy stubs the gap between
  major/minor variants of the same root can be tiny. Always cross-check with
  the chromagram. The script flags this with a `key_confidence_label` field.
- Swing detection picks up *all* onsets, not just hats. If your track has lots
  of straight elements (kick, vocal chops on the grid) the swing number will
  underestimate the hat shuffle. Eyeball the drums-stem mel-spectrogram for
  the real shuffle pattern.
- LUFS targets depend on the master destination (club master ≈ -8 LUFS,
  Spotify normalises to -14, SoundCloud is freer). The report will discuss
  whichever you specify.

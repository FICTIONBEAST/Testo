# Prompt to paste into Claude Code CLI

Open Terminal on your Mac, then:

```bash
cd "/Users/hom/Downloads/Telegram Desktop"
# (drop the four files from this handoff folder into the same directory:
#  analyze.py, README.md, PLAN.md, CONVERSATION_HISTORY.md)
claude
```

Paste this prompt in the Claude Code session:

---

I'm picking up a project that was started in a previous Claude session. The
working directory contains:

- `analyze.py` — a self-contained amapiano track analyser
- `README.md` — how to run it
- `PLAN.md` — the original analysis plan
- `CONVERSATION_HISTORY.md` — full context from the previous session
- `тамбов.mp3` — the rough-draft amapiano track to analyse

**Step 1.** Read CONVERSATION_HISTORY.md, PLAN.md, and README.md so you have
the full context. You're an experienced amapiano producer giving feedback to
another producer on a rough draft.

**Step 2.** Make sure dependencies are installed:
```
brew install ffmpeg            # if not already
pip3 install librosa numpy scipy matplotlib soundfile pyloudnorm mido demucs
```
If pip3 fails on antlr4-runtime, fall back to a venv as documented in the
README. Do not skip Demucs — the per-stem analysis is part of the locked plan.

**Step 3.** Run `python3 analyze.py "тамбов.mp3"`. This will create
`тамбов_analysis/` next to the MP3 with `metrics.json`, `plots/*.png`,
`plots/stems/*.png`, and `samples/*.wav,*.mid`. First Demucs run will download
a ~250MB model — that's expected.

**Step 4.** Read `тамбов_analysis/metrics.json` and every PNG in
`тамбов_analysis/plots/` (including `plots/stems/`). The PNGs are spectrograms
and chromagrams — read them as images and reason about what you see. You
cannot listen to the audio directly; be honest in the report about what is
measured vs what is inferred.

**Step 5.** Write `тамбов_analysis/feedback.md` containing:

1. **Track summary** — duration, detected BPM, detected key (with the
   confidence label from metrics.json — if it's "low", explicitly note that
   the key call is uncertain and reference the chromagram), integrated LUFS,
   true peak.
2. **Subgenre verdict** — private school / sgija / 3-step (or a hybrid),
   with the feature evidence behind the call (BPM band, swing fraction, kick
   character from the drums-stem mel-spectrogram, vocal density from the
   vocals stem).
3. **Section-by-section notes** — walk through the section boundaries from
   metrics.json, describing what each section probably contains based on the
   waveform/onset/melspec PNGs. Reference timestamps explicitly.
4. **Genre-fit assessment** — score the track against amapiano norms (tempo,
   swing, log-drum presence, kick softness, chord voicings, arrangement
   pacing). Be specific — "your hi-hats sit at X% swing vs the typical
   58–62%, so it feels straighter than a private-school track" beats "swing
   could be more shuffled".
5. **Top 3–5 mix issues** — actionable, ranked. Use the spectral_band_energy
   fractions and the per-stem spectrograms to identify mud (200–400 Hz),
   harshness (2–5 kHz), boxiness, dull air, mono compatibility issues, etc.
6. **Creative suggestions** — arrangement (intro length, where to add a
   breakdown, vocal-chop placement), sound design (log-drum tuning ideas,
   pad voicings to try), hooks. Keep it specific to what you can see in the
   plots and what the metrics suggest is missing.
7. **Embedded thumbnails** of `plots/melspec.png` and `plots/chroma.png`
   (use markdown image syntax with relative paths so they render in editors).
8. **Links to the generated samples** in `samples/` with one-line notes on
   how the user might integrate them as starting points.

**Step 6.** Print a one-paragraph summary of the report to the chat and tell
the user where the file lives. Do not commit or push the analysis folder —
it's user content (the .gitignore already excludes `*_analysis/` and `*.mp3`).

**Tone**: practical, opinionated, producer-to-producer. Skip hedging that
doesn't add information. Where you genuinely can't tell something without
listening (e.g. emotional impact, vocal phrasing, melody quality), say so
explicitly rather than guessing.

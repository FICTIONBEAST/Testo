# Conversation history — amapiano rough-draft MP3 analysis

This is a hand-off document for a fresh Claude Code CLI session. The user has
already had a planning conversation in another (web-based) Claude session; this
file summarises everything that was decided so the next agent can pick up cold.

---

## Original request

User produced a rough-draft amapiano track. The MP3 lives on the user's Mac at:

```
/Users/hom/Downloads/Telegram Desktop/тамбов.mp3
```

(Cyrillic; loosely "Tambov".) They want:

- detailed analysis of what they made,
- amapiano-specific insight & suggestions,
- generation of reference samples (drum loops, chord MIDI),
- producer-style feedback (mix critique, arrangement, sound design).

## Hard constraints (set by the user)

1. **Audio stays on the user's Mac.** They will not upload the track to GitHub
   or any third-party file-share. They ruled this out explicitly.
2. **Claude desktop on macOS doesn't accept MP3 attachments**, so the file
   couldn't be passed in via chat upload.
3. The previous (web) session was running in a Linux sandbox at
   `/home/user/Testo` and could not reach `/Users/hom/...` on the user's Mac —
   that's why this hand-off is happening.

## Decisions locked in (Plan-mode Q&A)

- **Depth**: full pipeline including Demucs 4-stem split + per-stem critique.
- **Samples**: log-drum loop (WAV), hat/shaker shuffle (WAV+MIDI), and two
  chord-progression MIDIs in the detected key.
- **Output format**: a single markdown report with embedded PNG thumbnails
  (no slide deck).
- **Subgenre**: inferred from features — private school / sgija / 3-step.

## What's already been built (committed on branch `claude/amapiano-music-analysis-aA8Yw`)

- **`analyze.py`** — a self-contained Python script that runs entirely on the
  user's Mac. Extracts tempo, key (with confidence gap), swing, LUFS, spectral
  balance, stereo width, and section boundaries; renders waveform /
  mel-spectrogram / chromagram / onset / structure PNGs; runs Demucs on each
  stem and re-extracts features per stem; generates 4 reference samples.
- **`README.md`** — how to install deps and run `analyze.py`.
- **`PLAN.md`** — the original analysis plan.

The script was smoke-tested in the web session against a synthetic 30-second
amapiano-style WAV. Detected ~115 BPM (intended 114), correctly identified A
as the tonal centre (confidence-gap was tiny, flagged as low). All five PNGs
plus three MIDIs and two WAVs were produced cleanly. One MIDI delta-time bug
was found and fixed during testing.

## What remains for the next agent

1. Make sure dependencies are installed on the user's Mac:
   - `brew install ffmpeg`
   - `pip3 install librosa numpy scipy matplotlib soundfile pyloudnorm mido demucs`
   - (use a venv if pip's antlr4-runtime build fails — see README)
2. Run `analyze.py` on the actual MP3.
3. Read the resulting `metrics.json` and the PNG plots.
4. Write the feedback report (`feedback.md`) inside the analysis folder.

## Honest limitations to carry forward

- The agent can read PNGs and JSON but **cannot listen to audio directly** — so
  feedback rests on extracted features + visual inspection of spectrograms and
  chromagrams. Subjective vibe / catchiness should be hedged.
- Krumhansl-Schmuckler key estimation can fumble major vs minor on percussive
  loops; cross-check against the chromagram.
- LUFS targets depend on the master destination — ask the user where it'll
  live (club master ≈ -8, Spotify -14, SoundCloud freer).

## Amapiano reference points

- Tempo: 110–118 BPM (sometimes 105–122).
- Drums: soft kick, claps on 2 & 4, 16th-note hat shuffle (~58–62% swing),
  shakers filling between hats.
- Log drum: pitched-sub percussive melody around 50–120 Hz, root + 5th + m3
  voicings; spectrogram shows pitched transients, not a sustained sine.
- Chords: jazzy 7ths & 9ths, often Dorian or Aeolian, mostly minor keys
  (Am, Dm, Em, Gm, F#m).
- Arrangement: long intros (32–64 bars), slow builds, breakdowns where the
  log drum drops out then re-enters as the hook.
- Mix: warm low end, controlled 200–400 Hz, bright but not harsh highs,
  plenty of headroom — kick is felt rather than punched.
- Reference artists: Kabza De Small, Mas Musiq, Vigro Deep, Major League DJz,
  De Mthuda, DJ Maphorisa, Sjavas Da Deejay, Mr JazziQ.

Subgenres for the verdict call:
- **Private school / soulful**: jazzy, slower, vocal-led, sparse drums.
- **Sgija**: faster, punchier, club-leaning, harder kicks.
- **3-step**: newer hybrid with a more house-leaning kick pattern.

# Amapiano Rough-Draft MP3 — Analysis & Feedback Plan

## Context

You have a rough-draft MP3 of a track you produced in the amapiano style and want
detailed analysis, insight, suggestions, generated reference samples, and creative
feedback.

Two important constraints shape the plan:

1. **No MP3 is on disk yet.** The working directory `/home/user/Testo` only
   contains a small `testo.py` (with an unrelated typo: `numpp` → `numpy`). Step 0
   is therefore "place the file somewhere I can read it."
2. **I cannot directly listen to audio.** I'm multimodal for images/PDFs but not
   audio. So all musical "listening" has to go through a feature-extraction
   pipeline (librosa / essentia / demucs) that produces numbers and PNG plots
   that I *can* read. This is more rigorous than ear-checking but loses some
   subjective nuance — I'll flag where that matters.

The output will be a structured producer-style feedback report grounded in
amapiano norms (BPM, log-drum patterns, swing, mix character, arrangement) plus
generated reference samples (WAV / MIDI) you can drop into your DAW.

## Locked-in choices (from clarifying Qs)
- **Depth**: full pipeline including Demucs stem split + per-stem critique.
- **Samples**: log-drum loop (WAV), hat/shaker shuffle (WAV+MIDI), and two
  chord-progression MIDIs in the detected key.
- **Output**: single markdown report with embedded PNG thumbnails (no slides).
- **Subgenre**: inferred from features — I'll pick the closest amapiano flavour
  (private school / sgija / 3-step) based on tempo, swing, kick character, and
  vocal density, then reference accordingly.

## Approach

### Step 0 — Get the file in scope
- You drop the MP3 into `/home/user/Testo/` (e.g. `track.mp3`).
- I confirm it with `ffprobe` (duration, sample rate, bitrate, channels, encoder).

### Step 1 — Environment setup (one-time, ~2 min)
Currently nothing audio-related is installed. I'll install:
- System: `ffmpeg` (apt) — required for MP3 decode.
- Python: `librosa`, `numpy`, `scipy`, `matplotlib`, `soundfile`, `pyloudnorm`,
  `mutagen`, and `demucs` (only if stem separation is requested — it's heavy).

### Step 2 — Whole-track feature extraction
A single Python script writes results to JSON + PNGs in `/home/user/Testo/analysis/`.

| Feature | Tool | Why it matters for amapiano |
|---|---|---|
| Tempo (global + per-beat stability) | `librosa.beat.beat_track` | Amapiano sits ~110–118 BPM; drift signals timing issues |
| Key & mode | chroma + Krumhansl-Schmuckler | Most amapiano is minor (Am, Dm, Gm, F#m); confirms tonal centre |
| Time signature / swing | onset autocorrelation | Amapiano hi-hats often shuffle; quantifies the groove feel |
| Loudness (integrated LUFS, true peak, LRA) | `pyloudnorm` | Streaming target ~-9 to -7 LUFS for club, -14 for Spotify |
| Dynamic range (PSR, crest factor) | numpy on RMS/peak | Amapiano keeps headroom for the log-drum punch |
| Spectral balance (band energy in sub / low / mid / high-mid / air) | FFT bands | Diagnoses muddy lows, harsh 2-5 kHz, dull air |
| Stereo width per band | mid/side analysis | Sub should be mono; pads/percs wide |
| Section/structure segmentation | `librosa.segment` | Maps intro / build / drop / break for arrangement notes |
| Onset density over time | `librosa.onset` | Reveals dynamic contour (amapiano breathes — sparse → dense) |
| Mel-spectrogram + waveform + chromagram PNGs | matplotlib | I read these PNGs back to "see" the track |

### Step 3 — Stem split (Demucs, 4-stem)
Run `demucs` (4-stem: drums / bass / vocals / other). Then re-run Step 2 on each
stem so feedback can be specific:
- **Drums stem** → kick consistency, hat shuffle pattern, shaker placement, log-drum tuning
- **Bass stem** → is the log-drum carrying the bass or is there a separate sub? mono-compatibility
- **Vocals stem** → chop placement, sibilance, reverb tail length
- **Other stem** → pad/Rhodes voicings, key changes, any clutter in the 200–500 Hz region

### Step 4 — Amapiano-specific evaluation
Score the extracted features against genre conventions:

- **Tempo & swing**: target 110–118 BPM; characteristic 16th-note hat shuffle
  (~58–62% swing). Flag if straight or out of pocket.
- **Log drum**: tuned percussive sub-melody, usually root + 5th/m3 around the
  chord. Spectrogram should show strong content 50–120 Hz with pitched
  transients, not a sustained sine.
- **Kick**: soft, short, often sidechained subtly to the log drum. Amapiano kicks
  are felt, not punched like house.
- **Hats & shakers**: shuffle on the off-16ths; shakers fill space between hats.
- **Pads / Rhodes / piano**: jazz-leaning 7ths, 9ths, often Dorian/Aeolian.
- **Arrangement**: long intros (32–64 bars), slow builds, vocal chops as hooks,
  breakdowns where the log drum drops out then re-enters.
- **Mix character**: warm low end, controlled 200–400 Hz, bright but not harsh
  highs, plenty of headroom.

I'll cross-reference with a small library of well-mixed amapiano reference
tracks (Kabza De Small, Mas Musiq, Vigro Deep, Major League DJz, De Mthuda)
fetched via WebSearch for current touchstones.

### Step 5 — Generated samples & suggestions
All three deliverables, written to `/home/user/Testo/analysis/samples/`:
- **`logdrum_<bpm>_<key>.wav`** — pitched-sub log-drum loop (root + 5th + m3
  with fast pitch-down envelope), 4 bars at the detected BPM and key.
- **`hats_<bpm>.wav` + `hats.mid`** — 16th-note hat + shaker shuffle pattern at
  the detected swing percentage; clap on 2 & 4.
- **`chords_v1.mid` and `chords_v2.mid`** — two amapiano-flavoured progressions
  in the detected key (e.g. i–VI–III–VII and i–iv–VII–III, voiced with 7ths/9ths).
- **Arrangement skeleton** appended to the report as a markdown timeline with
  bar counts (intro / build / drop / break / outro).

### Step 6 — Deliverable
A single markdown report `/home/user/Testo/analysis/feedback.md` with:
1. Track summary (tempo, key, length, LUFS)
2. Section-by-section notes referencing timestamps
3. Genre-fit assessment vs. amapiano norms
4. Mix notes (top 3–5 actionable issues)
5. Creative suggestions (arrangement, sound design, hooks)
6. Embedded thumbnails of the spectrogram & chromagram
7. Links to the generated WAV/MIDI samples in `analysis/samples/`
8. Inferred subgenre verdict (private school / sgija / 3-step) with the
   feature evidence behind that call.

## Critical files / paths
- `/home/user/Testo/track.mp3` — input (you provide)
- `/home/user/Testo/analyze.py` — pipeline script (new, single file)
- `/home/user/Testo/analysis/` — JSON metrics, PNGs, generated samples
- `/home/user/Testo/analysis/feedback.md` — final report

## Verification
1. `ffprobe track.mp3` returns valid duration/SR/bitrate.
2. `python3 analyze.py track.mp3` exits 0 and writes ≥4 PNGs + `metrics.json`.
3. Detected BPM is within ±1 of what you intended; key matches your project.
4. I open each PNG via Read and reference what I see in the report.
5. Generated WAV samples play at the detected BPM and align to the grid in
   your DAW.

## Honest limitations
- Vibe, emotional impact, and "is this catchy?" can't be measured — I'll mark
  those sections as opinion based on structural cues, not listening.
- Stem separation introduces artefacts; treat per-stem mix critique as
  directional, not gospel.
- LUFS targets depend on release destination (club master vs. streaming master).

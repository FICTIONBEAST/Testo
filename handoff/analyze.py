#!/usr/bin/env python3
"""
analyze.py - rough-draft amapiano track analyser

Usage on your Mac:
    brew install ffmpeg
    pip3 install librosa numpy scipy matplotlib soundfile pyloudnorm mido demucs
    python3 analyze.py "path/to/track.mp3"
    python3 analyze.py "path/to/track.mp3" --no-stems   # skip demucs (much faster)
    python3 analyze.py "path/to/track.mp3" --no-samples # skip generated samples

Outputs (next to the input file):
    <basename>_analysis/
      metrics.json          numeric features
      plots/                waveform, mel-spectrogram, chromagram, onset, structure (PNG)
      plots/stems/          per-stem mel-spectrograms (if demucs ran)
      samples/              log-drum WAV, hat WAV+MIDI, chord MIDIs

Drag the metrics.json and the contents of plots/ back into a Claude chat
and ask for the amapiano-specific feedback report. The audio never has to leave
your machine.
"""
import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
import librosa
import librosa.display
import soundfile as sf
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pyloudnorm as pyln
from mido import MidiFile, MidiTrack, Message, MetaMessage, bpm2tempo

NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
KRUMHANSL_MAJOR = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
KRUMHANSL_MINOR = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])


# -----------------------------------------------------------------------------
# feature extraction
# -----------------------------------------------------------------------------
def detect_key(y, sr):
    chroma = librosa.feature.chroma_cqt(y=y, sr=sr).mean(axis=1)
    scores = {}
    for i in range(12):
        scores[f"{NOTE_NAMES[i]} major"] = float(np.corrcoef(np.roll(KRUMHANSL_MAJOR, i), chroma)[0, 1])
        scores[f"{NOTE_NAMES[i]} minor"] = float(np.corrcoef(np.roll(KRUMHANSL_MINOR, i), chroma)[0, 1])
    best = max(scores, key=scores.get)
    return best, scores[best], scores


def detect_swing(y, sr, bpm):
    """Median fractional offset of off-16th onsets relative to a straight grid.
    0 = straight, ~0.17 = light swing, ~0.33 = strong shuffle.
    """
    if bpm <= 0:
        return None
    onset_env = librosa.onset.onset_strength(y=y, sr=sr)
    onset_frames = librosa.onset.onset_detect(onset_envelope=onset_env, sr=sr)
    if len(onset_frames) < 16:
        return None
    onset_times = librosa.frames_to_time(onset_frames, sr=sr)
    sixteenth = 60.0 / bpm / 4.0
    quanta = np.round(onset_times / sixteenth).astype(int)
    off_mask = (quanta % 4 == 1) | (quanta % 4 == 3)
    if off_mask.sum() < 4:
        return None
    delta = (onset_times[off_mask] - quanta[off_mask] * sixteenth) / sixteenth
    return float(np.median(delta))


def spectral_balance(y, sr):
    S = np.abs(librosa.stft(y)) ** 2
    freqs = librosa.fft_frequencies(sr=sr)
    bands = {
        "sub_20_60": (20, 60),
        "low_60_200": (60, 200),
        "low_mid_200_500": (200, 500),
        "mid_500_2k": (500, 2000),
        "high_mid_2k_6k": (2000, 6000),
        "air_6k_16k": (6000, 16000),
    }
    total = float(S.sum()) + 1e-12
    return {name: float(S[(freqs >= lo) & (freqs < hi)].sum() / total) for name, (lo, hi) in bands.items()}


def loudness(y, sr):
    meter = pyln.Meter(sr)
    audio = y if y.ndim == 1 else y.T
    integrated = float(meter.integrated_loudness(audio))
    peak = float(np.max(np.abs(y)))
    rms = float(np.sqrt(np.mean(y ** 2)) + 1e-12)
    return {
        "integrated_lufs": integrated,
        "true_peak_dbfs": float(20 * np.log10(peak + 1e-12)),
        "crest_factor_db": float(20 * np.log10(peak / rms)),
    }


def stereo_width(y_stereo):
    if y_stereo.ndim != 2 or y_stereo.shape[0] != 2:
        return None
    L, R = y_stereo
    M = (L + R) / 2
    S = (L - R) / 2
    eps = 1e-12
    return float(20 * np.log10((np.sqrt(np.mean(S ** 2)) + eps) / (np.sqrt(np.mean(M ** 2)) + eps)))


def section_boundaries(y, sr, n_segments=8):
    chroma = librosa.feature.chroma_cqt(y=y, sr=sr)
    bounds = librosa.segment.agglomerative(chroma, n_segments)
    return [float(t) for t in librosa.frames_to_time(bounds, sr=sr)]


# -----------------------------------------------------------------------------
# plots
# -----------------------------------------------------------------------------
def plot_waveform(y, sr, out):
    plt.figure(figsize=(12, 3))
    librosa.display.waveshow(y, sr=sr)
    plt.title("Waveform")
    plt.tight_layout()
    plt.savefig(out, dpi=110)
    plt.close()


def plot_melspec(y, sr, out, title="Mel-spectrogram"):
    S = librosa.feature.melspectrogram(y=y, sr=sr, n_mels=128, fmax=sr / 2)
    Sdb = librosa.power_to_db(S, ref=np.max)
    plt.figure(figsize=(12, 4))
    librosa.display.specshow(Sdb, sr=sr, x_axis="time", y_axis="mel", fmax=sr / 2)
    plt.colorbar(format="%+2.0f dB")
    plt.title(title)
    plt.tight_layout()
    plt.savefig(out, dpi=110)
    plt.close()


def plot_chroma(y, sr, out):
    chroma = librosa.feature.chroma_cqt(y=y, sr=sr)
    plt.figure(figsize=(12, 3))
    librosa.display.specshow(chroma, x_axis="time", y_axis="chroma", sr=sr)
    plt.colorbar()
    plt.title("Chromagram")
    plt.tight_layout()
    plt.savefig(out, dpi=110)
    plt.close()


def plot_onset(y, sr, out):
    env = librosa.onset.onset_strength(y=y, sr=sr)
    times = librosa.times_like(env, sr=sr)
    plt.figure(figsize=(12, 3))
    plt.plot(times, env)
    plt.title("Onset envelope")
    plt.xlabel("time (s)")
    plt.tight_layout()
    plt.savefig(out, dpi=110)
    plt.close()


def plot_structure(y, sr, bounds, out):
    plt.figure(figsize=(12, 2.5))
    librosa.display.waveshow(y, sr=sr, alpha=0.4)
    for b in bounds:
        plt.axvline(b, color="r", linestyle="--", alpha=0.7)
    plt.title("Section boundaries")
    plt.tight_layout()
    plt.savefig(out, dpi=110)
    plt.close()


# -----------------------------------------------------------------------------
# sample generators
# -----------------------------------------------------------------------------
def synth_log_drum(bpm, root_hz, sr=44100):
    spb = 60.0 / bpm
    total = spb * 16  # 4 bars of 4/4
    n = int(total * sr)
    out = np.zeros(n, dtype=np.float32)
    # pattern: (beat_position_in_quarter_notes, semitones above root)
    pattern = [
        (0.00, 0), (0.75, 7), (1.50, 0), (2.25, 5), (3.00, 0), (3.75, 3),
        (4.50, 7), (5.25, 0),
        (6.00, 0), (6.75, 7), (7.50, 0), (8.25, 5), (9.00, 0), (9.75, 3),
        (10.50, 7), (11.25, 12),
        (12.00, 0), (12.75, 7), (13.50, 0), (14.25, 5),
    ]
    for beat_pos, semis in pattern:
        t0 = beat_pos * spb
        f = root_hz * 2 ** (semis / 12.0)
        s = int(t0 * sr)
        if s >= n:
            continue
        e = min(s + int(0.35 * sr), n)
        tt = np.arange(e - s) / sr
        # downward pitch glide gives the log-drum punch
        pitch = f * (1.0 + 0.6 * np.exp(-tt * 30))
        phase = 2 * np.pi * np.cumsum(pitch) / sr
        amp = np.exp(-tt * 8)
        click = np.exp(-tt * 200) * 0.3
        out[s:e] += (np.sin(phase) * amp + click).astype(np.float32)
    out *= 0.7 / (np.max(np.abs(out)) + 1e-9)
    return out, sr


def synth_hats(bpm, swing=0.0, sr=44100):
    spb = 60.0 / bpm
    sixteenth = spb / 4
    total = spb * 16
    n = int(total * sr)
    out = np.zeros(n, dtype=np.float32)
    rng = np.random.default_rng(42)
    for i in range(64):
        t0 = i * sixteenth + (swing * sixteenth if i % 2 == 1 else 0.0)
        s = int(t0 * sr)
        if s >= n:
            continue
        e = min(s + int(0.04 * sr), n)
        tt = np.arange(e - s) / sr
        out[s:e] += (rng.standard_normal(e - s) * 0.4 * np.exp(-tt * 120)).astype(np.float32)
    for bar in range(4):
        for beat in (1, 3):
            t0 = bar * spb * 4 + beat * spb
            s = int(t0 * sr)
            if s >= n:
                continue
            e = min(s + int(0.2 * sr), n)
            tt = np.arange(e - s) / sr
            out[s:e] += (rng.standard_normal(e - s) * 0.7 * np.exp(-tt * 15) * 0.5).astype(np.float32)
    out *= 0.7 / (np.max(np.abs(out)) + 1e-9)
    return out, sr


def write_hats_midi(bpm, swing, out_path):
    mid = MidiFile()
    track = MidiTrack()
    mid.tracks.append(track)
    track.append(MetaMessage("set_tempo", tempo=bpm2tempo(bpm)))
    ppq = mid.ticks_per_beat
    sixteenth = ppq // 4
    swing_offset = int(swing * sixteenth)
    note_dur = 10
    events = []  # (abs_tick, kind, note, vel) — kind sorts 'note_off' before 'note_on'
    for i in range(64):
        tick = i * sixteenth + (swing_offset if i % 2 == 1 else 0)
        events.append((tick, "note_on", 42, 90))
        events.append((tick + note_dur, "note_off", 42, 0))
    for bar in range(4):
        for beat in (1, 3):
            tick = bar * ppq * 4 + beat * ppq
            events.append((tick, "note_on", 39, 110))
            events.append((tick + note_dur, "note_off", 39, 0))
    events.sort()
    last = 0
    for tick, kind, note, vel in events:
        delta = max(0, tick - last)
        track.append(Message(kind, note=note, velocity=vel, time=delta))
        last = tick
    mid.save(out_path)


def write_chord_midi(bpm, root_pc, is_minor, progression, out_path):
    """progression: list of scale-degree integers in semitones from the root."""
    mid = MidiFile()
    track = MidiTrack()
    mid.tracks.append(track)
    track.append(MetaMessage("set_tempo", tempo=bpm2tempo(bpm)))
    ppq = mid.ticks_per_beat
    bar = ppq * 4
    third = 3 if is_minor else 4
    seventh = 10 if is_minor else 11
    for deg in progression:
        root = 60 + root_pc + deg
        notes = [root, root + third, root + 7, root + seventh, root + 14]
        track.append(Message("note_on", note=notes[0], velocity=80, time=0))
        for n in notes[1:]:
            track.append(Message("note_on", note=n, velocity=80, time=0))
        track.append(Message("note_off", note=notes[0], velocity=0, time=bar))
        for n in notes[1:]:
            track.append(Message("note_off", note=n, velocity=0, time=0))
    mid.save(out_path)


# -----------------------------------------------------------------------------
# demucs wrapper
# -----------------------------------------------------------------------------
def run_demucs(input_path, work_dir):
    if shutil.which("demucs") is None and shutil.which("python3"):
        cmd = [sys.executable, "-m", "demucs", "-n", "htdemucs", "-o", str(work_dir), str(input_path)]
    else:
        cmd = ["demucs", "-n", "htdemucs", "-o", str(work_dir), str(input_path)]
    print("[demucs]", " ".join(cmd))
    subprocess.run(cmd, check=True)
    base = Path(input_path).stem
    return work_dir / "htdemucs" / base


# -----------------------------------------------------------------------------
# main
# -----------------------------------------------------------------------------
def analyse_file(path, sr_target=44100):
    y_stereo, sr = librosa.load(path, sr=sr_target, mono=False)
    y_mono = y_stereo if y_stereo.ndim == 1 else librosa.to_mono(y_stereo)
    return y_stereo, y_mono, sr


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input", help="path to input audio (mp3/wav/m4a/flac)")
    ap.add_argument("--no-stems", action="store_true", help="skip demucs stem split")
    ap.add_argument("--no-samples", action="store_true", help="skip sample generation")
    args = ap.parse_args()

    in_path = Path(args.input).expanduser().resolve()
    if not in_path.exists():
        sys.exit(f"input not found: {in_path}")

    out_dir = in_path.parent / f"{in_path.stem}_analysis"
    plots_dir = out_dir / "plots"
    stems_plots_dir = plots_dir / "stems"
    samples_dir = out_dir / "samples"
    for d in (out_dir, plots_dir, stems_plots_dir, samples_dir):
        d.mkdir(parents=True, exist_ok=True)

    print(f"[load] {in_path}")
    y_stereo, y, sr = analyse_file(in_path)
    duration = float(len(y) / sr)
    print(f"[load] sr={sr} duration={duration:.1f}s channels={y_stereo.ndim}")

    print("[features] tempo")
    tempo, beats = librosa.beat.beat_track(y=y, sr=sr)
    bpm = float(tempo) if np.isscalar(tempo) else float(tempo[0])

    print("[features] key")
    key, key_score, key_scores = detect_key(y, sr)
    root_pc = NOTE_NAMES.index(key.split()[0])
    is_minor = "minor" in key
    # confidence: gap between top-1 and top-2; small gap means low confidence
    sorted_keys = sorted(key_scores.items(), key=lambda kv: -kv[1])
    key_confidence_gap = float(sorted_keys[0][1] - sorted_keys[1][1])

    print("[features] swing")
    swing = detect_swing(y, sr, bpm)

    print("[features] loudness")
    loud = loudness(y, sr)

    print("[features] spectral balance")
    bands = spectral_balance(y, sr)

    print("[features] stereo width")
    width = stereo_width(y_stereo) if y_stereo.ndim == 2 else None

    print("[features] structure")
    bounds = section_boundaries(y, sr, n_segments=8)

    print("[plots] waveform / melspec / chroma / onset / structure")
    plot_waveform(y, sr, plots_dir / "waveform.png")
    plot_melspec(y, sr, plots_dir / "melspec.png")
    plot_chroma(y, sr, plots_dir / "chroma.png")
    plot_onset(y, sr, plots_dir / "onset.png")
    plot_structure(y, sr, bounds, plots_dir / "structure.png")

    metrics = {
        "input": str(in_path),
        "duration_s": duration,
        "sample_rate": sr,
        "channels": int(y_stereo.ndim if y_stereo.ndim == 1 else y_stereo.shape[0]),
        "tempo_bpm": bpm,
        "key": key,
        "key_correlation": key_score,
        "key_confidence_gap": key_confidence_gap,
        "key_confidence_label": (
            "high" if key_confidence_gap > 0.05
            else "medium" if key_confidence_gap > 0.015
            else "low (top candidates are close — inspect chromagram)"
        ),
        "key_top5": dict(sorted_keys[:5]),
        "swing_fraction_of_16th": swing,
        "loudness": loud,
        "spectral_band_energy_fractions": bands,
        "stereo_side_minus_mid_db": width,
        "section_boundaries_s": bounds,
    }

    if not args.no_stems:
        print("[demucs] running 4-stem split (downloads ~250MB model on first run)")
        try:
            stem_root = run_demucs(in_path, out_dir / "_demucs")
            stems_metrics = {}
            for stem in ("drums", "bass", "vocals", "other"):
                stem_path = stem_root / f"{stem}.wav"
                if not stem_path.exists():
                    continue
                ys, srs = librosa.load(stem_path, sr=sr_target, mono=True)
                plot_melspec(ys, srs, stems_plots_dir / f"{stem}_melspec.png", title=f"{stem} mel-spectrogram")
                stems_metrics[stem] = {
                    "loudness": loudness(ys, srs),
                    "spectral_balance": spectral_balance(ys, srs),
                }
            metrics["stems"] = stems_metrics
        except Exception as e:
            print(f"[demucs] failed: {e}")
            metrics["stems_error"] = str(e)

    if not args.no_samples:
        print("[samples] generating reference loops")
        # log-drum at root note, 2 octaves down (sub region)
        root_freq = 440.0 * 2 ** ((root_pc - 9) / 12.0) / 4.0  # A=440, then drop 2 octaves
        ld, sr_s = synth_log_drum(bpm, root_freq)
        sf.write(samples_dir / f"logdrum_{int(round(bpm))}_{key.replace(' ', '_')}.wav", ld, sr_s)

        swing_amount = swing if swing is not None else 0.0
        # clip swing_amount into a sensible audio range
        swing_amount = max(-0.4, min(0.4, swing_amount))
        hats, sr_s = synth_hats(bpm, swing=swing_amount)
        sf.write(samples_dir / f"hats_{int(round(bpm))}.wav", hats, sr_s)
        write_hats_midi(bpm, swing_amount, samples_dir / "hats.mid")

        # progression v1: minor i-VI-III-VII   (semitones: 0, 8, 3, 10)
        # progression v2: minor i-iv-VII-III   (semitones: 0, 5, 10, 3)
        # if major: I-vi-IV-V (0, 9, 5, 7) and I-V-vi-IV (0, 7, 9, 5)
        if is_minor:
            prog_v1 = [0, 8, 3, 10]
            prog_v2 = [0, 5, 10, 3]
        else:
            prog_v1 = [0, 9, 5, 7]
            prog_v2 = [0, 7, 9, 5]
        write_chord_midi(bpm, root_pc, is_minor, prog_v1, samples_dir / "chords_v1.mid")
        write_chord_midi(bpm, root_pc, is_minor, prog_v2, samples_dir / "chords_v2.mid")

    metrics_path = out_dir / "metrics.json"
    with open(metrics_path, "w") as f:
        json.dump(metrics, f, indent=2, default=float)

    print()
    print(f"=== done ===")
    print(f"output: {out_dir}")
    print(f"  metrics: {metrics_path}")
    print(f"  plots:   {plots_dir}")
    print(f"  samples: {samples_dir}")
    print()
    print("To get the feedback report, drag metrics.json and the contents of plots/")
    print("into your Claude chat and ask for the amapiano feedback report.")


if __name__ == "__main__":
    main()

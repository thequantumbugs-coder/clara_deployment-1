#!/usr/bin/env python3
"""Diagnostic: list audio devices, record 5s to /tmp/py_mic.wav, print RMS/peak. Optional playback."""
import os
import sys
from pathlib import Path

# Allow importing backend config and core when run from repo root or backend/
_BACKEND = Path(__file__).resolve().parent.parent
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

import numpy as np
import sounddevice as sd

from config import (
    AUDIO_INPUT_DEVICE_NAME,
    AUDIO_INPUT_DEVICE_INDEX,
    AUDIO_SAMPLE_RATE,
    AUDIO_CHANNELS,
)
from core.audio_pipeline import _resolve_input_device


def main() -> None:
    print("=== Audio devices ===")
    devices = sd.query_devices()
    for i, dev in enumerate(devices):
        in_ch = dev.get("max_input_channels", 0)
        out_ch = dev.get("max_output_channels", 0)
        name = dev.get("name", "?")
        default = ""
        if sd.default.device[0] == i:
            default = " [DEFAULT INPUT]"
        if sd.default.device[1] == i:
            default = " [DEFAULT OUTPUT]" if not default else " [DEFAULT IN/OUT]"
        print(f"  {i}: {name} (in={in_ch}, out={out_ch}){default}")
    print(f"Default input index: {sd.default.device[0]}")
    print(f"Default output index: {sd.default.device[1]}")

    device_id = _resolve_input_device()
    dev = devices[device_id] if device_id < len(devices) else {}
    dev_name = dev.get("name", "?")
    print(f"Using device {device_id}: {dev_name}")
    channels = min(dev.get("max_input_channels", 1), max(1, AUDIO_CHANNELS))
    duration_s = 5
    samples = int(AUDIO_SAMPLE_RATE * duration_s) * channels

    print(f"\nRecording {duration_s} s at {AUDIO_SAMPLE_RATE} Hz, {channels} ch, device {device_id}...")
    rec = sd.rec(samples, samplerate=AUDIO_SAMPLE_RATE, channels=channels, dtype="int16", device=device_id)
    sd.wait()
    if channels > 1:
        rec = rec.mean(axis=1).astype(np.int16)
    else:
        rec = rec.squeeze()

    rms = np.sqrt(np.mean(rec.astype(np.float64) ** 2)) / 32768.0
    peak = np.abs(rec).max() / 32768.0
    print(f"RMS (normalized): {rms:.6f}")
    print(f"Peak (normalized): {peak:.6f}")

    out_path = os.environ.get("MIC_PROBE_OUT", "/tmp/py_mic.wav")
    try:
        import scipy.io.wavfile
        scipy.io.wavfile.write(out_path, AUDIO_SAMPLE_RATE, rec)
    except ImportError:
        import wave
        with wave.open(out_path, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(AUDIO_SAMPLE_RATE)
            wf.writeframes(rec.tobytes())
    print(f"Wrote {out_path}")

    play = os.environ.get("MIC_PROBE_PLAY", "").lower() in ("1", "true", "yes")
    if play:
        print("Playing back...")
        sd.play(rec, samplerate=AUDIO_SAMPLE_RATE)
        sd.wait()
    else:
        print("Play with: aplay", out_path, "or set MIC_PROBE_PLAY=1 to auto-play.")


if __name__ == "__main__":
    main()

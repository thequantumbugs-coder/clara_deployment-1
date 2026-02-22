"""Backend audio capture: device resolution, VAD, WAV output. For use via asyncio.to_thread(record_audio)."""
import io
import logging
import struct
from typing import Optional

import numpy as np
import sounddevice as sd
import webrtcvad

from config import (
    AUDIO_CHANNELS,
    AUDIO_SAMPLE_RATE,
    AUDIO_SILENCE_STOP_MS,
    AUDIO_SPEECH_TIMEOUT_MS,
    AUDIO_VAD_FRAME_MS,
    AUDIO_INPUT_DEVICE_NAME,
    AUDIO_INPUT_DEVICE_INDEX,
    AUDIO_RECORD_MODE,
    AUDIO_FIXED_RECORD_SECONDS,
    AUDIO_SILENT_RMS_THRESHOLD,
)

logger = logging.getLogger(__name__)

# webrtcvad only accepts 10, 20, 30 ms
_VAD_FRAME_MS = 10 if AUDIO_VAD_FRAME_MS <= 10 else (20 if AUDIO_VAD_FRAME_MS <= 20 else 30)
SAMPLES_PER_FRAME = (AUDIO_SAMPLE_RATE * _VAD_FRAME_MS) // 1000
BYTES_PER_FRAME = SAMPLES_PER_FRAME * 2  # int16


def _resolve_input_device() -> int:
    """Resolve input device index from config (name substring or explicit index)."""
    devices = sd.query_devices()
    default_in = sd.default.device[0]
    if default_in is None:
        default_in = 0

    if AUDIO_INPUT_DEVICE_INDEX is not None:
        if 0 <= AUDIO_INPUT_DEVICE_INDEX < len(devices) and devices[AUDIO_INPUT_DEVICE_INDEX].get("max_input_channels", 0) > 0:
            logger.info("Using audio input device index %s: %s", AUDIO_INPUT_DEVICE_INDEX, devices[AUDIO_INPUT_DEVICE_INDEX].get("name", "?"))
            return AUDIO_INPUT_DEVICE_INDEX
        logger.warning("AUDIO_INPUT_DEVICE_INDEX=%s invalid or no input; using default %s", AUDIO_INPUT_DEVICE_INDEX, default_in)

    if AUDIO_INPUT_DEVICE_NAME:
        name_lower = AUDIO_INPUT_DEVICE_NAME.lower()
        for i, dev in enumerate(devices):
            if dev.get("max_input_channels", 0) > 0 and name_lower in (dev.get("name") or "").lower():
                logger.info("Using audio input device by name '%s': index %s, %s", AUDIO_INPUT_DEVICE_NAME, i, dev.get("name"))
                return i
        logger.warning("No input device name containing '%s'; using default %s", AUDIO_INPUT_DEVICE_NAME, default_in)

    logger.info("Using default audio input device index %s: %s", default_in, devices[default_in].get("name", "?") if default_in < len(devices) else "?")
    return default_in


def _frame_to_mono(frame: np.ndarray, channels: int) -> bytes:
    """Convert (samples, channels) int16 to mono bytes."""
    if channels <= 1:
        return frame.tobytes()
    mono = frame.mean(axis=1).astype(np.int16)
    return mono.tobytes()


def _compute_rms(mono_bytes: bytes) -> float:
    """Compute RMS (normalized 0..1) from mono int16 PCM."""
    if len(mono_bytes) < 2:
        return 0.0
    arr = np.frombuffer(mono_bytes, dtype=np.int16)
    return float(np.sqrt(np.mean(arr.astype(np.float64) ** 2)) / 32768.0)


def _record_fixed_duration(device_id: int, devices: list, channels: int) -> Optional[bytes]:
    """Record exactly AUDIO_FIXED_RECORD_SECONDS; return WAV bytes or None if silent."""
    duration_s = max(0.5, min(30.0, AUDIO_FIXED_RECORD_SECONDS))
    samples_total = int(AUDIO_SAMPLE_RATE * duration_s) * channels
    rec = sd.rec(samples_total, samplerate=AUDIO_SAMPLE_RATE, channels=channels, dtype="int16", device=device_id)
    sd.wait()
    if channels > 1:
        mono_arr = rec.mean(axis=1).astype(np.int16)
    else:
        mono_arr = rec.squeeze()
    mono_bytes = mono_arr.tobytes()
    rms = _compute_rms(mono_bytes)
    logger.info("Fixed record: %.2f s, RMS=%.6f", duration_s, rms)
    if rms < AUDIO_SILENT_RMS_THRESHOLD:
        logger.warning("MIC_SILENT: RMS %.6f below threshold %.6f", rms, AUDIO_SILENT_RMS_THRESHOLD)
        return None
    return _build_wav_from_mono_bytes(mono_bytes)


def _build_wav_from_mono_bytes(mono: bytes) -> bytes:
    """Build WAV from mono int16 PCM bytes."""
    if len(mono) == 0:
        return b""
    n_frames = len(mono) // 2
    buf = io.BytesIO()
    buf.write(b"RIFF")
    buf.write(struct.pack("<I", 36 + n_frames * 2))
    buf.write(b"WAVEfmt ")
    buf.write(struct.pack("<IHHIIHH", 16, 1, 1, AUDIO_SAMPLE_RATE, AUDIO_SAMPLE_RATE * 2, 2, 16))
    buf.write(b"data")
    buf.write(struct.pack("<I", n_frames * 2))
    buf.write(mono)
    return buf.getvalue()


def record_audio() -> Optional[bytes]:
    """
    Record from configured input. Mode "fixed": record N seconds; mode "vad": VAD start/stop.
    Returns WAV bytes (16 kHz mono int16) or None on timeout/error/silent.
    Intended to be run in asyncio.to_thread() so the event loop is not blocked.
    """
    try:
        device_id = _resolve_input_device()
        devices = sd.query_devices()
        dev = devices[device_id] if device_id < len(devices) else {}
        dev_name = dev.get("name", "?")
        max_ch = min(dev.get("max_input_channels", 1), max(1, AUDIO_CHANNELS))
        channels = max(1, max_ch)
        logger.info("record_audio: device_id=%s name=%s channels=%s mode=%s", device_id, dev_name, channels, AUDIO_RECORD_MODE)

        if AUDIO_RECORD_MODE == "fixed":
            return _record_fixed_duration(device_id, devices, channels)

        # VAD mode
        vad = webrtcvad.Vad(2)  # aggressiveness 0–3
        silence_frames_to_stop = (AUDIO_SILENCE_STOP_MS + _VAD_FRAME_MS - 1) // _VAD_FRAME_MS
        speech_timeout_frames = max(1, (AUDIO_SPEECH_TIMEOUT_MS + _VAD_FRAME_MS - 1) // _VAD_FRAME_MS)
        block_size = (AUDIO_SAMPLE_RATE * _VAD_FRAME_MS) // 1000
        accumulated: list[bytes] = []
        consecutive_silence = 0
        speech_started = False
        frames_without_speech = 0

        with sd.InputStream(
            device=device_id,
            samplerate=AUDIO_SAMPLE_RATE,
            channels=channels,
            dtype="int16",
            blocksize=block_size,
        ) as stream:
            while True:
                frame, overflowed = stream.read(block_size)
                if overflowed:
                    logger.warning("InputStream overflow")
                raw_mono = _frame_to_mono(frame, channels)
                if len(raw_mono) < BYTES_PER_FRAME:
                    continue
                for off in range(0, len(raw_mono) - BYTES_PER_FRAME + 1, BYTES_PER_FRAME):
                    vad_frame = raw_mono[off : off + BYTES_PER_FRAME]
                    if vad.is_speech(vad_frame, AUDIO_SAMPLE_RATE):
                        if not speech_started:
                            speech_started = True
                            logger.info("Speech detected start")
                        consecutive_silence = 0
                    else:
                        consecutive_silence += 1
                        if speech_started and consecutive_silence >= silence_frames_to_stop:
                            logger.info("Stop condition reached (silence frames %s)", consecutive_silence)
                            accumulated.append(raw_mono[:off])
                            wav = _build_wav_from_chunks(accumulated)
                            mono = b"".join(accumulated)
                            if len(mono) >= BYTES_PER_FRAME and _compute_rms(mono) < AUDIO_SILENT_RMS_THRESHOLD:
                                logger.warning("MIC_SILENT: VAD segment RMS below threshold")
                                return None
                            return wav
                accumulated.append(raw_mono)
                if not speech_started:
                    frames_without_speech += 1
                    if frames_without_speech >= speech_timeout_frames:
                        logger.warning("No speech detected within timeout (%s ms)", AUDIO_SPEECH_TIMEOUT_MS)
                        return None
                else:
                    frames_without_speech = 0
    except Exception as e:
        logger.exception("Recording failed: %s", e)
        return None


def _build_wav_from_chunks(chunks: list[bytes]) -> bytes:
    """Build mono 16-bit WAV from list of mono PCM chunks."""
    mono = b"".join(chunks)
    if len(mono) == 0:
        return b""
    n_frames = len(mono) // 2
    buf = io.BytesIO()
    buf.write(b"RIFF")
    buf.write(struct.pack("<I", 36 + n_frames * 2))
    buf.write(b"WAVEfmt ")
    buf.write(struct.pack("<IHHIIHH", 16, 1, 1, AUDIO_SAMPLE_RATE, AUDIO_SAMPLE_RATE * 2, 2, 16))
    buf.write(b"data")
    buf.write(struct.pack("<I", n_frames * 2))
    buf.write(mono)
    return buf.getvalue()

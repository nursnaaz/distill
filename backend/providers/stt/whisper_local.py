from __future__ import annotations
"""Local Whisper STT provider using faster-whisper.

Downloads model on first use (size from config). Runs on CPU by default.
Whisper prefers 16kHz mono audio — the frontend MediaRecorder should capture
at { audio: { channelCount: 1, sampleRate: 16000 } }.
"""

import asyncio
import tempfile
import time
from pathlib import Path

from .base import BaseSTTProvider
from core.config import AppConfig
from core.logging import get_logger

logger = get_logger(__name__)


class WhisperLocalProvider(BaseSTTProvider):
    """Transcribes audio using a locally-loaded Whisper model via faster-whisper."""

    def __init__(self, config: AppConfig):
        self._config = config
        self._model = None

        if config.speech_to_text.whisper_local.download_on_startup:
            self._load_model()

    def _load_model(self) -> None:
        from faster_whisper import WhisperModel

        model_size = self._config.speech_to_text.whisper_local.model_size
        device = self._config.speech_to_text.whisper_local.device
        compute_type = self._config.speech_to_text.whisper_local.compute_type

        logger.info(
            "Loading Whisper model — this may take a minute on first run",
            model=model_size,
            device=device,
        )
        t0 = time.time()
        self._model = WhisperModel(model_size, device=device, compute_type=compute_type)
        logger.info("Whisper model ready", elapsed_seconds=round(time.time() - t0, 1))

    async def transcribe(self, audio_bytes: bytes, filename: str) -> dict:
        if self._model is None:
            self._load_model()

        suffix = Path(filename).suffix or ".webm"

        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name

        try:
            language = self._config.speech_to_text.language or None

            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: self._run_transcribe(tmp_path, language),
            )
            return result
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    def _run_transcribe(self, path: str, language: str | None) -> dict:
        segments, info = self._model.transcribe(  # type: ignore[union-attr]
            path,
            language=language,
            beam_size=5,
        )
        transcript = " ".join(seg.text for seg in segments).strip()
        return {
            "transcript": transcript,
            "duration_seconds": info.duration,
            "language": info.language,
        }

    def get_provider_name(self) -> str:
        return "whisper_local"

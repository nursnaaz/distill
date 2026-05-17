from __future__ import annotations
"""Local Whisper STT provider using faster-whisper."""

import asyncio
import tempfile
import time
from pathlib import Path

from .base import BaseSTTProvider
from core.config import AppConfig
from core.logging import get_logger

logger = get_logger(__name__)


class WhisperLocalProvider(BaseSTTProvider):
    """Transcribes audio using a locally-loaded Whisper model."""

    def __init__(self, config: AppConfig):
        self._config = config
        self._model = None

        if config.speech_to_text.whisper_local.download_on_startup:
            self._load_model()

    def _load_model(self) -> None:
        """Load (and optionally download) the Whisper model."""
        from faster_whisper import WhisperModel

        model_size = self._config.speech_to_text.whisper_local.model_size
        device = self._config.speech_to_text.whisper_local.device

        logger.info(
            "Loading Whisper model — this may take a minute on first run",
            model=model_size,
            device=device,
        )
        t0 = time.time()
        self._model = WhisperModel(model_size, device=device, compute_type="int8")
        logger.info("Whisper model ready", elapsed_seconds=round(time.time() - t0, 1))

    async def transcribe(self, audio_bytes: bytes, filename: str) -> dict:
        """Transcribe audio using local Whisper model."""
        if self._model is None:
            self._load_model()

        suffix = Path(filename).suffix or ".webm"

        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name

        try:
            loop = asyncio.get_event_loop()

            def _run():
                segments, info = self._model.transcribe(  # type: ignore[union-attr]
                    tmp_path,
                    language=self._config.speech_to_text.language or None,
                )
                text = " ".join(seg.text for seg in segments).strip()
                return text, info

            text, info = await loop.run_in_executor(None, _run)
            return {
                "transcript": text,
                "duration_seconds": getattr(info, "duration", None),
                "language": getattr(info, "language", None),
            }
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    def get_provider_name(self) -> str:
        return "whisper_local"

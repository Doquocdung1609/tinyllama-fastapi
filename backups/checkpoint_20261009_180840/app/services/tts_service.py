"""Local-first speech synthesis; optional edge-tts compatibility fallback."""
import asyncio
from datetime import datetime
from pathlib import Path
import logging
import wave
from functools import lru_cache
from app.config import get_settings

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def voices() -> list[str]:
    try:
        import pyttsx3
        engine = pyttsx3.init()
        names = [voice.name for voice in engine.getProperty("voices")]
        engine.stop()
        return names
    except Exception:
        return []


def generate_audio(text: str, rate: int = 175, volume: float = 1.0, voice: str | None = None) -> dict:
    settings = get_settings()
    settings.audio_dir.mkdir(parents=True, exist_ok=True)
    output = settings.audio_dir / f"script_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.wav"
    try:
        import pyttsx3
        engine = pyttsx3.init()
        engine.setProperty("rate", rate)
        engine.setProperty("volume", volume)
        selected = None
        available_voices = engine.getProperty("voices")
        for item in available_voices:
            if voice and (voice.casefold() in item.name.casefold() or voice == item.id):
                selected = item.id
                break
        if voice and not selected:
            engine.stop()
            raise ValueError(f"Voice '{voice}' is not installed on this machine.")
        if selected:
            engine.setProperty("voice", selected)
        engine.save_to_file(text, str(output))
        engine.runAndWait()
        engine.stop()
        if not output.exists() or output.stat().st_size == 0:
            raise RuntimeError("Windows SAPI did not create an audio file")
        try:
            with wave.open(str(output), "rb") as wav_file:
                duration = wav_file.getnframes() / max(wav_file.getframerate(), 1)
        except (wave.Error, OSError):
            duration = None
        logger.info("local TTS generated voice=%s size_bytes=%d", voice or "Windows SAPI default", output.stat().st_size)
        return {"path": str(output), "voice": voice or "Windows SAPI default", "size_bytes": output.stat().st_size, "duration_seconds": duration}
    except ImportError:
        # Preserve the project's original edge-tts functionality as an explicit fallback.
        try:
            import edge_tts
        except ImportError as exc:
            raise RuntimeError("No TTS engine available. Install pyttsx3 (local Windows voice) or edge-tts.") from exc
        mp3 = output.with_suffix(".mp3")
        asyncio.run(edge_tts.Communicate(text, voice or "en-US-AriaNeural").save(str(mp3)))
        return {"path": str(mp3), "voice": voice or "en-US-AriaNeural (edge-tts)", "size_bytes": mp3.stat().st_size, "duration_seconds": None}
    except Exception:
        logger.exception("local TTS failed")
        output.unlink(missing_ok=True)
        raise

"""Backward-compatible local-first TTS functions."""
import asyncio
from app.services.tts_service import generate_audio


async def generate_speech(text: str, output_file: str):
    result = await asyncio.to_thread(generate_audio, text)
    from pathlib import Path
    destination = Path("audio") / output_file
    destination.parent.mkdir(parents=True, exist_ok=True)
    if Path(result["path"]).resolve() != destination.resolve():
        Path(result["path"]).replace(destination)
    return str(destination)


def text_to_speech(text: str, output_file: str = "output.wav"):
    return asyncio.run(generate_speech(text, output_file))

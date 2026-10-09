import os
from pathlib import Path
import wave
import pytest
from PIL import Image, ImageStat

RUN_REAL = os.getenv("RUN_REAL_MEDIA_TESTS") == "1"


@pytest.mark.integration
@pytest.mark.skipif(not RUN_REAL, reason="set RUN_REAL_MEDIA_TESTS=1 for real local media inference")
def test_real_tiny_sd_png_is_not_blank():
    from app.services.image_service import generate_image
    result = generate_image("a blue robot in a classroom, simple illustration", "blurry", 2, 7.0, 256, 256, 4321)
    path = Path(result["path"])
    assert path.exists() and path.stat().st_size > 1000
    image = Image.open(path).convert("RGB")
    assert image.size == (256, 256)
    assert sum(ImageStat.Stat(image).var) > 1


@pytest.mark.integration
@pytest.mark.skipif(not RUN_REAL, reason="set RUN_REAL_MEDIA_TESTS=1 for real local media inference")
def test_real_windows_sapi_wav():
    from app.services.tts_service import generate_audio
    result = generate_audio("This is a real offline speech synthesis test.", rate=175, volume=1.0)
    path = Path(result["path"])
    assert path.exists() and path.stat().st_size > 1000
    with wave.open(str(path), "rb") as audio:
        assert audio.getnframes() > 0 and audio.getframerate() > 0


@pytest.mark.integration
@pytest.mark.skipif(not RUN_REAL, reason="set RUN_REAL_MEDIA_TESTS=1 for real local media inference")
def test_real_ffmpeg_motion_demo(tmp_path):
    from app.services.video_service import create_motion_demo
    source = tmp_path / "source.png"
    Image.new("RGB", (320, 240), (20, 100, 180)).save(source)
    result = create_motion_demo(str(source), 28, 14)
    path = Path(result["path"])
    assert result["mode"] == "ken_burns_motion_demo_not_diffusion"
    assert path.exists() and path.stat().st_size > 1000

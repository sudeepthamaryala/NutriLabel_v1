"""test_ocr_non_blocking.py

Verifies that pytesseract OCR does NOT block the FastAPI event loop.

How the test works:
- We mock pytesseract to sleep for 0.5s (simulating real OCR latency).
- We send 3 concurrent /analyse requests using asyncio.gather.
- If OCR were blocking, the 3 requests would run serially → ~1.5s total.
- Because OCR is offloaded to a thread, they run concurrently → ~0.5s total.
- We assert total time < 1.0s to prove concurrency.

Run with:
    venv\\Scripts\\python.exe run_tests.py
or (from backend/ with venv active and PYTHONPATH=.):
    pytest tests/test_ocr_non_blocking.py -v
"""
import asyncio
import time
from io import BytesIO
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from PIL import Image, ImageDraw


# ── Helpers ──────────────────────────────────────────────────────────────────

def _make_image_bytes() -> bytes:
    """Create a minimal valid PNG image with nutrition text for OCR."""
    img = Image.new("RGB", (400, 200), "white")
    draw = ImageDraw.Draw(img)
    draw.text((10, 10), "Calories 220\nProtein 6g\nSugar 18g", fill="black")
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _slow_tesseract(image) -> str:
    """Fake pytesseract that sleeps to simulate real OCR processing time."""
    time.sleep(0.5)
    return "Calories 220\nProtein 6g\nSugar 18g"


# ── Test ──────────────────────────────────────────────────────────────────────

def test_ocr_does_not_block_event_loop():
    """Confirm 3 concurrent OCR calls complete in ~0.5s, not ~1.5s.

    If the event loop were blocked, each call would wait for the previous
    one to finish → total ~1.5s. Because we offload to a thread with
    anyio.to_thread.run_sync, all 3 run in parallel → total ~0.5s.
    """
    from app.services.ocr_service import _extract_with_tesseract

    image_bytes = _make_image_bytes()

    async def run_three_concurrent_ocr_calls():
        # Patch pytesseract.image_to_string inside the service module
        with patch("pytesseract.image_to_string", side_effect=_slow_tesseract):
            start = time.perf_counter()
            # asyncio.gather runs all three coroutines concurrently.
            # If non-blocking, they should all complete in ~0.5s (not 1.5s).
            results = await asyncio.gather(
                _extract_with_tesseract(image_bytes=image_bytes, timeout=10.0),
                _extract_with_tesseract(image_bytes=image_bytes, timeout=10.0),
                _extract_with_tesseract(image_bytes=image_bytes, timeout=10.0),
            )
            elapsed = time.perf_counter() - start
        return results, elapsed

    results, elapsed = asyncio.run(run_three_concurrent_ocr_calls())

    # All 3 should succeed
    assert len(results) == 3
    for result in results:
        assert result.provider == "tesseract"
        assert result.text != ""
        assert 0.0 <= result.confidence <= 1.0

    # Key assertion: concurrent execution, not sequential.
    # 3 sequential calls at 0.5s each = 1.5s.
    # 3 concurrent calls = ~0.5s.
    # We give a generous 1.0s budget to account for thread startup overhead.
    assert elapsed < 1.0, (
        f"OCR appears to be blocking the event loop! "
        f"3 concurrent calls took {elapsed:.2f}s (expected < 1.0s). "
        f"pytesseract must be wrapped in anyio.to_thread.run_sync."
    )

    print(f"\n✅ Non-blocking OCR confirmed: 3 concurrent calls completed in {elapsed:.2f}s")

#!/usr/bin/env python3
# Smoke tests for PaddleOCR VL15 runtime patch.
# Run with: myenv/Scripts/python scripts/test_paddleocr_fix.py

import sys
import os
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import torch
from PIL import Image, ImageDraw, ImageFont

from modules.ocr.ocr_paddleVL15 import PaddleOCRVL15


def make_text_image(text="Hello World", width=300, height=80):
    """Create a small white image with black text rendered on it."""
    img = Image.new("RGB", (width, height), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    try:
        # Try to load a system font; fall back to default bitmap font
        font = ImageFont.truetype("arial.ttf", size=28)
    except Exception:
        font = ImageFont.load_default()
    draw.text((10, 20), text, fill=(0, 0, 0), font=font)
    return np.array(img)


def assert_model_shape(ocr_instance):
    model = ocr_instance.model
    # AutoModelForImageTextToText may wrap the inner model; check both levels
    inner = getattr(model, "model", model)
    missing = [n for n in ("visual", "get_rope_index")
               if not hasattr(model, n) and not hasattr(inner, n)]
    if missing:
        raise AssertionError("Model missing expected attributes: {}".format(missing))


def tiny_inference(ocr_instance):
    img = make_text_image("Hello World", width=300, height=80)
    out = ocr_instance.ocr_img(img)
    if not out or (isinstance(out, str) and out.strip() == ""):
        raise AssertionError("Inference returned empty output: {!r}".format(out))
    return out


def run_device_tests(device):
    print("=== Running tests on device: {} ===".format(device))
    # Test idempotence of _ensure_default_rope
    PaddleOCRVL15._ensure_default_rope()
    PaddleOCRVL15._ensure_default_rope()

    ocr1 = PaddleOCRVL15(device=device)
    ocr1._load_model()
    assert_model_shape(ocr1)
    print("First load OK and attributes present.")

    # Idempotence: second instance reuses same load path
    ocr2 = PaddleOCRVL15(device=device)
    ocr2._load_model()
    assert_model_shape(ocr2)
    print("Second load OK and attributes present.")

    out = tiny_inference(ocr1)
    print("Tiny inference output (truncated): {}".format(repr(out[:200])))


def main():
    try:
        run_device_tests("cpu")
        print("CPU tests passed.")
    except Exception:
        traceback.print_exc()
        print("CPU tests FAILED.")
        sys.exit(1)

    if not torch.cuda.is_available():
        print("CUDA not available - skipping GPU tests. Exiting OK (0).")
        sys.exit(0)

    try:
        run_device_tests("cuda")
        print("CUDA tests passed.")
        sys.exit(0)
    except Exception:
        traceback.print_exc()
        print("CUDA tests FAILED.")
        sys.exit(1)


if __name__ == "__main__":
    import logging
    logging.disable(logging.CRITICAL)  # suppress transformers INFO/WARNING noise
    main()

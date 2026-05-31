import sys
import os
import cv2
import importlib.util

# Ensure project root on path
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

def load_detector_module():
    path = os.path.join(ROOT, "modules", "textdetector", "detector_comic-text-and-bubble-detector.py")
    spec = importlib.util.spec_from_file_location("detector_comic_hf", path)
    mod = importlib.util.module_from_spec(spec)
    # set package to allow relative imports
    mod.__package__ = "modules.textdetector"
    spec.loader.exec_module(mod)
    return mod

# lazy load detector class from file to avoid import errors due to hyphenated filename
DetModule = load_detector_module()
ComicTextAndBubbleDetector = getattr(DetModule, "ComicTextAndBubbleDetector")

def main():
    if len(sys.argv) < 2:
        print("Usage: debug_run_detector.py <image_path> [debug_dir]")
        sys.exit(2)
    img_path = sys.argv[1]
    debug_dir = sys.argv[2] if len(sys.argv) > 2 else "debug_dump"
    if not os.path.isfile(img_path):
        print("Image not found:", img_path)
        sys.exit(1)

    img_bgr = cv2.imread(img_path)
    if img_bgr is None:
        print("Failed to read image:", img_path)
        sys.exit(1)
    img = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)

    det = ComicTextAndBubbleDetector()
    # enable debug dump
    det.params["debug_dump_path"] = {"type": "line_editor", "value": debug_dir}
    print("Debug dump path set to:", debug_dir)

    print("Loading model (may download weights)...")
    det._load_model()
    if det.pipe is None:
        print("Warning: HF pipeline not available or failed to load. _detect will skip inference.")
    else:
        print("Model loaded.")

    print("Running detection...")
    mask, blks = det._detect(img)
    print("Detection finished. Blocks:", len(blks), "Mask nonzero pixels:", int((mask > 0).sum()))

    # Save outputs for quick inspection
    os.makedirs(debug_dir, exist_ok=True)
    out_mask_path = os.path.join(debug_dir, "mask_final.png")
    try:
        cv2.imwrite(out_mask_path, mask)
        print("Saved final mask to", out_mask_path)
    except Exception as e:
        print("Failed to save final mask:", e)

    # Save block summaries
    try:
        with open(os.path.join(debug_dir, "blocks_summary.txt"), "w", encoding="utf-8") as f:
            for i, b in enumerate(blks):
                f.write(f"{i}: xyxy={b.xyxy} _detected_font_size={getattr(b, '_detected_font_size', None)} lines={getattr(b,'lines',None)}\\n")
        print("Saved blocks summary.")
    except Exception as e:
        print("Failed to write blocks summary:", e)

if __name__ == '__main__':
    main()
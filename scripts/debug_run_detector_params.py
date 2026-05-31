import sys
import os
import cv2
import importlib.util
from pathlib import Path

# Ensure project root on path
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

def load_detector_module():
    path = os.path.join(ROOT, "modules", "textdetector", "detector_comic-text-and-bubble-detector.py")
    spec = importlib.util.spec_from_file_location("detector_comic_hf", path)
    mod = importlib.util.module_from_spec(spec)
    mod.__package__ = "modules.textdetector"
    spec.loader.exec_module(mod)
    return mod

DetModule = load_detector_module()
ComicTextAndBubbleDetector = getattr(DetModule, "ComicTextAndBubbleDetector")

def run(img_path, debug_dir="debug_dump", pad_val=None, dilate_val=None, no_merge=False):
    img_bgr = cv2.imread(img_path)
    if img_bgr is None:
        raise SystemExit("Failed to read image: " + img_path)
    img = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)

    det = ComicTextAndBubbleDetector()
    det.params["debug_dump_path"] = {"type": "line_editor", "value": debug_dir}
    if pad_val is not None:
        det.params["box_padding"] = {"type": "line_editor", "value": int(pad_val)}
    if dilate_val is not None:
        det.params["mask dilate size"] = {"type": "line_editor", "value": int(dilate_val)}

    if no_merge:
        try:
            setattr(DetModule, "_merge_overlapping_blocks", lambda blks, iou: blks)
        except Exception:
            pass

    det._load_model()
    mask, blks = det._detect(img)

    Path(debug_dir).mkdir(parents=True, exist_ok=True)
    suffix = f"pad{pad_val}_dilate{dilate_val}" + ("_nomerge" if no_merge else "")
    final = Path(debug_dir) / f"mask_final_{suffix}.png"
    cv2.imwrite(str(final), mask)
    with open(Path(debug_dir) / f"blocks_summary_{suffix}.txt", "w", encoding="utf-8") as f:
        for i, b in enumerate(blks):
            f.write(f"{i}: xyxy={b.xyxy} _detected_font_size={getattr(b, '_detected_font_size', None)} lines={getattr(b,'lines',None)}\n")
    print("Saved:", final, "blocks:", len(blks))

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: debug_run_detector_params.py <image_path> [debug_dir] [pad] [dilate] [no_merge]")
        sys.exit(2)
    img = sys.argv[1]
    debug = sys.argv[2] if len(sys.argv) > 2 else "debug_dump"
    pad = sys.argv[3] if len(sys.argv) > 3 else None
    dil = sys.argv[4] if len(sys.argv) > 4 else None
    nom = (len(sys.argv) > 5 and sys.argv[5].lower() in ("1","true","yes","y","nomerge"))
    run(img, debug, pad, dil, nom)
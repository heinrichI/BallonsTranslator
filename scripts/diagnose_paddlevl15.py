#!/usr/bin/env python3
import sys
import os
import json
import traceback

from utils.logger import logger as LOGGER
from modules import OCR, GET_VALID_OCR
import modules
from utils.config import pcfg

def main():
    # Ensure registries are populated
    try:
        modules.init_ocr_registries()
    except Exception:
        pass

    module_name = None
    if len(sys.argv) > 1:
        module_name = sys.argv[1]
    else:
        # configured OCR module
        try:
            module_name = pcfg.module.ocr
        except Exception:
            module_name = None

    print("Registered OCR keys:", list(OCR.module_dict.keys()))
    print("GET_VALID_OCR():", GET_VALID_OCR())

    if not module_name:
        print("No OCR module specified (argument or config). Exiting.")
        return

    print(f"Diagnosing OCR module: {module_name}")

    cls = OCR.module_dict.get(module_name)
    if cls is None:
        print(f"Module '{module_name}' not found in registry.")
        return

    # Get params from config if present
    try:
        params_map = pcfg.module.get_params('ocr')
        params = params_map.get(module_name)
    except Exception:
        params = None

    print("Params (repr):", repr(params))

    inst = None
    try:
        if params is not None:
            inst = cls(**params)
        else:
            inst = cls()
    except Exception:
        print("Instantiation failed:")
        traceback.print_exc()
        # attempt to show any partial report
        if inst is not None and hasattr(inst, "module_init_report"):
            try:
                print("module_init_report:", json.dumps(inst.module_init_report, indent=2, ensure_ascii=False))
            except Exception:
                print("module_init_report (repr):", repr(inst.module_init_report))
        return

    # Attempt to call _load_model if available to trigger diagnostics
    try:
        if hasattr(inst, "_load_model"):
            inst._load_model()
    except Exception:
        print("Error during _load_model():")
        traceback.print_exc()
    finally:
        report = getattr(inst, "module_init_report", None)
        if report is not None:
            try:
                print("module_init_report:")
                print(json.dumps(report, indent=2, ensure_ascii=False))
            except Exception:
                print("module_init_report (repr):", repr(report))

        # If the module exposes LOCAL_MODEL_DIR or similar, attempt to list files
        local_dir = getattr(inst, "LOCAL_MODEL_DIR", None)
        if local_dir is None:
            # common pattern in this repo: module-level LOCAL_MODEL_DIR variable
            try:
                local_dir = getattr(__import__(inst.__class__.__module__), "LOCAL_MODEL_DIR", None)
            except Exception:
                local_dir = None

        if local_dir:
            try:
                print(f"Local model dir ({local_dir}) contents:")
                for p in os.listdir(local_dir):
                    print(" ", p)
            except Exception as e:
                print(f"Failed to list {local_dir}: {e}")

if __name__ == "__main__":
    main()
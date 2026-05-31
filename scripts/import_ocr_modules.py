#!/usr/bin/env python3
import os, traceback, importlib
from utils.logger import logger as LOGGER

ocr_dir = os.path.join(os.path.dirname(__file__), '..', 'modules', 'ocr')
ocr_dir = os.path.normpath(ocr_dir)
files = [f for f in os.listdir(ocr_dir) if f.startswith('ocr_') and f.endswith('.py')]
print("Found ocr files:", files)
for f in files:
    modname = 'modules.ocr.' + f[:-3]
    try:
        importlib.import_module(modname)
        print("Imported", modname)
    except Exception:
        print("Failed to import", modname)
        traceback.print_exc()
print("Registered OCR keys after imports:")
from modules.ocr.base import OCR
print(list(OCR.module_dict.keys()))
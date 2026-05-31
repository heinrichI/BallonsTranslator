import sys, os, warnings
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

with warnings.catch_warnings():
    warnings.filterwarnings('ignore')
    from transformers import AutoProcessor
    proc = AutoProcessor.from_pretrained('data/models/paddle_ocr_vl_15')

import inspect
src = inspect.getsource(type(proc))
# Find apply_chat_template override if any
if 'apply_chat_template' in src:
    idx = src.index('apply_chat_template')
    print('Has apply_chat_template override at char', idx)
    print(src[idx:idx+500])
else:
    print('No apply_chat_template override in processor class')

# Check processor_config.json
import json
cfg = json.load(open('data/models/paddle_ocr_vl_15/processor_config.json'))
print('\nprocessor_config.json:', json.dumps(cfg, indent=2)[:500])

# Check what the processor builds for text input
from PIL import Image
import numpy as np
img = Image.new('RGB', (100, 30), color='white')
image_token = proc.image_token
text = f"<|im_start|>user\n{image_token}OCR:<|im_end|>\n<|im_start|>assistant\n"
print('\nText:', repr(text))
with warnings.catch_warnings():
    warnings.filterwarnings('ignore')
    out = proc(text=[text], images=[img], return_tensors='pt')
print('Keys:', list(out.keys()))
print('input_ids shape:', out['input_ids'].shape)
if 'image_grid_thw' in out:
    print('image_grid_thw:', out['image_grid_thw'])
if 'pixel_values' in out:
    print('pixel_values shape:', out['pixel_values'].shape)
print('decoded:', repr(proc.decode(out['input_ids'][0])))
# modified from https://github.com/kha-white/manga-ocr/blob/master/manga_ocr/ocr.py
import re
import jaconv
from transformers import AutoProcessor, AutoModelForImageTextToText
import numpy as np
import torch
from typing import List
from PIL import Image
import concurrent.futures # Added for timeout functionality

from .base import OCRBase, register_OCR, DEFAULT_DEVICE, DEVICE_SELECTOR, TextBlock

MODEL_CACHE_PATH = r'data/models'
class Idefics2Wrap:
    def __init__(self, device='cuda:0'):
        self.language = None
        self.device = device
        # require about 16GB of GPU RAM in half precision (float16)
        self.processor = AutoProcessor.from_pretrained("HuggingFaceM4/idefics2-8b", 
            cache_dir='j:\Comic translate\OCR_bench\models')
        self.model = AutoModelForImageTextToText.from_pretrained(
            "HuggingFaceM4/idefics2-8b",
            torch_dtype=torch.float16,  
            cache_dir='j:\Comic translate\OCR_bench\models'  
        ).to(device)
        self.messages = [
            {
                "role": "user",
                "content": [
                    {"type": "image"},
                    {"type": "text", "text": "Give me text from image, writen in English language, nothing else."},
                ]
            }      
        ]


    @torch.no_grad()
    def __call__(self, img: np.ndarray):
        # Convert np.ndarray to PIL Image
        if img.dtype != np.uint8:
            # You may need to convert or normalize based on your image format
            img = (img * 255).astype(np.uint8)
        pil_img = Image.fromarray(img)

        # pixel_values = self.processor(images=pil_img, return_tensors="pt").pixel_values

        prompt = self.processor.apply_chat_template(self.messages, add_generation_prompt=True)
        inputs = self.processor(text=prompt, images=[pil_img], return_tensors="pt")
        inputs = {k: v.to(self.device) for k, v in inputs.items()}


        # Generate
        generated_ids = self.model.generate(**inputs, max_new_tokens=500)
        generated_texts = self.processor.batch_decode(generated_ids, skip_special_tokens=True)[0]
        generated_texts = generated_texts.replace("User: Give me text from image, writen in English language, nothing else. \nAssistant: ", "")
        print(generated_texts)

        return generated_texts



@register_OCR('idefics2_ocr')
class Idefics2OCR(OCRBase):

    _load_model_keys = {'model'}

    def __init__(self, **params) -> None:
        super().__init__(**params)
        self.engine: Idefics2Wrap = None

    def _load_model(self):
        if self.engine is None:
            self.logger.debug(f'Load Idefics2')
            self.engine = Idefics2Wrap()

    def ocr_img(self, img: np.ndarray) -> str:
        # import debugpy
        # debugpy.debug_this_thread()
        # debugpy.breakpoint()
        self.logger.debug(f'ocr_img')
        return self.engine(img)

    def _ocr_blk_list(self, img: np.ndarray, blk_list: List[TextBlock], *args, **kwargs):
        # import debugpy
        # debugpy.debug_this_thread()
        # debugpy.breakpoint()
        # self.logger.debug(f'_ocr_blk_list')
        # self.engine.model.to('cuda')
        im_h, im_w = img.shape[:2]
        for blk in blk_list:
            x1, y1, x2, y2 = blk.xyxy
            if y2 < im_h and x2 < im_w and \
                x1 > 0 and y1 > 0 and x1 < x2 and y1 < y2: 
                # blk.text = self.engine(img[y1:y2, x1:x2])
                blk.text = self.engine(img[y1:y2 + 5, x1 - 15:x2 + 15])
                if (blk.text == ''):
                    break
            else:
                self.logger.warning('invalid textbbox to target img')
                blk.text = ['']


    def updateParam(self, param_key: str, param_content):
        super().updateParam(param_key, param_content)
        device = self.params['device']['value']
        self.engine.language = self.language()
        # if self.device != device and self.model is not None:
        #     self.model.to(device)

   
import re
from transformers import AutoModelForCausalLM, AutoProcessor
import numpy as np
import torch
from typing import List

from .base import OCRBase, register_OCR, DEFAULT_DEVICE, DEVICE_SELECTOR, TextBlock
from collections import Counter

# Local model directory where prepare_local_files will download files
LOCAL_MODEL_DIR = r"data/models/paddle_ocr_vl_15"


@register_OCR('PaddleOCRVL15')
class PaddleOCRVL15(OCRBase):
    """
    PaddleOCR-VL-1.5 integration.

    - Relies on class attribute `download_file_list` consumed by prepare_local_files.
    - Loads model and processor from LOCAL_MODEL_DIR using transformers AutoModelForCausalLM
      and AutoProcessor (trust_remote_code=True).
    - Supports CPU / CUDA device switching and uses float16 on CUDA, float32 on CPU.
    - Reuses garbage detection logic from ocr_paddleVL_my.py.
    """
    params = {
        "device": DEVICE_SELECTOR(),
        "max_new_tokens": {
            "value": 1024,
            "description": "Max generation tokens"
        },
    }
    device = DEFAULT_DEVICE

    # Files to download via utils.download_util (prepare_local_files will call download_and_check_files)
    download_file_list = [{
        # Base HF URL - concatenate with filenames when downloading
        'url': 'https://huggingface.co/PaddlePaddle/PaddleOCR-VL-1.5/resolve/main/',
        'files': [
            'config.json',
            'configuration_paddleocr_vl.py',
            'generation_config.json',
            'model.safetensors',
            'modeling_paddleocr_vl.py',
            'tokenizer_config.json',
            'tokenizer.json',
            'tokenizer.model',
            'preprocessor_config.json',
            'processing_paddleocr_vl.py',
            'processor_config.json',
            'special_tokens_map.json',
            'inference.yml',
            'image_processing_paddleocr_vl.py',
            'README.md'
        ],
        'sha256_pre_calculated': [None, None, None, None, None, None, None, None, None, None, None, None, None, None, None],
        'save_dir': LOCAL_MODEL_DIR,
        'concatenate_url_filename': 1,
    }]

    _load_model_keys = {'model', 'processor'}

    def __init__(self, **params) -> None:
        super().__init__(**params)
        self.device = self.params['device']['value']
        self.model = None
        self.processor = None

    def is_garbage(self, text, min_len=18):
        # Copied verbatim logic from ocr_paddleVL_my.py
        if not text:
            return False

        clean_text = "".join(text.split())
        if len(clean_text) < min_len:
            return False

        counts = Counter(clean_text)
        most_common = counts.most_common(1)
        char, count = most_common[0]

        unique_count = len(counts)

        if count / len(clean_text) > 0.6:
            self.logger.warning("Flagged: Single character dominance")
            return True

        if len(clean_text) > 30 and unique_count <= 4:
            self.logger.warning(f"Flagged: Low character diversity ({unique_count} unique chars)")
            return True

        if len(clean_text) > 30:
            top3_count = sum(c for _, c in counts.most_common(3))
            top3_ratio = top3_count / len(clean_text)
            if top3_ratio > 0.75:
                self.logger.warning(
                    f"Flagged: Top-3 chars cover {top3_ratio:.0%} of text ({counts.most_common(3)})"
                )
                return True

        if re.search(r'(.{1,6})\s*(\1[\s]*){19,}', text):
            self.logger.warning("Flagged: Repeated short pattern")
            return True

        return False

    def ocr_img(self, img: np.ndarray) -> str:
        # Ensure model & processor loaded
        self._load_model()

        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "image", "image": img},
                    {"type": "text", "text": "OCR:"},
                ],
            }
        ]

        # Apply chat template and build inputs
        text = self.processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        inputs = self.processor(text=[text], images=[img], return_tensors="pt")
        inputs = {
            k: (v.to(self.model.device) if isinstance(v, torch.Tensor) else v)
            for k, v in inputs.items()
        }

        # Generate
        with torch.inference_mode():
            generated = self.model.generate(
                **inputs,
                max_new_tokens=self.get_param_value('max_new_tokens'),
                do_sample=False,
                use_cache=False
            )

        input_length = inputs["input_ids"].shape[1]
        generated_tokens = generated[:, input_length:]
        answer = self.processor.batch_decode(generated_tokens, skip_special_tokens=True)[0]

        if self.is_garbage(answer):
            raise Exception(f"Garbage OCR output: {answer}")

        return answer

    def _load_model(self):
        # Load model and processor from the local directory
        # Instrumented to capture initialization diagnostics for debugging.
        report = {
            'module': 'PaddleOCRVL15',
            'local_model_dir': LOCAL_MODEL_DIR,
            'files': None,
            'device': self.device,
            'success': False,
            'exception': None,
            'timestamp': __import__('datetime').datetime.utcnow().isoformat() + 'Z'
        }
        try:
            try:
                report['files'] = list(__import__('os').listdir(LOCAL_MODEL_DIR))
            except Exception as e:
                report['files'] = f'failed to list dir: {e}'

            if self.model is None or self.processor is None:
                dtype = torch.float16 if self.device == "cuda" else torch.float32

                # Load model
                model = AutoModelForCausalLM.from_pretrained(
                    LOCAL_MODEL_DIR,
                    trust_remote_code=True,
                    torch_dtype=dtype
                ).to(self.device).eval()

                # Load processor
                processor = AutoProcessor.from_pretrained(
                    LOCAL_MODEL_DIR,
                    trust_remote_code=True,
                    use_fast=True
                )

                # Ensure pad_token_id to suppress generation warnings
                try:
                    if getattr(model, "generation_config", None) is not None:
                        if model.generation_config.pad_token_id is None:
                            model.generation_config.pad_token_id = processor.tokenizer.eos_token_id
                    else:
                        # Backwards compat: some HF versions expect config.pad_token_id
                        if getattr(model.config, "pad_token_id", None) is None:
                            model.config.pad_token_id = processor.tokenizer.eos_token_id
                except Exception:
                    # Non-fatal; log and continue
                    self.logger.warning("Failed to set pad_token_id on model/generation_config")

                self.model = model
                self.processor = processor

            report['success'] = True
        except Exception as e:
            import traceback as _tb
            report['exception'] = _tb.format_exc()
            self.logger.error(f"_load_model failed for PaddleOCRVL15: {report['exception']}")
            # Expose report on the instance for higher-level diagnostics
            self.module_init_report = report
            # Re-raise so callers can handle as before
            raise
        else:
            # store successful report
            self.module_init_report = report

    def _ocr_blk_list(self, img: np.ndarray, blk_list: List[TextBlock], *args, **kwargs):
        im_h, im_w = img.shape[:2]
        for blk in blk_list:
            x1, y1, x2, y2 = blk.xyxy
            x1 = int(max(0, x1 - 10))
            x2 = int(min(im_w, x2 + 10))
            y1 = int(max(0, y1 - 2))
            y2 = int(min(im_h, y2 + 5))
            if y2 < im_h and x2 < im_w and x1 > 0 and y1 > 0 and x1 < x2 and y1 < y2:
                region = img[y1:y2, x1:x2]
                try:
                    answer = self.ocr_img(region)
                    blk.text = answer
                except Exception as e:
                    self.logger.error(f"_ocr_blk_list: {e}", exc_info=self.debug_mode)
                    blk.text = ['']
            else:
                self.logger.warning('invalid textbbox to target img')
                blk.text = ['']

    def updateParam(self, param_key: str, param_content):
        super().updateParam(param_key, param_content)
        device = self.params['device']['value']
        if self.device != device and self.model is not None:
            # move model to new device
            try:
                self.model.to(device)
            except Exception as e:
                self.logger.error(f"Failed to move model to device {device}: {e}")
        self.device = device
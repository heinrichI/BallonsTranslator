import sys, os, warnings
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np, torch
from PIL import Image
from transformers import AutoProcessor, AutoModelForImageTextToText
from transformers.modeling_rope_utils import ROPE_INIT_FUNCTIONS

LOCAL_MODEL_DIR = 'data/models/paddle_ocr_vl_15'
TEST_IMAGE = r"j:\Comic translate\OCR_bench\test_data\en\Archie & Friends - Summer Vacation 001-003_0.png"

if 'default' not in ROPE_INIT_FUNCTIONS:
    def _f(config, device=None, seq_len=None, **kw):
        head_dim = getattr(config, 'head_dim', None) or config.hidden_size // config.num_attention_heads
        dim = int(head_dim); base = config.rope_theta
        inv_freq = 1.0 / (base ** (torch.arange(0, dim, 2, dtype=torch.int64).float() / dim))
        return inv_freq, 1.0
    ROPE_INIT_FUNCTIONS['default'] = _f

with warnings.catch_warnings():
    warnings.filterwarnings('ignore')
    model = AutoModelForImageTextToText.from_pretrained(LOCAL_MODEL_DIR, dtype=torch.bfloat16).cuda().eval()
    proc = AutoProcessor.from_pretrained(LOCAL_MODEL_DIR)

img = np.array(Image.open(TEST_IMAGE).convert('RGB'))
pil = Image.fromarray(img)
print('Image size:', pil.size)

TMPL = (
    "{% set image_count = namespace(value=0) %}"
    "{% for message in messages %}"
    "<|im_start|>{{ message['role'] }}\n"
    "{% if message['content'] is string %}{{ message['content'] }}"
    "{% else %}{% for content in message['content'] %}"
    "{% if content['type'] == 'image' or 'image' in content %}<|IMAGE_PLACEHOLDER|>"
    "{% elif 'text' in content %}{{ content['text'] }}"
    "{% endif %}{% endfor %}{% endif %}"
    "<|im_end|>\n{% endfor %}"
    "{% if add_generation_prompt %}<|im_start|>assistant\n{% endif %}"
)

# Check what the processor does with image token in text
image_token = proc.image_token
print('image_token:', repr(image_token))
print('image_token_id:', proc.tokenizer.convert_tokens_to_ids(image_token))

# Check if processor has its own chat_template in tokenizer_config
tmpl = getattr(proc.tokenizer, 'chat_template', None)
print('Processor chat_template:', repr(tmpl[:100]) if tmpl else None)

# Render template manually
TMPL = (
    "{% set image_count = namespace(value=0) %}"
    "{% for message in messages %}"
    "<|im_start|>{{ message['role'] }}\n"
    "{% if message['content'] is string %}{{ message['content'] }}"
    "{% else %}{% for content in message['content'] %}"
    "{% if content['type'] == 'image' or 'image' in content %}<|IMAGE_PLACEHOLDER|>"
    "{% elif 'text' in content %}{{ content['text'] }}"
    "{% endif %}{% endfor %}{% endif %}"
    "<|im_end|>\n{% endfor %}"
    "{% if add_generation_prompt %}<|im_start|>assistant\n{% endif %}"
)
messages = [{'role': 'user', 'content': [{'type': 'image', 'image': pil}, {'type': 'text', 'text': 'OCR:'}]}]
with warnings.catch_warnings():
    warnings.filterwarnings('ignore')
    text = proc.apply_chat_template(messages, chat_template=TMPL, tokenize=False, add_generation_prompt=True)
print('Rendered text:', repr(text))

# Now call processor with text + image
with warnings.catch_warnings():
    warnings.filterwarnings('ignore')
    inputs = proc(text=[text], images=[pil], return_tensors='pt').to('cuda')

print('input_ids shape:', inputs['input_ids'].shape)
print('pixel_values present:', 'pixel_values' in inputs)
if 'pixel_values' in inputs:
    print('pixel_values shape:', inputs['pixel_values'].shape)
print('decoded full input_ids:', repr(proc.decode(inputs['input_ids'][0])))

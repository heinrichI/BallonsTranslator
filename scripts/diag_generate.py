import sys, os, warnings
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import torch
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

import numpy as np
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
messages = [{'role': 'user', 'content': [{'type': 'image', 'image': pil}, {'type': 'text', 'text': 'OCR:'}]}]

with warnings.catch_warnings():
    warnings.filterwarnings('ignore')
    text = proc.apply_chat_template(messages, chat_template=TMPL, tokenize=False, add_generation_prompt=True)

with warnings.catch_warnings():
    warnings.filterwarnings('ignore')
    inputs = proc(text=[text], images=[pil], return_tensors='pt',
                  size={'shortest_edge': 112896, 'longest_edge': 1003520})

print('Input keys:', list(inputs.keys()))
print('input_ids shape:', inputs['input_ids'].shape)
print('image_grid_thw:', inputs.get('image_grid_thw'))
print('mm_token_type_ids present:', 'mm_token_type_ids' in inputs)

inputs = {k: v.to('cuda') if isinstance(v, torch.Tensor) else v for k, v in inputs.items()}

# Try a direct forward pass first to check it works
with torch.inference_mode():
    out = model(**inputs, output_hidden_states=False)
    logits = out.logits
    print('Forward pass OK, logits shape:', logits.shape)
    top5 = logits[0, -1].topk(10)
    for score, idx in zip(top5.values.tolist(), top5.indices.tolist()):
        print(f'  token {idx:6d} {score:.2f} {repr(proc.decode([idx]))}')

# Generate suppressing the literal '<' character token to avoid <|im_end|> runaway
# Also try with forced_eos suppressed
import torch as _t
# Find all tokens that decode to '<' or '|im_end|>' or similar garbage starters
bad_tokens = [93953]  # literal '<'
print('\nGenerating with suppress_tokens=[93953]...')
with torch.inference_mode():
    gen2 = model.generate(**inputs, max_new_tokens=100, do_sample=False,
                          use_cache=False, suppress_tokens=bad_tokens)
new2 = gen2[:, inputs['input_ids'].shape[-1]:]
print('Result:', repr(proc.batch_decode(new2, skip_special_tokens=True)[0]))

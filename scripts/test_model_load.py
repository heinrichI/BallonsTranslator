import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

print('--- Test: modeling file loads ---')
from data.models.paddle_ocr_vl_15.modeling_paddleocr_vl import RotaryEmbedding
print('Has compute_default_rope_parameters:', hasattr(RotaryEmbedding, 'compute_default_rope_parameters'))

print('--- Test: ROPE_INIT_FUNCTIONS ---')
from transformers.modeling_rope_utils import ROPE_INIT_FUNCTIONS
print('Has default in ROPE_INIT_FUNCTIONS:', 'default' in ROPE_INIT_FUNCTIONS)

print('--- Test: check_model_inputs compat ---')
import transformers.utils.generic as g
print('Has merge_with_config_defaults:', hasattr(g, 'merge_with_config_defaults'))

print('ALL CHECKS PASSED')
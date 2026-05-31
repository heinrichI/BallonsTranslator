简体中文 | [pt_BR](../doc/Manual_TuanziOCR_pt-BR.md) | [Español](../doc/Manual_TuanziOCR_ES.md) | [Français](../doc/Manual_TuanziOCR_FR.md)

## 官方提供的请求参数参考：
<p align = "center">
<img src="https://github.com/PiDanShouRouZhouXD/BallonsTranslator/assets/38401147/3c3985e9-f36e-41fb-af94-d6a8088e5ccd" width="85%" height="85%">

</p>

## 团子OCR说明

### 登录
第一次登录时可能会提示密码出错等问题，可以在确认正确输入后勾选并取消勾选`force_refresh_token`选项，以重新登陆。保存后即可正常使用。

### 文本检测
文本检测功能也会提取出文字，而且是整体识别提取。所以当有使用团子的需求时，推荐不要单独使用OCR功能，而是使用团子的文本检测与none_ocr。
团子有自带的拟声词过滤等功能，详细参数设置请参考上方的`官方提供的请求参数参考`

### 本地运行与 PaddleOCR-VL-1.5 运行时补丁
- 如果在本地使用 PaddleOCR-VL-1.5 的本地模型（data/models/paddle_ocr_vl_15），项目在运行时会应用以下非侵入性补丁以兼容 transformers >=5.x：
  1. **ROPE 回退** — 在 `ROPE_INIT_FUNCTIONS` 中注册缺失的 `'default'` 处理器。
  2. **suppress_tokens=[93953]** — 在 `model.generate()` 中屏蔽字面 `<` 字符 token，防止其触发无限 `<|im_end|>` 循环（该 token 的 logit 与正确首词仅差 0.25，导致模型偶发性跑偏）。
  3. **两步提示构建** — 先 `apply
- 该补丁为运行时修改，不会更改 data/ 下的任何文件。测试脚本 scripts/test_paddleocr_fix.py 会在加载两次模型以验证幂等性，并在必要时进行一次简单的合成推理以确认整体验证流程。
- **_CHAT_TEMPLATE** — 针对本地模型目录缺少 `chat_template` 的情况，在 `apply_chat_template()` 调用时直接传入 Jinja2 模板，确保图像 token（`<|IMAGE_PLACEHOLDER|>`）能被正确处理。CPU 与 GPU 下的合成文字图像推理输出已通过验证（EXIT 0）。

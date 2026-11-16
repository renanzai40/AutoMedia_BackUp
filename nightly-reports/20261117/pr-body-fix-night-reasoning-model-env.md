## 夜间验证 REAL-BUG 修复 2/2 —— AUTOMEDIA_LLM_REASONING_MODEL 环境层缺位（sandbox 丢 reasoning 标志）

### 现象（夜间实测）
验证套件（per-run sandbox）内所有 structured completion 首次解析即失败：
`invalid JSON: Expecting value: line 1 column 1 (char 0)`（空内容）或
`Unterminated string / Expecting ',' delimiter`（截断），一次修复调用同样失败；
`ContentWriterGate: LLM returned empty content`（gate.failed, failure_mode=stop）。
**非 sandbox 环境（同机、同 key、同模型）完全复现不出**。

### 根因
per-run sandbox 使用全新 config dir → 文件层 `llm.text_generation.reasoning_model: true`
（#525 thinking-disable 路径）**丢失**；env 层（唯一能穿透 sandbox 的通道）没有该键的映射
（generic split 会错误落 `llm.llm.reasoning.model`）。推理模型 thinking 保持开启：
reasoning 吃掉 max_tokens 预算 → 输出 JSON 被截断/为空。

实证配置 diff（同机同 env）：
- 非 sandbox：`reasoning_model: true` ✓
- sandbox：`reasoning_model` 缺失 ✗（其余键完全一致）

### 修复
`config_loader._env_to_config` 的特殊 LLM 键映射表新增
`AUTOMEDIA_LLM_REASONING_MODEL → llm.text_generation.reasoning_model`
（bool 解析：1/true/yes/on，大小写不敏感），env 层即可携带该标志穿透 sandbox。

### DoD（全部当轮验证）
- 新增 `tests/test_config_loader_reasoning_model_env.py`：4 用例 → **4 passed**
- **反向实证**：回退映射 ⇒ `test_case_insensitive_and_whitespace` 等失败（键落错路径）
- sandbox 配置复验：设 env 后 `load_config()` 在 sandbox config dir 下返回 `reasoning_model: true`
- `ruff` / `mypy config_loader.py` ✓；`pytest tests/test_adapters/ tests/test_config_loader.py` 回归全绿

### 夜间上下文
同 issue #552；与 PR（修复 1/2）同源夜间验证，两条分支各自自洽。

## 夜间验证 REAL-BUG 修复 3/4 —— LengthFinishReasonError 不在 structured fallback 表

### 现象（夜间实测）
`evaluate_content_quality` tool 步骤失败，错误信封：
`Could not parse response content as the length limit was reached - CompletionUsage(completion_tokens=2048, ..., reasoning_tokens=1777, ...)`
——beta `parse()` 尝试在 max_tokens 处截断（推理模型 thinking 吃掉 87% 预算），openai SDK 抛
`LengthFinishReasonError`。该异常**不是 APIError 子类** → 不在 `_FALLBACK_STRUCTURED_ERRORS`
→ 整条 structured 链直接中止，**手工 json_object 回退路径从未执行**（该路径带 thinking-disable
extra_body，本可成功）。journey 场景第 4 步（quality spot-check）全线红。

### 根因
`src/automedia/core/llm_client.py` `_get_fallback_structured_errors()` 返回
`(AttributeError, NotImplementedError, openai.APIError)`，不含 `LengthFinishReasonError`。

### 修复
补入 `openai.LengthFinishReasonError`（`getattr` 防旧 SDK），beta 截断 → 缓存 skip → 手工路径接管。

### DoD（当轮验证）
- `tests/test_llm_client_structured_fallback.py`：2 用例全绿（元组含该异常 + 行为级：monkeypatch beta 抛
  LengthFinishReasonError → 断言回退到 json_object 手工路径并成功解析）
- **反向实证**：回退本 hunk ⇒ 行为用例红（原始异常逃逸出链）
- `ruff` / `mypy llm_client.py` ✓；pre-commit 全钩子绿（含全量 pytest）

### 夜间上下文
报告落点 backup repo `nightly-reports/20261117/`（PAT 无 Issues:write / PR write，见夜间报告两个阻塞段）。

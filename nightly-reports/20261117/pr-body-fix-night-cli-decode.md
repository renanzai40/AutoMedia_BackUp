## 夜间验证 REAL-BUG 修复 1/2 —— validation CLI 适配器子进程解码崩溃

### 现象（夜间实测）
2026-11-17 夜间全量验证（159 场景、真实 LLM、main @ f39823f7、Windows 11 / cp936 区域设置 / Python utf8_mode=1）：
CLI 步骤子进程输出非 UTF-8 字节（GBK）时，`subprocess._readerthread` 抛 `UnicodeDecodeError`，
步骤 stdout/stderr **静默丢失**，原本健康的用例红。夜间日志 4 分钟内出现 3 次。

### 根因
`src/automedia/validation/adapters.py` 的 `_run_process` 使用 `text=True` —— 本机 Python 处于
UTF-8 模式（`locale.getpreferredencoding()=='utf-8'`），对子进程字节流做**严格 UTF-8 解码**；
原生 Windows 子进程（非 Python 工具）控制台输出为 GBK → 读取线程死亡 → stdout=None。

### 修复
单点收口 `_run_process`：捕获 bytes，按 **utf-8 → gbk → replacement** 容错解码
（新增模块级 `_tolerant_decode`）。Linux/CI 行为不变（UTF-8 先行成功即返回）。

### DoD（全部当轮验证）
- 新增 `tests/test_adapters/test_cli_adapter_decode.py`：8 用例（GBK/UTF-8/坏字节/None/str 直测 + 子进程级 3 例）→ **8 passed**
- **反向实证**：回退本 hunk ⇒ 测试文件收集期即红（`_tolerant_decode` 不存在）；夜间日志可复现"stdout 丢失"模式
- `ruff check` ✓；`mypy src/automedia/validation/adapters.py --ignore-missing-imports` ✓（无新错误）
- 回归：`pytest tests/test_adapters/ tests/test_config_loader.py` 全绿（170+ 用例）

### 夜间上下文
报告落点 issue #552；评论通道受 PAT 权限限制（缺 Issues:write），夜间报告以 backup repo + PR body 承载。

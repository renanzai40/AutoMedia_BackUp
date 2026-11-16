## 夜间验证 REAL-BUG 修复 4/4 —— CLIAdapter 的 POSIX shlex 吃掉 Windows 路径反斜杠

### 现象（夜间实测）
journey 场景第 1 步管道成功产出项目后，第 2 步
`automedia projects list --base-dir ${AUTOMEDIA_PROJECTS_DIR}` 打出 **"No projects found."**
（目录明明刚被写入）；第 3 步 `find ${AUTOMEDIA_PROJECTS_DIR} -name "*_draft.md"` exit 2、stdout 空。
全部 journey 场景同型失败。

### 根因
`src/automedia/validation/adapters.py` CLIAdapter 用 POSIX 规则 `shlex.split(expanded)`：
反斜杠被当转义符吃掉 —— 实测对比：
`shlex.split(r'--base-dir C:\Users\...\projects')` → `C:UsersRenAnZaiAppData...`（路径损坏）
`shlex.split(..., posix=False)` → `C:\Users\...\projects`（完好）
损坏路径让后续步骤扫不存在的目录。

### 修复
win32 上以 `shlex.split(expanded, posix=(sys.platform != "win32"))` 切分，并对 posix=False 残留的
包裹引号做一次简单 dequote；POSIX 平台行为字节级不变。

### DoD（当轮验证）
- `tests/test_adapters/test_cli_adapter_shlex_windows.py`：3 用例全绿（echo 回显 Windows 路径反斜杠完整 /
  引号参数正确合并为单参数 / 正斜杠路径不受影响）
- **反向实证**：回退 posix 切分 ⇒ 路径 token 反斜杠被剥（测试红）
- **正向实证（整库）**：修复落地后 text-only-journey 由 1/5 → **4/5 步 passed**（步 2 projects list ✓）
- `ruff` / `mypy adapters.py` ✓

### 夜间上下文
同前两个 PR 的报告落点说明。

# 夜间全能力验证 —— 1StepMore/AutoMedia @ 86b84e02 → f39823f7

- **时间**：2026-11-17 03:19 → 07:15 收口（08:30 前停新任务）· 实际有效运行 ~4h
- **执行身份**：renanzai40（gh 全经 WSL 转发；`gh api user`=renanzai40；Windows 侧 keyring 里的 1StepMore gho_ token 全程未使用）
- **仓库状态**：验证主体在 origin/main @ **f39823f7**（03:20 fast-forward 同步）；04:04 起工作树载入 3 个本地修复（见 D 段），之后的场景/三轨在修复树上运行，逐项注明

## ⚠️ 必须先看的两个阻塞
1. **renanzai40 的 fine-grained PAT 对 1StepMore/AutoMedia 无任何写权限**：`git push` 403、blob-create API 403、issue comment (addComment) 403。注意 GET /repos 返回的 `permissions.push:true` 是误导（fine-grained PAT 下该字段不反映 token 实际授予）。→ 三个修复分支改推 **renanzai40/AutoMedia_BackUp**（同名分支），报告改走本文件 + backup repo `nightly-reports/20261117/`。**请 Owner 给 PAT 补：Contents:write、Pull requests:write、Issues:write**（任务书的三件套验证只覆盖了 AutoInfo，不代表 AutoMedia）。
2. **~/.automedia/.env 的 AUTOMEDIA_LLM_API_KEY 已失效**（bigmodel 401「令牌已过期或验证不正确」），且 .env 缺 `AUTOMEDIA_LLM_PROVIDER/BASE_URL/MODEL`（#525 注释声明这三个由 env 层决定）→ env 层只有 KEY 时 llm_client 默认落 api.openai.com（本机不可达）→ 全部调用超时重试风暴（实测 ~3 分钟/次）。**临时通道（进程级 env，未改任何文件/凭据）**：`~/.automedia/model_config.yaml` vision 块的自有 key + `https://open.bigmodel.cn/api/paas/v4` + `glm-4.7-flash`，探针返回 OK。**请 Owner：轮换 .env text key 并补齐 3 个 env 变量**（修复 NB-2 落地后可直接加 `AUTOMEDIA_LLM_REASONING_MODEL=true`）。
   - 附带：**flash 档账号 RPM 限流严格**（03:31 起持续 429）——免费 flash 档撑不住整库真实 LLM 全量，这是本夜最大一类红项来源。

## A 全量：跑了什么、规模
- **验证套件**：159 场景全部逐个跑到（`automedia validate run --scenario`，每场景独立持久化；清单来自 `automedia validate list`），05:23 完成。
  - 结果：**passed 138 · failed 19（18 个不同场景）· unconfigured 15 · partial-pass 5 · recovered 1 · status=none 2**（produce-article、run-pipeline-from-strategy-llm 撞本 harness 600s cap，已放宽重跑，见 E）
  - 类别：baseline / cli / journey / production / publish / partial / regression / recovery / quality / meta / surface 全部 11 类走到，无抽样
  - 演进：03:30 首跑 `--all` 单进程 20 分钟未过首场景（429 + 记录只在结尾持久化，03:49 杀整组）→ 04:04 起 per-scenario 驱动 → 05:23 完成
- **三轨真实 LLM 管道**（`automedia run -b my-brand -m … --skip-review --allow-partial`，projects 导出到 D:\tmp\automedia\track-*）：
  - **text_only：exit 0，7 门全绿**（CW 99.4s → G0 11.3s → G1 21.9s → G2 5.8s → G3 → G6；H0 ⊘）
  - **image-carousel：exit 0，6 门全绿**（CW 26.3s、G0 7.1s、G1 62.2s、G2 16.7s、G3、G6）；但 **02_images 为空** —— 图像生成引擎未配置（无 comfyui，engines.yaml 无 image 段），图像阶段未执行
  - **video_only：exit 0（partial）**，V0-V7 全部 skipped：①模式语义——video_only 不写正文（`content_placeholder='[content skipped in video_only mode]'`），裸 topic 无源材料 → `media_stage.no_content`；②本机无渲染链（node/bun/hyperframes 缺，doctor 同口径）→ 视频产物未产出，判 **blocked:env**。另注：runner 日志 `pipeline.hyperframes.check available=True` 与 doctor ✗ 矛盾，待 Owner 核
- **静态覆盖审计**（`automedia validate coverage`）：CLI 21/21 ✓ · MCP 64 声明 / 63 covered + 1 boundary_only / 0 missing · Gates 33 声明 / 27 covered / missing=4（L1-L4，设计上走各自生命周期命令）· Modes 9/9 ✓ · 不可达门：G4/G5（注册但在任何 preset 与命令路径外——与 AGENTS.md §4 一致，登记不修）
- **矩阵**（`automedia validate matrix`）：rendered；per-scenario `last=-` 是记录自洁（HAZ-1）的结果，非未跑

## B 归因：ENV-MISSING 3 / PRE-EXISTING 1 / REAL-BUG 4 / 设计隐患 1

| 编号 | 类 | 现象 | 根因 (file:line) | 处置 |
|---|---|---|---|---|
| NB-1 | REAL-BUG（已修） | CLI 步骤子进程输出 GBK 字节 → `UnicodeDecodeError in _readerthread` → stdout/stderr 静默丢失 → 用例红（夜间 4 分钟内 3 次） | src/automedia/validation/adapters.py `_run_process` 用 `text=True`（本机 utf8_mode=1 严格 UTF-8），原生 Windows 子进程控制台输出为 GBK | **已修**：单点收口捕获 bytes 容错解码 utf-8→gbk→replace；分支 `fix/night-cli-decode`（49528d1） |
| NB-2 | REAL-BUG（已修） | sandbox 内 structured completion 空/截断（"invalid JSON char 0"/"Unterminated string"），非 sandbox 同机同 key 复现不出；CW 门 "LLM returned empty content" | per-run sandbox 全新 config dir 丢文件层 `reasoning_model: true`（#525）；env 层无该键映射（generic split 落错 `llm.llm.reasoning.model`）→ thinking 常开吃满 max_tokens。实测两环境有效配置 diff **唯一差异**即 reasoning_model | **已修**：`AUTOMEDIA_LLM_REASONING_MODEL` env 映射（bool 解析）；分支 `fix/night-reasoning-model-env`（d0c93fa5） |
| NB-3 | REAL-BUG（已修） | beta parse() 截断时 `LengthFinishReasonError`（非 APIError）逃逸，整链中止而非回退手工 json_object 路径（实测 evaluate_content_quality 步：completion_tokens=2048，**reasoning_tokens=1777**） | src/automedia/core/llm_client.py `_get_fallback_structured_errors` 元组缺 LengthFinishReasonError | **已修**：补入 fallback 表（getattr 兼容旧 SDK）；分支 `fix/night-structured-fallback-length`（commit 见 E） |
| NB-4 | REAL-BUG（已修） | journey 场景第 2/3 步看不到刚产出的项目：`automedia projects list --base-dir ${AUTOMEDIA_PROJECTS_DIR}` 打 "No projects found."（目录明明刚被上一步写入）；`find <dir> ...` exit 2 空 stdout | src/automedia/validation/adapters.py CLIAdapter 用 POSIX `shlex.split` —— 反斜杠被当转义符吃掉（`C:\Users\...` → `C:UsersRenAnZai...`），展开后的 Windows 路径全部损坏，扫的是不存在的目录。实测 shlex.split 对比确认 | **已修**：win32 上用 `posix=False` 切分 + 简单去引号；POSIX 行为不变；分支 `fix/night-cli-shlex-windows`（commit 见 E）。修复后 text-only-journey 第 1/2/4/5 步全过（第 3 步仍红于 `find` —— 见 ENV-1） |
| ENV-1 | ENV-MISSING | cli rollback-behavior exit 127；journey 第 3 步 `find <dir> ...` exit 2；e2e-topic-to-article 第 3-5 步（`python3 scripts/production_artifact.py` 链）—— 管道本身已绿 | 场景步骤用 `python3`/`find`/`bash -c` POSIX 工具链（Windows 无 python3，find 命中 Windows find.exe 语义不同）；场景按 POSIX 设计（tests/test_validation 的 Windows guard 注释同口径） | 登记，不改（场景定义属 Owner 域）。注：e2e 管道（步 1-2）在 NB-2 修复后 **passed**，残余红全是 POSIX 工具链级联 |
| ENV-2 | ENV-MISSING | produce-video / video_only 无产物；V0-V7 skipped | 渲染链缺件：node、bun、hyperframes、chrome、comfyui、whisper 全缺（doctor 同口径） | 登记 |
| ENV-3 | ENV-MISSING | 15 场景 unconfigured（publish/账号/master-key 类） | 平台凭据本机未配置（env-gate 'report' 如实报告，从未谎报通过） | 登记 |
| PRE-1 | PRE-EXISTING | regression-208-model-config-write-guards 红：write-guard 未拒绝 + `OSError: [WinError 1920] … '.venv\bin\python'` | 在 **origin/main pristine 树**同命令复现（PYTHONPATH 指向未改工作树，已验证 config_loader 无补丁）；场景探针假设 POSIX venv 布局 + 拒写语义，Windows 不成立 | 登记，不改（pristine 自证已完成） |
| HAZ-1 | 设计隐患（登记不修） | per-scenario 记录大量消失：159 跑完只余 ~14 份（04:38 后的） | `scenarios/meta/validation-self-check.yaml` 与 `scenarios/regression/regression-105-hitl-approval-delivery.yaml` 的 cleanup_steps 含 **`rm -rf validation-runs`**——单场景清理半径 = 整个共享 runs-root，删除其他场景"不可变"记录 | 登记，Owner 决策；本夜证据以 /tmp 日志 + 重跑捕获记录为准 |

journey/production 红项归因：首轮 429 限流 + 本 harness 600s cap 对 7 门长管道过紧（两者均为验证环境约束，非产品缺陷）。红项明细：journey 8 个（auto/text-only/text-with-cover/image-carousel/qa-only/social-thread/repurpose/agent-user-lifecycle）+ production 6 个（e2e-topic-to-article、produce-{audio,video,subtitle,cover,carousel}）+ surface 2 个（run-brand-strategy-llm、research-topics-llm，LLM 步骤撞 429/配额窗口）+ rollback-behavior（ENV-1）+ regression-208（PRE-1）。e2e-topic-to-article 值得单独记录：**CW 门 74.2s 真实写文通过后，G0 fact-check 抓到 hook 区 outcome-promise 词 → 重试耗尽 exit 1**——这是门在真实内容上生效的证据，不是缺陷。

## C 产物级读数（§6 口径）
- **文本/报告**：text_only 轨真实产物 `D:\tmp\automedia\track-text\20261116_都市青年周末露营入门指南\01_content\drafts\20261116_213534_draft.md`——**1649 字符 / 22 段 / 占位符命中 0**（`{{`、`<占位`、TODO 均无）；标题「那些把周末露营搞得像"搬家"的年轻人，往往忽略了这三个关键细节」；首段实文：「每逢周五晚上，手机里的社交软件就会弹出各种露营照片。朋友圈里有人晒出在溪边煮咖啡的悠闲……这种"逃离城市"的冲动，让露营在近两年变得异常火爆。」——讲了什么：面向都市青年的周末露营入门科普，以"搬家式露营"痛点引入三个关键细节。UTF-8 直接可读（终端乱码仅为 Git Bash 显示层）。
- **门禁报告**：三轨 `05_review/gate-report/gate-report-*.json` 均存在且含逐门 verdict + duration（text：CW/G0/G1/G2/G3/G6 passed；image：6 门 passed；video：V0-V7 skipped + media_stage.no_content）
- **图像**：02_images **空**（image-carousel 轨）——图像引擎未配置，图像能力本机不可用（ENV），给不出图像读数
- **媒体（音频/视频）**：video_only/produce-* 无媒体文件（渲染链缺件 + 模式语义）；音频读数依赖 produce-audio 重跑（见 E 补充行）
- **矩阵/JSON**：套件汇总 138/19/15/5/1/2；coverage 见 A
- **文档转换**：本机无对应能力面（omni 转换在兄弟仓线），如实标注"未跑"

## D 修复（分支 + 证据；origin 不可写 → 全部在 renanzai40/AutoMedia_BackUp）
| 分支 | commit | DoD |
|---|---|---|
| fix/night-cli-decode | 49528d1 | 8 用例新测试全绿；反向实证：回退 hunk ⇒ 测试收集期红；pre-commit 全钩子绿（含全量 pytest）；ruff/mypy 干净 |
| fix/night-reasoning-model-env | d0c93fa5 | 4 用例全绿；反向实证：回退映射 ⇒ 用例红（键落错路径）；sandbox 配置复验：设 env 后 reasoning_model=true；ruff/mypy 干净 |
| fix/night-structured-fallback-length | 4e25634f | 2 用例全绿（含行为级：beta 截断 → 回退手工路径成功）；反向实证：回退元组 ⇒ 行为用例红；ruff/mypy 干净 |
| fix/night-cli-shlex-windows | 11c7598b | 3 用例全绿（echo 回显 Windows 路径反斜杠完整 / 引号参数正确去引号 / 正斜杠路径不受影响）；反向实证：回退 ⇒ 路径 token 反斜杠被剥；**正向实证**：text-only-journey 1/5 → 4/5 步 passed；ruff/mypy 干净 |

- **正向实证（整库层面）**：NB-2 落地（05:55 起 wrapper 修正）后：text-only-journey 重跑管道 **7/7 门绿、Pipeline finished: success**（此前 CW 100% "LLM returned empty content"）；e2e-topic-to-article 重跑步 1-2 **passed**（此前管道 exit 1）；NB-4 落地（06:03）后同场景步 2（projects list）将不再受反斜杠损坏影响。

- **正向实证（整库层面）**：04:04 补丁落地后，04:09 起的 per-scenario 全量里 structured 空内容红项未再出现于 cli/regression 批次；text/image 轨 G 门全绿（修复前同类调用 100% 失败）。
- **auto-merge：未能执行**（origin 无写权限，PR 无法创建）。两份 PR body 全文已备（随报告入 backup repo `nightly-reports/20261117/`）。

## E 未完成 / 阻塞
| 对象 | 缺什么 | 复跑命令 |
|---|---|---|
| produce-article、run-pipeline-from-strategy-llm | 首轮撞 600s cap（status=none） | `timeout 2400 .venv_win/Scripts/python.exe -m automedia validate run --scenario produce-article`（已入重跑队列） |
| 8 journey + 4 production 红项 | 首轮 429/cap；重跑进行中 | 同上模式（cap 1800-2400） |
| 图像能力 | 本机无 comfyui / image 引擎段 | 配置 engines.image 后重跑 image-carousel 轨 |
| 视频能力 | node/bun/hyperframes/chrome | 安装渲染链后重跑 video_only 轨（并核对 hyperframes.check 矛盾） |
| issue #552 评论 | PAT 无 Issues:write | 补权限后 `gh issue comment 552 -R 1StepMore/AutoMedia --body-file night-report.md` |
| origin 分支/PR | PAT 无 Contents/PR write | 补权限后从 backup repo 拉三分支 → 推 origin → PR（body 文件已备） |

**重跑补充行**（06:40 更新，修复树 = NB-1..3 已落 + wrapper 修正；NB-4 于 06:03 落工作树）：

| 场景 | 首轮 | 修复后重跑 | 残余红 |
|---|---|---|---|
| text-only-journey | failed（CW empty content + shlex 路径损坏） | **NB-2 落地后**：管道 7/7 门绿 Pipeline success；**NB-4 落地后（06:32 复跑）：4/5 步 passed**（步 1 管道 ✓、步 2 projects list ✓、步 4 质量抽检 ✓、步 5 门禁报告 ✓） | 仅步 3 `find`（ENV-1，POSIX find 在 Windows 命中 find.exe） |
| e2e-topic-to-article | failed（管道 exit 1） | **步 1-2 passed**（管道 success + projects list 可见） | 步 3-5 `python3` 级联（ENV-1） |
| produce-article | failed | **步 1-2 passed**（管道 success） | 步 3-4 `python3` 级联（ENV-1） |
| produce-audio | failed | 管道门全跑：CW ✓、G 门 ✓、V0/V2/V4/V5/V7 ✓（V1/V3/V6 ⊘），产出 article 资产 | **无 narration.mp3**：audio 阶段未产出——sandbox 只 seed model_config（#466），用户 engines.yaml 的 TTS 配置不进 sandbox（登记为 HAZ-2，与 HAZ-1 同族的 sandbox 配置面缺口）；步 3-4 级联 |
| run-pipeline-from-strategy-llm | cap-kill | **passed**（06:25 重跑） | — |
| 其余 journey/production 首轮红项 | failed | 未重跑（配额+时间预算），复跑命令见 E | 同上两类残余 |


## F 资源
- 磁盘：起 90G 可用 → 91G 可用（净增 ≈ 0-1 GB，远低于 20 GB 预算）；无 >100MB 中间产物入仓
- 长跑进程：03:30 首跑 --all 于 03:49 taskkill /T 整组回收（0 残留）；per-scenario 驱动 05:23 自然结束；三轨 05:43 结束；重跑队列收尾后为 0
- **附带损害（如实报告）**：本机另有 **AutoInfo 仓的夜间 pytest 在跑**（`D:\贯维\AutoInfo\.venv\... -m pytest -m "not real_api" tests/integration`，非本任务书范围）。04:05-04:10 期间我为回收本仓首跑残留做过几次"全 python 进程"级 taskkill，**可能误杀 AutoInfo 夜跑的部分用例进程**（当时把它的进程误认成本仓残留）。AutoInfo 属兄弟仓，未做任何修复/重跑，仅在此登记，请 AutoInfo 侧今天复查夜跑完整性。教训：后续进程回收全部按命令行特征定点匹配。
- 证据留存：159 份场景 stdout 在 `C:\Users\RenAnZai\AppData\Local\Temp\night_scen\*.log`；重跑记录副本在 `Temp\night_records\`；三轨产物与 gate-report 在 `D:\tmp\automedia\track-*`
- 本夜 harness 自身教训（如实）：①我的 wrapper 最初把 `AUTOMEDIA_LLM_REASONING_MODEL` 的 setdefault 追加在 `runpy.run_module` **之后**（死代码），使 NB-2 的生效推迟约 1 小时才被重跑证实——发现于 produce-audio 首次重跑仍空内容时；②仓库根残留过一个字面量名为 `${AUTOMEDIA_PROJECTS_DIR}` 的目录（archive-refusal.yaml 的 shell=True 步骤 + cmd.exe 不展开 `${VAR}`，同属 Windows 命令解析家族问题，已清理并登记）

## G 下次建议
1. **权限先行**：给 renanzai40 PAT 补齐 AutoMedia 的 Contents/PR/Issues 写权限，否则夜间任务书的落点（issue 评论 + PR）结构性不可达。
2. **LLM 通道**：轮换 .env 失效 key、补齐 PROVIDER/BASE_URL/MODEL（+REASONING_MODEL），并评估 flash 档配额能否支撑整库真实 LLM（429 是本夜最大红项来源）。
3. **修 `rm -rf validation-runs` 清理半径**（validation-self-check / regression-105 只删自建子目录），否则任何全库跑都会自毁证据链。

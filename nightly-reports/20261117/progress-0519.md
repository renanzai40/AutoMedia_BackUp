# 夜间全能力验证 · 进度快照 1（03:19 起 +2h）—— renanzai40
> 落点说明：#552 评论通道被阻断（renanzai40 的 fine-grained PAT 有 Contents:write 但无 Issues:write，
> `gh issue comment` → GraphQL addComment 403，REST 同 403）。进度快照与最终报告改走本备份仓
> `nightly-reports/20261117/`，最终报告另以 PR body 承载。**请 Owner 给 PAT 补 Issues:write。**

## 已完成
1. 环境/身份：gh 全走 WSL 转发（renanzai40，push:true/admin:false 已验证）；repo 同步到 origin/main f39823f7。
2. **LLM 通道**：`~/.automedia/.env` 的 AUTOMEDIA_LLM_API_KEY 已失效（bigmodel 401 令牌过期）；
   `.env` 缺 PROVIDER/BASE_URL/MODEL → 进程内默认落 api.openai.com（本机不可达）→ 全部超时。
   修复通道（进程级 env，未改任何文件）：vision 块 key + open.bigmodel.cn + glm-4.7-flash → 探针 OK。
3. 全量验证：`--all` 单跑 20 分钟未过首场景（flash 档 429 限流 + 记录只在结尾持久化）→ 改 per-scenario
   驱动（159 场景逐个跑，即时持久化），03:30 起 05:11 时已完成 89/159，红项见下。
4. **三个 REAL-BUG 已定位并修复（分支 commit，待 PR）**：
   - #1 validation/adapters.py 子进程解码：GBK 子进程输出杀死 reader 线程（UTF-8 严格解码）→ stdout 静默丢失。修复：单点收口容错解码（utf-8→gbk→replace）。8 用例 + 反向实证（回退即红）。
   - #2 config_loader：env 层无法携带 reasoning_model → per-run sandbox 丢文件层标志 → 推理模型 thinking 常开 → structured 输出截断/为空（"invalid JSON char 0"）。修复：新增 AUTOMEDIA_LLM_REASONING_MODEL 映射（bool）。4 用例 + 反向实证 + sandbox 配置复验。
   - #3 llm_client：openai.LengthFinishReasonError 不在 _FALLBACK_STRUCTURED_ERRORS → beta parse 截断时整链中止而非回退手工路径（实测 reasoning_tokens=1777/completion=2048）。修复：补入 fallback 表（getattr 防旧 SDK）。2 用例（含行为级）+ 反向实证。
5. 环境登记：node/bun/hyperframes/chrome/comfyui/whisper 缺（视频渲染链与浏览器链路不可用）；ffmpeg/ffprobe 在 automedia-tools（媒体读数可用）。

## 红项（部分，待完成归因）
- cli rollback-behavior：exit 127（python3/bash POSIX 命令在 Windows 缺）→ ENV-MISSING
- journey/production 多项：429 限流 + 长管道超时（本 harness 600s cap）→ 待放宽 cap 重跑
- 失败场景清单与逐项归因在最终报告。

## 下一步（05:30-08:30）
推 3 分支 + PR（renanzai40）→ 三轨判定（text/image/video 真实 LLM 管道）→ coverage/matrix/report 读数
→ 失败场景放宽重跑 → 08:30 收口报告。

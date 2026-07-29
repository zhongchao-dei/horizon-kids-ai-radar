# 儿童 AI 教育新闻雷达配置说明

这份 Fork 已按“中文儿童 AI 教育启蒙博主”的工作场景做了定制：

- 受众：小学三年级至初中阶段孩子的家长
- 输出：简体中文
- 运行时间：每天北京时间 09:30（GitHub Actions 定时任务可能延迟）
- 日报上限：12 条
- 重点栏目：
  - 中国儿童与中小学 AI 教育
  - K12 实践与学习
  - 儿童安全、研究与政策
  - 与孩子相关的 AI 产品变化
- 过滤原则：优先真实 K12 场景、一手来源、研究证据、平台规则和家长可观察的变化；降低成人办公、企业采购、纯技术更新、软广和“AI 时代不学就落后”类内容的分数。

## 需要添加的 GitHub Secrets

定时任务默认使用 Gemini；DeepSeek 作为手动备用模型。**不要把 API Key 写进仓库、Issue、聊天记录或 `data/config.github.json`。**

在本 Fork 中打开：

`Settings` → `Secrets and variables` → `Actions` → `New repository secret`

- Name：`GOOGLE_API_KEY`
- Secret：粘贴你的 Gemini API Key

如需测试备用模型，再添加：

- Name：`DEEPSEEK_API_KEY`
- Secret：粘贴你的 DeepSeek API Key

`GITHUB_TOKEN` 由 GitHub Actions 自动提供，不需要自己创建。

## 首次运行

1. 打开 `Actions`。
2. 选择 `Daily Horizon Summary`。
3. 点击 `Run workflow`。
4. Provider 先选择 `gemini`，等待任务成功完成。
5. 如需验证备用模型，再选择 `deepseek` 手动运行一次。

如果 GitHub 提示工作流尚未启用，先点击 `I understand my workflows, go ahead and enable them`。

## 开启 GitHub Pages

首次工作流成功后会创建 `gh-pages` 分支。然后打开：

`Settings` → `Pages`

- Source：`Deploy from a branch`
- Branch：`gh-pages`
- Folder：`/(root)`

保存后，GitHub 会显示日报站点地址。

## 主要定制文件

- `data/config.github.json`：模型、新闻源、栏目配额和受众筛选规则
- `src/models.py`：允许配置 `ai.curation_profile`
- `src/ai/analyzer.py`：在新闻评分阶段加载受众筛选规则
- `src/ai/enricher.py`：在二次整理阶段加载受众编辑规则
- `.github/workflows/daily-summary.yml`：每天定时运行并发布到 GitHub Pages

## 后续可选项

- 飞书/钉钉/Slack 推送：启用 `webhook` 后再添加对应 Webhook Secret
- 邮件日报：配置 SMTP/IMAP 和邮箱授权码
- 调整时间：修改工作流中的 UTC cron 表达式
- 调整每日数量：修改 `filtering.max_items` 和各栏目 `limit`


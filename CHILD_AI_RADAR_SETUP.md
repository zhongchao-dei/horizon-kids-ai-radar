# K12 AI 双路径新闻雷达配置说明

这份 Fork 已升级为“共享证据底座 + 家长 / 教师双路径”。教师端是新的主定位，家长端继续保留并独立筛选。

## 每天生成什么

每天北京时间 09:30 左右运行（GitHub Actions 可能有少量延迟），中文模式会生成三份独立材料：

1. `YYYY-MM-DD-all-candidates-zh.md`：当天去重后的全部候选资讯，保留标题、原始链接、来源、双端评分与入选状态；
2. `YYYY-MM-DD-parent-topics-zh.md`：家长端 3—5 条重点选题；
3. `YYYY-MM-DD-teacher-topics-zh.md`：教师端 3—5 条重点选题，也是邮件、Webhook 与旧版摘要入口的默认内容。

同一条资讯可以同时入选两端，也可以只入选其中一端。两端各自评分、各自筛选，不用教师榜单替代家长榜单。

## 筛选重点

### 家长端

- 孩子在家庭中的真实使用场景；
- 家长能观察到的学习过程证据；
- 儿童安全、隐私、判断力与亲子协作；
- 不是纯成人办公、软广或恐吓式未来论。

### 教师端（主路径）

- 备课、课堂任务、作业、评价与班级管理；
- 学生是否保留思考、修改与协作过程；
- 学术诚信、数据隐私、公平性和学校治理；
- 可复用的课堂案例、政策、研究与一手证据。

## GitHub Secrets

定时任务默认优先使用 DeepSeek；当 DeepSeek 出现余额或配额不足、限流、鉴权失败、服务不可用或空响应时，自动切换到 Gemini。

不要把 API Key 写进仓库、Issue、聊天记录或配置文件。

打开仓库：`Settings` → `Secrets and variables` → `Actions` → `New repository secret`

- `DEEPSEEK_API_KEY`：DeepSeek API Key
- `GOOGLE_API_KEY`：Gemini API Key

`GITHUB_TOKEN` 由 GitHub Actions 自动提供，不需要自行创建。

## 首次或手动运行

1. 打开 `Actions`；
2. 选择 `Daily Horizon Summary`；
3. 点击 `Run workflow`；
4. Provider 保持 `deepseek`；
5. 等待运行成功，并确认 `gh-pages/_posts/` 下出现三份当天材料。

如果 GitHub 提示工作流尚未启用，先点击 `I understand my workflows, go ahead and enable them`。

## GitHub Pages

首次工作流成功后会创建 `gh-pages` 分支。打开 `Settings` → `Pages`：

- Source：`Deploy from a branch`
- Branch：`gh-pages`
- Folder：`/(root)`

## Obsidian 同步位置

- 全部候选：`K12-AI共享证据库/00-每日全部候选/`
- 家长精选：`家长端AI教育选题/01-选题/AI家庭教育选题库/`
- 教师精选：`教师端AI教育选题/01-选题/AI教师教育选题库/`

2026-08-01 为双路径正式启用日。旧日期没有持久化的候选标题不会反向编造。

## 主要定制文件

- `data/config.github.deepseek.json`：DeepSeek 主模型、Gemini 回退与双路径筛选配置；
- `data/config.github.json`：Gemini 主模型、DeepSeek 回退与双路径筛选配置；
- `src/ai/analyzer.py`：一次分析同时产出家长端与教师端评分；
- `src/ai/enricher.py`：生成两套结构化选题字段；
- `src/ai/summarizer.py`：生成全部候选表和两端精选稿；
- `src/orchestrator.py`：两端独立筛选并发布三份材料；
- `.github/workflows/daily-summary.yml`：每日运行并发布到 GitHub Pages。

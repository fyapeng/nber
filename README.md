# NBER 每周工作论文

这个项目会自动获取最新一期 NBER Working Papers，抓取论文标题、作者、摘要和原文链接，并用 Kimi API 生成中文标题与中文摘要。最终数据会写入 Astro 静态站点并发布到 GitHub Pages。

网站地址：`https://fyapeng.com/nber/`

## 功能概览

- 展示最新一期 NBER Working Papers。
- 保留英文标题、英文摘要、作者、发布日期和 NBER 原文链接。
- 使用 Kimi API 翻译标题和摘要。
- 维护最近批次数据：`papers.json`、`update-meta.json`、`archive.json`、`translation-cache.json` 和 `translation-audit.md`。
- 优先从邮箱 IMAP 读取 NBER 邮件中的论文链接。
- 如果邮箱源不可用，会自动回退到 NBER Working Papers API。
- GitHub Actions 每周一北京时间 13:00 和 18:00 自动运行更新。

## 技术栈

- Astro 7
- Python 3
- NBER Working Papers 页面与 API
- IMAP SSL 邮箱读取
- Kimi / Moonshot API 翻译
- GitHub Actions + GitHub Pages

## 本地开发

安装前端依赖：

```powershell
npm install
```

启动本地开发服务：

```powershell
npm run dev
```

构建静态站点：

```powershell
npm run build
```

## Python 环境

安装脚本依赖：

```powershell
python -m pip install -r requirements.txt
```

在这台 Windows 机器上，Codex 通常使用 `codex` Conda 环境：

```powershell
conda run -n codex python scripts/update_papers.py --dry-run
```

## 本地环境变量

真实密钥放在本地 `.env`，不要提交。仓库提供了 `.env.example` 作为模板。

```env
NBER_EMAIL_IMAP_HOST=你的 IMAP 服务器地址
NBER_EMAIL_IMAP_PORT=993
NBER_EMAIL_IMAP_USER=your-email@example.com
NBER_EMAIL_IMAP_PASSWORD=你的三方客户端安全密码
NBER_EMAIL_IMAP_MAILBOX=INBOX
NBER_EMAIL_IMAP_LOOKBACK=100
NBER_SOURCE=auto
KIMI_API_KEY=你的 Kimi API key
KIMI_MODEL=moonshot-v1-8k
```

`.gitignore` 已经忽略 `.env` 和 `.env.*`，但允许提交 `.env.example`。

## 更新论文数据

推荐先 dry run，确认来源和解析都正常：

```powershell
python scripts/update_papers.py --dry-run
```

强制从邮箱源读取：

```powershell
python scripts/update_papers.py --source email --dry-run
```

强制使用 NBER API：

```powershell
python scripts/update_papers.py --source api --dry-run
```

真实更新数据文件：

```powershell
python scripts/update_papers.py
```

如果要求必须配置 Kimi API key：

```powershell
python scripts/update_papers.py --require-api-key
```

只审计当前译文，不抓取论文、不调用 Kimi：

```powershell
python scripts/update_papers.py --audit-translations
```

审计报告默认写入 `src/data/translation-audit.md`。如果只想在终端查看：

```powershell
python scripts/update_papers.py --audit-translations --audit-output -
```

## 邮箱源

默认 `NBER_SOURCE=auto`，流程是：

1. 通过 IMAP SSL 登录邮箱。
2. 只读选择 `INBOX`。
3. 在最近的邮件中寻找 NBER 相关邮件。
4. 解析正文中的 `/papers/wxxxxx` 链接。
5. 同时支持转发正文和 `.eml` 附件转发。
6. 用链接访问 NBER 详情页，补齐标题、作者和摘要。
7. 邮箱源失败时回退 NBER API。

邮箱读取使用 `BODY.PEEK` 和只读 mailbox，不会标记已读、删除邮件或修改邮箱状态。

测试 IMAP 登录：

```powershell
python scripts/update_papers.py --test-email-login
```

成功时会输出：

```text
IMAP SSL connection successful
IMAP login successful
INBOX message count: ...
```

## GitHub Actions

主要 workflow 是 `.github/workflows/update-papers.yml`。

触发方式：

- 手动触发：`workflow_dispatch`
- 自动触发：每周一北京时间 13:00 和 18:00

GitHub cron 使用 UTC，因此配置为：

```yaml
- cron: "0 5 * * 1"
- cron: "0 10 * * 1"
```

更新 workflow 会：

1. 安装 Python 依赖。
2. 运行 `python scripts/update_papers.py --require-api-key`。
3. 生成 `src/data/translation-audit.md` 翻译审计报告。
4. 如果 `src/data` 有变化，自动提交数据文件和审计报告。
5. 上传 `translation-audit` artifact，方便在 Actions 页面下载。
6. 安装 Node 依赖。
7. 构建 Astro 站点。
8. 部署到 GitHub Pages。

普通 push 到 `main` 会触发 `.github/workflows/deploy.yml`，只构建并部署当前数据。

## GitHub Secrets

在 GitHub 仓库中进入：

```text
Settings -> Secrets and variables -> Actions -> New repository secret
```

需要配置：

```text
KIMI_API_KEY
NBER_EMAIL_IMAP_HOST
NBER_EMAIL_IMAP_PORT
NBER_EMAIL_IMAP_USER
NBER_EMAIL_IMAP_PASSWORD
```

示例配置：

```text
NBER_EMAIL_IMAP_HOST = 你的 IMAP 服务器地址
NBER_EMAIL_IMAP_PORT = 993
NBER_EMAIL_IMAP_USER = your-email@example.com
```

如果使用阿里企业邮箱，`NBER_EMAIL_IMAP_HOST` 通常是 `imap.qiye.aliyun.com`。`NBER_EMAIL_IMAP_PASSWORD` 使用邮箱服务商生成的三方客户端安全密码，不要使用明文写入仓库。

## 数据文件

主要数据位于 `src/data/`：

- `papers.json`：当前展示的最新批次论文。
- `update-meta.json`：最近一次更新时间、来源、批次日期和备注。
- `archive.json`：历史批次归档。
- `translation-cache.json`：翻译缓存，避免重复调用 Kimi。
- `translation-audit.md`：自动生成的翻译审计报告，列出疑似错译、术语表未命中项和需要人工复核的英文片段。

## 常见排错

如果 IMAP 登录失败：

- 确认阿里邮箱后台已允许该账号使用三方客户端。
- 确认使用的是客户端安全密码，而不是网页登录密码。
- 确认 host 和端口与邮箱服务商的 IMAP SSL 设置一致；阿里企业邮箱通常使用 `imap.qiye.aliyun.com` 和 `993`。
- 本地先运行 `python scripts/update_papers.py --test-email-login`。

如果邮箱里没有解析出论文：

- 确认 NBER 邮件已经转发或投递到 `INBOX`。
- 直接转发原始邮件正文即可；`.eml` 附件转发也支持。
- 默认只检查最近 100 封邮件，可通过 `NBER_EMAIL_IMAP_LOOKBACK` 调整。

如果 Kimi 翻译失败：

- 检查 `KIMI_API_KEY` 是否配置。
- 脚本会保留英文原文，并在 `translation_status` 中记录失败或跳过状态。

## 翻译质量

翻译质量采用“术语表 + 确定性后处理 + 审计报告”的长期维护方式。

核心文件是 `scripts/translation_glossary.json`：

- `prompt_terms`：写入 Kimi system prompt，要求模型优先使用这些经济学译法。
- `replacement_rules`：已知高频错译的确定性修正规则；缓存命中时也会执行。
- `global_cleanup`：清理重复词、叠词等机械错误。
- `audit.suspect_translations`：审计报告中高亮的疑似错译。
- `audit.source_terms`：当英文原文出现某个术语、中文译文没有出现推荐译法时，列入人工复核。
- `audit.allowed_english_terms`：允许保留的英文缩写或专名。

维护流程：

1. 每周自动更新论文和译文。
2. 脚本生成 `src/data/translation-audit.md`。
3. 人工优先检查审计报告里的 `High-Priority Suspect Terms` 和 `Preferred-Term Misses`。
4. 如果发现通用错译，把术语加入 `scripts/translation_glossary.json`。
5. 如果只是需要关注但不能确定替换，先加入 `audit` 区域，不直接改译文。
6. 修改术语表后，脚本会根据术语表内容生成新的 `translation_prompt_version` 指纹，下一次更新会重新翻译或规范化缓存译文。

代表性约束包括：`benefit-based taxation` -> “基于受益原则的税收”、`labor market` -> “劳动力市场”、`Digital Safe Havens` -> “数字避风港”、`Quantitative Easing` -> “量化宽松”、`QSBS Program` -> “合格小企业股票（QSBS）计划”。完整约束以 `scripts/translation_glossary.json` 为准。

## 免责声明

论文内容来自 NBER。中文标题和中文摘要由 Kimi API 自动生成，仅供快速浏览参考；正式引用、研究判断和学术表达请以 NBER 原文为准。

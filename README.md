# 本周 NBER 工作论文

这是一个静态网页项目，用于每周抓取 NBER Working Papers，提取论文标题、作者和摘要，并通过 Kimi API 生成中文翻译，最终以 Astro 静态站点展示。

网站链接：`https://fyapeng.github.io/nber/`

## 本地开发

```powershell
npm install
npm run dev
npm run build
```

## 手动更新论文数据

更新脚本会把最新批次写入 `src/data/papers.json`，并维护 `src/data/update-meta.json`、`src/data/archive.json` 和 `src/data/translation-cache.json`。

```powershell
python scripts/update_papers.py --dry-run
python scripts/update_papers.py
```

如果本机没有配置 `KIMI_API_KEY`，脚本不会写入假的中文翻译；缺失翻译会保留英文内容，并在结构化字段中标记状态。

## GitHub Secrets

在仓库的 GitHub Actions Secrets 中配置：

```text
KIMI_API_KEY
```

定时更新 workflow 会从该 secret 读取 Kimi API key，不要把密钥写入仓库。

## 数据来源

论文列表和详情来自 [NBER Working Papers](https://www.nber.org/papers)。脚本优先使用 NBER 列表 API 中的 `newthisweek` 标记；如果该标记不可用，则回退到最新日期批次。

## 免责声明

内容来自 NBER。中文标题和摘要由 Kimi API 自动生成，仅供快速浏览参考；正式引用和研究判断请以 NBER 原文为准。

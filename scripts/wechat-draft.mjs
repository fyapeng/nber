import fs from "node:fs/promises";
import path from "node:path";
import process from "node:process";

const root = process.cwd();
const args = new Set(process.argv.slice(2));
const dryRun = args.has("--dry-run");
const issueArg = [...args].find((arg) => arg.startsWith("--issue="));
const issueNumber = Math.max(1, Number(issueArg?.split("=")[1] || 1));
const updateArg = [...args].find((arg) => arg.startsWith("--update="));
const updateMediaId = updateArg?.slice("--update=".length) || "";

const parseEnv = (text) => Object.fromEntries(
  text.split(/\r?\n/)
    .map((line) => line.trim())
    .filter((line) => line && !line.startsWith("#") && line.includes("="))
    .map((line) => {
      const index = line.indexOf("=");
      return [line.slice(0, index).trim(), line.slice(index + 1).trim().replace(/^['"]|['"]$/g, "")];
    }),
);

const env = parseEnv(await fs.readFile(path.join(root, ".env"), "utf8"));
const wechatAuthor = env.WECHAT_AUTHOR || "YAPO";
const wechatSourceUrl = env.WECHAT_SOURCE_URL || "https://fyapeng.com/nber/";
const wechatDigest = env.WECHAT_DIGEST || "\u200B";
const wechatOpenComment = env.WECHAT_OPEN_COMMENT === "0" ? 0 : 1;
const wechatOnlyFansCanComment = env.WECHAT_ONLY_FANS_CAN_COMMENT === "1" ? 1 : 0;
const papers = JSON.parse(await fs.readFile(path.join(root, "src/data/papers.json"), "utf8"));
const meta = JSON.parse(await fs.readFile(path.join(root, "src/data/update-meta.json"), "utf8"));
const outputDir = path.join(root, "output");
const cachePath = path.join(outputDir, "wechat-assets.json");
await fs.mkdir(outputDir, { recursive: true });

const FIELD_RULES = [
  ["劳动与教育", ["labor", "labour", "employment", "worker", "wage", "occupation", "school", "student", "college", "teacher", "education", "training", "劳动", "就业", "工人", "工资", "职业", "学校", "学生", "大学", "教师", "教育", "培训"]],
  ["宏观与货币", ["inflation", "monetary", "central bank", "business cycle", "recession", "macroeconomic", "aggregate", "interest rate", "quantitative easing", "通货膨胀", "货币", "中央银行", "商业周期", "衰退", "宏观", "总需求", "利率", "量化宽松"]],
  ["公共财政与政治经济", ["tax", "taxation", "government", "public spending", "social security", "regulation", "political", "election", "voting", "democracy", "税", "税收", "政府", "公共支出", "社会保障", "监管", "政治", "选举", "投票", "民主"]],
  ["金融与资产定价", ["asset pricing", "stock", "bond", "bank", "banking", "credit", "finance", "financial", "investor", "portfolio", "capital market", "资产定价", "股票", "债券", "银行", "信贷", "金融", "投资者", "投资组合", "资本市场"]],
  ["产业组织与企业", ["market power", "competition", "pricing", "merger", "firm", "productivity", "innovation", "patent", "entrepreneur", "supply chain", "市场势力", "竞争", "定价", "并购", "企业", "生产率", "创新", "专利", "创业", "供应链"]],
  ["国际贸易与发展", ["international trade", "trade", "export", "import", "tariff", "exchange rate", "foreign", "migration", "immigration", "developing countries", "贸易", "出口", "进口", "关税", "汇率", "外国", "移民", "发展中国家"]],
  ["医疗与健康", ["health", "hospital", "medical", "medicine", "mortality", "disease", "patient", "drug", "physician", "insurance", "健康", "医院", "医疗", "死亡率", "疾病", "患者", "药物", "医生", "保险"]],
  ["环境、能源与城市", ["climate", "environment", "pollution", "carbon", "energy", "electricity", "transportation", "housing", "urban", "city", "环境", "污染", "碳", "能源", "电力", "交通", "住房", "城市"]],
  ["数字经济与人工智能", ["artificial intelligence", "machine learning", "chatbot", "algorithm", "digital", "online platform", "social media", "人工智能", "机器学习", "聊天机器人", "算法", "数字", "在线平台", "社交媒体"]],
  ["经济史、文化与制度", ["economic history", "historical", "history", "culture", "religion", "slavery", "institution", "colonial", "经济史", "历史", "文化", "宗教", "奴隶制", "制度", "殖民"]],
];

const classify = (paper) => {
  const title = `${paper.title || ""} ${paper.title_cn || ""}`.toLowerCase();
  const full = `${title} ${paper.abstract || ""} ${paper.abstract_cn || ""}`.toLowerCase();
  let best = "其他经济学主题";
  let bestScore = 0;
  for (const [label, keywords] of FIELD_RULES) {
    let score = 0;
    for (const keyword of keywords) {
      const word = keyword.toLowerCase();
      if (title.includes(word)) score += 4;
      else if (full.includes(word)) score += 1;
    }
    if (score > bestScore) {
      best = label;
      bestScore = score;
    }
  }
  return best;
};

const grouped = new Map();
for (const paper of papers) {
  const label = classify(paper);
  grouped.set(label, [...(grouped.get(label) || []), paper]);
}
const groups = [...grouped.entries()]
  .map(([label, items]) => ({ label, items }))
  .sort((a, b) => b.items.length - a.items.length || a.label.localeCompare(b.label, "zh-CN"));
const desiredCount = Math.min(3, papers.length);
const idealSize = Math.ceil(papers.length / desiredCount);
const assignable = groups.flatMap((group) => {
  if (group.items.length <= Math.ceil(idealSize * 1.25)) return [group];
  const chunks = [];
  for (let start = 0; start < group.items.length; start += idealSize) {
    chunks.push({ label: group.label, items: group.items.slice(start, start + idealSize) });
  }
  return chunks;
}).sort((a, b) => b.items.length - a.items.length || a.label.localeCompare(b.label, "zh-CN"));
const issues = Array.from({ length: desiredCount }, () => []);
const sizes = Array.from({ length: desiredCount }, () => 0);
for (const group of assignable) {
  let target = 0;
  for (let index = 1; index < sizes.length; index += 1) if (sizes[index] < sizes[target]) target = index;
  issues[target].push(group);
  sizes[target] += group.items.length;
}

const escapeHtml = (value = "") => String(value)
  .replaceAll("&", "&amp;")
  .replaceAll("<", "&lt;")
  .replaceAll(">", "&gt;")
  .replaceAll('"', "&quot;")
  .replaceAll("'", "&#39;");
const accent = "#0b1015";
const styles = {
  container: "max-width:677px;margin:0 auto;padding:24px 4px 40px;background:#fff;color:#252927;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI','Microsoft YaHei','PingFang SC',sans-serif;font-size:14px;line-height:1.7;word-break:break-word;",
  h1: `display:table;max-width:100%;box-sizing:border-box;margin:0 auto 28px;padding:0 2px 10px;border:0;border-bottom:2px solid ${accent};color:#202523;font-size:20px;line-height:1.45;font-weight:700;letter-spacing:.02em;text-align:center;white-space:normal;overflow-wrap:break-word;`,
  h2: `display:table;max-width:calc(100% - 28px);box-sizing:border-box;margin:34px auto 18px;padding:7px 14px;border:0;background:${accent};color:#f2f0ea;font-size:17px;line-height:1.5;font-weight:700;text-align:center;white-space:normal;overflow-wrap:break-word;border-radius:7px;`,
  h3: `margin:28px 0 14px;padding:7px 11px;border:0;border-left:4px solid ${accent};background:#f3f5f4;color:#202523;font-size:15px;line-height:1.6;font-weight:700;border-radius:2px;`,
  p: "margin:1em 0;color:#303633;font-size:14px;line-height:1.75;text-align:justify;text-justify:inter-ideograph;letter-spacing:.01em;",
  note: "margin:14px 0 22px;padding:10px 12px;border-left:3px solid #0b1015;background:#f3f1ec;color:#555b57;font-size:12px;line-height:1.65;text-align:left;",
  table: "width:90%;max-width:560px;margin:16px auto 24px;border-collapse:collapse;border-spacing:0;table-layout:auto;font-size:13px;line-height:1.55;",
  th: `padding:8px 6px;border:0;border-bottom:2px solid ${accent};background:transparent;color:${accent};font-size:13px;line-height:1.5;text-align:left;font-weight:700;`,
  td: "padding:8px 6px;border:0;border-bottom:1px solid #e2e5e3;color:#303633;font-size:13px;line-height:1.55;text-align:left;vertical-align:top;",
  en: "margin:8px 0 20px;padding:12px 14px;background:#f6f7f6;color:#59615e;font-family:Georgia,'Times New Roman',serif;font-size:13px;line-height:1.7;text-align:justify;",
  disclaimer: "margin:24px 0 10px;color:#737975;font-size:12px;line-height:1.65;text-align:left;",
  image: "display:block;width:100%;max-width:677px;height:auto;margin:28px auto 0;border:0;",
};

const p = (text, extra = "") => `<p style="${styles.p}${extra}">${text}</p>`;
const distributionRows = [...grouped.entries()]
  .sort((a, b) => b[1].length - a[1].length)
  .map(([label, items]) => `<tr><td style="${styles.td}">${escapeHtml(label)}</td><td style="${styles.td}text-align:right;">${items.length}</td></tr>`)
  .join("");
const distribution = `<table style="${styles.table}"><thead><tr><th style="${styles.th}">研究领域</th><th style="${styles.th}text-align:right;">论文数量</th></tr></thead><tbody>${distributionRows}</tbody></table>`;

const buildArticle = (issueGroups, imageUrl) => {
  const topics = issueGroups.map((group) => group.label);
  const shortTopics = topics.length > 2 ? `${topics.slice(0, 2).join("、")}等主题` : topics.join("、");
  const issuePapers = issueGroups.flatMap((group) => group.items);
  const date = meta.batch_date || papers[0]?.public_date || new Date().toISOString().slice(0, 10);
  let number = 0;
  const sections = issueGroups.map((group) => {
    const blocks = group.items.map((paper) => {
      number += 1;
      return `<h3 style="${styles.h3}">${number}. ${escapeHtml(paper.title_cn || paper.title || paper.id)}</h3>`
        + p(`<strong>NBER 编号：</strong> ${escapeHtml(paper.id || "未提供")}`)
        + p(`<strong>英文标题：</strong> ${escapeHtml(paper.title || "")}`)
        + p(`<strong>作者：</strong> ${escapeHtml((paper.authors || []).join("、"))}`)
        + p(escapeHtml(paper.abstract_cn || "中文摘要尚未生成。"))
        + p("<strong>英文摘要：</strong>")
        + `<p style="${styles.en}">${escapeHtml(paper.abstract || "English abstract is not available.")}</p>`;
    }).join("");
    return `<h2 style="${styles.h2}">${escapeHtml(group.label)}（${group.items.length} 篇）</h2>${blocks}`;
  }).join("");
  const content = `<section style="${styles.container}">`
    + `<h1 style="${styles.h1}">NBER Weekly</h1>`
    + p("NBER（美国国家经济研究局）的 Working Papers 系列持续发布经济学领域的工作论文，覆盖宏观、劳动、金融、公共经济学等多个方向。")
    + p(`${escapeHtml(date)} 这一批次共收录 ${papers.length} 篇论文，本期推送“${escapeHtml(topics.join("、"))}”主题，共 ${issuePapers.length} 篇。`)
    + `<p style="${styles.note}">本文基础材料由 <strong>NBER Weekly</strong> 自动化项目生成。项目网页：fyapeng.com/nber</p>`
    + `<h2 style="${styles.h2}">本周领域分布</h2>${distribution}${sections}`
    + `<p style="${styles.disclaimer}"><em>论文信息来自 NBER；中文标题与摘要由 AI 辅助翻译，仅供快速浏览。正式引用与研究判断请以英文原文为准。可通过 NBER 编号或论文标题检索原文。</em></p>`
    + (imageUrl ? `<img src="${escapeHtml(imageUrl)}" style="${styles.image}" alt="申椿公众号二维码名片">` : "")
    + `</section>`;
  return { title: `NBER︱本周工作论文：${shortTopics}`, content, topics, count: issuePapers.length };
};

const selectedGroups = issues[issueNumber - 1];
if (!selectedGroups) throw new Error(`分期不存在：${issueNumber}，当前共有 ${issues.length} 期`);
const previewArticle = buildArticle(selectedGroups, "");
await fs.writeFile(path.join(outputDir, `wechat-issue-${issueNumber}-preview.html`), `<!doctype html><meta charset="utf-8">${previewArticle.content}`, "utf8");
console.log(JSON.stringify({ issue: issueNumber, totalIssues: issues.length, sizes, title: previewArticle.title, papers: previewArticle.count, htmlCharacters: previewArticle.content.length, htmlBytes: Buffer.byteLength(previewArticle.content) }, null, 2));
if (dryRun) process.exit(0);

if (!env.WECHAT_APP_ID || !env.WECHAT_APP_SECRET) throw new Error(".env 缺少 WECHAT_APP_ID 或 WECHAT_APP_SECRET");
const assertApi = async (response, action) => {
  const data = await response.json();
  if (!response.ok || (data.errcode && data.errcode !== 0)) throw new Error(`${action}失败：${data.errcode || response.status} ${data.errmsg || response.statusText}`);
  return data;
};
const tokenData = await assertApi(await fetch(`https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid=${encodeURIComponent(env.WECHAT_APP_ID)}&secret=${encodeURIComponent(env.WECHAT_APP_SECRET)}`), "获取 access_token");
const token = tokenData.access_token;

let assetCache = {};
try { assetCache = JSON.parse(await fs.readFile(cachePath, "utf8")); } catch {}
const upload = async (endpoint, filePath, action) => {
  const bytes = await fs.readFile(filePath);
  const form = new FormData();
  form.append("media", new Blob([bytes], { type: "image/png" }), path.basename(filePath));
  return assertApi(await fetch(`${endpoint}${endpoint.includes("?") ? "&" : "?"}access_token=${encodeURIComponent(token)}`, { method: "POST", body: form }), action);
};

if (!assetCache.coverMediaId) {
  const cover = await upload("https://api.weixin.qq.com/cgi-bin/material/add_material?type=image", path.join(root, "public/brand/sencium-nber-weekly-cover-v3.png"), "上传封面素材");
  assetCache.coverMediaId = cover.media_id;
}
if (!assetCache.namecardMobileV3Url) {
  const namecard = await upload("https://api.weixin.qq.com/cgi-bin/media/uploadimg", path.join(root, "public/brand/sencium-wechat-namecard-mobile-v3.png"), "上传移动端正文名片");
  assetCache.namecardMobileV3Url = namecard.url;
}
await fs.writeFile(cachePath, JSON.stringify(assetCache, null, 2), "utf8");

const article = buildArticle(selectedGroups, assetCache.namecardMobileV3Url);
const articlePayload = {
  article_type: "news",
  title: article.title,
  author: wechatAuthor,
  digest: wechatDigest,
  content: article.content,
  content_source_url: wechatSourceUrl,
  thumb_media_id: assetCache.coverMediaId,
  show_cover_pic: 0,
  need_open_comment: wechatOpenComment,
  only_fans_can_comment: wechatOnlyFansCanComment,
};
const endpoint = updateMediaId ? "update" : "add";
const payload = updateMediaId
  ? { media_id: updateMediaId, index: 0, articles: articlePayload }
  : { articles: [articlePayload] };
const draft = await assertApi(await fetch(`https://api.weixin.qq.com/cgi-bin/draft/${endpoint}?access_token=${encodeURIComponent(token)}`, {
  method: "POST",
  headers: { "Content-Type": "application/json; charset=utf-8" },
  body: JSON.stringify(payload),
}), updateMediaId ? "更新草稿" : "新增草稿");
const result = { createdAt: new Date().toISOString(), issue: issueNumber, title: article.title, papers: article.count, draftMediaId: draft.media_id || updateMediaId, action: updateMediaId ? "updated" : "created" };
await fs.writeFile(path.join(outputDir, `wechat-draft-issue-${issueNumber}.json`), JSON.stringify(result, null, 2), "utf8");
console.log(JSON.stringify(result, null, 2));

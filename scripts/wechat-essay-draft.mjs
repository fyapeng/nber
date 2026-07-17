import crypto from "node:crypto";
import fs from "node:fs/promises";
import path from "node:path";
import process from "node:process";
import { spawnSync } from "node:child_process";
import { marked } from "marked";

const root = process.cwd();
const argv = process.argv.slice(2);
const valueArg = (name, fallback = "") => argv.find((arg) => arg.startsWith(`${name}=`))?.slice(name.length + 1) || fallback;
const dryRun = argv.includes("--dry-run");
const inputPath = path.resolve(valueArg("--input"));
const coverPath = path.resolve(valueArg("--cover"));
const updateMediaId = valueArg("--update");
if (!valueArg("--input") || !valueArg("--cover")) {
  throw new Error("用法：node scripts/wechat-essay-draft.mjs --input=文章.md --cover=封面.jpg [--dry-run]");
}

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
const outputDir = path.join(root, "output");
const formulaDir = path.join(outputDir, "wechat-optimal-transport-formulas");
const cachePath = path.join(outputDir, "wechat-essay-assets.json");
await fs.mkdir(formulaDir, { recursive: true });

const source = await fs.readFile(inputPath, "utf8");
const frontmatterMatch = source.match(/^---\r?\n([\s\S]*?)\r?\n---\r?\n/);
const frontmatter = frontmatterMatch?.[1] || "";
const field = (name) => frontmatter.match(new RegExp(`^${name}:\\s*["']?(.*?)["']?\\s*$`, "m"))?.[1] || "";
const title = valueArg("--title", field("title") || "经济学中的最优运输");
const digest = valueArg("--digest", "从配置与对偶出发，介绍最优运输的数学结构、计算方法及其在经济学中的应用。");
const sourceUrl = valueArg("--source-url", "https://fyapeng.com/essays/optimal-transport-in-economics/");
let markdown = source.slice(frontmatterMatch?.[0].length || 0);

const formulas = [];
markdown = markdown.replace(/\$\$([\s\S]*?)\$\$/g, (_, formula) => {
  const index = formulas.push(formula.trim()) - 1;
  return `\n<div data-wechat-formula="${index}"></div>\n`;
});

const inlineSymbols = new Map([
  ["\\mu", "μ"], ["\\nu", "ν"], ["\\pi", "π"], ["\\varphi", "φ"], ["\\phi", "φ"],
  ["\\psi", "ψ"], ["\\theta", "θ"], ["\\varepsilon", "ε"], ["\\rho", "ρ"],
  ["\\Sigma", "Σ"], ["\\tau", "τ"], ["\\ell", "ℓ"], ["\\in", "∈"],
  ["\\ge", "≥"], ["\\le", "≤"], ["\\ne", "≠"], ["\\times", "×"], ["\\to", "→"],
  ["\\infty", "∞"], ["\\partial", "∂"], ["\\nabla", "∇"], ["\\mathbb E", "E"],
]);
const inlineMath = (raw) => {
  let text = raw;
  for (const [from, to] of inlineSymbols) text = text.replaceAll(from, to);
  text = text
    .replace(/\\operatorname\{([^}]+)\}/g, "$1")
    .replace(/\\mathcal\{([^}]+)\}/g, "$1")
    .replace(/\\mathbb\{([^}]+)\}/g, "$1")
    .replace(/\\#|\\,/g, "")
    .replace(/\\([A-Za-z]+)/g, "$1")
    .replace(/[{}]/g, "")
    .replace(/\s+/g, " ")
    .trim();
  return `<span style="font-family:Georgia,'Times New Roman',serif;color:#252927;white-space:nowrap;">${text}</span>`;
};
markdown = markdown.replace(/\$([^$\n]+?)\$/g, (_, formula) => inlineMath(formula));

const texEscape = (formula) => formula.replaceAll("\\#", "\\#");
const tex = String.raw`\documentclass{article}
\usepackage[active,tightpage]{preview}
\usepackage{amsmath,amssymb,mathtools}
\usepackage{xeCJK}
\setCJKmainfont{Microsoft YaHei}
\setlength\PreviewBorder{10pt}
\begin{document}
${formulas.map((formula) => String.raw`\begin{preview}
\[
${texEscape(formula)}
\]
\end{preview}`).join("\n")}
\end{document}
`;
const texPath = path.join(formulaDir, "formulas.tex");
await fs.writeFile(texPath, tex, "utf8");
for (const name of await fs.readdir(formulaDir)) {
  if (/^formula-\d+\.png$/.test(name)) await fs.unlink(path.join(formulaDir, name));
}
const pdflatex = spawnSync("xelatex.exe", ["-interaction=nonstopmode", "-halt-on-error", `-output-directory=${formulaDir}`, texPath], { encoding: "utf8" });
if (pdflatex.status !== 0) throw new Error(`公式编译失败：\n${pdflatex.stdout}\n${pdflatex.stderr}`);
const pdfPath = path.join(formulaDir, "formulas.pdf");
const cairo = spawnSync("pdftocairo.exe", ["-png", "-r", "180", pdfPath, path.join(formulaDir, "formula")], { encoding: "utf8" });
if (cairo.status !== 0) throw new Error(`公式转图片失败：\n${cairo.stdout}\n${cairo.stderr}`);
const formulaFiles = (await fs.readdir(formulaDir))
  .filter((name) => /^formula-\d+\.png$/.test(name))
  .sort((a, b) => Number(a.match(/\d+/)?.[0]) - Number(b.match(/\d+/)?.[0]))
  .map((name) => path.join(formulaDir, name));
if (formulaFiles.length !== formulas.length) {
  throw new Error(`公式页数不一致：解析 ${formulas.length} 个，渲染 ${formulaFiles.length} 个`);
}

marked.setOptions({ gfm: true, breaks: false });
let html = marked.parse(markdown, { async: false });
html = html
  .replace(/<a\b[^>]*>([\s\S]*?)<\/a>/g, "$1")
  .replace(/<p>\s*https?:\/\/[^<\s]+\s*<\/p>/g, "")
  .replace(/<hr\s*\/?>/g, "")
  .replace(/<h1>[\s\S]*?<\/h1>/, "");

const accent = "#0b1015";
const styles = {
  container: "max-width:677px;margin:0 auto;padding:18px 4px 36px;background:#fff;color:#252927;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI','Microsoft YaHei','PingFang SC',sans-serif;font-size:15px;line-height:1.8;word-break:break-word;",
  h2: `display:table;max-width:calc(100% - 20px);box-sizing:border-box;margin:34px auto 18px;padding:7px 14px;background:${accent};color:#f2f0ea;font-size:18px;line-height:1.5;font-weight:700;text-align:center;border-radius:7px;`,
  h3: `margin:26px 0 12px;padding:6px 10px;border-left:4px solid ${accent};background:#f3f5f4;color:#202523;font-size:16px;line-height:1.6;font-weight:700;`,
  p: "margin:1em 0;color:#303633;font-size:15px;line-height:1.85;text-align:justify;letter-spacing:.01em;",
  blockquote: "margin:16px 0 22px;padding:10px 14px;border-left:3px solid #0b1015;background:#f3f1ec;color:#555b57;font-size:14px;line-height:1.75;",
  list: "margin:10px 0 18px;padding-left:1.5em;color:#303633;font-size:15px;line-height:1.8;",
  table: "width:100%;margin:16px auto 24px;border-collapse:collapse;font-size:13px;line-height:1.55;",
  th: `padding:8px 6px;border-bottom:2px solid ${accent};color:${accent};text-align:left;font-weight:700;`,
  td: "padding:8px 6px;border-bottom:1px solid #e2e5e3;color:#303633;text-align:left;vertical-align:top;",
  formula: "display:block;max-width:100%;height:auto;margin:18px auto 22px;border:0;",
  note: "margin:10px 0 24px;padding:10px 12px;border-left:3px solid #0b1015;background:#f3f1ec;color:#555b57;font-size:13px;line-height:1.7;",
  namecard: "display:block;width:100%;max-width:677px;height:auto;margin:30px auto 0;border:0;",
};
html = html
  .replace(/<h2(\s[^>]*)?>/g, `<h2 style="${styles.h2}">`)
  .replace(/<h3(\s[^>]*)?>/g, `<h3 style="${styles.h3}">`)
  .replace(/<p(\s[^>]*)?>/g, `<p style="${styles.p}">`)
  .replace(/<blockquote(\s[^>]*)?>/g, `<blockquote style="${styles.blockquote}">`)
  .replace(/<(ul|ol)(\s[^>]*)?>/g, `<$1 style="${styles.list}">`)
  .replace(/<table(\s[^>]*)?>/g, `<table style="${styles.table}">`)
  .replace(/<th(\s[^>]*)?>/g, `<th style="${styles.th}">`)
  .replace(/<td(\s[^>]*)?>/g, `<td style="${styles.td}">`);

const assertApi = async (response, action) => {
  const data = await response.json();
  if (!response.ok || (data.errcode && data.errcode !== 0)) {
    throw new Error(`${action}失败：${data.errcode || response.status} ${data.errmsg || response.statusText}`);
  }
  return data;
};
let cache = {};
try { cache = JSON.parse(await fs.readFile(cachePath, "utf8")); } catch {}
cache.formulas ||= {};
const fileHash = async (filePath) => crypto.createHash("sha256").update(await fs.readFile(filePath)).digest("hex");
const mimeFor = (filePath) => path.extname(filePath).toLowerCase() === ".png" ? "image/png" : "image/jpeg";
const upload = async (endpoint, filePath, token, action) => {
  const bytes = await fs.readFile(filePath);
  const form = new FormData();
  form.append("media", new Blob([bytes], { type: mimeFor(filePath) }), path.basename(filePath));
  return assertApi(await fetch(`${endpoint}${endpoint.includes("?") ? "&" : "?"}access_token=${encodeURIComponent(token)}`, { method: "POST", body: form }), action);
};

let token = "";
if (!dryRun) {
  if (!env.WECHAT_APP_ID || !env.WECHAT_APP_SECRET) throw new Error(".env 缺少 WECHAT_APP_ID 或 WECHAT_APP_SECRET");
  const tokenData = await assertApi(await fetch(`https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid=${encodeURIComponent(env.WECHAT_APP_ID)}&secret=${encodeURIComponent(env.WECHAT_APP_SECRET)}`), "获取 access_token");
  token = tokenData.access_token;
}

const formulaUrls = [];
for (let index = 0; index < formulaFiles.length; index += 1) {
  const filePath = formulaFiles[index];
  const hash = await fileHash(filePath);
  if (!dryRun && !cache.formulas[hash]) {
    const uploaded = await upload("https://api.weixin.qq.com/cgi-bin/media/uploadimg", filePath, token, `上传公式 ${index + 1}`);
    cache.formulas[hash] = uploaded.url;
  }
  formulaUrls.push(dryRun ? `wechat-optimal-transport-formulas/${path.basename(filePath)}` : cache.formulas[hash]);
}
html = html.replace(/<div data-wechat-formula="(\d+)"><\/div>/g, (_, index) => `<img src="${formulaUrls[Number(index)]}" style="${styles.formula}" alt="公式">`);

let coverMediaId = cache.coverMediaId || "";
let namecardUrl = cache.namecardUrl || "";
if (!dryRun) {
  const coverHash = await fileHash(coverPath);
  if (!coverMediaId || cache.coverHash !== coverHash) {
    const uploaded = await upload("https://api.weixin.qq.com/cgi-bin/material/add_material?type=image", coverPath, token, "上传文章封面");
    coverMediaId = uploaded.media_id;
    cache.coverMediaId = coverMediaId;
    cache.coverHash = coverHash;
  }
  if (!namecardUrl) {
    const uploaded = await upload("https://api.weixin.qq.com/cgi-bin/media/uploadimg", path.join(root, "public/brand/sencium-wechat-namecard-mobile-v3.png"), token, "上传公众号名片");
    namecardUrl = uploaded.url;
    cache.namecardUrl = namecardUrl;
  }
  await fs.writeFile(cachePath, JSON.stringify(cache, null, 2), "utf8");
}

const note = `<p style="${styles.note}">公众号版不保留正文外部超链接。完整参考资料、可复制公式与后续修订见文末“阅读原文”。</p>`;
const namecard = namecardUrl ? `<img src="${namecardUrl}" style="${styles.namecard}" alt="申椿公众号二维码名片">` : "";
const content = `<section style="${styles.container}">${note}${html}${namecard}</section>`;
const previewPath = path.join(outputDir, "wechat-optimal-transport-preview.html");
await fs.writeFile(previewPath, `<!doctype html><meta charset="utf-8"><title>${title}</title>${content}`, "utf8");
console.log(JSON.stringify({ title, formulas: formulas.length, htmlCharacters: content.length, htmlBytes: Buffer.byteLength(content), previewPath, dryRun }, null, 2));
if (dryRun) process.exit(0);

const article = {
  article_type: "news",
  title,
  author: valueArg("--author", "付亚鹏"),
  digest,
  content,
  content_source_url: sourceUrl,
  thumb_media_id: coverMediaId,
  show_cover_pic: 1,
  need_open_comment: env.WECHAT_OPEN_COMMENT === "0" ? 0 : 1,
  only_fans_can_comment: env.WECHAT_ONLY_FANS_CAN_COMMENT === "1" ? 1 : 0,
};
const endpoint = updateMediaId ? "update" : "add";
const payload = updateMediaId ? { media_id: updateMediaId, index: 0, articles: article } : { articles: [article] };
const draft = await assertApi(await fetch(`https://api.weixin.qq.com/cgi-bin/draft/${endpoint}?access_token=${encodeURIComponent(token)}`, {
  method: "POST",
  headers: { "Content-Type": "application/json; charset=utf-8" },
  body: JSON.stringify(payload),
}), updateMediaId ? "更新草稿" : "新增草稿");
const result = { createdAt: new Date().toISOString(), title, draftMediaId: draft.media_id || updateMediaId, action: updateMediaId ? "updated" : "created", previewPath };
await fs.writeFile(path.join(outputDir, "wechat-optimal-transport-draft.json"), JSON.stringify(result, null, 2), "utf8");
console.log(JSON.stringify(result, null, 2));

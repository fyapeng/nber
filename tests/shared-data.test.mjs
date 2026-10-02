import assert from 'node:assert/strict';
import { test } from 'node:test';
import fs from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import vm from 'node:vm';
import { execFileSync } from 'node:child_process';
import { transform } from 'esbuild';

const root = process.cwd();
const papers = JSON.parse(await fs.readFile('src/data/papers.json', 'utf8'));
const meta = JSON.parse(await fs.readFile('src/data/update-meta.json', 'utf8'));
const expected = papers.map(p => p.id).sort();
const editor = await fs.readFile('src/pages/wechat-editor.astro', 'utf8');
// Exercise the actual pure functions inside the existing Astro script, without
// a browser/network or duplicating the publication grouping implementation.
const start = editor.indexOf('  const escapeMarkdown =');
const end = editor.indexOf('  const activateIssue =');
assert.ok(start > 0 && end > start);
const { code } = await transform(editor.slice(start, end) + '\nglobalThis.buildIssues = buildPublicationIssues;', { loader: 'ts' });
const context = vm.createContext({});
vm.runInContext(code, context);

test('site build renders every paper from the shared JSON exactly once', async () => {
  const page = await fs.readFile('dist/index.html', 'utf8');
  assert.equal((page.match(/class="paper-card"/g) || []).length, papers.length);
  const ids = [...page.matchAll(/class="paper-meta"[^>]*>[^<]*· (w\d+)/g)].map(match => match[1]).sort();
  assert.deepEqual(ids, expected);
  assert.equal(meta.paper_count, papers.length);
  assert.ok(page.includes(meta.batch_date));
  assert.ok((await fs.readFile('dist/wechat-editor/index.html', 'utf8')).includes('载入本周 NBER'));
});

for (const count of [2, 3, 4]) {
  test(`editor partitions all shared papers exactly once into ${count} issues`, () => {
    const issues = context.buildIssues(papers, meta, count);
    assert.equal(issues.length, count);
    assert.deepEqual(Array.from(issues.flatMap(issue => issue.paperIds)).sort(), expected);
    for (const issue of issues) {
      assert.ok(issue.markdown.includes(meta.batch_date));
      for (const id of issue.paperIds) assert.ok(issue.markdown.includes(`**NBER 编号：** ${id}`));
    }
  });
}

test('editor still fetches papers and metadata from the same main data directory', () => {
  assert.ok(editor.includes('https://raw.githubusercontent.com/fyapeng/nber/main/src/data'));
  assert.ok(editor.includes('fetch(`${REMOTE_BASE}/papers.json`'));
  assert.ok(editor.includes('fetch(`${REMOTE_BASE}/update-meta.json`'));
});

test('WeChat CLI dry runs cover the same IDs in three issues without credentials/network', async () => {
  const tmp = await fs.mkdtemp(path.join(os.tmpdir(), 'nber-wechat-test-'));
  try {
    await fs.mkdir(path.join(tmp, 'src/data'), { recursive: true });
    await fs.writeFile(path.join(tmp, '.env'), '');
    for (const filename of ['papers.json', 'update-meta.json']) await fs.copyFile(path.join(root, 'src/data', filename), path.join(tmp, 'src/data', filename));
    const offlineGuard = path.join(tmp, 'offline.cjs');
    await fs.writeFile(offlineGuard, 'globalThis.fetch = () => { throw new Error("Network disabled in dry-run test"); };');
    const allIds = [];
    for (let issue = 1; issue <= 3; issue++) {
      const result = JSON.parse(execFileSync(process.execPath, ['--require', offlineGuard, path.join(root, 'scripts/wechat-draft.mjs'), `--issue=${issue}`, '--dry-run'], { cwd: tmp, encoding: 'utf8', env: {} }));
      assert.equal(result.totalIssues, 3);
      const preview = await fs.readFile(path.join(tmp, 'output', `wechat-issue-${issue}-preview.html`), 'utf8');
      const ids = [...preview.matchAll(/NBER 编号：[^w]*?(w\d+)/g)].map(match => match[1]);
      assert.equal(ids.length, result.papers);
      allIds.push(...ids);
    }
    assert.deepEqual(allIds.sort(), expected);
  } finally {
    await fs.rm(tmp, { recursive: true, force: true });
  }
});

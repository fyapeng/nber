# Translation Audit

- Generated at: `2026-10-26T10:24:02Z`
- Paper count: `35`
- Glossary version: `econ-zh-v7-f0ad525007`
- Suspect translation hits: `0`
- Preferred-term misses: `0`
- Failed or skipped fields: `0`
- Translation quality warnings: `0`

## Review Workflow

1. 先看 `High-Priority Suspect Terms`，这些通常是已知错译再次出现。
2. 再看 `Preferred-Term Misses`，这里是英文原文命中了术语表，但中文译文没有出现推荐译法，可能有误报。
3. 最后扫 `English Fragments`，确认保留英文是否合理；合理的缩写可以加入 `allowed_english_terms`。
4. 只有通用问题才写入 `scripts/translation_glossary.json`，不要为单篇做过拟合规则。

## High-Priority Suspect Terms

No known high-priority suspect terms were found.

## Preferred-Term Misses

No preferred-term misses were found.

## Failed Or Skipped Fields

No failed or skipped translation fields were found.

## Translation Quality Warnings

No structural translation quality warnings were found.

## English Fragments

| Fragment | Papers |
| --- | --- |
| GDP | w35934, w35949 |
| Medicare | w35936, w35946 |
| ACA | w35955 |
| BLP | w35954 |
| CMS | w35955 |
| CSR | w35955 |
| DID | w35935 |
| Econometrica | w35948 |
| Economy Score | w35949 |
| H-2A | w35941 |
| hat-algebra | w35942 |
| HouseholdBench | w35927 |
| Hulten | w35934 |
| Kline | w35948 |
| Leave-Out Estimation | w35948 |
| LLM | w35947 |
| LLMs | w35927 |
| market | w35928 |
| Marketplace | w35955 |
| Mata | w35948 |
| match deletion | w35948 |
| Matlab | w35948 |
| MMF | w35954 |
| MMFs | w35954 |
| multihoming | w35953 |
| neoclassical | w35934 |
| pricing | w35928 |
| Razin | w35957 |
| Rust | w35948 |
| Saggio | w35948 |
| silver loading | w35955 |
| Stata | w35948 |
| Svensson | w35957 |
| Variance Components | w35948 |
| Visale | w35932 |
| weekly liquid assets | w35954 |

## Maintenance Notes

- 新术语优先加到 `prompt_terms`，让模型以后主动使用。
- 已知错译再加到 `replacement_rules`，保证缓存命中和模型偶发输出都能被修正。
- 如果只是需要人工关注但不能确定替换，加入 `audit.suspect_translations` 或 `audit.source_terms`。
- 修改术语表会自动改变 `translation_prompt_version` 指纹，下一次更新会重新翻译。

# Translation Audit

- Generated at: `2026-11-09T13:14:06Z`
- Paper count: `21`
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
| Airbnb | w35989 |
| Boehm | w36004 |
| Coarsened Exact Matching | w35989 |
| Diffidence | w36001 |
| GBV | w35986 |
| Kroner | w36004 |
| Lucas Tree | w36001 |
| Marine Degree Days | w35994 |
| Markowitz | w35988 |
| Medicare Part | w35997 |
| MMP | w36004 |
| MOUD | w35997 |
| NET | w35987 |
| NET Center | w35987 |
| NP-hard | w35993 |
| p-hacking | w35999 |
| precautionary augment | w36001 |
| RCTs | w35999 |
| Set | w35997 |
| ShotSpotter | w36005 |
| Stanford Task Network | w35987 |
| TaskNet | w35987 |
| Treatment Episode Data | w35997 |
| USD PPP | w35991 |
| ZIP | w35989 |
| ZLB | w35985 |

## Maintenance Notes

- 新术语优先加到 `prompt_terms`，让模型以后主动使用。
- 已知错译再加到 `replacement_rules`，保证缓存命中和模型偶发输出都能被修正。
- 如果只是需要人工关注但不能确定替换，加入 `audit.suspect_translations` 或 `audit.source_terms`。
- 修改术语表会自动改变 `translation_prompt_version` 指纹，下一次更新会重新翻译。

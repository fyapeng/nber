# Translation Audit

- Generated at: `2026-09-14T10:20:58Z`
- Paper count: `34`
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
| Abowd | w35746 |
| ACA | w35751 |
| bunching | w35733 |
| business stealing | w35729 |
| checkout stigma | w35739 |
| CIS | w35740 |
| Coasean exchange | w35745 |
| Communities | w35740 |
| CTD | w35746 |
| degenerate responses | w35733 |
| Diamond-Mirrlees | w35741 |
| Dirac | w35757 |
| Dixit | w35745 |
| EITC | w35747 |
| establishments | w35749 |
| Facebook | w35732 |
| Federal Lands | w35745 |
| GDP | w35755 |
| HOPE | w35736 |
| Krueger | w35745 |
| LMF | w35751 |
| maximum sustained-yield | w35745 |
| MRT | w35756 |
| Multiple Use principle | w35745 |
| NHIS | w35751 |
| OAI | w35748 |
| OSHA | w35646 |
| Pigouvian restrictions | w35745 |
| post-neonatal period | w35743 |
| Progressive Era | w35745 |
| rent-seeking | w35745 |
| Schools | w35740 |
| SFR | w35755 |
| SFRs | w35755 |
| shift-share | w35743 |
| Sims | w35741 |
| SNAP | w35739 |
| SSI | w35725 |
| SST | w35646 |
| Startup Cartography Project | w35752 |
| ZIP | w35646 |

## Maintenance Notes

- 新术语优先加到 `prompt_terms`，让模型以后主动使用。
- 已知错译再加到 `replacement_rules`，保证缓存命中和模型偶发输出都能被修正。
- 如果只是需要人工关注但不能确定替换，加入 `audit.suspect_translations` 或 `audit.source_terms`。
- 修改术语表会自动改变 `translation_prompt_version` 指纹，下一次更新会重新翻译。

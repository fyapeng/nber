# Translation Audit

- Generated at: `2026-10-05T12:03:54Z`
- Paper count: `45`
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
| STEM | w35847, w35857, w35859 |
| ADHD | w35873 |
| aftermath | w35858 |
| AIR | w35840 |
| Akbarpour | w35841 |
| amenities | w35852 |
| Cameron | w35801 |
| Cameron and Miller | w35800 |
| Carbon Disclosure Project | w35869 |
| CFTC | w35845 |
| ChatGPT-4o | w35839 |
| Climate Fund | w35834 |
| Climate Targets Database | w35869 |
| Condorcet cycles | w35839 |
| Conley | w35801 |
| cutoff | w35847 |
| ERLL | w35848 |
| ERLLs | w35848 |
| FT3 | w35858 |
| GDP | w35865 |
| general partner | w35860 |
| HAC | w35801 |
| HIV | w35833 |
| hyperscaler | w35865 |
| IRS | w35874 |
| Jim Crow | w35842 |
| LLM | w35839 |
| longshots | w35845 |
| Miller | w35801 |
| money-pump | w35839 |
| NAACP | w35842 |
| NielsenIQ | w35835 |
| OPEC | w35864 |
| P-EBT | w35835 |
| PM2.5 | w35871 |
| PredictIt | w35845 |
| RCT | w35872 |
| Recovery | w35858 |
| RES | w35840 |
| Rosenwald | w35842 |
| Salata Institute Corporate | w35869 |
| SNAP | w35835 |
| soft reserves | w35841 |
| STI | w35833 |
| Study | w35858 |
| substantial | w35860 |
| SYS | w35840 |
| temperature | w35839 |
| Tsunami Aftermath and | w35858 |
| UBI | w35836 |
| W-2 | w35856 |
| WTO | w35834 |

## Maintenance Notes

- 新术语优先加到 `prompt_terms`，让模型以后主动使用。
- 已知错译再加到 `replacement_rules`，保证缓存命中和模型偶发输出都能被修正。
- 如果只是需要人工关注但不能确定替换，加入 `audit.suspect_translations` 或 `audit.source_terms`。
- 修改术语表会自动改变 `translation_prompt_version` 指纹，下一次更新会重新翻译。

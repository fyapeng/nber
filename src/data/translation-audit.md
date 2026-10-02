# Translation Audit

- Generated at: `2026-09-28T07:14:03Z`
- Paper count: `43`
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
| affiliation | w35820 |
| Aging | w35792 |
| AMOC | w35811 |
| Bergeron | w35813 |
| Bloom | w35791 |
| broadly similar | w35831 |
| Caselli | w35826 |
| Cassa per | w35802 |
| CME | w35819 |
| coding agents | w35793 |
| CPI | w35790 |
| CPS | w35796 |
| Diamond | w35823 |
| Dingle | w35791 |
| distinct beliefs | w35831 |
| durable jobs | w35815 |
| FERU | w35804 |
| Food | w35817 |
| FPR | w35797 |
| GDP | w35826 |
| Green Paradox | w35794 |
| Home | w35817 |
| Korean Longitudinal Study | w35792 |
| LLM | w35782 |
| LPR | w35797 |
| LRP | w35819 |
| LRP-CME | w35819 |
| magnitude | w35796 |
| maximin | w35798 |
| Mezzogiorno | w35802 |
| minimax-regret | w35798 |
| Moonshot | w35802 |
| NBA | w35803 |
| Neiman | w35791 |
| New Frontier | w35802 |
| OLG | w35823 |
| relative market thickness | w35822 |
| RESET | w35817 |
| RESET Demonstration Project | w35817 |
| S-IAM | w35811 |
| TCJA | w35805 |
| vehicle currencies | w35822 |
| WFH | w35791 |

## Maintenance Notes

- 新术语优先加到 `prompt_terms`，让模型以后主动使用。
- 已知错译再加到 `replacement_rules`，保证缓存命中和模型偶发输出都能被修正。
- 如果只是需要人工关注但不能确定替换，加入 `audit.suspect_translations` 或 `audit.source_terms`。
- 修改术语表会自动改变 `translation_prompt_version` 指纹，下一次更新会重新翻译。

# Translation Audit

- Generated at: `2026-08-24T10:25:45Z`
- Paper count: `26`
- Glossary version: `econ-zh-v7-f0ad525007`
- Suspect translation hits: `0`
- Preferred-term misses: `0`
- Failed or skipped fields: `1`
- Translation quality warnings: `1`

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

| Paper | Field | Status | Error |
| --- | --- | --- | --- |
| w35655 | abstract | failed | Error code: 400 - {'error': {'code': 400, 'message': 'The request was rejected because it was considered high risk', 'param': 'prompt', 'type': 'content_filter'}} |

## Translation Quality Warnings

| Paper | Field | Issue | Current output |
| --- | --- | --- | --- |
| w35655 | abstract | translation is identical to the English source | The 2016 Panama Papers leak tightened regulatory enforcement around money laundering and offshore banking. W |

## English Fragments

| Fragment | Papers |
| --- | --- |
| aid diversion | w35655 |
| aid diversion across | w35655 |
| aid tranche arrivals | w35655 |
| alternative laundering platform | w35655 |
| and apply | w35655 |
| and Governance | w35655 |
| and integration sequence | w35655 |
| and IP-linked web | w35655 |
| and offshore banking | w35655 |
| and recover diverted | w35655 |
| anonymous and newly | w35655 |
| around money laundering | w35655 |
| billion across the | w35655 |
| billion dollars | w35655 |
| both tax-haven and | w35655 |
| but its transparent | w35655 |
| cents per aid | w35655 |
| combining on-chain Bitcoin | w35655 |
| consistent with the | w35655 |
| conventional money laundering | w35655 |
| created wallets | w35655 |
| creation | w35655 |
| crypto activity | w35655 |
| cryptocurrency | w35655 |
| cryptocurrency activity | w35655 |
| CWITE | w35643 |
| detect | w35655 |
| develop | w35655 |
| developing countries led | w35655 |
| disbursement-timed forensic measure | w35655 |
| disbursements covering | w35655 |
| diversion | w35655 |
| dollar | w35655 |
| driven mainly | w35655 |
| during | w35655 |
| estimate | w35655 |
| Exploiting the administrative | w35655 |
| find sharp | w35655 |
| foreign aid | w35655 |
| forensic traces that | w35655 |
| forensics reveal patterns | w35655 |
| funding penalty | w35655 |
| funding. Cryptocurrency facilitates | w35655 |
| funds | w35655 |
| github.com | w35643 |
| HANK | w35642 |
| https | w35643 |
| implied leakage | w35655 |
| IMS | w35647 |
| investigate whether the | w35655 |
| layering | w35655 |
| ledgers also leave | w35655 |
| mainstream exchanges. Blockchain | w35655 |
| may help detect | w35655 |
| MLD3 | w35643 |
| off-chain exchange records | w35655 |
| our estimation sample | w35655 |
| Panama Papers leak | w35655 |
| placement | w35655 |
| RANK | w35642 |

## Maintenance Notes

- 新术语优先加到 `prompt_terms`，让模型以后主动使用。
- 已知错译再加到 `replacement_rules`，保证缓存命中和模型偶发输出都能被修正。
- 如果只是需要人工关注但不能确定替换，加入 `audit.suspect_translations` 或 `audit.source_terms`。
- 修改术语表会自动改变 `translation_prompt_version` 指纹，下一次更新会重新翻译。

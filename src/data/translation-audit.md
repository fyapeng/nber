# Translation Audit

- Generated at: `2026-09-07T15:21:06Z`
- Paper count: `34`
- Glossary version: `econ-zh-v7-f0ad525007`
- Suspect translation hits: `0`
- Preferred-term misses: `2`
- Failed or skipped fields: `68`
- Translation quality warnings: `68`

## Review Workflow

1. 先看 `High-Priority Suspect Terms`，这些通常是已知错译再次出现。
2. 再看 `Preferred-Term Misses`，这里是英文原文命中了术语表，但中文译文没有出现推荐译法，可能有误报。
3. 最后扫 `English Fragments`，确认保留英文是否合理；合理的缩写可以加入 `allowed_english_terms`。
4. 只有通用问题才写入 `scripts/translation_glossary.json`，不要为单篇做过拟合规则。

## High-Priority Suspect Terms

No known high-priority suspect terms were found.

## Preferred-Term Misses

| Paper | Source term | Preferred Chinese | English title | Current Chinese title |
| --- | --- | --- | --- | --- |
| w35697 | labor market | 劳动力市场 | Do Online Job Postings Capture Job Vacancies? | Do Online Job Postings Capture Job Vacancies? |
| w35709 | labor market | 劳动力市场 | Signals, Steps, and Setbacks: Age Discrimination in a Laddered Labor Market | Signals, Steps, and Setbacks: Age Discrimination in a Laddered Labor Market |

## Failed Or Skipped Fields

| Paper | Field | Status | Error |
| --- | --- | --- | --- |
| w35670 | title | failed | Error code: 404 - {'error': {'message': 'Not found the model moonshot-v1-8k or Permission denied', 'type': 'resource_not_found_error'}} |
| w35670 | abstract | failed | Error code: 404 - {'error': {'message': 'Not found the model moonshot-v1-8k or Permission denied', 'type': 'resource_not_found_error'}} |
| w35694 | title | failed | Error code: 404 - {'error': {'message': 'Not found the model moonshot-v1-8k or Permission denied', 'type': 'resource_not_found_error'}} |
| w35694 | abstract | failed | Error code: 404 - {'error': {'message': 'Not found the model moonshot-v1-8k or Permission denied', 'type': 'resource_not_found_error'}} |
| w35706 | title | failed | Error code: 404 - {'error': {'message': 'Not found the model moonshot-v1-8k or Permission denied', 'type': 'resource_not_found_error'}} |
| w35706 | abstract | failed | Error code: 404 - {'error': {'message': 'Not found the model moonshot-v1-8k or Permission denied', 'type': 'resource_not_found_error'}} |
| w35710 | title | failed | Error code: 404 - {'error': {'message': 'Not found the model moonshot-v1-8k or Permission denied', 'type': 'resource_not_found_error'}} |
| w35710 | abstract | failed | Error code: 404 - {'error': {'message': 'Not found the model moonshot-v1-8k or Permission denied', 'type': 'resource_not_found_error'}} |
| w35699 | title | failed | Error code: 404 - {'error': {'message': 'Not found the model moonshot-v1-8k or Permission denied', 'type': 'resource_not_found_error'}} |
| w35699 | abstract | failed | Error code: 404 - {'error': {'message': 'Not found the model moonshot-v1-8k or Permission denied', 'type': 'resource_not_found_error'}} |
| w35708 | title | failed | Error code: 404 - {'error': {'message': 'Not found the model moonshot-v1-8k or Permission denied', 'type': 'resource_not_found_error'}} |
| w35708 | abstract | failed | Error code: 404 - {'error': {'message': 'Not found the model moonshot-v1-8k or Permission denied', 'type': 'resource_not_found_error'}} |
| w35697 | title | failed | Error code: 404 - {'error': {'message': 'Not found the model moonshot-v1-8k or Permission denied', 'type': 'resource_not_found_error'}} |
| w35697 | abstract | failed | Error code: 404 - {'error': {'message': 'Not found the model moonshot-v1-8k or Permission denied', 'type': 'resource_not_found_error'}} |
| w35719 | title | failed | Error code: 404 - {'error': {'message': 'Not found the model moonshot-v1-8k or Permission denied', 'type': 'resource_not_found_error'}} |
| w35719 | abstract | failed | Error code: 404 - {'error': {'message': 'Not found the model moonshot-v1-8k or Permission denied', 'type': 'resource_not_found_error'}} |
| w35722 | title | failed | Error code: 404 - {'error': {'message': 'Not found the model moonshot-v1-8k or Permission denied', 'type': 'resource_not_found_error'}} |
| w35722 | abstract | failed | Error code: 404 - {'error': {'message': 'Not found the model moonshot-v1-8k or Permission denied', 'type': 'resource_not_found_error'}} |
| w35715 | title | failed | Error code: 404 - {'error': {'message': 'Not found the model moonshot-v1-8k or Permission denied', 'type': 'resource_not_found_error'}} |
| w35715 | abstract | failed | Error code: 404 - {'error': {'message': 'Not found the model moonshot-v1-8k or Permission denied', 'type': 'resource_not_found_error'}} |
| w35724 | title | failed | Error code: 404 - {'error': {'message': 'Not found the model moonshot-v1-8k or Permission denied', 'type': 'resource_not_found_error'}} |
| w35724 | abstract | failed | Error code: 404 - {'error': {'message': 'Not found the model moonshot-v1-8k or Permission denied', 'type': 'resource_not_found_error'}} |
| w35714 | title | failed | Error code: 404 - {'error': {'message': 'Not found the model moonshot-v1-8k or Permission denied', 'type': 'resource_not_found_error'}} |
| w35714 | abstract | failed | Error code: 404 - {'error': {'message': 'Not found the model moonshot-v1-8k or Permission denied', 'type': 'resource_not_found_error'}} |
| w35717 | title | failed | Error code: 404 - {'error': {'message': 'Not found the model moonshot-v1-8k or Permission denied', 'type': 'resource_not_found_error'}} |
| w35717 | abstract | failed | Error code: 404 - {'error': {'message': 'Not found the model moonshot-v1-8k or Permission denied', 'type': 'resource_not_found_error'}} |
| w35693 | title | failed | Error code: 404 - {'error': {'message': 'Not found the model moonshot-v1-8k or Permission denied', 'type': 'resource_not_found_error'}} |
| w35693 | abstract | failed | Error code: 404 - {'error': {'message': 'Not found the model moonshot-v1-8k or Permission denied', 'type': 'resource_not_found_error'}} |
| w35723 | title | failed | Error code: 404 - {'error': {'message': 'Not found the model moonshot-v1-8k or Permission denied', 'type': 'resource_not_found_error'}} |
| w35723 | abstract | failed | Error code: 404 - {'error': {'message': 'Not found the model moonshot-v1-8k or Permission denied', 'type': 'resource_not_found_error'}} |
| w35718 | title | failed | Error code: 404 - {'error': {'message': 'Not found the model moonshot-v1-8k or Permission denied', 'type': 'resource_not_found_error'}} |
| w35718 | abstract | failed | Error code: 404 - {'error': {'message': 'Not found the model moonshot-v1-8k or Permission denied', 'type': 'resource_not_found_error'}} |
| w35709 | title | failed | Error code: 404 - {'error': {'message': 'Not found the model moonshot-v1-8k or Permission denied', 'type': 'resource_not_found_error'}} |
| w35709 | abstract | failed | Error code: 404 - {'error': {'message': 'Not found the model moonshot-v1-8k or Permission denied', 'type': 'resource_not_found_error'}} |
| w35704 | title | failed | Error code: 404 - {'error': {'message': 'Not found the model moonshot-v1-8k or Permission denied', 'type': 'resource_not_found_error'}} |
| w35704 | abstract | failed | Error code: 404 - {'error': {'message': 'Not found the model moonshot-v1-8k or Permission denied', 'type': 'resource_not_found_error'}} |
| w35713 | title | failed | Error code: 404 - {'error': {'message': 'Not found the model moonshot-v1-8k or Permission denied', 'type': 'resource_not_found_error'}} |
| w35713 | abstract | failed | Error code: 404 - {'error': {'message': 'Not found the model moonshot-v1-8k or Permission denied', 'type': 'resource_not_found_error'}} |
| w35705 | title | failed | Error code: 404 - {'error': {'message': 'Not found the model moonshot-v1-8k or Permission denied', 'type': 'resource_not_found_error'}} |
| w35705 | abstract | failed | Error code: 404 - {'error': {'message': 'Not found the model moonshot-v1-8k or Permission denied', 'type': 'resource_not_found_error'}} |
| w35698 | title | failed | Error code: 404 - {'error': {'message': 'Not found the model moonshot-v1-8k or Permission denied', 'type': 'resource_not_found_error'}} |
| w35698 | abstract | failed | Error code: 404 - {'error': {'message': 'Not found the model moonshot-v1-8k or Permission denied', 'type': 'resource_not_found_error'}} |
| w35707 | title | failed | Error code: 404 - {'error': {'message': 'Not found the model moonshot-v1-8k or Permission denied', 'type': 'resource_not_found_error'}} |
| w35707 | abstract | failed | Error code: 404 - {'error': {'message': 'Not found the model moonshot-v1-8k or Permission denied', 'type': 'resource_not_found_error'}} |
| w35695 | title | failed | Error code: 404 - {'error': {'message': 'Not found the model moonshot-v1-8k or Permission denied', 'type': 'resource_not_found_error'}} |
| w35695 | abstract | failed | Error code: 404 - {'error': {'message': 'Not found the model moonshot-v1-8k or Permission denied', 'type': 'resource_not_found_error'}} |
| w35696 | title | failed | Error code: 404 - {'error': {'message': 'Not found the model moonshot-v1-8k or Permission denied', 'type': 'resource_not_found_error'}} |
| w35696 | abstract | failed | Error code: 404 - {'error': {'message': 'Not found the model moonshot-v1-8k or Permission denied', 'type': 'resource_not_found_error'}} |
| w35712 | title | failed | Error code: 404 - {'error': {'message': 'Not found the model moonshot-v1-8k or Permission denied', 'type': 'resource_not_found_error'}} |
| w35712 | abstract | failed | Error code: 404 - {'error': {'message': 'Not found the model moonshot-v1-8k or Permission denied', 'type': 'resource_not_found_error'}} |
| w35701 | title | failed | Error code: 404 - {'error': {'message': 'Not found the model moonshot-v1-8k or Permission denied', 'type': 'resource_not_found_error'}} |
| w35701 | abstract | failed | Error code: 404 - {'error': {'message': 'Not found the model moonshot-v1-8k or Permission denied', 'type': 'resource_not_found_error'}} |
| w35716 | title | failed | Error code: 404 - {'error': {'message': 'Not found the model moonshot-v1-8k or Permission denied', 'type': 'resource_not_found_error'}} |
| w35716 | abstract | failed | Error code: 404 - {'error': {'message': 'Not found the model moonshot-v1-8k or Permission denied', 'type': 'resource_not_found_error'}} |
| w35703 | title | failed | Error code: 404 - {'error': {'message': 'Not found the model moonshot-v1-8k or Permission denied', 'type': 'resource_not_found_error'}} |
| w35703 | abstract | failed | Error code: 404 - {'error': {'message': 'Not found the model moonshot-v1-8k or Permission denied', 'type': 'resource_not_found_error'}} |
| w35702 | title | failed | Error code: 404 - {'error': {'message': 'Not found the model moonshot-v1-8k or Permission denied', 'type': 'resource_not_found_error'}} |
| w35702 | abstract | failed | Error code: 404 - {'error': {'message': 'Not found the model moonshot-v1-8k or Permission denied', 'type': 'resource_not_found_error'}} |
| w35721 | title | failed | Error code: 404 - {'error': {'message': 'Not found the model moonshot-v1-8k or Permission denied', 'type': 'resource_not_found_error'}} |
| w35721 | abstract | failed | Error code: 404 - {'error': {'message': 'Not found the model moonshot-v1-8k or Permission denied', 'type': 'resource_not_found_error'}} |
| w35692 | title | failed | Error code: 404 - {'error': {'message': 'Not found the model moonshot-v1-8k or Permission denied', 'type': 'resource_not_found_error'}} |
| w35692 | abstract | failed | Error code: 404 - {'error': {'message': 'Not found the model moonshot-v1-8k or Permission denied', 'type': 'resource_not_found_error'}} |
| w35720 | title | failed | Error code: 404 - {'error': {'message': 'Not found the model moonshot-v1-8k or Permission denied', 'type': 'resource_not_found_error'}} |
| w35720 | abstract | failed | Error code: 404 - {'error': {'message': 'Not found the model moonshot-v1-8k or Permission denied', 'type': 'resource_not_found_error'}} |
| w35700 | title | failed | Error code: 404 - {'error': {'message': 'Not found the model moonshot-v1-8k or Permission denied', 'type': 'resource_not_found_error'}} |
| w35700 | abstract | failed | Error code: 404 - {'error': {'message': 'Not found the model moonshot-v1-8k or Permission denied', 'type': 'resource_not_found_error'}} |
| w35711 | title | failed | Error code: 404 - {'error': {'message': 'Not found the model moonshot-v1-8k or Permission denied', 'type': 'resource_not_found_error'}} |
| w35711 | abstract | failed | Error code: 404 - {'error': {'message': 'Not found the model moonshot-v1-8k or Permission denied', 'type': 'resource_not_found_error'}} |

## Translation Quality Warnings

| Paper | Field | Issue | Current output |
| --- | --- | --- | --- |
| w35670 | title | translation is identical to the English source | Air Pollution and Learning |
| w35670 | abstract | translation is identical to the English source | Nearly the entire world's population breathes air exceeding WHO pollution guidelines, but the extent to whic |
| w35694 | title | translation is identical to the English source | Comparisons |
| w35694 | abstract | translation is identical to the English source | Economic decisions are often shaped by comparison points such as reference points, goals, expectations and p |
| w35706 | title | translation is identical to the English source | Meetings |
| w35706 | abstract | translation is identical to the English source | Why do we have so many meetings? Few workplace features are so scorned, yet seemingly so necessary. This pap |
| w35710 | title | translation is identical to the English source | Female Micro-Entrepreneurship and Child Development |
| w35710 | abstract | translation is identical to the English source | Ultra-poor graduation programs (UPG) reliably reduce extreme poverty among adult recipients, yet their inter |
| w35699 | title | translation is identical to the English source | PLRD: Partially Linear Regression Discontinuity Inference |
| w35699 | abstract | translation is identical to the English source | Regression discontinuity designs have become one of the most popular research designs in empirical economics |
| w35708 | title | translation is identical to the English source | “Non-Marginal” Investor Beliefs |
| w35708 | abstract | translation is identical to the English source | This paper provides evidence of how the beliefs of investors who step out of the market, or “non-marginal” i |
| w35697 | title | translation is identical to the English source | Do Online Job Postings Capture Job Vacancies? |
| w35697 | abstract | translation is identical to the English source | We ask whether online job postings capture U.S. job vacancies, matching near-universal Burning Glass (BG) po |
| w35719 | title | translation is identical to the English source | The Utility of AI Tools in Auditing Adherence to Pre-Analysis Plans |
| w35719 | abstract | translation is identical to the English source | Pre-analysis plans (PAPs) can improve research reproducibility by reducing researchers’ degrees of freedom, |
| w35722 | title | translation is identical to the English source | The Multigenerational Effects of Legal Access to the Pill on Infant Health |
| w35722 | abstract | translation is identical to the English source | We examine whether expanded legal access to the contraceptive pill for minors generated health benefits for |
| w35715 | title | translation is identical to the English source | Fiscal Policy and the Saving Glut of the Rich |
| w35715 | abstract | translation is identical to the English source | Since the 1980s, the United States has experienced a pronounced saving glut of the rich, a large accumulatio |
| w35724 | title | translation is identical to the English source | Risk Perceptions of E-Cigarettes and the Evaluation of EVALI Messaging |
| w35724 | abstract | translation is identical to the English source | With the growth of sales of e-cigarettes and other alternative nicotine products, governments face the new c |
| w35714 | title | translation is identical to the English source | Behavioral Signatures of Cognitive Noise |
| w35714 | abstract | translation is identical to the English source | The cognitive noise hypothesis is an increasingly popular explanation for a wide range of puzzling regularit |
| w35717 | title | translation is identical to the English source | The No Surprises Act’s Surprises: Arbitration, Provider Network, and Insurer Pricing |
| w35717 | abstract | translation is identical to the English source | The No Surprises Act (NSA) capped patients' liability for surprise bills and established federal final-offer |
| w35693 | title | translation is identical to the English source | Pensions and Turbulence: Automatic Adjustment, Risk, and Fairness in Long-Term Pension Design |
| w35693 | abstract | translation is identical to the English source | Public pension systems are long-term social contracts operating under persistent economic, demographic, and |
| w35723 | title | translation is identical to the English source | An Empirically-Grounded Theory of Voting Based on Prosocial Motives |
| w35723 | abstract | translation is identical to the English source | We propose a model of costly voting in a canonical spatial setting that reconciles key empirical features of |
| w35718 | title | translation is identical to the English source | Will New Transportation Technologies Increase Urban Density |
| w35718 | abstract | translation is identical to the English source | Will 21st century transportation innovations work against urban density, as the car did in the 20th century, |
| w35709 | title | translation is identical to the English source | Signals, Steps, and Setbacks: Age Discrimination in a Laddered Labor Market |
| w35709 | abstract | translation is identical to the English source | We study age discrimination in a labor market with a job ladder, where worker productivity is revealed over |
| w35704 | title | translation is identical to the English source | The Allocative Cost of War: A View to a Kill...ing of Productivity |
| w35704 | abstract | translation is identical to the English source | Why is war so economically costly? Our answer is that modern war lowers output not only by destroying produc |
| w35713 | title | translation is identical to the English source | Rust in Motion: The Political Environmental Trap of Vehicle Tax Exemptions |
| w35713 | abstract | translation is identical to the English source | Transportation is a major source of greenhouse gas and air pollution emissions worldwide, with most automobi |
| w35705 | title | translation is identical to the English source | Unemployment Insurance in Macroeconomic Stabilization with Imperfect Expectations |
| w35705 | abstract | translation is identical to the English source | Automatic stabilizers can respond to a recession without a new policy decision, but their effects on aggrega |
| w35698 | title | translation is identical to the English source | Is a Dollar a Dollar? How Transfer Design Shapes Household Spending |
| w35698 | abstract | translation is identical to the English source | Government transfers vary along two design dimensions that standard models predict should not matter: whethe |
| w35707 | title | translation is identical to the English source | Dynamic Investment and Product Market Rivalry: the Network Q Model |
| w35707 | abstract | translation is identical to the English source | We present a new dynamic model of corporate investment in imperfectly competitive product markets that exten |
| w35695 | title | translation is identical to the English source | Rain Follows the Forest: Land Use Policy, Climate Change, and Adaptation |
| w35695 | abstract | translation is identical to the English source | Human actions can alter the climate via land use. We analyze the 1930s Great Plains Shelterbelt, a large-sca |
| w35696 | title | translation is identical to the English source | Loan Rates as Incentive Instruments |
| w35696 | abstract | translation is identical to the English source | Loan rates are usually viewed as prices that shape borrower incentives, but they can also serve another role |
| w35712 | title | translation is identical to the English source | The Limits of Verifiability: Credibility and Flexibility in Communication |
| w35712 | abstract | translation is identical to the English source | We compare verifiable and unverifiable communication in a sender–receiver setting with partially aligned pre |
| w35701 | title | translation is identical to the English source | Tracking Inequality: Teachers and the Allocation of Educational Opportunities |
| w35701 | abstract | translation is identical to the English source | Professionals routinely make consequential decisions for others without systematically observing how those d |
| w35716 | title | translation is identical to the English source | Expectations-based Capital Inflow Shocks |
| w35716 | abstract | translation is identical to the English source | Identifying the impact of capital inflows on output is challenging because inflows are forward-looking and r |
| w35703 | title | translation is identical to the English source | How Big is Small? The Economic Effects of Access to Small Business Government Support |
| w35703 | abstract | translation is identical to the English source | We study the effects of vast increases in U.S. small business program eligibility standards, which expanded |
| w35702 | title | translation is identical to the English source | Rational Inattention to Discrete Choices with Stable Priors |
| w35702 | abstract | translation is identical to the English source | How does prior information affect discrete choice? In the seminal rational inattention model of Matějka and |
| w35721 | title | translation is identical to the English source | Politics-driven Market Access and Its Cost: Evidence from China’s Grand Canal |
| w35721 | abstract | translation is identical to the English source | Transportation networks often radiate from national capitals, reflecting political priorities as much as eco |
| w35692 | title | translation is identical to the English source | Health Insurance Underwriting and the Heterogeneous Effects of the Affordable Care Act |
| w35692 | abstract | translation is identical to the English source | The Affordable Care Act, the largest US welfare reform since 1965, banned health insurance underwriting and |
| w35720 | title | translation is identical to the English source | Does AI Assistance Enhance or Erode Expertise? Evidence from a Three-Month Field Experiment in Patent Drafti |
| w35720 | abstract | translation is identical to the English source | Whether AI assistance builds or erodes professional expertise is unsettled. In a pre-registered three-month |
| w35700 | title | translation is identical to the English source | Cross-Section Estimation of Long-Run Relations Using Time-Compressed Data |
| w35700 | abstract | translation is identical to the English source | Many empirical investigations of long-run relations are based on cross-section regressions in averaged or lo |
| w35711 | title | translation is identical to the English source | The Impact of Patient Capital |
| w35711 | abstract | translation is identical to the English source | We show that investor patience shapes venture-capital (VC) investment strategies and outcomes. Through a ran |

## English Fragments

| Fragment | Papers |
| --- | --- |
| model | w35692, w35707, w35709, w35723 |
| access | w35703, w35720, w35722 |
| changes | w35693, w35702, w35718 |
| develop | w35694, w35715, w35716 |
| effects | w35701, w35710, w35724 |
| accompanied | w35701, w35717 |
| affected | w35701, w35722 |
| based | w35692, w35700 |
| consistent with | w35694, w35713 |
| contrast | w35694, w35715 |
| document | w35692, w35704 |
| find that the | w35715, w35717 |
| firms | w35703, w35707 |
| impact | w35705, w35716 |
| impacts | w35695, w35710 |
| income | w35692, w35700 |
| markets | w35693, w35721 |
| more than | w35694, w35706 |
| output | w35694, w35716 |
| propose | w35699, w35723 |
| show that the | w35696, w35710 |
| structure | w35695, w35714 |
| study | w35710, w35724 |
| Sweden | w35693, w35724 |
| through | w35702, w35721 |
| using | w35705, w35716 |
| wide range | w35714, w35716 |
| about | w35705 |
| about half its | w35705 |
| about unobservable effort | w35696 |
| about which candidate | w35723 |
| above the statutory | w35717 |
| absolute risks | w35724 |
| academic performance and | w35701 |
| academically demanding schools | w35701 |
| Access | w35703 |
| access and | w35721 |
| access raised the | w35720 |
| accommodate heterogeneous | w35707 |
| account for the | w35706 |
| accumulating claims | w35715 |
| accurate forecasting | w35701 |
| accurately reflect her | w35712 |
| achievement gaps | w35670 |
| across borrowers and | w35696 |
| across the | w35695 |
| across transfer types | w35698 |
| across Ukrainian districts | w35704 |
| Act The Affordable | w35692 |
| actions can alter | w35695 |
| actual path. This | w35721 |
| adapt while maintaining | w35693 |
| additional condition that | w35723 |
| adequacy | w35693 |
| adherence | w35719 |
| adjustment mechanisms | w35693 |
| adult smokers | w35724 |
| affect discrete choice | w35702 |
| affect outcomes such | w35723 |
| afforestation and enabling | w35695 |

## Maintenance Notes

- 新术语优先加到 `prompt_terms`，让模型以后主动使用。
- 已知错译再加到 `replacement_rules`，保证缓存命中和模型偶发输出都能被修正。
- 如果只是需要人工关注但不能确定替换，加入 `audit.suspect_translations` 或 `audit.source_terms`。
- 修改术语表会自动改变 `translation_prompt_version` 指纹，下一次更新会重新翻译。

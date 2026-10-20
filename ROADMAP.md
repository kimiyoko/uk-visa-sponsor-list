# Roadmap · 路线图

**Goal / 目标:** a sponsorable UK job offer with a Certificate of Sponsorship (CoS) by **2027-01-17**.
在 **2027-01-17** 前拿到一份可担保 Skilled Worker 签证的 offer，并且雇主已分配 CoS。

- Full plan / 完整计划: <https://claude.ai/artifact/MzTqgEzMTzTH75jxMWHLxG>
- Progress / 进度: [Milestones](https://github.com/kimiyoko/uk-visa-sponsor-list/milestones) · [Issues](https://github.com/kimiyoko/uk-visa-sponsor-list/issues)
- Decisions / 决策记录: [project/decisions.md](project/decisions.md)

## Why the dates / 为什么是这些日期

Data analyst roles (SOC 3544) can only be sponsored if the CoS is assigned **before 2026-12-31** (Temporary Shortage List). Roles under SOC 2425 / 2135 / 2424 have no such deadline but a higher salary floor (£46,200–£48,500).
数据分析师（SOC 3544）只有在 **2026-12-31 前**发出 CoS 才能担保；2425 / 2135 / 2424 没有截止日，但薪资下限更高（£46,200–£48,500）。

## Gates / 关卡

| Gate | Due | Pass when / 通过标准 | If not / 没过怎么办 |
| --- | --- | --- | --- |
| [G0 基础就绪](https://github.com/kimiyoko/uk-visa-sponsor-list/milestone/1) | 2026-10-25 | Visa status confirmed; target SOC + salary floor set; master CV + tracker ready; tools trialled and chosen | Slip 1 week, apply with existing CVs meanwhile |
| [G1 岗位数据跑通](https://github.com/kimiyoko/uk-visa-sponsor-list/milestone/2) | 2026-11-08 | ≥ 30 sponsorable roles found automatically per week | Widen cities / industries; add job-board alerts |
| [G2 投递有回音](https://github.com/kimiyoko/uk-visa-sponsor-list/milestone/3) | 2026-11-22 | ≥ 50 applications, response rate ≥ 10% | Rewrite CV opening and cover letter; more referrals |
| [G3 3544 岗位决策](https://github.com/kimiyoko/uk-visa-sponsor-list/milestone/4) | 2026-12-11 | A 3544 role at final round or offer | Move fully to 2425 / 2135 roles |
| [G4 Offer + CoS](https://github.com/kimiyoko/uk-visa-sponsor-list/milestone/5) | 2027-01-17 | Offer + CoS, SOC and salary checked | Retro, plan the next 3 months |

## Pipeline: existing tools vs build / 筛选管道：现成工具 vs 自建

Principle: track which companies are **paying to hire for UK roles now**, not which companies look valuable. Use an existing tool wherever one covers the layer; build only what nothing on the market does.
原则：追踪「哪些公司正在为英国岗位花钱招人」，而不是「哪些公司有价值」。每层能用现成工具就用，只自建市场上没有的部分。

| Layer / 层 | What it does / 做什么 | Existing tool / 现成工具 | Build? / 自建 | Issue |
| --- | --- | --- | --- | --- |
| Sources | Sponsor register, updated every weekday | This repo's site (①) | Done | — |
| L1 | Register ∩ companies with open UK roles | Apify ATS scrapers (Greenhouse, Lever, Workable, Ashby) | Merge logic only | [#6](https://github.com/kimiyoko/uk-visa-sponsor-list/issues/6) |
| L2 | Parse the job ad: sponsorship wording, salary, location, level → SOC and threshold check. Rules first, LLM only for unclear cases | Tarve (going rates, for spot checks) | **Yes — the core** | [#7](https://github.com/kimiyoko/uk-visa-sponsor-list/issues/7) |
| L3 | Company due diligence: active, size, SIC, accounts | Companies House MCP | Health-score rules | [#21](https://github.com/kimiyoko/uk-visa-sponsor-list/issues/21) |
| L4 | Award-list tags (unicorn, fintech, women-friendly) — ranking only, never filtering | — | Yes (scoring) | [#21](https://github.com/kimiyoko/uk-visa-sponsor-list/issues/21) |
| Human check | Cross-check on job boards and a sponsor-checker browser extension; Google AI lookups as fallback | Hunt UK Visa Sponsors, visasponsor.jobs, LinkedIn / Indeed / Reed, UK Work Sponsors extension | No | [#20](https://github.com/kimiyoko/uk-visa-sponsor-list/issues/20) |
| ④ Apply | Keyword match, tailored CV and cover letter | Teal or Jobscan | Experience bank | [#3](https://github.com/kimiyoko/uk-visa-sponsor-list/issues/3), [#10](https://github.com/kimiyoko/uk-visa-sponsor-list/issues/10) |
| ⑤ Interview | Mock interviews | Yoodli | STAR story bank | [#3](https://github.com/kimiyoko/uk-visa-sponsor-list/issues/3), [#14](https://github.com/kimiyoko/uk-visa-sponsor-list/issues/14) |
| ⑥ Track | Applications, funnel numbers | Airtable (Huntr as backup; free tier capped at 100 applications) | No | [#20](https://github.com/kimiyoko/uk-visa-sponsor-list/issues/20), [#15](https://github.com/kimiyoko/uk-visa-sponsor-list/issues/15) |

**Priority score / 优先级分** (roles that pass L1 + L2 only): hiring signal 40 · sponsor rating + Companies House 25 · industry / unicorn lists 20 · employer-brand lists 15. Weights are a starting guess, recalibrated in week 3.

Build issues went from 12 to 5: #20 tool selection, #3 experience bank, #6 L1, #7 L2, #21 L3 + L4. Tools the scan could not verify (e.g. Sponsorship Scout, Sponsor Seal, WPC Jobs) are not relied on. Full scan with sources: see the plan.
建设类 issue 从 12 个合并为 5 个。搜不到可靠页面的工具不依赖；完整摸排和来源见计划文档。

## Records / 记录规则

- Weekly review every Sunday as an issue (template: *Weekly review*). Numbers only, no company names or personal details.
  每周日开一个周报 issue，只写统计数字，不写公司名和个人信息。
- Personal data (applications, salaries, visa status) stays in the private tracker, never in this public repo.
  投递、薪资、签证状态等个人数据只放私有追踪表，不进这个公开仓库。
- Every decision that changes scope or priority goes into [project/decisions.md](project/decisions.md).

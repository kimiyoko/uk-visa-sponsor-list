# Roadmap · 路线图

**Goal:** a sponsorable UK job offer with a Certificate of Sponsorship (CoS) by **2027-01-17**.
**目标：** 在 **2027-01-17** 前拿到一份可担保 Skilled Worker 签证的 offer，并且雇主已分配 CoS。

- Full plan / 完整计划: <https://claude.ai/artifact/MzTqgEzMTzTH75jxMWHLxG>
- Progress / 进度: [Milestones](https://github.com/kimiyoko/uk-visa-sponsor-list/milestones) · [Issues](https://github.com/kimiyoko/uk-visa-sponsor-list/issues)
- Decisions / 决策记录: [project/decisions.md](project/decisions.md)

## Why the dates · 为什么是这些日期

Data analyst roles (SOC 3544) can only be sponsored if the CoS is assigned **before 2026-12-31** (Temporary Shortage List). Roles under SOC 2425 / 2135 / 2424 have no such deadline but a higher salary floor (£46,200–£48,500).

数据分析师（SOC 3544）只有在 **2026-12-31 前**发出 CoS 才能担保（临时短缺清单）；2425 / 2135 / 2424 没有截止日，但薪资下限更高（£46,200–£48,500）。

## Gates · 关卡

| Gate / 关卡 | Due / 截止 | Pass when / 通过标准 | If not / 没过怎么办 |
| --- | --- | --- | --- |
| [G0 Foundations ready / 基础就绪](https://github.com/kimiyoko/uk-visa-sponsor-list/milestone/1) | 2026-10-25 | Visa status confirmed; target SOC and salary floor set; master CV and tracker ready; tools trialled and chosen<br>签证状态确认；目标 SOC 和薪资底线定下；主简历和追踪表可用；工具试用选型完成 | Slip 1 week, apply with existing CVs meanwhile<br>延后 1 周，先用现有简历投递 |
| [G1 Job data flowing / 岗位数据跑通](https://github.com/kimiyoko/uk-visa-sponsor-list/milestone/2) | 2026-11-08 | ≥ 30 sponsorable roles found automatically per week, cross-checked with the company list<br>每周自动发现 ≥ 30 个可担保岗位，并和公司清单交叉验证 | Widen cities / industries; add job-board alerts<br>扩大城市和行业范围，加招聘网站提醒 |
| [G2 Applications get replies / 投递有回音](https://github.com/kimiyoko/uk-visa-sponsor-list/milestone/3) | 2026-11-22 | ≥ 50 applications, response rate ≥ 10%<br>累计 ≥ 50 个投递，回复率 ≥ 10% | Rewrite CV opening and cover letter; more referrals<br>重写简历开头和求职信；提高内推比例 |
| [G3 Decision on SOC 3544 / 3544 岗位决策](https://github.com/kimiyoko/uk-visa-sponsor-list/milestone/4) | 2026-12-11 | A 3544 role at final round or offer<br>有 3544 岗位进入终面或拿到 offer | Move fully to 2425 / 2135 roles<br>全部转向 2425 / 2135 岗位 |
| [G4 Offer + CoS / 拿到 Offer 和 CoS](https://github.com/kimiyoko/uk-visa-sponsor-list/milestone/5) | 2027-01-17 | Offer + CoS, SOC and salary checked<br>拿到 offer 和 CoS，SOC 和薪资核对无误 | Retro, plan the next 3 months<br>复盘漏斗，定下一个 3 个月的方向 |

## Two lists, cross-checked · 两份清单，交叉验证

- **Company list:** the sponsor register filtered by the cities and industries you choose, ranked by rating, size and award tags.
  **公司清单：** 从担保名单出发，按你选的城市和目标行业筛选，再按评级、规模、榜单标签排序。
- **Role list:** UK roles from applicant tracking systems and job boards, filtered by SOC, salary threshold and sponsorship wording. It does not depend on the register.
  **职位清单：** 从 ATS 和招聘网站出发，按 SOC、薪资门槛和担保字样过滤，不依赖担保名单。
- **Cross-check:** roles on both lists go first. Role only → the company isn't on the register, or the "sponsorship" tag is self-reported by the employer, so check before applying. Company only → watch list, rechecked weekly.
  **交叉验证：** 两边都有的岗位优先投；只有职位的（公司不在名单上，或担保标签只是雇主自填）先核实再投；只有公司的进观察名单，每周复查。

Principle: track which companies are **paying to hire for UK roles now**, not which companies look valuable.
原则：追踪「哪些公司正在为英国岗位花钱招人」，而不是「哪些公司有价值」。

## Pipeline: existing tools vs build · 筛选管道：现成工具 vs 自建

Use an existing tool wherever one covers the layer; build only what nothing on the market does.
每层能用现成工具就用，只自建市场上没有的部分。

| Layer / 层 | What it does / 做什么 | Existing tool / 现成工具 | Build? / 自建 | Issue |
| --- | --- | --- | --- | --- |
| Source / 数据源 | Sponsor register, updated every weekday<br>担保名单，每个工作日更新 | This repo's site (①)<br>本仓库的名单网站 | Done / 已完成 | — |
| L1 | Role list from ATS, cross-checked with the company list<br>从 ATS 拿职位清单，和公司清单交叉验证 | Apify ATS scrapers (Greenhouse, Lever, Workable, Ashby)<br>Apify 上的 ATS 抓取器 | Merge logic only<br>只自建合并逻辑 | [#6](https://github.com/kimiyoko/uk-visa-sponsor-list/issues/6) |
| L2 | Parse the ad: sponsorship wording, salary, location, level → SOC and threshold check. Rules first, LLM only for unclear cases<br>解析岗位描述：担保字样、薪资、地点、级别 → 推断 SOC、对照门槛；规则优先，模糊的才交给 LLM | Tarve (going rates, for spot checks)<br>Tarve（市场价，抽查用） | **Yes — the core**<br>**是，核心** | [#7](https://github.com/kimiyoko/uk-visa-sponsor-list/issues/7) |
| L3 | Company due diligence: active, size, SIC, accounts<br>公司尽调：是否存续、规模、行业代码、账目类型 | Companies House MCP | Health-score rules<br>健康度规则 | [#21](https://github.com/kimiyoko/uk-visa-sponsor-list/issues/21) |
| L4 | Award tags (unicorn, fintech, women-friendly): ranking only, never filtering<br>榜单标签（独角兽、金融科技、女性友好）：只排序，不筛选 | — | Yes (scoring)<br>是（打分） | [#21](https://github.com/kimiyoko/uk-visa-sponsor-list/issues/21) |
| Human check / 人工复核 | Cross-check on job boards and a sponsor-checker extension; Google AI lookups as fallback<br>在招聘平台和浏览器插件上核对；Google AI 查询兜底 | Hunt UK Visa Sponsors, visasponsor.jobs, LinkedIn / Indeed / Reed, UK Work Sponsors extension | No / 否 | [#20](https://github.com/kimiyoko/uk-visa-sponsor-list/issues/20) |
| ④ Apply / 投递 | Keyword match, tailored CV and cover letter<br>关键词匹配，定制简历和求职信 | Teal or Jobscan | Experience bank<br>经历库 | [#3](https://github.com/kimiyoko/uk-visa-sponsor-list/issues/3), [#10](https://github.com/kimiyoko/uk-visa-sponsor-list/issues/10) |
| ⑤ Interview / 面试 | Mock interviews<br>模拟面试 | Yoodli | STAR story bank<br>STAR 故事库 | [#3](https://github.com/kimiyoko/uk-visa-sponsor-list/issues/3), [#14](https://github.com/kimiyoko/uk-visa-sponsor-list/issues/14) |
| ⑥ Track / 追踪 | Applications and funnel numbers<br>投递和漏斗数字 | Airtable (Huntr as backup; free tier capped at 100 applications)<br>Airtable（Huntr 备选，免费版上限 100 个投递） | No / 否 | [#20](https://github.com/kimiyoko/uk-visa-sponsor-list/issues/20), [#15](https://github.com/kimiyoko/uk-visa-sponsor-list/issues/15) |

**Priority score** (roles that pass L1 + L2 only): hiring signal 40 · sponsor rating + Companies House 25 · industry / unicorn lists 20 · employer-brand lists 15. Weights are a starting guess, recalibrated in week 3.
**优先级分**（只给通过 L1 + L2 的岗位）：在招信号 40 · 担保评级 + Companies House 25 · 行业 / 独角兽榜单 20 · 雇主品牌榜单 15。权重是起始假设，第 3 周校准。

Build issues went from 12 to 5: #20 tool selection, #3 experience bank, #6 L1, #7 L2, #21 L3 + L4. Tools the scan could not verify (e.g. Sponsorship Scout, Sponsor Seal, WPC Jobs) are not relied on. The full scan with sources is in the plan.
建设类 issue 从 12 个合并为 5 个：#20 工具选型、#3 经历库、#6 L1、#7 L2、#21 L3 + L4。搜不到可靠页面的工具（如 Sponsorship Scout、Sponsor Seal、WPC Jobs）不依赖；完整摸排和来源见计划文档。

## Records · 记录规则

- Weekly review every Sunday as an issue (template: *Weekly review*). Numbers only, no company names or personal details.
  每周日开一个周报 issue（模板：*Weekly review*），只写统计数字，不写公司名和个人信息。
- Personal data (applications, salaries, visa status) stays in the private tracker, never in this public repo.
  投递、薪资、签证状态等个人数据只放私有追踪表，不进这个公开仓库。
- Every decision that changes scope or priority goes into [project/decisions.md](project/decisions.md).
  每个改变范围或优先级的决定都写进 [project/decisions.md](project/decisions.md)。
- Every issue and description in this repo is written in English first, then Chinese.
  本仓库的 issue 和说明都写成英文在前、中文在后。

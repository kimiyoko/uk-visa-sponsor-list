# Decision log · 决策记录

Newest first. Each entry says what was decided, why, and what it changes.
最新的在最上面。每条写：决定了什么、为什么、影响什么。

| Date / 日期 | Decision / 决定 | Why / 原因 | Impact / 影响 |
| --- | --- | --- | --- |
| 2026-10-21 | Every GitHub description is written in English first, then Chinese<br>GitHub 上所有说明都写成英文在前、中文在后 | Readers include non-Chinese speakers<br>读者不只是中文用户 | All issues, milestones, labels, docs<br>所有 issue、里程碑、标签、文档 |
| 2026-10-21 | Build a company list and a role list separately and cross-check them before applying<br>公司清单和职位清单分开建，交叉验证后才投递 | The register says who can sponsor, job ads say who is hiring; neither is enough alone<br>名单只说明谁能担保，招聘广告只说明谁在招，单看一边都不够 | #6, plan funnel<br>#6、计划里的漏斗 |
| 2026-10-21 | Use existing tools wherever they cover a layer; build only L2 eligibility rules, L4 scoring and the experience / STAR bank<br>能用现成工具就用，只自建 L2 担保判断规则、L4 打分和经历库 / STAR 库 | Market scan found ready tools for scraping (Apify), company checks (Companies House MCP), CV matching (Teal / Jobscan), mock interviews (Yoodli) and tracking (Airtable)<br>摸排发现抓取（Apify）、公司核查（Companies House MCP）、简历匹配（Teal / Jobscan）、模拟面试（Yoodli）、追踪（Airtable）都有现成工具 | Build issues 12 → 5; #2, #5, #8, #9, #13 merged into #20, #6, #10, #3<br>建设类 issue 从 12 个减到 5 个；#2、#5、#8、#9、#13 并入 #20、#6、#10、#3 |
| 2026-10-21 | Rank by "paying to hire for UK roles now"; award lists only add points, never filter<br>按「正在为英国岗位花钱招人」排序；榜单只加分，不筛选 | Being on the register or an award list doesn't mean a company is hiring<br>在名单或榜单上不代表正在招人 | Priority score, #21<br>优先级分，#21 |
| 2026-10-21 | Don't rely on tools the scan couldn't verify; give third-party tools company names only<br>搜不到可靠页面的工具不依赖；给第三方工具只传公司名 | Unverified sources and extension permissions are a data and privacy risk<br>来源不明的工具和插件权限有数据和隐私风险 | #20<br>#20 |
| 2026-10-20 | Run the search as a 3-month project with gates G0–G4<br>按 3 个月项目推进，设 G0–G4 五道关卡 | Need a clear finish line and weekly checkpoints<br>需要明确的终点和每周检查点 | [ROADMAP.md](../ROADMAP.md), milestones, issues<br>[ROADMAP.md](../ROADMAP.md)、里程碑、issue |
| 2026-10-20 | Target data analyst (SOC 3544) roles first, decide at G3 (2026-12-11)<br>先主攻数据分析师（SOC 3544），G3（2026-12-11）决定去留 | 3544 is sponsorable only if the CoS is assigned before 2026-12-31<br>3544 只有 2026-12-31 前发出 CoS 才能担保 | 3544 applications front-loaded in Oct–Nov<br>3544 的投递集中在 10–11 月 |
| 2026-10-20 | Keep personal data in a private tracker; the public repo holds code and anonymous stats<br>个人数据只放私有追踪表；公开仓库只放代码和匿名统计 | Repo and site are public<br>仓库和网站是公开的 | #20<br>#20 |
| 2026-10-20 | Build role-level data next (job radar + eligibility check)<br>下一步建岗位级数据（岗位雷达 + 担保判断） | Company-level "hiring" doesn't say whether a role fits the visa rules<br>公司层面的「在招」说明不了岗位是否符合签证规则 | #6, #7<br>#6、#7 |
| 2026-10-19 | Label Claude web-search results separately from Google AI and hand-checked ones<br>Claude 网页搜索的结果和 Google AI、人工核实的分开标注 | Keep the source of every link visible<br>每条链接的来源都要看得到 | Page labels<br>网页标签 |
| 2026-10-16 | Look up companies with Google AI Mode in the desktop browser, starting with Manchester IT<br>用桌面浏览器里的 Google AI 模式查公司，从曼彻斯特 IT 开始 | Google results judged more accurate than Claude's own guesses<br>Google 的结果比 Claude 自己的推测更准 | `scripts/google_queue.py`, scheduled lookups<br>`scripts/google_queue.py`、定时查询 |
| 2026-10-16 | Publish the public site on GitHub Pages<br>公开网站发布在 GitHub Pages | claude.ai isn't reachable from mainland China<br>中国大陆打不开 claude.ai | `docs/`<br>`docs/` |
| 2026-10-15 | Use the official GOV.UK register as the single source, refreshed every weekday<br>以 GOV.UK 官方登记表为唯一数据源，每个工作日更新 | Authoritative and updated daily<br>权威且每天更新 | `scripts/update_register.py`, GitHub Actions<br>`scripts/update_register.py`、GitHub Actions |

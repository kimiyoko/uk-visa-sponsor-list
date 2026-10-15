# UK Visa Sponsor Finder · 英国工签担保雇主名单

**[English](#english)** · **[中文](#chinese)**

**Live site / 在线使用：** https://kimiyoko.github.io/uk-visa-sponsor-list/ (add `#en` or `#zh` to open in English or Chinese / 链接末尾加 `#en` 或 `#zh` 可直接打开对应语言)

---

<a id="english"></a>

## English

A tool for finding UK employers that can sponsor a work visa. The data comes from the official [Register of licensed sponsors: workers](https://www.gov.uk/government/publications/register-of-licensed-sponsors-workers), published by UK Visas and Immigration on GOV.UK, and is updated automatically every weekday.

### What it does

- Filter by **industry** (18 categories guessed from the company name), **town / county**, **visa route** (Skilled Worker, Global Business Mobility and others) and **rating**, and search by company name
- Filter by **date added to the register**: last 24 hours, last 7 days, last 30 days. Join dates are recorded from 2026-10-15 onwards
- Organisations added in the last 24 hours carry a **New added** badge next to their name
- Every organisation has links to its **website, careers page, LinkedIn jobs and Companies House**. Hand-checked links go straight to the page; the rest open a search for that company
- Save companies with ☆ and **download your saved list** as a CSV, or export the current filtered results
- Switch between **中文 and English** from the top right of the page

Please note: being on the register means an organisation is **allowed** to sponsor visas. It does not mean it is hiring, or that it will sponsor you. Industry tags are guessed from keywords in company names; names that give no clue are listed as "Unclassified".

### Repository layout

| Path | Contents |
|---|---|
| `src/sponsor-finder.html` | Page source (also used for the claude.ai version) |
| `docs/` | The GitHub Pages site: `index.html`, `data.json` (register data) and `links.json` (hand-checked website and careers links) |
| `scripts/build_data.py` | Turns the official CSV into the page data, adds industry tags and records join dates |
| `scripts/update_register.py` | Downloads the latest register, compares it with the previous one and updates the data |
| `scripts/make_static.py` | Builds `docs/index.html` from `src/` |
| `data/changes/<date>.json` | Organisations added and removed in each update |
| `data/history.csv` | One summary line per update (date, organisations, added, removed) |
| `apps-script/Code.gs` | Google Apps Script: saves each day's CSV to Google Drive and sends WeChat (PushPlus) and email alerts |
| `.github/workflows/update.yml` | Runs the update every weekday and commits the result |

### Setup

**1. Turn on GitHub Pages.** Settings → Pages → Source: **Deploy from a branch**, Branch: `main`, folder: `/docs` → Save. The site appears at the address above within a few minutes.

**2. Daily updates.** `.github/workflows/update.yml` checks GOV.UK at 10:20 and 15:20 UTC on weekdays. When a newer register is published it updates `docs/data.json`, records the changes and commits them. To run it by hand: Actions → **Daily register update** → **Run workflow**. If the workflow can't commit, go to Settings → Actions → General → Workflow permissions and choose **Read and write permissions**.

**3. WeChat and email alerts (optional).** See the notes at the top of `apps-script/Code.gs`. Put the PushPlus token and the email address in the Apps Script **Project Settings → Script Properties** as `PUSHPLUS_TOKEN` and `EMAIL_TO`. **Never commit the token to this repository.**

### Making changes

Edit the page in `src/sponsor-finder.html`, then rebuild the public copy:

```bash
python3 scripts/make_static.py
```

To change the industry tags, edit the `INDUSTRIES` keywords in `scripts/build_data.py` and rebuild from the latest CSV, passing the current data so join dates are kept:

```bash
python3 scripts/build_data.py <register.csv> /tmp/out docs/data.json
cp /tmp/out/data.json docs/data.json
```

To add a hand-checked website or careers link, edit `docs/links.json`. Each key is the organisation ID: a hash of `lower-case name|lower-case town` (see `hash()` in `src/sponsor-finder.html`). Set `status` to `verified`. Links verified on the claude.ai version are copied here automatically each weekday morning.

**Data format note:** each row in `data.json` ends with the join date, stored as days since 2020-01-01. `0` means the organisation was already on the register when tracking began.

### Data source and licence

Register data from GOV.UK, used under the [Open Government Licence v3.0](https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/). This tool is not affiliated with the UK Government.

---

<a id="chinese"></a>

## 中文

在英国找需要签证担保（visa sponsorship）的工作时，可以用这个工具筛选公司。数据来自 UK Visas and Immigration 在 GOV.UK 发布的官方登记表 [Register of licensed sponsors: workers](https://www.gov.uk/government/publications/register-of-licensed-sponsors-workers)，每个工作日自动更新。

### 能做什么

- 按 **行业**（从公司名推断，18 类）、**城市 / 郡**、**签证路线**（Skilled Worker、Global Business Mobility 等）、**评级** 筛选，支持搜索公司名
- 按 **加入名单时间** 筛选：24 小时内、7 日内、30 日内。从 2026-10-15 起记录每家公司加入名单的日期
- 24 小时内新加入的公司，名称旁会显示「今日新增」角标
- 每家公司附 **官网、招聘页、LinkedIn 职位、Companies House** 链接。核实过的直接打开对应页面，其余的打开该公司的搜索结果
- 点 ☆ 收藏公司，可以 **一键下载收藏名单**（CSV），也可以导出当前筛选结果
- 页面右上角可切换 **中文 / English**

需要注意：在名单上只说明这家公司**有资格**担保，不代表现在在招人，也不代表愿意给你担保。行业标签是根据公司名关键词推断的，名字看不出行业的公司归入「未分类」。

### 仓库结构

| 路径 | 内容 |
|---|---|
| `src/sponsor-finder.html` | 网页源文件（claude.ai 版本也用它） |
| `docs/` | GitHub Pages 发布的网页：`index.html`、`data.json`（名单数据）、`links.json`（核实过的官网 / 招聘页） |
| `scripts/build_data.py` | 把官方 CSV 转成网页数据，给公司打行业标签，并记录加入日期 |
| `scripts/update_register.py` | 下载最新登记表、和上一版对比、更新数据 |
| `scripts/make_static.py` | 由 `src/` 生成 `docs/index.html` |
| `data/changes/<日期>.json` | 每次更新新增和移除的公司 |
| `data/history.csv` | 每次更新的汇总（日期、机构数、新增、移除） |
| `apps-script/Code.gs` | Google Apps Script：每天存 CSV 到 Google Drive，推送微信（PushPlus）并发邮件 |
| `.github/workflows/update.yml` | 每个工作日自动运行更新，并提交到仓库 |

### 设置

**1. 开启 GitHub Pages。** Settings → Pages → Source 选 **Deploy from a branch**，Branch 选 `main`，文件夹选 `/docs`，保存。几分钟后就能访问上面的地址。

**2. 每日自动更新。** `.github/workflows/update.yml` 会在每个工作日 10:20 和 15:20（UTC）检查 GOV.UK。有新版就更新 `docs/data.json`，记录变化，然后自动提交。手动运行：Actions → **Daily register update** → **Run workflow**。如果 Actions 没有权限提交：Settings → Actions → General → Workflow permissions，选 **Read and write permissions**。

**3. 微信和邮件通知（可选）。** 见 `apps-script/Code.gs` 文件开头的说明。PushPlus token 和收件邮箱放在 Apps Script 的「项目设置 → 脚本属性」里，属性名分别是 `PUSHPLUS_TOKEN` 和 `EMAIL_TO`。**不要把 token 写进代码提交到 GitHub。**

### 修改

改网页：编辑 `src/sponsor-finder.html`，然后运行下面的命令生成公开版本：

```bash
python3 scripts/make_static.py
```

改行业标签：编辑 `scripts/build_data.py` 里的 `INDUSTRIES` 关键词，再用最新 CSV 重新生成。命令里带上当前数据，加入日期才不会丢：

```bash
python3 scripts/build_data.py <登记表.csv> /tmp/out docs/data.json
cp /tmp/out/data.json docs/data.json
```

添加核实过的官网 / 招聘页：编辑 `docs/links.json`。每条的键是公司 ID，由「公司名小写|城市小写」做哈希得到（算法见 `src/sponsor-finder.html` 里的 `hash()`），`status` 写 `verified`。在 claude.ai 版本里核实的链接，每个工作日早上会自动同步到这里。

**数据格式说明：** `data.json` 每行最后一个字段是加入日期，存为自 2020-01-01 起的天数；`0` 表示开始记录前已在名单上。

### 数据来源和许可

登记表数据来自 GOV.UK，使用 [Open Government Licence v3.0](https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/) 授权。本工具与英国政府无关。

# 英国工签担保雇主名单

在英国找需要签证担保（visa sponsorship）的工作时，可以用这个工具筛选公司。数据来自 UK Visas and Immigration 在 gov.uk 发布的官方登记表 [Register of licensed sponsors: workers](https://www.gov.uk/government/publications/register-of-licensed-sponsors-workers)，每个工作日自动更新。

**在线使用**：开启 GitHub Pages 后，地址是 `https://<你的用户名>.github.io/uk-visa-sponsor-list/`

## 能做什么

- 按 **行业**（从公司名推断，18 类）、**城市 / 郡**、**签证路线**（Skilled Worker、Global Business Mobility 等）、**评级** 筛选，支持搜索公司名
- 每家公司附 **官网、招聘页、LinkedIn 职位、Companies House** 链接。核实过的显示直达链接，其余的直接打开搜索结果
- 收藏公司，把当前筛选结果导出成 CSV
- 名单更新后，新出现的公司会标「本次新增」

需要注意：在名单上只说明这家公司**有资格**担保，不代表现在在招人，也不代表愿意给你担保。行业标签是根据公司名关键词推断的，名字看不出行业的公司归入「未分类」。

## 仓库结构

| 路径 | 内容 |
|---|---|
| `src/sponsor-finder.html` | 网页源文件（claude.ai 版本也用它） |
| `docs/` | GitHub Pages 发布的网页：`index.html`、`data.json`（名单数据）、`links.json`（核实过的官网/招聘页） |
| `scripts/build_data.py` | 把官方 CSV 转成网页数据，并给公司打行业标签 |
| `scripts/update_register.py` | 下载最新登记表、和上一版对比、更新数据 |
| `scripts/make_static.py` | 由 `src/` 生成 `docs/index.html` |
| `data/changes/<日期>.json` | 每次更新新增和移除的公司 |
| `data/history.csv` | 每次更新的汇总（日期、机构数、新增、移除） |
| `apps-script/Code.gs` | Google Apps Script：每天存 CSV 到 Google Drive，推送微信（PushPlus）并发邮件 |
| `.github/workflows/update.yml` | 每个工作日自动运行更新，并提交到仓库 |

## 设置

### 1. 开启 GitHub Pages
仓库 → **Settings** → **Pages** → Source 选 **Deploy from a branch**，Branch 选 `main`，文件夹选 `/docs`，保存。一两分钟后就能访问上面的地址。

### 2. 每日自动更新
`.github/workflows/update.yml` 会在每个工作日 10:20 和 15:20（UTC）检查 gov.uk。有新版就更新 `docs/data.json`，记录变化，然后自动提交。也可以在 **Actions** → **Daily register update** → **Run workflow** 手动运行。

如果 Actions 没有权限提交：Settings → Actions → General → Workflow permissions，选 **Read and write permissions**。

### 3. 微信和邮件通知（可选）
见 `apps-script/Code.gs` 文件开头的说明。PushPlus token 放在 Apps Script 的「项目设置 → 脚本属性」里，属性名 `PUSHPLUS_TOKEN`。**不要把 token 写进代码提交到 GitHub。**

### 修改网页
改 `src/sponsor-finder.html`，然后运行：

```bash
python3 scripts/make_static.py
```

### 修改行业标签
改 `scripts/build_data.py` 里的 `INDUSTRIES` 关键词，再用最新 CSV 重新生成：

```bash
python3 scripts/build_data.py <登记表.csv> /tmp/out docs/data.json
cp /tmp/out/data.json docs/data.json
```

### 添加核实过的官网 / 招聘页
编辑 `docs/links.json`。每条的键是公司 ID：对「公司名小写|城市小写」做哈希得到（算法见 `src/sponsor-finder.html` 里的 `hash()`）。`status` 写 `verified`。

## 数据来源和许可

登记表数据来自 gov.uk，使用 [Open Government Licence v3.0](https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/) 授权。本工具与英国政府无关。

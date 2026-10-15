/**
 * 英国工签担保雇主名单 · 每日更新到 Google Drive + 微信（PushPlus）+ 邮件
 *
 * 做什么：
 *   每个工作日从 gov.uk 下载最新的 Register of licensed sponsors: workers CSV，
 *   存进你 Google Drive 的「UK Sponsor Register」文件夹，和上一版对比，
 *   把新增 / 移除的公司写进「担保雇主名单 · 更新记录」表格，
 *   然后推送到微信（PushPlus）并发邮件给你。
 *
 * 第一次使用：
 *   1. 左侧齿轮「项目设置」→ 最下面「脚本属性」→ 添加两条：
 *        PUSHPLUS_TOKEN = 你的 PushPlus 用户 token
 *        EMAIL_TO       = 接收通知的邮箱
 *      （放在脚本属性里，代码公开到 GitHub 也不会泄露。）然后按需修改下方 KEYWORDS / PLACES。
 *   2. 在顶部函数下拉框选 setup，点「运行」，按提示授权（Drive、外部网络、发邮件）。
 *      setup 会建好每日定时，并立刻跑一次，建立第一版基线。
 *   3. 想测试微信推送，选 testPush 运行。
 */

// ======================= 设置 =======================

/** PushPlus 用户 token。更稳妥的做法：放到「项目设置 → 脚本属性」里，属性名 PUSHPLUS_TOKEN，然后把这里清空。 */
const PUSHPLUS_TOKEN = ''; // 不要把 token 写在这里提交到 GitHub，放在「项目设置 → 脚本属性」PUSHPLUS_TOKEN

/** 收邮件的地址。推荐放在「项目设置 → 脚本属性」EMAIL_TO（多个地址用逗号分隔）；都没填则发给运行脚本的 Google 账号。 */
const EMAIL_TO = '';

/** 你关注的关键词（公司名里出现就会在通知里优先列出、加 ★）。不区分大小写。 */
const KEYWORDS = ['software', 'tech', 'digital', 'data', 'care', 'health', 'nhs', 'engineering', 'finance', 'accountant'];

/** 你关注的城市 / 郡（出现就优先列出）。留空数组表示不限。 */
const PLACES = ['Stoke', 'Staffordshire', 'Manchester', 'Birmingham', 'London'];

/** 只统计这些签证路线（空数组 = 全部路线）。 */
const ROUTES = ['Skilled Worker'];

/** Drive 文件夹名、保留多少份历史 CSV。 */
const FOLDER_NAME = 'UK Sponsor Register';
const KEEP_CSV = 10;

/** 你的在线名单网页（通知里附上链接）。 */
const WEB_LIST_URL = 'https://claude.ai/artifact/YUqKN9s4QPjh3h5CkeKrRV';

/** 每天几点检查（英国时间，整点）。gov.uk 一般上午 9 点多更新。 */
const RUN_HOUR = 11;

// ===================================================

const CONTENT_API = 'https://www.gov.uk/api/content/government/publications/register-of-licensed-sponsors-workers';
const PAGE_URL = 'https://www.gov.uk/government/publications/register-of-licensed-sponsors-workers';
const LOG_SHEET_NAME = '担保雇主名单 · 更新记录';

/** 一次性设置：建立每日定时并立即运行一次。 */
function setup() {
  ScriptApp.getProjectTriggers()
    .filter((t) => t.getHandlerFunction() === 'dailyCheck')
    .forEach((t) => ScriptApp.deleteTrigger(t));
  ScriptApp.newTrigger('dailyCheck')
    .timeBased()
    .everyDays(1)
    .atHour(RUN_HOUR)
    .inTimezone('Europe/London')
    .create();
  dailyCheck();
}

/** 测试微信推送是否通。 */
function testPush() {
  const html = '<p>这是一条测试消息。以后 gov.uk 名单更新时，会在这里收到新增和移除的公司。</p>';
  const ok = pushPlus_('测试：担保名单通知已接通', html);
  Logger.log(ok ? 'PushPlus 推送成功，请看微信。' : 'PushPlus 推送失败，请检查脚本属性 PUSHPLUS_TOKEN。');
  const to = PropertiesService.getScriptProperties().getProperty('EMAIL_TO') || EMAIL_TO || Session.getEffectiveUser().getEmail();
  MailApp.sendEmail({ to: to, subject: '测试：担保名单通知已接通', htmlBody: html, name: '担保名单更新' });
  Logger.log('测试邮件已发到 ' + to + '（如果收件箱没有，看看垃圾邮件）');
}

/** 每日主流程。 */
function dailyCheck() {
  const props = PropertiesService.getScriptProperties();
  try {
    const latest = findLatestCsv_();
    const lastDate = props.getProperty('LAST_DATE');
    if (lastDate && latest.date && latest.date <= lastDate) {
      Logger.log('名单未更新，仍为 ' + lastDate);
      return;
    }

    const resp = UrlFetchApp.fetch(latest.url, { muteHttpExceptions: true, followRedirects: true });
    if (resp.getResponseCode() !== 200) throw new Error('下载 CSV 失败，HTTP ' + resp.getResponseCode());
    const text = resp.getContentText('UTF-8');
    const current = parseRegister_(text);

    const folder = getFolder_();
    const csvFile = folder.createFile(Utilities.newBlob(text, 'text/csv', latest.filename));
    pruneOldCsv_(folder);

    const prevId = props.getProperty('LAST_FILE_ID');
    let diff = null;
    if (prevId) {
      try {
        const prevText = DriveApp.getFileById(prevId).getBlob().getDataAsString('UTF-8');
        diff = diffRegisters_(parseRegister_(prevText), current);
      } catch (e) {
        Logger.log('读不到上一版 CSV，本次只建立基线：' + e);
      }
    }

    const dateLabel = latest.date || Utilities.formatDate(new Date(), 'Europe/London', 'yyyy-MM-dd');
    const sheetUrl = writeLog_(folder, dateLabel, current, diff);

    props.setProperty('LAST_DATE', dateLabel);
    props.setProperty('LAST_FILE_ID', csvFile.getId());

    notify_(dateLabel, current, diff, csvFile.getUrl(), sheetUrl);
  } catch (err) {
    const msg = '担保名单每日检查出错：' + (err && err.message ? err.message : err);
    Logger.log(msg);
    pushPlus_('担保名单检查出错', '<p>' + escapeHtml_(msg) + '</p><p>打开 Apps Script 的「执行记录」可以看到详情。</p>');
  }
}

// ---------------- 取数 ----------------

/** 从 gov.uk 内容接口找到最新的 Worker and Temporary Worker CSV。 */
function findLatestCsv_() {
  const resp = UrlFetchApp.fetch(CONTENT_API, { muteHttpExceptions: true });
  if (resp.getResponseCode() !== 200) throw new Error('gov.uk 内容接口返回 HTTP ' + resp.getResponseCode());
  const body = resp.getContentText();
  const urls = findCsvUrls_(body);
  if (!urls.length) throw new Error('在 gov.uk 页面里没找到 Worker and Temporary Worker 的 CSV 链接，页面结构可能变了：' + PAGE_URL);
  // 多个链接时取文件名日期最新的
  urls.sort((a, b) => (b.date || '').localeCompare(a.date || ''));
  return urls[0];
}

function findCsvUrls_(body) {
  const re = /https:\/\/assets\.publishing\.service\.gov\.uk\/[^"'\s<>\\]+?\.csv/gi;
  const seen = {};
  const out = [];
  let m;
  while ((m = re.exec(body)) !== null) {
    const url = m[0];
    if (seen[url]) continue;
    seen[url] = true;
    const filename = decodeURIComponent(url.split('/').pop());
    if (!/worker/i.test(filename)) continue;
    const d = filename.match(/(\d{4}-\d{2}-\d{2})/);
    out.push({ url: url, filename: filename, date: d ? d[1] : '' });
  }
  return out;
}

// ---------------- 解析与对比 ----------------

/** 解析登记表 CSV → { key: {name, town, county, rating, routes:Set-like obj} }，按 名称+城市 合并。 */
function parseRegister_(text) {
  if (text.charCodeAt(0) === 0xfeff) text = text.slice(1);
  const rows = Utilities.parseCsv(text);
  const head = rows[0].map((h) => String(h).trim().toLowerCase());
  const iName = head.indexOf('organisation name');
  const iTown = head.indexOf('town/city');
  const iCounty = head.indexOf('county');
  const iRating = head.indexOf('type & rating');
  const iRoute = head.indexOf('route');
  if (iName < 0) throw new Error('CSV 表头不认识：' + rows[0].join(', '));
  const routeFilter = ROUTES.map((r) => r.toLowerCase());
  const orgs = {};
  let total = 0;
  for (let i = 1; i < rows.length; i++) {
    const r = rows[i];
    const name = clean_(r[iName]);
    if (!name) continue;
    const route = clean_(r[iRoute]);
    if (routeFilter.length && routeFilter.indexOf(route.toLowerCase()) < 0) continue;
    total++;
    const town = clean_(r[iTown]);
    const key = (name + '|' + town).toLowerCase();
    const o = orgs[key] || (orgs[key] = { name: name, town: town, county: clean_(r[iCounty]), rating: clean_(r[iRating]), routes: {} });
    o.routes[route] = true;
  }
  return { orgs: orgs, rowCount: total, orgCount: Object.keys(orgs).length };
}

function diffRegisters_(prev, cur) {
  const added = [];
  const removed = [];
  Object.keys(cur.orgs).forEach((k) => { if (!prev.orgs[k]) added.push(cur.orgs[k]); });
  Object.keys(prev.orgs).forEach((k) => { if (!cur.orgs[k]) removed.push(prev.orgs[k]); });
  const score = (o) => (isInteresting_(o) ? 0 : 1);
  const byInterest = (a, b) => score(a) - score(b) || a.name.localeCompare(b.name);
  added.sort(byInterest);
  removed.sort(byInterest);
  return { added: added, removed: removed };
}

function isInteresting_(o) {
  const n = o.name.toLowerCase();
  const p = (o.town + ' ' + o.county).toLowerCase();
  const kw = KEYWORDS.some((k) => new RegExp('\\b' + escapeRe_(k.toLowerCase()) + '\\b').test(n));
  const pl = PLACES.length === 0 || PLACES.some((x) => p.indexOf(x.toLowerCase()) >= 0);
  return kw && pl;
}

// ---------------- Drive 输出 ----------------

function getFolder_() {
  const it = DriveApp.getFoldersByName(FOLDER_NAME);
  return it.hasNext() ? it.next() : DriveApp.createFolder(FOLDER_NAME);
}

/** 只保留最近 KEEP_CSV 份 CSV，更早的移到回收站（30 天内可恢复）。 */
function pruneOldCsv_(folder) {
  const files = [];
  const it = folder.getFilesByType('text/csv');
  while (it.hasNext()) files.push(it.next());
  files.sort((a, b) => b.getDateCreated() - a.getDateCreated());
  files.slice(KEEP_CSV).forEach((f) => f.setTrashed(true));
}

/** 写入「更新记录」表格：汇总 / 新增 / 移除 三个分页。返回表格链接。 */
function writeLog_(folder, dateLabel, current, diff) {
  const props = PropertiesService.getScriptProperties();
  let ss = null;
  const id = props.getProperty('LOG_SHEET_ID');
  if (id) { try { ss = SpreadsheetApp.openById(id); } catch (e) { ss = null; } }
  if (!ss) {
    ss = SpreadsheetApp.create(LOG_SHEET_NAME);
    DriveApp.getFileById(ss.getId()).moveTo(folder);
    const s1 = ss.getSheets()[0];
    s1.setName('汇总');
    s1.appendRow(['登记表日期', '机构数（所选路线）', '行数', '新增', '移除', '运行时间']);
    ss.insertSheet('新增').appendRow(['登记表日期', '关注', '公司名称', '城市', '郡', '评级', '路线', '搜官网', '搜招聘页']);
    ss.insertSheet('移除').appendRow(['登记表日期', '关注', '公司名称', '城市', '郡', '评级', '路线']);
    ss.getSheets().forEach((s) => { s.setFrozenRows(1); s.getRange(1, 1, 1, s.getLastColumn()).setFontWeight('bold'); });
    props.setProperty('LOG_SHEET_ID', ss.getId());
  }
  const now = Utilities.formatDate(new Date(), 'Europe/London', 'yyyy-MM-dd HH:mm');
  ss.getSheetByName('汇总').appendRow([dateLabel, current.orgCount, current.rowCount, diff ? diff.added.length : '首次基线', diff ? diff.removed.length : '', now]);
  if (diff && diff.added.length) {
    const rows = diff.added.map((o) => [dateLabel, isInteresting_(o) ? '★' : '', o.name, o.town, o.county, o.rating, Object.keys(o.routes).join(' / '),
      'https://www.google.com/search?q=' + encodeURIComponent('"' + o.name + '" ' + o.town + ' official website'),
      'https://www.google.com/search?q=' + encodeURIComponent('"' + o.name + '" careers jobs')]);
    appendRows_(ss.getSheetByName('新增'), rows);
  }
  if (diff && diff.removed.length) {
    const rows = diff.removed.map((o) => [dateLabel, isInteresting_(o) ? '★' : '', o.name, o.town, o.county, o.rating, Object.keys(o.routes).join(' / ')]);
    appendRows_(ss.getSheetByName('移除'), rows);
  }
  return ss.getUrl();
}

function appendRows_(sheet, rows) {
  sheet.getRange(sheet.getLastRow() + 1, 1, rows.length, rows[0].length).setValues(rows);
}

// ---------------- 通知 ----------------

function notify_(dateLabel, current, diff, csvUrl, sheetUrl) {
  const title = diff
    ? `担保名单 ${dateLabel}：新增 ${diff.added.length}，移除 ${diff.removed.length}`
    : `担保名单 ${dateLabel}：已建立基线（${current.orgCount} 家）`;
  const html = buildHtml_(dateLabel, current, diff, csvUrl, sheetUrl);
  pushPlus_(title, html);
  const to = PropertiesService.getScriptProperties().getProperty('EMAIL_TO') || EMAIL_TO || Session.getEffectiveUser().getEmail();
  if (to) MailApp.sendEmail({ to: to, subject: title, htmlBody: html, name: '担保名单更新' });
}

function buildHtml_(dateLabel, current, diff, csvUrl, sheetUrl) {
  const routeLabel = ROUTES.length ? ROUTES.join(' / ') : '全部路线';
  let h = `<p><b>登记表 ${escapeHtml_(dateLabel)} 版</b> · ${routeLabel} · 共 ${current.orgCount} 家机构</p>`;
  if (!diff) {
    h += '<p>这是第一次运行，已保存为基线。从下一次更新起，会推送新增和移除的公司。</p>';
  } else {
    h += section_('新增', diff.added, 20);
    h += section_('移除（如果你投过这些公司要留意）', diff.removed, 10);
  }
  h += `<p><a href="${WEB_LIST_URL}">打开在线名单（可筛选）</a><br>` +
       `<a href="${sheetUrl}">Drive 更新记录表</a> · <a href="${csvUrl}">今日 CSV</a> · <a href="${PAGE_URL}">gov.uk 原页面</a></p>`;
  h += '<p style="color:#888;font-size:12px">★ = 名称含你关注的关键词且在关注城市。名单只说明有担保资格，不代表正在招人。</p>';
  return h;
}

function section_(label, list, max) {
  if (!list.length) return `<p><b>${label}：</b>无</p>`;
  const items = list.slice(0, max).map((o) => {
    const star = isInteresting_(o) ? '★ ' : '';
    const q = encodeURIComponent('"' + o.name + '" careers jobs');
    return `<li>${star}<a href="https://www.google.com/search?q=${q}">${escapeHtml_(o.name)}</a> · ${escapeHtml_(o.town || o.county || '')}</li>`;
  }).join('');
  const more = list.length > max ? `<p>……另有 ${list.length - max} 家，见 Drive 表格。</p>` : '';
  return `<p><b>${label}（${list.length}）：</b></p><ul>${items}</ul>${more}`;
}

/** 推送到微信（PushPlus）。返回是否成功。 */
function pushPlus_(title, html) {
  const token = PropertiesService.getScriptProperties().getProperty('PUSHPLUS_TOKEN') || PUSHPLUS_TOKEN;
  if (!token) { Logger.log('未设置 PUSHPLUS_TOKEN，跳过微信推送'); return false; }
  const body = html.length > 18000 ? html.slice(0, 18000) + '<p>（内容过长已截断，见邮件或 Drive）</p>' : html;
  const resp = UrlFetchApp.fetch('https://www.pushplus.plus/send', {
    method: 'post',
    contentType: 'application/json',
    payload: JSON.stringify({ token: token, title: title, content: body, template: 'html' }),
    muteHttpExceptions: true,
  });
  let ok = false;
  try { ok = JSON.parse(resp.getContentText()).code === 200; } catch (e) {}
  if (!ok) Logger.log('PushPlus 返回：' + resp.getResponseCode() + ' ' + resp.getContentText());
  return ok;
}

// ---------------- 小工具 ----------------

function clean_(s) { return String(s == null ? '' : s).replace(/\s+/g, ' ').trim(); }
function escapeRe_(s) { return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'); }
function escapeHtml_(s) { return String(s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c])); }

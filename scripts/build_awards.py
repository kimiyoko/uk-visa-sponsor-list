"""Build docs/awards.json: award lists grouped into themes and matched to the sponsor register.

Usage: python3 scripts/build_awards.py [docs/data.json] [docs/awards.json]

Raw lists live in data/awards/ (one file per list, see LISTS below for the format of each).
Companies are matched to the register by name only, so the result is a lead, not proof:
  - "core" name = lower case, accents and punctuation removed, legal / generic endings
    (Ltd, plc, LLP, UK, Group, Holdings, International...) stripped from the end;
  - a match needs the same core name. One-word names that are short (≤ 6 letters) or an
    ordinary English word (e.g. "Unit", "Merge", "Chapter") are only matched for UK-only lists and only when exactly one register
    organisation has that core name; otherwise they are listed as "not matched";
  - trading names count: a register entry such as "ABC Ltd T/A Brand", "t/as", "TA", "trading as",
    "d/b/a" or "(formerly X)" is indexed under the legal name and under each trading / former name.
    A legal-name match wins; a trading name is used only when no legal name matches, exactly one
    organisation trades under it (many "t/a Specsavers" franchisees are not Specsavers itself)
    and it isn't a short or ordinary word;
  - one name, one answer: if a name is matched on any list, the same name on every other list
    is matched to the same organisation (so a company never appears twice, matched and unmatched).
Runs in the daily update (.github/workflows/update.yml) after the register is refreshed.
Organisation IDs are the same hash the page uses: hash(lower-case name | lower-case town).
"""
import json, os, re, sys, unicodedata, datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "data", "awards")

DIMS = {
    "fintech": {"zh": "金融科技", "en": "Fintech",
                "desc_zh": "金融科技公司和金融技术供应商的榜单。", "desc_en": "Lists of fintech companies and financial technology suppliers."},
    "women": {"zh": "女性友好", "en": "Women-friendly",
              "desc_zh": "女性职场和性别平等方面的雇主榜单。", "desc_en": "Employer lists for women at work and gender equality."},
    "unicorn": {"zh": "独角兽", "en": "Unicorn",
                "desc_zh": "估值 10 亿美元以上、尚未上市的创业公司。", "desc_en": "Private start-ups valued at $1bn or more."},
    "growth": {"zh": "高增长", "en": "High growth",
               "desc_zh": "按营收增长排名的公司、热门创业公司和英国国王企业奖得主。", "desc_en": "Companies ranked by revenue growth, rising start-ups and King's Award for Enterprise winners."},
    "ai": {"zh": "人工智能", "en": "AI",
           "desc_zh": "人工智能领域的创业公司榜单。", "desc_en": "Lists of AI start-ups."},
    "employer": {"zh": "最佳雇主", "en": "Best employer",
                 "desc_zh": "按员工评价或人力资源认证评出的英国最佳雇主。", "desc_en": "UK best employers, rated by staff reviews or HR certification."},
}

# fmt: "years" = lines "YYYY: a; b; c"; "digits" = "Name|<last digits of 202x years>[|UK]" joined by ';';
#      "snapshot" = "Name[|UK]" joined by ';' (one undated snapshot, year given below)
LISTS = {
    "forbes_fintech50": dict(dim="fintech", file="forbes_fintech50.txt", fmt="years", scope="global",
        zh="福布斯金融科技 50 强", en="Forbes Fintech 50", publisher="Forbes",
        url="https://www.forbes.com/lists/fintech50/",
        coverage_zh="2022–2026 年，每年 50 家，完整收录。", coverage_en="2022–2026, 50 a year, complete."),
    "idc_fintech100": dict(dim="fintech", file="idc_top100.txt", fmt="years", scope="global",
        zh="IDC 金融科技百强", en="IDC FinTech Rankings Top 100", publisher="IDC",
        url="https://idc.com/research/industry/fintech-rankings",
        coverage_zh="2024–2026 年完整；2022、2023 年公开资料只列出部分公司。", coverage_en="2024–2026 complete; 2022 and 2023 only partly public."),
    "forbes_women": dict(dim="women", file="forbes_women.txt", fmt="digits", scope="global",
        zh="福布斯全球女性最佳雇主", en="Forbes World's Top Companies for Women", publisher="Forbes × Statista",
        url="https://www.forbes.com/lists/top-companies-women/",
        coverage_zh="2023–2026 年，每年 400 家，完整收录；2021、2022 年的数据在福布斯网站上已不完整。", coverage_en="2023–2026, 400 a year, complete; 2021 and 2022 are no longer complete on Forbes."),
    "gptw_women": dict(dim="women", file="gptw_women.txt", fmt="digits", scope="uk",
        zh="英国女性最佳职场", en="UK's Best Workplaces for Women", publisher="Great Place To Work UK",
        url="https://www.greatplacetowork.co.uk/best-workplaces/women/2026",
        coverage_zh="2022–2026 年，每年 260–350 家，完整收录。", coverage_en="2022–2026, 260–350 a year, complete."),
    "times_gender50": dict(dim="women", file="times_top50.txt", fmt="years", scope="uk",
        zh="泰晤士报性别平等雇主 50 强", en="The Times Top 50 Employers for Gender Equality", publisher="The Times × Business in the Community",
        url="https://www.bitc.org.uk/the-times-top-50-employers-for-gender-equality/",
        coverage_zh="2022–2026 年，每年 50 家，完整收录（2022 年名为 Top 50 Employers for Women）。", coverage_en="2022–2026, 50 a year, complete (called Top 50 Employers for Women in 2022)."),
    "cbinsights_unicorns": dict(dim="unicorn", file="cbinsights.txt", fmt="snapshot", snapshot_year=2026, scope="global",
        zh="CB Insights 独角兽全名单", en="CB Insights Complete List of Unicorn Companies", publisher="CB Insights",
        url="https://www.cbinsights.com/research-unicorn-companies",
        coverage_zh="实时名单，2026 年 10 月抓取，约 1,450 家（已上市或跌出的公司不在其中）。", coverage_en="Live list taken October 2026, about 1,450 companies (those that listed or dropped out are not included)."),
    "hurun_unicorns": dict(dim="unicorn", file="hurun_uk.txt", fmt="years", scope="global",
        zh="胡润全球独角兽榜", en="Hurun Global Unicorn Index", publisher="Hurun Research Institute",
        url="https://www.hurun.co.uk/uk-unicorns-2026",
        coverage_zh="只收录 2026 年报告里点名的英国独角兽；完整名单放在网页表格控件里，无法提取。", coverage_en="Only the UK unicorns named in the 2026 report; the full list sits in an embedded table that can't be extracted."),
    "pwc_unicorns100": dict(dim="unicorn", file="pwc_top100.txt", fmt="years", scope="global",
        zh="普华永道全球独角兽 100 强", en="PwC Global Top 100 Unicorns", publisher="PwC",
        url="https://www.pwc.co.uk/services/audit/insights/global-top-100-unicorns.html",
        coverage_zh="2022–2025 年报告只公布汇总，不列完整 100 家；这里只收录报告正文点名的公司。", coverage_en="The 2022–2025 reports publish totals, not the full 100; only companies named in the text are included."),
    "deloitte_fast50": dict(dim="growth", file="deloitte_fast50.txt", fmt="years", scope="uk",
        zh="德勤英国科技 Fast 50", en="Deloitte UK Technology Fast 50", publisher="Deloitte",
        url="https://www.deloitte.co.uk/fast50/winners/2025/",
        coverage_zh="2021–2025 年，每年 50 家，完整收录。", coverage_en="2021–2025, 50 a year, complete."),
    "cbinsights_fintech100": dict(dim="fintech", file="cbinsights_fintech100.txt", fmt="years", scope="global",
        zh="CB Insights 金融科技 100 强", en="CB Insights Fintech 100", publisher="CB Insights",
        url="https://www.cbinsights.com/research/report/fintech-100-most-promising-fintech-startups-2025/",
        coverage_zh="2023–2026 年，从榜单图片逐个转录，可能有个别拼写差异；2022 年发布的是 Fintech 250，未收录。", coverage_en="2023–2026, transcribed from the list images, so a few spellings may differ; 2022 was the Fintech 250 and isn't included."),
    "wifc": dict(dim="women", file="wifc.txt", fmt="years", scope="uk",
        zh="金融业女性宪章签署机构", en="Women in Finance Charter signatories", publisher="HM Treasury (英国财政部)",
        url="https://www.gov.uk/government/publications/women-in-finance-charter",
        coverage_zh="英国政府数据。2026 年 6 月的当前签署名单，约 420 家；名单只有当前版本，没有按年份。", coverage_en="UK government data. Current signatories as of June 2026, about 420; only the current list exists, not one per year."),
    "gender_pay_gap": dict(dim="women", file="gender_pay_gap.txt", fmt="digits", scope="uk",
        zh="性别薪酬差距小的雇主", en="Employers with a small gender pay gap", publisher="UK gender pay gap service (英国政府)",
        url="https://gender-pay-gap.service.gov.uk/",
        coverage_zh="英国政府数据，250 人以上雇主必须申报。筛选条件：时薪中位数差距 ≤ 5%，且薪酬最高四分之一里女性 ≥ 40%，近 5 个申报年里至少 3 年符合。年份按公布年份记（2021/22 申报年记为 2022）。", coverage_en="UK government data; employers with 250+ staff must report. Included if the median hourly pay gap is 5% or less and women are at least 40% of the top pay quarter, in at least 3 of the last 5 reporting years. Years are the year published (2021/22 shows as 2022)."),
    "gptw_best": dict(dim="employer", file="gptw_best.txt", fmt="digits", scope="uk",
        zh="英国最佳职场", en="UK's Best Workplaces", publisher="Great Place To Work UK",
        url="https://www.greatplacetowork.co.uk/best-workplaces/2026",
        coverage_zh="2022–2026 年，大、中、小型组织全部类别，完整收录，约 1,000 家。", coverage_en="2022–2026, all size categories, complete, about 1,000 organisations."),
    "glassdoor_uk": dict(dim="employer", file="glassdoor_uk.txt", fmt="years", scope="uk",
        zh="Glassdoor 英国最佳工作场所", en="Glassdoor Best Places to Work UK", publisher="Glassdoor",
        url="https://www.glassdoor.co.uk/Award/Best-Places-to-Work-UK-LST_KQ0,22.htm",
        coverage_zh="2022–2026 年，每年 50 家，按员工匿名评价评出，完整收录。", coverage_en="2022–2026, 50 a year, based on anonymous staff reviews, complete."),
    "top_employers_uk": dict(dim="employer", file="top_employers_uk.txt", fmt="years", scope="uk",
        zh="英国杰出雇主认证", en="Top Employers United Kingdom", publisher="Top Employers Institute",
        url="https://www.top-employers.com/en-GB/",
        coverage_zh="2026 年约 100 家（来自媒体公布的完整名单）；2025 年只找到媒体点名的 23 家；更早年份没有公开名单。", coverage_en="2026: about 100 (full list published in the press); 2025: only the 23 named in the press; no public list for earlier years."),
    "statista_best_employers_uk": dict(dim="employer", file="statista_best_employers_uk.txt", fmt="years", scope="uk",
        zh="英国最佳雇主（Statista × 金融时报）", en="UK's Best Employers (Statista × Financial Times)", publisher="Statista × Financial Times",
        url="https://rankings.statista.com/en/employers/rankings/best-employers-uk-2026/",
        coverage_zh="2025、2026 年，每年 500 家，基于大规模员工匿名调查，完整收录；更早年份 Statista 已不提供。", coverage_en="2025 and 2026, 500 a year, based on a large anonymous staff survey, complete; earlier years are no longer on Statista."),
    "forbes_ai50": dict(dim="ai", file="forbes_ai50.txt", fmt="years", scope="global",
        zh="福布斯 AI 50", en="Forbes AI 50", publisher="Forbes",
        url="https://www.forbes.com/lists/ai50/",
        coverage_zh="2022–2026 年，每年 50 家，完整收录。大多是美国公司。", coverage_en="2022–2026, 50 a year, complete. Mostly US companies."),
    "cbinsights_ai100": dict(dim="ai", file="cbinsights_ai100.txt", fmt="years", scope="global",
        zh="CB Insights AI 100", en="CB Insights AI 100", publisher="CB Insights",
        url="https://www.cbinsights.com/research/report/artificial-intelligence-top-startups-2025/",
        coverage_zh="2022、2024、2025、2026 年，从榜单图片逐个转录；2023 年的榜单页没有找到。", coverage_en="2022, 2024, 2025 and 2026, transcribed from the list images; the 2023 page couldn't be found."),
    "ft1000_uk": dict(dim="growth", file="ft1000_uk.txt", fmt="years", scope="uk",
        zh="金融时报欧洲增长最快公司 1000 强（英国部分）", en="FT 1000: Europe's Fastest-Growing Companies (UK entries)", publisher="Financial Times × Statista",
        url="https://rankings.statista.com/en/fastest-growing-companies/rankings/europes-fastest-growing-companies-2026/",
        coverage_zh="2025、2026 年，只收总部在英国的公司（每年 130–180 家）；2022–2024 年 Statista 已不提供。", coverage_en="2025 and 2026, UK-headquartered companies only (130–180 a year); 2022–2024 are no longer on Statista."),
    "linkedin_startups_uk": dict(dim="growth", file="linkedin_startups_uk.txt", fmt="years", scope="uk",
        zh="领英英国热门创业公司", en="LinkedIn Top Startups UK", publisher="LinkedIn News UK",
        url="https://www.linkedin.com/pulse/linkedin-top-startups-2025-20-uk-companies-rise-linkedin-news-uk-vczpc",
        coverage_zh="2022–2025 年，每年 15–20 家，完整收录；2026 年版还没找到。", coverage_en="2022–2025, 15–20 a year, complete; the 2026 edition wasn't found yet."),
    "kings_awards": dict(dim="growth", file="kings_awards.txt", fmt="years", scope="uk",
        zh="英国国王企业奖", en="King's Awards for Enterprise", publisher="The Gazette (英国政府公报)",
        url="https://www.gov.uk/kings-awards-for-enterprise",
        coverage_zh="英国政府奖项，含国际贸易、创新、可持续发展、促进机会四类。2022–2026 年（2022 年为女王企业奖），从政府公报 PDF 解析，个别名称可能被拆开或合并。", coverage_en="UK government award for international trade, innovation, sustainable development and promoting opportunity. 2022–2026 (Queen's Awards in 2022), parsed from Gazette PDFs, so a few names may be split or joined."),
}

MISSING = [
    dict(dim="fintech", zh="CNBC × Statista 全球金融科技榜", en="CNBC World's Top Fintech Companies", publisher="CNBC × Statista",
         url="https://www.cnbc.com/the-worlds-top-fintech-companies-2025/",
         reason_zh="CNBC 网站拒绝访问，网页存档里也没有名单表格，暂未收录。", reason_en="CNBC's site refused access and archived copies don't contain the tables, so it isn't included yet."),
    dict(dim="fintech", zh="CNBC × Statista 英国金融科技 150 强", en="CNBC × Statista Top Fintech Companies UK", publisher="CNBC × Statista",
         url="https://www.cnbc.com/",
         reason_zh="和全球榜一样，CNBC 网站拒绝访问、存档里没有表格，暂未收录。", reason_en="As with the world list, CNBC's site refused access and archives have no tables, so it isn't included yet."),
    dict(dim="fintech", zh="毕马威 × H2 Ventures 金融科技 100 强", en="KPMG × H2 Ventures Fintech100", publisher="KPMG × H2 Ventures",
         url="https://home.kpmg/xx/en/home/industries/financial-services/fintech100.html",
         reason_zh="2019 年后停办，最近一期已超出 5 年范围，不收录。", reason_en="Discontinued after 2019, so the latest edition is outside the five-year window; not included."),
    dict(dim="growth", zh="德勤 EMEA 科技 Fast 500", en="Deloitte Technology Fast 500 EMEA", publisher="Deloitte",
         url="https://www.deloitte.com/uk/en/services/deloitte-private/about/emea-tech-fast500-winners.html",
         reason_zh="网页只列前几名，完整 500 家名单不公开发布，暂未收录。英国部分基本已被德勤英国 Fast 50 覆盖。", reason_en="The site lists only the top few; the full 500 isn't published, so it isn't included. UK entries are mostly covered by the Deloitte UK Fast 50."),
]

# Hand-checked false matches: (core name on the list, register organisation name) that are NOT the same company.
NOT_SAME = {
    ("gupshup", "A Squared Eats Ltd t/a Gupshup"),  # restaurant, not the messaging unicorn
    ("burger king", "NI Trade Ltd T/A Burger King"),  # single franchisee, not Burger King UK
    ("co op", "DANU RETAIL LIMITED T/A CO OP"),  # a convenience store, not the Co-op Group
    ("holiday inn", "Pool Cottages (Kenilworth) Limited T/A Holiday Inn"),  # one franchised hotel
}

GENERIC_END = set("""limited ltd plc llp lp llc inc incorporated corp corporation co company companies group holdings holding
uk u k gb britain great international intl europe emea global worldwide the and services ireland i ag sa se nv bv gmbh
""".split())


def norm(s):
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    s = s.replace("&", " and ").replace("’", "'")
    s = re.sub(r"\(.*?\)", " ", s)
    s = re.sub(r"\bt/a\b.*", " ", s)
    s = re.sub(r"[^a-z0-9]+", " ", s)
    s = re.sub(r"\bunited kingdom\b", " uk ", s)
    return s.split()


TA_SPLIT_CS = re.compile(r"\sTA\s")  # bare "TA" only in capitals, so words like "Pasta Ta Mare" aren't split


def name_parts(s):
    """Legal name first, then any trading or former names: "ABC Ltd T/A Brand (formerly Old)" -> [ABC Ltd, Brand, Old]."""
    s = TA_SPLIT_CS.sub(" t/a ", s)
    parts = [p.strip(" ()'\"") for p in re.split(r"\s*[(,]?\s*\b(?:t\s*/\s*as?|trading\s+as|d\s*/\s*b\s*/\s*a|dba|formerly)\b\.?\s*:?\s*", s, flags=re.I)]
    return [p for p in parts if p]


def core(s):
    t = norm(s)
    while t and t[-1] in GENERIC_END:
        t.pop()
    while t and t[0] == "the":
        t.pop(0)
    return " ".join(t)


def _load_words():
    words = set()
    for path in ("/usr/share/hunspell/en_US.dic", "/usr/share/hunspell/en_GB.dic", "/usr/share/dict/words"):
        if os.path.exists(path):
            for line in open(path, encoding="utf-8", errors="ignore"):
                w = line.split("/")[0].strip().lower()
                if w.isalpha():
                    words.add(w)
    return words


WORDS = _load_words()


def weak(c):
    """One short or ordinary English word (e.g. "Unit", "Chapter"): too likely to clash with another company."""
    return " " not in c and (len(c) <= 6 or c in WORDS)


def js_hash(s):
    h1, h2 = 0x811C9DC5, 0x9747B28C
    units = s.encode("utf-16-le")
    for i in range(0, len(units), 2):
        c = units[i] | (units[i + 1] << 8)
        h1 = ((h1 ^ c) * 16777619) & 0xFFFFFFFF
        h2 = ((h2 ^ c) * 2246822519) & 0xFFFFFFFF
    return f"{h1:08x}{h2:08x}"


def read_list(cfg):
    """Return {name: set(years)} and per-name UK flag."""
    txt = open(os.path.join(SRC, cfg["file"]), encoding="utf-8").read().strip()
    out, uk = {}, set()
    if cfg["fmt"] == "years":
        for line in txt.splitlines():
            if ":" not in line:
                continue
            y, rest = line.split(":", 1)
            for n in rest.split(";"):
                n = n.strip()
                if n:
                    out.setdefault(n, set()).add(int(y))
    else:
        for item in txt.split(";"):
            parts = [p.strip() for p in item.split("|")]
            if not parts[0]:
                continue
            n = parts[0]
            if cfg["fmt"] == "digits":
                ys = {2020 + int(d) for d in parts[1]}
                flag = parts[2:] == ["UK"]
            else:
                ys = {cfg["snapshot_year"]}
                flag = parts[1:] == ["UK"]
            out.setdefault(n, set()).update(ys)
            if flag:
                uk.add(n)
    # merge names that are the same company spelt slightly differently within one list
    merged, canon = {}, {}
    for n in sorted(out, key=lambda x: (-len(out[x]), x)):
        c = core(n) or n.lower()
        if c in canon:
            merged[canon[c]] |= out[n]
            if n in uk:
                uk.add(canon[c])
        else:
            canon[c] = n
            merged[n] = set(out[n])
    return merged, uk


def main():
    data_path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "docs", "data.json")
    out_path = sys.argv[2] if len(sys.argv) > 2 else os.path.join(ROOT, "docs", "awards.json")
    d = json.load(open(data_path, encoding="utf-8"))
    index, n_trading = {}, 0
    for r in d["rows"]:
        town = d["towns"][r[1]] if r[1] >= 0 else ""
        oid = js_hash(r[0].lower() + "|" + town.lower())
        parts = name_parts(r[0])
        for i, nm in enumerate(parts):
            c = core(nm)
            if c and all(h[0] != oid for h in index.get(c, [])):
                index.setdefault(c, []).append((oid, r[0], town, int(i > 0)))
                if i > 0:
                    n_trading += 1

    def pick(hits):
        """Legal names win. A trading name only counts when one organisation uses it:
        "t/a Specsavers" or "t/a McDonald's" is a franchisee, not the company on the list."""
        legal = [h for h in hits if not h[3]]
        if legal:
            return legal
        return hits if len(hits) == 1 else []

    loaded = {key: read_list(cfg) for key, cfg in LISTS.items()}
    # pass 1: names each list can match on its own; a name matched anywhere is matched everywhere
    confirmed = {}
    for key, cfg in LISTS.items():
        for n in loaded[key][0]:
            c = core(n)
            hits = pick([h for h in index.get(c, []) if (c, h[1]) not in NOT_SAME])
            if hits and hits[0][3] and weak(c):
                hits = []  # "t/a Reward", "t/a Impact": an ordinary word as a trading name is too loose
            if hits and (not weak(c) or (cfg["scope"] == "uk" and len(hits) == 1)):
                confirmed[c] = hits

    lists, orgs, entries = {}, {}, {}
    via_trading = 0
    for key, cfg in LISTS.items():
        names, uk = loaded[key]
        rows, matched = [], 0
        for n in sorted(names, key=str.lower):
            c = core(n)
            hits = confirmed.get(c) or []
            years = sorted(names[n])
            row = {"n": n, "y": years}
            if n in uk:
                row["uk"] = 1
            if hits:
                matched += 1
                row["m"] = [[oid, nm, town, ta] for oid, nm, town, ta in hits[:5]]
                via_trading += sum(h[3] for h in hits[:5])
                for oid, _, _, _ in hits:
                    orgs.setdefault(oid, []).append({"list": key, "years": years})
            elif index.get(c):
                row["amb"] = len(index[c])
            rows.append(row)
        entries[key] = rows
        ys = sorted({y for v in names.values() for y in v})
        lists[key] = {k: cfg[k] for k in ("dim", "zh", "en", "publisher", "url", "coverage_zh", "coverage_en", "scope")}
        lists[key].update(years=ys, count=len(rows), matched=matched)
        print(f"{key:22s} {len(rows):5d} companies  {matched:4d} matched  years {ys}")
    print(f"register trading / former names indexed: {n_trading}; list matches made through a trading name: {via_trading}")

    out = {"version": 2, "generated": datetime.date.today().isoformat(), "dims": DIMS, "lists": lists,
           "missing": MISSING, "orgs": orgs, "entries": entries}
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))
    print("organisations tagged:", len(orgs), "→", out_path, os.path.getsize(out_path), "bytes")


if __name__ == "__main__":
    main()

"""Build docs/awards.json: award lists grouped into four dimensions and matched to the sponsor register.

Usage: python3 scripts/build_awards.py [docs/data.json] [docs/awards.json]

Raw lists live in data/awards/ (one file per list, see LISTS below for the format of each).
Companies are matched to the register by name only, so the result is a lead, not proof:
  - "core" name = lower case, accents and punctuation removed, legal / generic endings
    (Ltd, plc, LLP, UK, Group, Holdings, International...) stripped from the end;
  - a match needs the same core name. One-word names that are short (≤ 6 letters) or an
    ordinary English word (e.g. "Unit", "Merge", "Chapter") are only matched for UK-only lists and only when exactly one register
    organisation has that core name; otherwise they are listed as "not matched".
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
               "desc_zh": "按营收增长排名的英国科技公司。", "desc_en": "UK tech companies ranked by revenue growth."},
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
}

MISSING = [
    dict(dim="fintech", zh="CNBC × Statista 全球金融科技榜", en="CNBC World's Top Fintech Companies", publisher="CNBC × Statista",
         url="https://www.cnbc.com/the-worlds-top-fintech-companies-2025/",
         reason_zh="CNBC 网站拒绝访问，网页存档里也没有名单表格，暂未收录。", reason_en="CNBC's site refused access and archived copies don't contain the tables, so it isn't included yet."),
]

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
    index = {}
    for r in d["rows"]:
        town = d["towns"][r[1]] if r[1] >= 0 else ""
        oid = js_hash(r[0].lower() + "|" + town.lower())
        names = [r[0]] + [p for p in re.split(r"\bt/a\b|\btrading as\b", r[0], flags=re.I)[1:]]
        for nm in names:
            c = core(nm)
            if c:
                index.setdefault(c, []).append((oid, r[0], town))

    lists, orgs, entries = {}, {}, {}
    for key, cfg in LISTS.items():
        names, uk = read_list(cfg)
        rows, matched = [], 0
        for n in sorted(names, key=str.lower):
            c = core(n)
            hits = index.get(c, [])
            ok = bool(hits) and (not weak(c) or (cfg["scope"] == "uk" and len(hits) == 1))
            years = sorted(names[n])
            row = {"n": n, "y": years}
            if n in uk:
                row["uk"] = 1
            if ok:
                matched += 1
                row["m"] = [[oid, nm, town] for oid, nm, town in hits[:5]]
                for oid, _, _ in hits:
                    orgs.setdefault(oid, []).append({"list": key, "years": years})
            elif hits:
                row["amb"] = len(hits)
            rows.append(row)
        entries[key] = rows
        ys = sorted({y for v in names.values() for y in v})
        lists[key] = {k: cfg[k] for k in ("dim", "zh", "en", "publisher", "url", "coverage_zh", "coverage_en", "scope")}
        lists[key].update(years=ys, count=len(rows), matched=matched)
        print(f"{key:22s} {len(rows):5d} companies  {matched:4d} matched  years {ys}")

    out = {"version": 2, "generated": datetime.date.today().isoformat(), "dims": DIMS, "lists": lists,
           "missing": MISSING, "orgs": orgs, "entries": entries}
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))
    print("organisations tagged:", len(orgs), "→", out_path, os.path.getsize(out_path), "bytes")


if __name__ == "__main__":
    main()

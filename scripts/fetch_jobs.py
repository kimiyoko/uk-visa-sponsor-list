"""Daily job radar: Adzuna ads that mention visa sponsorship + company career sites (Apify) → sponsor-register match → L2 → private Airtable.
每日岗位雷达：Adzuna 上提到担保的广告 + 公司招聘官网岗位（Apify）→ 对上担保名单 → L2 判断 → 写入私有 Airtable。

Usage: python3 scripts/fetch_jobs.py [--days 2] [--max-calls 30] [--apify-range 24h] [--apify-limit 50] [--dry-run]
Env (GitHub Actions secrets): ADZUNA_APP_ID, ADZUNA_APP_KEY, APIFY_TOKEN, AIRTABLE_TOKEN (scoped to the 求职追踪 base only).
Each source runs only if its keys are set. Apify bills per job returned, so --apify-limit caps the cost.
Without AIRTABLE_TOKEN, or with --dry-run, nothing is written.

The repository is public, so this script only ever prints counts. Job details go to Airtable, never to the log or the repo.
仓库是公开的：日志里只打印数字，岗位明细只写进 Airtable，不进日志也不进仓库。
"""
import argparse, json, os, re, sys, time, datetime, urllib.parse, urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_awards import core, name_parts, js_hash, weak  # same name matching as the award lists
from l2_rules import judge

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Roles from the job-search plan (SOC 3544 / 2425 / 2135). Each is searched together with each phrase.
ROLES = ["data analyst", "business analyst", "financial analyst", "data scientist",
         "insight analyst", "business intelligence analyst", "commercial analyst", "pricing analyst"]
PHRASES = ["visa sponsorship", "skilled worker visa"]

AIRTABLE = {
    "base": "appmgEKWrKvmXPVEK",
    "companies": "tblNeIIUEcOFfAJtW",
    "jobs": "tbldQ6vkCGhRnCf4n",
    # company fields
    "c_name": "fldwFGsjojhl4ASOw", "c_regname": "fldYGi6u7qrF9V8lm", "c_oid": "fldYmb5D8sGg4793c",
    "c_town": "fldpIzL9tfNvttBWS", "c_rating": "fldERYsGtWVnHzqT7", "c_tags": "fldDziIwdXVhAzuZY",
    "c_source": "fldbSee7FwX545EeP", "c_added": "fld17PwZ2iLInvNcX", "c_hiring": "fld1n9mkcC6ZmFl2f", "c_ch": "fldmNGpadt99nxxNb",
    # job fields
    "j_title": "fldAImZ1CPcxHZyZ5", "j_company": "fldl26T3b06JHOLFV", "j_url": "fldA1uxsOzbhwBCOU", "j_source": "fldoA8FGDe4W2cvm1",
    "j_found": "fldQ3H68o5yvw3IEx", "j_place": "flddDeW7n5xLPqu4B", "j_smin": "fldGKvcoFoQw85PAJ", "j_smax": "fldtUp6TPx4IzzrVk",
    "j_soc": "fldYj2SUGyevszPVE", "j_text": "fld7zEQatcyKWRRPr", "j_l2": "fld5CF6OqhDmFew97", "j_why": "fldGeWDqaTCoHMF9u",
    "j_how": "fldqftQHgVtaiHhv1", "j_score": "fldNTAUCaRbxxXMqN", "j_stage": "fld0KmlmpQUsDxNcW", "j_ext": "fld6vt8HAKB0twd98",
}
SOC_CHOICE = {"3544": "3544 数据分析师", "2425": "2425 商业 / 金融分析", "2135": "2135 IT 业务分析", "2424": "2424 管理咨询", "1132": "1132 营销经理"}
DIM_ZH = {"fintech": "金融科技", "ai": "人工智能", "growth": "高增长", "unicorn": "独角兽", "women": "女性友好", "employer": "最佳雇主"}


def http_json(url, data=None, method=None, headers=None):
    req = urllib.request.Request(url, data=json.dumps(data).encode() if data is not None else None, method=method,
                                 headers={"Content-Type": "application/json", "User-Agent": "uk-visa-sponsor-list job radar", **(headers or {})})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())


# ---------------- register index ----------------
def load_register():
    d = json.load(open(os.path.join(ROOT, "docs", "data.json"), encoding="utf-8"))
    sw_bit = 1 << [k for k, _ in d["routes"]].index("sw")
    links = {}
    try:
        links = json.load(open(os.path.join(ROOT, "docs", "links.json"), encoding="utf-8"))
    except Exception:
        pass
    awards = {}
    try:
        A = json.load(open(os.path.join(ROOT, "docs", "awards.json"), encoding="utf-8"))
        for oid, es in A["orgs"].items():
            awards[oid] = sorted({A["lists"][e["list"]]["dim"] for e in es if e["list"] in A["lists"]})
    except Exception:
        pass
    index = {}
    for r in d["rows"]:
        town = d["towns"][r[1]] if r[1] >= 0 else ""
        oid = js_hash(r[0].lower() + "|" + town.lower())
        org = {"oid": oid, "name": r[0], "town": town, "rating": r[5], "skilled_worker": bool(r[4] & sw_bit), "dims": awards.get(oid, [])}
        names = name_parts(r[0])
        tn = (links.get(oid) or {}).get("tradingName")
        if tn:
            names.append(tn)
        for i, nm in enumerate(names):
            c = core(nm)
            if c and all(o["oid"] != oid for o, _ in index.get(c, [])):
                index.setdefault(c, []).append((org, i > 0))
    return index


def match_company(index, display_name):
    c = core(display_name or "")
    hits = index.get(c, [])
    if not hits:
        return None
    legal = [o for o, ta in hits if not ta]
    pool = legal or [o for o, _ in hits]
    org = dict(pool[0])
    org["how"] = "exact" if (len(pool) == 1 and not weak(c)) else "ambiguous"
    if org["how"] == "ambiguous":
        # several register entries share the name: prefer one that can sponsor Skilled Worker at A rating
        best = [o for o in pool if o["skilled_worker"] and o["rating"] == "a"]
        if best:
            org.update(best[0])
    return org


# ---------------- Adzuna ----------------
def adzuna_search(app_id, app_key, role, phrase, days, page):
    q = {"app_id": app_id, "app_key": app_key, "results_per_page": 50, "what": role, "what_phrase": phrase,
         "max_days_old": days, "sort_by": "date", "content-type": "application/json"}
    url = f"https://api.adzuna.com/v1/api/jobs/gb/search/{page}?" + urllib.parse.urlencode(q)
    return http_json(url)


def priority(l2, org):
    s = {"可担保": 40, "存疑": 20}.get(l2["label"], 0)
    s += 25 if org and org.get("rating") == "a" else 0
    dims = set((org or {}).get("dims", []))
    s += 20 if dims & {"fintech", "ai", "growth", "unicorn"} else 0
    s += 15 if dims & {"women", "employer"} else 0
    return min(100, s + l2["score_bonus"])


# ---------------- Airtable ----------------
class Airtable:
    def __init__(self, token):
        self.h = {"Authorization": f"Bearer {token}"}
        self.base = f"https://api.airtable.com/v0/{AIRTABLE['base']}"

    def all(self, table, fields):
        out, offset = [], None
        while True:
            q = [("returnFieldsByFieldId", "true")] + [("fields[]", f) for f in fields] + ([("offset", offset)] if offset else [])
            d = http_json(f"{self.base}/{table}?" + urllib.parse.urlencode(q), headers=self.h)
            out += d["records"]
            offset = d.get("offset")
            if not offset:
                return out
            time.sleep(0.25)

    def create(self, table, records):
        made = []
        for i in range(0, len(records), 10):
            d = http_json(f"{self.base}/{table}", {"records": [{"fields": r} for r in records[i:i + 10]], "typecast": True,
                                                  "returnFieldsByFieldId": True}, "POST", self.h)
            made += d["records"]
            time.sleep(0.25)
        return made


APIFY_ACTOR = "fantastic-jobs~career-site-job-listing-api"  # company career sites across 58 job systems, $4 per 1,000 jobs
APIFY_TITLES = ROLES + ["insights analyst", "reporting analyst", "fp&a analyst"]


def adzuna_jobs(app_id, app_key, days, max_calls):
    raw, calls, stopped = {}, 0, False
    for role in ROLES:
        for phrase in PHRASES:
            page = 1
            while calls < max_calls and not stopped:
                try:
                    d = adzuna_search(app_id, app_key, role, phrase, days, page)
                except Exception as e:  # quota used up (test plan: 25 calls) or Adzuna down: keep what we have
                    print(f"Adzuna stopped after {calls} calls: {type(e).__name__} {getattr(e, 'code', '')}")
                    stopped = True
                    break
                calls += 1
                for r in d.get("results", []):
                    raw.setdefault(str(r["id"]), r)
                if page * 50 >= d.get("count", 0) or page >= 3:
                    break
                page += 1
                time.sleep(2.5)  # stay well under 25 calls a minute
            time.sleep(2.5)
    out = []
    for jid, r in raw.items():
        real = r.get("salary_is_predicted") != "1"
        out.append({"ext": f"adzuna:{jid}", "source": "Adzuna", "company": (r.get("company") or {}).get("display_name"),
                    "title": r.get("title"), "description": r.get("description"), "url": r.get("redirect_url"),
                    "location": (r.get("location") or {}).get("display_name"), "contract_time": r.get("contract_time"),
                    "contract_type": r.get("contract_type"),
                    "salary_min": r.get("salary_min") if real else None, "salary_max": r.get("salary_max") if real else None})
    print(f"Adzuna: {calls} calls, {len(out)} ads")
    return out


def apify_jobs(token, time_range, limit):
    body = {"titleSearch": APIFY_TITLES, "locationSearch": ["United Kingdom"], "timeRange": time_range, "limit": limit,
            "descriptionType": "text", "removeAgency": True}
    url = f"https://api.apify.com/v2/acts/{APIFY_ACTOR}/run-sync-get-dataset-items?timeout=280"
    try:
        items = http_json(url, body, "POST", {"Authorization": f"Bearer {token}"})
    except Exception as e:
        print(f"Apify failed: {type(e).__name__} {getattr(e, 'code', '')}")
        return []
    out = []
    for r in items if isinstance(items, list) else []:
        yearly = (r.get("ai_salary_unit_text") or "").upper() == "YEAR" and (r.get("ai_salary_currency") or "GBP") == "GBP"
        etype = " ".join(r.get("ai_employment_type") or []).upper()
        locs = r.get("locations_derived") or []
        out.append({"ext": f"apify:{r.get('id')}", "source": "Apify", "company": r.get("organization"), "title": r.get("title"),
                    "description": r.get("description_text"), "url": r.get("url"), "location": "; ".join(map(str, locs[:2])) or None,
                    "contract_time": "part_time" if "PART_TIME" in etype and "FULL_TIME" not in etype else None, "contract_type": None,
                    "salary_min": r.get("ai_salary_min_value") if yearly else None, "salary_max": r.get("ai_salary_max_value") if yearly else None,
                    "visa_flag": bool(r.get("ai_visa_sponsorship"))})
    print(f"Apify: {len(out)} jobs")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=2, help="Adzuna look-back in days")
    ap.add_argument("--max-calls", type=int, default=30, help="max Adzuna calls")
    ap.add_argument("--apify-range", default="24h", choices=["1h", "24h", "7d", "6m"])
    ap.add_argument("--apify-limit", type=int, default=50, help="max Apify jobs (billed per job)")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    env = os.environ.get
    token = env("AIRTABLE_TOKEN")
    write = bool(token) and not a.dry_run

    found = []
    if env("ADZUNA_APP_ID") and env("ADZUNA_APP_KEY") and a.max_calls > 0:
        found += adzuna_jobs(env("ADZUNA_APP_ID"), env("ADZUNA_APP_KEY"), a.days, a.max_calls)
    if env("APIFY_TOKEN") and a.apify_limit > 0:
        found += apify_jobs(env("APIFY_TOKEN"), a.apify_range, max(10, a.apify_limit))
    if not found:
        print("no jobs fetched")
        return

    index = load_register()
    today = datetime.date.today().isoformat()
    counts = {"jobs": len(found), "on_register": 0, "可担保": 0, "存疑": 0, "不行": 0}
    keep = []
    for job in found:
        org = match_company(index, job["company"])
        if org:
            counts["on_register"] += 1
        l2 = judge(job, org, today)
        if job.get("visa_flag") and "写明可担保" not in l2["reasons"]:
            l2["score_bonus"] += 10
            l2["reasons"].append("Apify 识别为提到签证担保")
        counts[l2["label"]] += 1
        if l2["label"] != "不行":
            keep.append((job, org, l2))
    print("L2:", json.dumps(counts, ensure_ascii=False))
    if not write:
        print("dry run: nothing written (no AIRTABLE_TOKEN or --dry-run)")
        return

    at = Airtable(token)
    F = AIRTABLE
    seen = {rec["fields"].get(F["j_ext"]) for rec in at.all(F["jobs"], [F["j_ext"]])}
    comp = {rec["fields"].get(F["c_oid"]): rec["id"] for rec in at.all(F["companies"], [F["c_oid"]])}
    new_comp = {}
    for job, org, l2 in keep:
        if org and org["oid"] not in comp and org["oid"] not in new_comp:
            new_comp[org["oid"]] = {F["c_name"]: job["company"] or org["name"], F["c_regname"]: org["name"],
                                    F["c_oid"]: org["oid"], F["c_town"]: org["town"], F["c_rating"]: org["rating"].upper() if org["rating"] in "ab" else None,
                                    F["c_tags"]: [DIM_ZH[x] for x in org["dims"] if x in DIM_ZH], F["c_source"]: "招聘网站反查",
                                    F["c_added"]: today, F["c_hiring"]: "有英国岗位", F["c_ch"]: "未查"}
    for rec in at.create(F["companies"], [{k: v for k, v in f.items() if v not in (None, [])} for f in new_comp.values()]):
        comp[rec["fields"].get(F["c_oid"])] = rec["id"]

    rows = []
    for job, org, l2 in keep:
        if job["ext"] in seen:
            continue
        seen.add(job["ext"])
        f = {F["j_title"]: job["title"], F["j_url"]: job["url"], F["j_source"]: job["source"], F["j_found"]: today,
             F["j_place"]: job["location"], F["j_text"]: (job["description"] or "")[:2000], F["j_l2"]: l2["label"],
             F["j_why"]: "；".join(l2["reasons"]), F["j_how"]: "规则", F["j_score"]: priority(l2, org), F["j_stage"]: "发现", F["j_ext"]: job["ext"]}
        if job.get("salary_min"):
            f[F["j_smin"]] = round(job["salary_min"])
        if job.get("salary_max"):
            f[F["j_smax"]] = round(job["salary_max"])
        if l2["soc"]:
            f[F["j_soc"]] = SOC_CHOICE[l2["soc"]]
        if org and org["oid"] in comp:
            f[F["j_company"]] = [comp[org["oid"]]]
        rows.append({k: v for k, v in f.items() if v not in (None, "")})
    at.create(F["jobs"], rows)
    print(f"Airtable: {len(new_comp)} new companies, {len(rows)} new jobs")


if __name__ == "__main__":
    main()

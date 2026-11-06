"""Daily job radar: Adzuna ads that mention visa sponsorship → sponsor-register match → L2 → private Airtable.
每日岗位雷达：Adzuna 上提到担保的广告 → 对上担保名单 → L2 判断 → 写入私有 Airtable。

Usage: python3 scripts/fetch_jobs.py [--days 2] [--max-calls 30] [--dry-run]
Env (GitHub Actions secrets): ADZUNA_APP_ID, ADZUNA_APP_KEY, AIRTABLE_TOKEN (scoped to the 求职追踪 base only).
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=2)
    ap.add_argument("--max-calls", type=int, default=30)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    app_id, app_key, token = os.environ.get("ADZUNA_APP_ID"), os.environ.get("ADZUNA_APP_KEY"), os.environ.get("AIRTABLE_TOKEN")
    if not (app_id and app_key):
        sys.exit("ADZUNA_APP_ID / ADZUNA_APP_KEY not set")
    write = bool(token) and not a.dry_run

    index = load_register()
    today = datetime.date.today().isoformat()
    jobs, calls, stopped = {}, 0, False
    for role in ROLES:
        for phrase in PHRASES:
            page = 1
            while calls < a.max_calls and not stopped:
                try:
                    d = adzuna_search(app_id, app_key, role, phrase, a.days, page)
                except Exception as e:  # quota used up (test plan: 25 calls) or Adzuna down: keep what we have
                    print(f"Adzuna stopped after {calls} calls: {type(e).__name__} {getattr(e, 'code', '')}")
                    stopped = True
                    break
                calls += 1
                for r in d.get("results", []):
                    jobs.setdefault(str(r["id"]), r)
                if page * 50 >= d.get("count", 0) or page >= 3:
                    break
                page += 1
                time.sleep(2.5)  # stay well under 25 calls a minute
            time.sleep(2.5)

    counts = {"ads": len(jobs), "calls": calls, "on_register": 0, "可担保": 0, "存疑": 0, "不行": 0}
    keep = []
    for jid, r in jobs.items():
        org = match_company(index, (r.get("company") or {}).get("display_name"))
        if org:
            counts["on_register"] += 1
        job = {"title": r.get("title"), "description": r.get("description"), "contract_time": r.get("contract_time"),
               "contract_type": r.get("contract_type"),
               "salary_min": None if r.get("salary_is_predicted") == "1" else r.get("salary_min"),
               "salary_max": None if r.get("salary_is_predicted") == "1" else r.get("salary_max")}
        l2 = judge(job, org, today)
        counts[l2["label"]] += 1
        if l2["label"] != "不行":
            keep.append((jid, r, org, l2))
    print("Adzuna:", json.dumps(counts, ensure_ascii=False))
    if not write:
        print("dry run: nothing written (no AIRTABLE_TOKEN or --dry-run)")
        return

    at = Airtable(token)
    F = AIRTABLE
    seen = {rec["fields"].get(F["j_ext"]) for rec in at.all(F["jobs"], [F["j_ext"]])}
    comp = {rec["fields"].get(F["c_oid"]): rec["id"] for rec in at.all(F["companies"], [F["c_oid"]])}
    new_comp = {}
    for jid, r, org, l2 in keep:
        if org and org["oid"] not in comp and org["oid"] not in new_comp:
            new_comp[org["oid"]] = {F["c_name"]: (r.get("company") or {}).get("display_name") or org["name"], F["c_regname"]: org["name"],
                                    F["c_oid"]: org["oid"], F["c_town"]: org["town"], F["c_rating"]: org["rating"].upper() if org["rating"] in "ab" else None,
                                    F["c_tags"]: [DIM_ZH[x] for x in org["dims"] if x in DIM_ZH], F["c_source"]: "招聘网站反查",
                                    F["c_added"]: today, F["c_hiring"]: "有英国岗位", F["c_ch"]: "未查"}
    for rec in at.create(F["companies"], [{k: v for k, v in f.items() if v not in (None, [])} for f in new_comp.values()]):
        comp[rec["fields"].get(F["c_oid"])] = rec["id"]

    rows = []
    for jid, r, org, l2 in keep:
        ext = f"adzuna:{jid}"
        if ext in seen:
            continue
        loc = (r.get("location") or {}).get("display_name")
        f = {F["j_title"]: r.get("title"), F["j_url"]: r.get("redirect_url"), F["j_source"]: "Adzuna", F["j_found"]: today,
             F["j_place"]: loc, F["j_text"]: (r.get("description") or "")[:2000], F["j_l2"]: l2["label"],
             F["j_why"]: "；".join(l2["reasons"]), F["j_how"]: "规则", F["j_score"]: priority(l2, org), F["j_stage"]: "发现", F["j_ext"]: ext}
        if r.get("salary_is_predicted") != "1":
            if r.get("salary_min"): f[F["j_smin"]] = round(r["salary_min"])
            if r.get("salary_max"): f[F["j_smax"]] = round(r["salary_max"])
        if l2["soc"]:
            f[F["j_soc"]] = SOC_CHOICE[l2["soc"]]
        if org and org["oid"] in comp:
            f[F["j_company"]] = [comp[org["oid"]]]
        rows.append({k: v for k, v in f.items() if v not in (None, "")})
    at.create(F["jobs"], rows)
    print(f"Airtable: {len(new_comp)} new companies, {len(rows)} new jobs")


if __name__ == "__main__":
    main()

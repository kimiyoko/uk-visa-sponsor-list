"""L2: can this job be sponsored on a Skilled Worker visa?  /  L2：这个岗位能不能办技术工签担保？

Every rule lives in RULES below, so a change in the immigration rules means editing one table.
所有规则都在下面的 RULES 里，签证规则变了只改这一处。

judge(job, company) -> {"label": "可担保" | "存疑" | "不行", "soc": ..., "reasons": [...], "score_bonus": int}
  job:     {"title", "description", "salary_min", "salary_max", "contract_time", "contract_type"}
  company: register match or None: {"rating": "a"|"b"|"p", "skilled_worker": bool, "how": "exact"|"trading"|"ambiguous"}

Order (stop at the first 不行): company → explicit "no sponsorship" → contractor → part-time → SOC (off-target titles are 不行) → salary → 3544 deadline → wording.
Thresholds as of 2026-11 (gov.uk Appendix Skilled Occupations); the user does not qualify for new-entrant rates.
"""
import re, datetime

RULES = {
    "as_of": "2026-11-05",
    "general_threshold": 41700,
    # SOC: (name, going rate, title patterns). First match wins, so the more specific ones come first.
    "soc": [
        ("2135", "IT business analyst", 48500,
         r"\b(it|systems?|technical|crm|erp|salesforce|sap|digital)\b.{0,25}\b(business|systems?) analyst\b|\bsystems analyst\b|\bbusiness analyst\b.{0,40}\b(it|systems?|crm|erp|software|digital|technology)\b"),
        ("2425", "data scientist", 52500, r"\bdata scientist\b|\bmachine learning (scientist|engineer)\b"),
        ("2425", "business / financial analyst", 46200,
         r"\b(business|financial|finance|commercial|pricing|risk|credit|investment|fp&a|strategy|operations|revenue) analyst\b|\bfp&a\b"),
        ("3544", "data analyst", 41700,
         r"\b(data|insights?|reporting|mi|bi|business intelligence|analytics|marketing|product|customer|people|hr|performance) analyst\b|\banalytics (specialist|executive)\b"),
        ("2424", "management consultant", 48400, r"\b(management|strategy|business) consultant\b"),
        ("1132", "marketing manager", 47800, r"\bmarketing (manager|lead)\b"),
    ],
    # 3544 is on the temporary shortage list only for CoS issued by this date.
    "soc_3544_cos_deadline": "2026-12-31",
    "soc_3544_warn_after": "2026-12-11",
    "no_sponsorship": r"\b(no|not|unable to|cannot|can ?not|can't|won't|will not|do not|does not|don't|doesn't|are not able to|is not able to)\b[^.]{0,40}\b(sponsor|sponsorship)\b|\bsponsorship (is )?not (available|offered|provided)\b|\bwithout (the need for )?(visa )?sponsorship\b",
    "right_to_work_only": r"\b(must|need to|required to|should) (already )?have (the |full )?(right to work|eligibility to work) in the uk\b",
    "sponsor_yes": r"\bvisa sponsorship (is )?(available|offered|provided|considered)\b|\b(we|can|will|able to) (offer |provide )?(visa )?sponsor(ship)?\b|\bskilled worker (visa|sponsorship)\b|\bcertificate of sponsorship\b|\bsponsorship available\b",
    "contractor": r"\b(day rate|per day|outside ir35|inside ir35|umbrella company|contractor|freelance)\b",
    "part_time": r"\bpart[- ]time\b",
}

_C = {k: re.compile(v, re.I) for k, v in RULES.items() if isinstance(v, str) and k not in ("as_of", "soc_3544_cos_deadline", "soc_3544_warn_after")}


def infer_soc(title):
    t = (title or "").lower()
    for code, name, rate, pat in RULES["soc"]:
        if re.search(pat, t, re.I):
            return code, name, max(rate, RULES["general_threshold"])
    return None, None, None


def judge(job, company, today=None):
    today = today or datetime.date.today().isoformat()
    text = f"{job.get('title') or ''}\n{job.get('description') or ''}"
    reasons, bonus = [], 0

    def out(label, soc=None):
        return {"label": label, "soc": soc, "reasons": reasons, "score_bonus": bonus}

    # 1 company
    if company is None:
        reasons.append("公司不在担保名单上（或名称对不上）")
        return out("不行")
    if company.get("how") == "ambiguous":
        reasons.append("公司名在担保名单上对应到多家，需人工确认")
    if not company.get("skilled_worker"):
        reasons.append("该公司没有 Skilled Worker 路线")
        return out("不行")
    if company.get("rating") == "b":
        reasons.append("担保评级 B 级：改正前不能新发 CoS")
        return out("不行")
    if company.get("rating") == "p":
        reasons.append("担保评级为临时（provisional），需确认能否发 CoS")

    # 2 explicit no
    m = _C["no_sponsorship"].search(text)
    if m:
        reasons.append(f"写明不担保：「{m.group(0).strip()}」")
        return out("不行")
    # 3 contractor
    # day rate / IR35 anywhere, or "contractor"/"freelance" in the title. A fixed-term contract on its own is fine.
    m = re.search(r"\b(day rate|per day|outside ir35|inside ir35|umbrella company)\b", text, re.I) or _C["contractor"].search(job.get("title") or "")
    if m:
        reasons.append(f"承包商 / 日薪岗位：「{m.group(0)}」")
        return out("不行")
    # 4 part-time (fixed-term contracts are fine)
    if (job.get("contract_time") or "").lower() == "part_time" or _C["part_time"].search(job.get("title") or ""):
        reasons.append("兼职岗位")
        return out("不行")

    # 5 SOC
    soc, soc_name, threshold = infer_soc(job.get("title"))
    if not soc:
        reasons.append("不是目标岗位：职位名对不上 3544 / 2425 / 2135 / 2424 / 1132")
        return out("不行")
    reasons.append(f"推断 SOC {soc}（{soc_name}），薪资门槛 £{threshold:,}")

    # 6 salary
    lo, hi = job.get("salary_min"), job.get("salary_max") or job.get("salary_min")
    salary_ok = None
    if hi and hi < threshold:
        reasons.append(f"薪资上限 £{int(hi):,} 低于门槛")
        return out("不行", soc)
    if lo and lo >= threshold:
        salary_ok = True
        reasons.append(f"薪资下限 £{int(lo):,} 达到门槛")
    elif lo or hi:
        reasons.append("薪资区间跨过门槛，要看最终 offer")
    else:
        reasons.append("没写薪资")

    # 7 3544 deadline
    late_3544 = soc == "3544" and today >= RULES["soc_3544_warn_after"]
    if soc == "3544":
        reasons.append(f"3544 的 CoS 必须在 {RULES['soc_3544_cos_deadline']} 前发出")

    # 8 wording
    rtw_only = False
    if _C["sponsor_yes"].search(text):
        bonus += 10
        reasons.append("写明可担保")
    elif _C["right_to_work_only"].search(text):
        rtw_only = True
        reasons.append("只写了「需有英国工作权」，通常意味着不担保")

    if salary_ok and not rtw_only and not late_3544 and company.get("how") != "ambiguous" and company.get("rating") == "a":
        return out("可担保", soc)
    return out("存疑", soc)

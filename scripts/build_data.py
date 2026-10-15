"""Turn the gov.uk 'Register of licensed sponsors: workers' CSV into a compact
data file for the filterable sponsor list page, with keyword-inferred industry tags.

Usage: python3 build_data.py <register.csv> <out_dir> [<previous data.json>]
"""
import csv, json, re, sys, os, datetime
from collections import OrderedDict

# First-seen dates are stored as whole days since this epoch; 0 means "already on the
# register when tracking started" (no known date).
DAY0 = datetime.date(2020, 1, 1)

def day_number(iso):
    try:
        return (datetime.date.fromisoformat(iso) - DAY0).days
    except (TypeError, ValueError):
        return 0

# Industry tags inferred from the organisation name (the register has no industry field).
# Order matters only for display; an organisation can carry several tags.
INDUSTRIES = OrderedDict([
    ("health", ("医疗护理", r"\b(care|carers|caring|nursing|nurses?|health ?care|healthcare|home ?care|homecare|domiciliary|nhs|hospitals?|hospice|medical|medics?|clinics?|clinical|dental|dentists?|dentistry|pharmacy|pharmacies|chemists?|surgery|surgeries|practice ?gp|gp|physio\w*|therapy|therapies|health|wellbeing|well-being|residential home|rest home|care home|supported living|optic\w*|opticians?|vets?|veterinary|animal hospital)\b")),
    ("it", ("IT / 软件 / 数据", r"\b(software|tech|techs|technology|technologies|digital|it|ict|data|cyber|cloud|computing|computers?|systems|ai|analytics|infotech|infosys|saas|apps?|web|internet|networks?|telecoms?|telecommunications?|electronics|robotics|fintech|devops|quantum|semiconductors?)\b")),
    ("edu", ("教育培训", r"\b(schools?|academy|academies|college|colleges|university|universities|education|educational|learning|tuition|tutors?|tutoring|training|nursery|nurseries|childcare|montessori|pre-school|preschool|institute)\b")),
    ("food", ("餐饮酒店", r"\b(restaurants?|cafe|café|cafes|takeaway|kitchens?|food|foods|catering|caterers|hotels?|pizza|pizzeria|grill|grills|bar|bars|curry|tandoori|kebab|bakery|bakers?|chicken|sushi|noodles?|spice|dining|hospitality|inn|pubs?|coffee|tea|bistro|brasserie|diner|cuisine|eatery|burgers?|biryani|masala|chef|deli|patisserie|desserts?|ice cream|lounge|tavern|steakhouse|wok)\b")),
    ("retail", ("零售批发", r"\b(retail|retailers?|stores?|shops?|supermarkets?|wholesale|wholesalers?|mart|minimarket|convenience|off licen[cs]e|cash and carry|cash & carry|fashion|clothing|boutique|jewell\w*|garments?|textiles?|furniture|e-?commerce|imports?|exports?|import & export|import and export|distribut\w*)\b")),
    ("construction", ("建筑地产", r"\b(construction|constructions|build|builders|building|buildings|property|properties|estates?|developments?|roofing|roofers?|scaffold\w*|plumbing|plumbers?|joinery|joiners?|carpentry|architects?|architecture|architectural|surveyors?|surveying|civil|civils|interiors?|refurbishment|renovations?|homes|housing|lettings|letting agents?|groundworks|bricklaying|plastering|glazing|flooring|kitchens and bathrooms)\b")),
    ("eng", ("工程制造", r"\b(engineering|engineers?|manufactur\w*|industries|industrial|automotive|aerospace|motors?|steel|metals?|metalwork|fabrication|fabricators?|plastics?|ceramics?|pottery|chemicals?|energy|power|electrical|electric|electricians?|solar|renewables?|mechanical|machinery|machines|precision|tools|tooling|components|packaging|printing|engines?|vehicles?|marine|nuclear|oil|gas|mining|foundry|welding|instruments?)\b")),
    ("finance", ("金融会计", r"\b(accountants?|accounting|accountancy|finance|financial|capital|banks?|banking|investments?|investors?|insurance|insurers?|wealth|tax|taxation|assets?|funds?|securities|brokers?|brokerage|payments?|pensions?|mortgages?|audit|auditors?|bookkeeping|equity|asset management|credit|lending|loans?)\b")),
    ("legal", ("法律", r"\b(solicitors?|law|legal|lawyers?|chambers|barristers?|attorneys?|notary|immigration advisers?|conveyancing)\b")),
    ("consult", ("咨询 / 商业服务", r"\b(consulting|consultancy|consultants?|management|advisory|advisors?|advisers?|strategy|business services|outsourcing|marketing|advertising|pr|public relations|branding|events?|translation|translators?|interpreters?)\b")),
    ("recruit", ("招聘 / 人力外包", r"\b(recruitment|recruiting|staffing|employment|personnel|resourcing|workforce|talent|manpower|recruitment agency|employment agency|staffing agency|nursing agency|locums?|headhunt\w*|hr)\b")),
    ("logistics", ("物流运输", r"\b(logistics|transport|transportation|haulage|hauliers?|freight|couriers?|delivery|deliveries|shipping|cargo|warehous\w*|travel|travels|tours?|airlines?|aviation|airways|airport|taxi|taxis|cars|car hire|coaches|buses|bus|rail|railway|removals|movers|parcel|garage|tyres?|mot)\b")),
    ("science", ("科研 / 制药 / 生物", r"\b(pharma|pharmaceuticals?|biotech|biotechnology|bio|biosciences?|biologics|therapeutics|laboratories|laboratory|labs?|research|sciences?|scientific|genomics?|diagnostics|biomedical|medicines?|vaccines?|drug|drugs|life sciences)\b")),
    ("creative", ("创意 / 媒体 / 体育", r"\b(media|design|designs|designers?|studios?|films?|productions?|pictures|music|musical|theatre|theater|arts|art|creative|creatives|publishing|publishers?|games|gaming|entertainment|broadcast\w*|tv|television|radio|animation|photography|fashion design|orchestra|opera|ballet|dance|festival|football|cricket|rugby|sports?|club|athletic\w*|fitness|gym)\b")),
    ("public", ("公共部门 / 慈善", r"\b(council|charity|charities|charitable|foundation|association|society|borough|police|government|department|ministry|embassy|high commission|consulate|federation|union|cic|church|mosque|temple|gurdwara|diocese|parish|mission|ministries|religious)\b")),
    ("beauty", ("美容美发", r"\b(salon|salons|beauty|barbers?|barbershop|hair|hairdress\w*|spa|nails?|aesthetics?|cosmetics?|massage|tattoo|lashes|brows)\b")),
    ("facility", ("清洁 / 安保 / 物业维护", r"\b(cleaning|cleaners?|security|guarding|facilities|facility|maintenance|hygiene|pest|waste|recycling|laundry|launderette|dry clean\w*|landscaping|gardening|gardeners?)\b")),
    ("agri", ("农业 / 食品加工", r"\b(farms?|farming|farmers?|agricultur\w*|agri|growers?|horticultur\w*|dairy|poultry|meat|meats|butchers?|fisheries|fish|seafood|produce|fruit|vegetables?|abattoir|food processing|mills?|brewery|breweries|distillery|winery|vineyard)\b")),
])
COMPILED = [(k, re.compile(rx, re.I)) for k, (_, rx) in INDUSTRIES.items()]

# Group the register's routes into the buckets a job seeker cares about.
def route_key(r):
    r = r.strip()
    if r == "Skilled Worker" or r == "Tier 2 General":
        return "sw"
    if r.startswith("Global Business Mobility") or r.startswith("Intra"):
        return "gbm"
    if r == "Scale-up":
        return "scale"
    if r in ("Creative Worker", "International Sportsperson"):
        return "creative"
    if r in ("Charity Worker", "Government Authorised Exchange", "International Agreement"):
        return "temp"
    if r in ("Tier 2 Ministers of Religion", "Religious Worker"):
        return "religion"
    if r == "Seasonal Worker":
        return "seasonal"
    return "other"

ROUTES = OrderedDict([
    ("sw", "Skilled Worker（技术工签，含医护签）"),
    ("gbm", "Global Business Mobility（跨国调派等）"),
    ("scale", "Scale-up（高成长企业）"),
    ("creative", "Creative / Sportsperson（文艺体育）"),
    ("temp", "Charity / 交流 / 国际协议（临时）"),
    ("religion", "宗教工作者"),
    ("seasonal", "季节工"),
    ("other", "其他"),
])

def rating_key(t):
    t = t.lower()
    if "provisional" in t:
        return "p"
    if "b rating" in t:
        return "b"
    return "a"

def clean(s):
    return re.sub(r"\s+", " ", (s or "").strip())

def title_town(s):
    s = clean(s)
    if not s:
        return ""
    # Normalise ALL-CAPS / lower-case towns so 'LONDON' and 'London' group together.
    if s.isupper() or s.islower():
        s = s.title()
    return s

def main():
    src, out_dir = sys.argv[1], sys.argv[2]
    prev_path = sys.argv[3] if len(sys.argv) > 3 else None
    os.makedirs(out_dir, exist_ok=True)

    orgs = OrderedDict()
    raw_rows = 0
    with open(src, newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            raw_rows += 1
            name = clean(row.get("Organisation Name"))
            if not name:
                continue
            town = title_town(row.get("Town/City"))
            county = title_town(row.get("County"))
            key = (name.lower(), town.lower())
            o = orgs.get(key)
            if o is None:
                o = orgs[key] = {"n": name, "t": town, "c": county, "r": set(), "rt": set(), "routes_raw": set()}
            if county and not o["c"]:
                o["c"] = county
            o["r"].add(rating_key(row.get("Type & Rating", "")))
            o["rt"].add(route_key(row.get("Route", "")))
            o["routes_raw"].add(clean(row.get("Route")))

    towns = sorted({o["t"] for o in orgs.values() if o["t"]}, key=str.lower)
    counties = sorted({o["c"] for o in orgs.values() if o["c"]}, key=str.lower)
    tidx = {t: i for i, t in enumerate(towns)}
    cidx = {c: i for i, c in enumerate(counties)}
    ind_keys = list(INDUSTRIES.keys())
    route_keys = list(ROUTES.keys())

    m = re.search(r"(\d{4}-\d{2}-\d{2})", os.path.basename(src))
    register_date = m.group(1) if m else ""
    today_n = day_number(register_date) or (datetime.date.today() - DAY0).days

    prev_names = None
    prev_fs = {}
    prev_meta_tracking = ""
    if prev_path and os.path.exists(prev_path):
        with open(prev_path, encoding="utf-8") as f:
            p = json.load(f)
        prev_names = {}
        for r in p["rows"]:
            k = (r[0].lower(), (p["towns"][r[1]] if r[1] >= 0 else "").lower())
            prev_names[k] = r[0]
            prev_fs[k] = r[7] if len(r) > 7 else 0
        prev_meta_tracking = p.get("meta", {}).get("tracking_since", "")

    rows = []
    tag_counts = {k: 0 for k in ind_keys}
    added = []
    for key, o in orgs.items():
        tags = 0
        for i, (k, rx) in enumerate(COMPILED):
            if rx.search(o["n"]):
                tags |= 1 << i
                tag_counts[k] += 1
        routes = 0
        for rk in o["rt"]:
            routes |= 1 << route_keys.index(rk)
        rating = "a" if "a" in o["r"] else ("b" if "b" in o["r"] else "p")
        is_new = 1 if (prev_names is not None and key not in prev_names) else 0
        if is_new:
            added.append(o["n"])
        first_seen = today_n if is_new else prev_fs.get(key, 0)
        rows.append([o["n"], tidx.get(o["t"], -1), cidx.get(o["c"], -1), tags, routes, rating, is_new, first_seen])

    removed = []
    if prev_names is not None:
        removed = sorted(name for k, name in prev_names.items() if k not in orgs)

    meta = {
        "register_date": register_date,
        "day0": DAY0.isoformat(),
        "tracking_since": (prev_meta_tracking or register_date),
        "source_file": os.path.basename(src),
        "raw_rows": raw_rows,
        "orgs": len(rows),
        "untagged": sum(1 for r in rows if r[3] == 0),
        "tag_counts": tag_counts,
        "added": len(added),
        "removed": len(removed),
    }
    data = {
        "meta": meta,
        "industries": [[k, INDUSTRIES[k][0]] for k in ind_keys],
        "routes": [[k, ROUTES[k]] for k in route_keys],
        "towns": towns,
        "counties": counties,
        "rows": rows,
    }
    with open(os.path.join(out_dir, "data.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
    with open(os.path.join(out_dir, "changes.json"), "w", encoding="utf-8") as f:
        json.dump({"added": added, "removed": removed}, f, ensure_ascii=False, indent=1)
    print(json.dumps(meta, ensure_ascii=False, indent=1))

if __name__ == "__main__":
    main()

"""Turn the gov.uk 'Register of licensed sponsors: workers' CSV into a compact
data file for the filterable sponsor list page, with industry tags (Companies House SIC code, else keywords in the name).

Usage: python3 build_data.py <register.csv> <out_dir> [<previous data.json>] [<sic.json>]
       python3 build_data.py --retag <data.json> <sic.json>   (re-tag industries in place)
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

# Industries: 14 single-choice groups. Primary source is the organisation's first SIC code
# at Companies House (sic.json, written by build_sizes.py); organisations with no match or
# only a generic SIC code fall back to keywords in the name; anything left is "other".
INDUSTRIES = OrderedDict([
    ("health", "医疗健康"),
    ("retail", "零售与电商"),
    ("tech", "科技与软件"),
    ("hospitality", "酒店餐饮"),
    ("prof", "专业服务"),
    ("property", "地产与建筑"),
    ("mfg", "制造与工业"),
    ("finance", "金融服务"),
    ("transport", "交通出行与物流"),
    ("media", "媒体、营销与创意"),
    ("edu", "教育"),
    ("public", "公共部门与非营利"),
    ("energy", "能源、公用事业与可持续"),
    ("other", "其他"),
])
IND_KEYS = list(INDUSTRIES.keys())

# SIC codes too generic to say anything ("other business support", dormant, etc.).
GENERIC_SIC = {"99999", "74990", "82990", "96090", "70100", "64209", "98000", "99000"}

def sic_industry(code):
    """UK SIC 2007 five-digit code -> industry key (None if unusable)."""
    if not code or not code[:2].isdigit():
        return None
    d, c4 = int(code[:2]), code[:4]
    if d <= 3: return "other"
    if d <= 9: return "energy"
    if d == 21: return "health"
    if d <= 33: return "mfg"
    if d <= 39: return "energy"
    if d <= 43: return "property"
    if d <= 47: return "retail"
    if d <= 53: return "transport"
    if d <= 56: return "hospitality"
    if d == 58: return "tech" if c4 in ("5821", "5829") else "media"
    if d <= 60: return "media"
    if d <= 63: return "media" if c4 == "6391" else "tech"
    if d <= 66: return "finance"
    if d == 68: return "property"
    if d <= 70: return "prof"
    if d == 71: return "property" if c4 == "7111" else "prof"
    if d == 72: return "health" if c4 == "7211" else "prof"
    if d == 73: return "media"
    if d == 74: return "media" if c4[:3] in ("741", "742") else "prof"
    if d == 75: return "health"
    if d == 77: return "transport" if c4.startswith("771") else "prof"
    if d == 79: return "transport"
    if d <= 82: return "prof"
    if d == 84: return "public"
    if d == 85: return "edu"
    if d <= 88: return "health"
    if d <= 91: return "media"
    if d == 93: return "hospitality"                       # sport, fitness, leisure
    if c4 in ("9602", "9604"): return "retail"              # hairdressing, beauty, wellbeing
    if d == 94 or d == 99: return "public"
    return "other"

# Name rules that win over the SIC code: NHS bodies, universities and government bodies.
OVERRIDES = [
    ("health", re.compile(r"\bnhs\b", re.I)),
    ("edu", re.compile(r"\b(university|universities)\b", re.I)),
    ("public", re.compile(r"\b(council|government|ministry|department (for|of)|home office|cabinet office|hm revenue|hmrc|police|fire and rescue|parliament|embassy|high commission|consulate|authority|ombudsman)\b", re.I)),
]

COMPANY = re.compile(r"\b(ltd|limited|plc|llp)\b", re.I)

# Name keywords, tried in this order; the first group that matches wins.
KEYWORDS = [
    ("prof", r"\b(solicitors?|law|legal|lawyers?|chambers|barristers?|attorneys?|notary|conveyancing|recruitment|recruiting|staffing|employment agency|personnel|resourcing|headhunt\w*)\b"),
    ("health", r"\b(care|carers|caring|nursing|nurses?|health ?care|healthcare|home ?care|homecare|domiciliary|nhs|hospitals?|hospice|medical|medics?|clinics?|clinical|dental|dentists?|dentistry|pharmacy|pharmacies|chemists?|surgery|surgeries|gp|physio\w*|therapy|therapies|health|wellbeing|well-being|rest home|care home|supported living|opticians?|vets?|veterinary|pharma|pharmaceuticals?|biotech|biosciences?|therapeutics|diagnostics|biomedical|life sciences)\b"),
    ("edu", r"\b(schools?|academy|academies|college|colleges|university|universities|education|educational|learning|tuition|tutors?|tutoring|training|nursery|nurseries|childcare|montessori|pre-school|preschool|institute)\b"),
    ("public", r"\b(council|charity|charities|charitable|foundation|association|society|borough|police|government|department|ministry|embassy|high commission|consulate|federation|union|cic|church|mosque|temple|gurdwara|synagogue|sangat|masjid|masjed|islamic|chapel|cio|diocese|parish|mission|ministries|religious)\b"),
    ("finance", r"\b(accountants?|accounting|accountancy|finance|financial|capital|banks?|banking|investments?|investors?|insurance|insurers?|wealth|tax|taxation|funds?|securities|brokers?|brokerage|payments?|pensions?|mortgages?|audit|auditors?|bookkeeping|equity|asset management|credit|lending|loans?|fintech)\b"),
    ("tech", r"\b(software|tech|techs|technology|technologies|digital|it|ict|data|cyber|cloud|computing|computers?|systems|ai|analytics|infotech|saas|apps?|web|internet|networks?|telecoms?|telecommunications?|electronics|robotics|devops|quantum|semiconductors?)\b"),
    ("retail", r"\b(salon|salons|beauty|barbers?|barbershop|hair|hairdress\w*|nails?|aesthetics?|cosmetics?|lashes|brows)\b"),
    ("hospitality", r"\b(sports? clubs?|football|cricket|rugby|golf|tennis|leisure|fitness|gym|athletic\w*|restaurants?|cafe|café|cafes|takeaway|kitchens?|food|foods|catering|caterers|hotels?|pizza|pizzeria|grill|grills|bar|bars|curry|tandoori|balti|kebab|chippy|fish and chips|fish & chips|bakery|bakers?|chicken|sushi|noodles?|spice|dining|hospitality|inn|pubs?|coffee|bistro|brasserie|diner|cuisine|eatery|burgers?|biryani|masala|chef|deli|patisserie|desserts?|ice cream|lounge|tavern|steakhouse|wok)\b"),
    ("energy", r"\b(energy|power|solar|renewables?|nuclear|oil|gas|utilities|utility|water|waste|recycling|electricity|wind|sustainab\w*|environmental|ev charging)\b"),
    ("mfg", r"\b(engineering|engineers?|manufactur\w*|industries|industrial|automotive|aerospace|motors?|steel|metals?|metalwork|fabrication|fabricators?|plastics?|ceramics?|chemicals?|electrical|electricians?|mechanical|machinery|machines|precision|tools|tooling|components|packaging|printing|engines?|vehicles?|marine|mining|foundry|welding|instruments?|brewery|breweries|distillery|food processing|mills?)\b"),
    ("property", r"\b(construction|constructions|build|builders|building|buildings|property|properties|estates?|developments?|roofing|roofers?|scaffold\w*|plumbing|plumbers?|joinery|joiners?|carpentry|architects?|architecture|architectural|surveyors?|surveying|civil|civils|interiors?|refurbishment|renovations?|homes|housing|lettings|letting agents?|groundworks|bricklaying|plastering|glazing|flooring)\b"),
    ("transport", r"\b(logistics|transport|transportation|haulage|hauliers?|freight|couriers?|delivery|deliveries|shipping|cargo|warehous\w*|travel|travels|tours?|airlines?|aviation|airways|airport|taxi|taxis|cars|car hire|coaches|buses|bus|rail|railway|removals|movers|parcel|garage|tyres?|mot|mobility)\b"),
    ("retail", r"\b(retail|retailers?|stores?|shops?|supermarkets?|wholesale|wholesalers?|mart|minimarket|convenience|off licen[cs]e|cash and carry|cash & carry|fashion|clothing|boutique|jewell\w*|garments?|textiles?|furniture|e-?commerce|imports?|exports?|distribut\w*)\b"),
    ("media", r"\b(media|design|designs|designers?|studios?|films?|productions?|pictures|music|musical|theatre|theater|arts|art|creative|creatives|publishing|publishers?|publications?|news|magazines?|games|gaming|entertainment|broadcast\w*|tv|television|radio|animation|photography|orchestra|opera|ballet|dance|festival|marketing|advertising|pr|public relations|branding)\b"),
    ("prof", r"\b(consulting|consultancy|consultants?|management|advisory|advisors?|advisers?|strategy|business services|outsourcing|events?|translation|translators?|interpreters?|cleaning|cleaners?|security|guarding|facilities|facility|maintenance|hr)\b"),
]
KW = [(k, re.compile(rx, re.I)) for k, rx in KEYWORDS]

def keyword_industry(name):
    for k, rx in KW:
        if rx.search(name):
            return k
    return None

def industry_of(name, sic):
    """(industry key, basis) where basis is 's' (SIC), 'k' (name keywords) or 'o' (nothing found)."""
    for k, rx in OVERRIDES:
        # Government bodies aren't companies; "Embassy Ltd" is usually a restaurant.
        if rx.search(name) and not (k == "public" and COMPANY.search(name)):
            return k, "k"
    if sic and sic not in GENERIC_SIC:
        k = sic_industry(sic)
        if k:
            return k, "s"
    k = keyword_industry(name)
    if k:
        return k, "k"
    if sic:
        k = sic_industry(sic)
        if k:
            return k, "s"
    return "other", "o"

def js_hash(s):
    """Same as the page's hash() and build_sizes.py: two 32-bit FNV-style lanes over UTF-16 code units."""
    h1, h2 = 0x811C9DC5, 0x9747B28C
    data = s.encode("utf-16-le")
    for i in range(0, len(data), 2):
        c = data[i] | (data[i + 1] << 8)
        h1 = ((h1 ^ c) * 16777619) & 0xFFFFFFFF
        h2 = ((h2 ^ c) * 2246822519) & 0xFFFFFFFF
    return f"{h1:08x}{h2:08x}"

def load_sic(path):
    if not path or not os.path.exists(path):
        return {}, ""
    with open(path, encoding="utf-8") as f:
        j = json.load(f)
    return j.get("sic", {}), j.get("meta", {}).get("snapshot", "")

def tag_rows(rows, towns, sic):
    """Set each row's industry bit (r[3]); return counts and how many came from SIC / keywords / nothing."""
    counts = {k: 0 for k in IND_KEYS}
    basis = {"s": 0, "k": 0, "o": 0}
    for r in rows:
        town = towns[r[1]] if r[1] >= 0 else ""
        k, b = industry_of(r[0], sic.get(js_hash(r[0].lower() + "|" + town.lower())))
        r[3] = 1 << IND_KEYS.index(k)
        counts[k] += 1
        basis[b] += 1
    return counts, basis

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

def retag(data_path, sic_path):
    with open(data_path, encoding="utf-8") as f:
        D = json.load(f)
    sic, snap = load_sic(sic_path)
    counts, basis = tag_rows(D["rows"], D["towns"], sic)
    D["industries"] = [[k, INDUSTRIES[k]] for k in IND_KEYS]
    D["meta"].update(untagged=0, tag_counts=counts, industry_basis=basis, sic_snapshot=snap)
    with open(data_path, "w", encoding="utf-8") as f:
        json.dump(D, f, ensure_ascii=False, separators=(",", ":"))
    print(json.dumps({"tag_counts": counts, "industry_basis": basis}, ensure_ascii=False, indent=1))

def main():
    if sys.argv[1] == "--retag":
        return retag(sys.argv[2], sys.argv[3])
    src, out_dir = sys.argv[1], sys.argv[2]
    prev_path = sys.argv[3] if len(sys.argv) > 3 and sys.argv[3] else None
    sic, sic_snap = load_sic(sys.argv[4] if len(sys.argv) > 4 else None)
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
    added = []
    for key, o in orgs.items():
        tags = 0
        routes = 0
        for rk in o["rt"]:
            routes |= 1 << route_keys.index(rk)
        rating = "a" if "a" in o["r"] else ("b" if "b" in o["r"] else "p")
        is_new = 1 if (prev_names is not None and key not in prev_names) else 0
        if is_new:
            added.append(o["n"])
        first_seen = today_n if is_new else prev_fs.get(key, 0)
        rows.append([o["n"], tidx.get(o["t"], -1), cidx.get(o["c"], -1), tags, routes, rating, is_new, first_seen])

    tag_counts, basis = tag_rows(rows, towns, sic)

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
        "untagged": 0,
        "tag_counts": tag_counts,
        "industry_basis": basis,
        "sic_snapshot": sic_snap,
        "added": len(added),
        "removed": len(removed),
    }
    data = {
        "meta": meta,
        "industries": [[k, INDUSTRIES[k]] for k in IND_KEYS],
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

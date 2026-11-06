"""Estimate company size for sponsor-register organisations from the Companies House
'Free Company Data Product' (BasicCompanyDataAsOneFile-YYYY-MM-DD.zip).

Size is inferred from the type of the latest accounts filed (Accounts.AccountCategory):
  small  <- MICRO ENTITY, TOTAL EXEMPTION FULL/SMALL, SMALL, UNAUDITED/AUDITED ABRIDGED
  medium <- MEDIUM, FULL      (page label: mid/large)
  large  <- GROUP             (page label: group)
Everything else (dormant, no accounts yet, subsidiary exemptions...) is left blank.

Usage: python3 -I build_sizes.py <ch.zip> <sponsor data.json> <out sizes.json> [<out sic.json>]
The optional sic.json maps each matched organisation to its first SIC code; build_data.py
uses it for the industry groups.
Prints only a short summary.
"""
import csv, io, json, os, re, sys, zipfile
from collections import Counter, defaultdict

SIZE = {
    "MICRO ENTITY": "small", "TOTAL EXEMPTION FULL": "small", "TOTAL EXEMPTION SMALL": "small",
    "SMALL": "small", "UNAUDITED ABRIDGED": "small", "AUDITED ABRIDGED": "small",
    "MEDIUM": "medium", "FULL": "medium", "GROUP": "large",
}

def js_hash(s):
    """Same as the page's hash(): two 32-bit FNV-style lanes over UTF-16 code units."""
    h1, h2 = 0x811C9DC5, 0x9747B28C
    data = s.encode("utf-16-le")
    for i in range(0, len(data), 2):
        c = data[i] | (data[i + 1] << 8)
        h1 = ((h1 ^ c) * 16777619) & 0xFFFFFFFF
        h2 = ((h2 ^ c) * 2246822519) & 0xFFFFFFFF
    return f"{h1:08x}{h2:08x}"

SUFFIX = re.compile(r"\b(ltd|plc|llp|lp|cic|cio|uk|group|holdings?|international|company|co)\b")

def norm(name):
    """Full normalised name, keeping the legal suffix (limited -> ltd)."""
    s = name.lower()
    s = re.split(r"\s+(?:t/a|t\\a|ta|trading as|trading under)\b|\(trading as|\(t/a", s)[0]
    s = s.replace("&", " and ").replace("+", " and ")
    s = re.sub(r"\bpublic limited company\b", " plc ", s)
    s = re.sub(r"\blimited liability partnership\b", " llp ", s)
    s = re.sub(r"\blimited\b", " ltd ", s)
    s = re.sub(r"\(.*?\)", " ", s)
    s = re.sub(r"[^a-z0-9]+", " ", s)
    s = re.sub(r"^the\s+", "", s)
    return re.sub(r"\s+", " ", s).strip()

def core(n):
    """Normalised name with legal suffixes removed (used only when unambiguous)."""
    return re.sub(r"\s+", " ", SUFFIX.sub(" ", n)).strip()

def main():
    ch_zip, data_path, out_path = sys.argv[1:4]
    sic_path = sys.argv[4] if len(sys.argv) > 4 else None
    m = re.search(r"(\d{4}-\d{2}-\d{2})", os.path.basename(ch_zip))
    snapshot = m.group(1) if m else ""
    with open(data_path, encoding="utf-8") as f:
        D = json.load(f)
    regs = []  # (hash key, full norm, core norm, town lower)
    want_full, want_core = set(), set()
    for r in D["rows"]:
        town = D["towns"][r[1]] if r[1] >= 0 else ""
        n = norm(r[0])
        c = core(n)
        regs.append((js_hash(r[0].lower() + "|" + town.lower()), n, c, town.lower()))
        if n:
            want_full.add(n)
        if len(c) >= 4:
            want_core.add(c)

    by_full = defaultdict(list)
    by_core = defaultdict(list)
    cats = Counter()
    with zipfile.ZipFile(ch_zip) as z:
        name = [x for x in z.namelist() if x.lower().endswith(".csv")][0]
        with z.open(name) as raw:
            rd = csv.reader(io.TextIOWrapper(raw, encoding="utf-8", errors="replace", newline=""))
            hdr = [h.strip() for h in next(rd)]
            iN, iNo, iT, iS, iA = (hdr.index(k) for k in ("CompanyName", "CompanyNumber", "RegAddress.PostTown", "CompanyStatus", "Accounts.AccountCategory"))
            iSic = hdr.index("SICCode.SicText_1") if "SICCode.SicText_1" in hdr else None
            for row in rd:
                if len(row) <= iA:
                    continue
                n = norm(row[iN])
                c = core(n)
                hit_f, hit_c = n in want_full, c in want_core
                if not (hit_f or hit_c):
                    continue
                sic = row[iSic].strip()[:5] if iSic is not None and iSic < len(row) else ""
                rec = (row[iNo], row[iA].strip().upper(), row[iT].strip().lower(), row[iS].strip().lower().startswith("active"), sic if sic.isdigit() else "")
                if hit_f:
                    by_full[n].append(rec)
                if hit_c:
                    by_core[c].append(rec)

    def pick(cands, town):
        live = [x for x in cands if x[3]] or cands
        if len(live) == 1:
            return live[0]
        same_town = [x for x in live if town and x[2] == town]
        return same_town[0] if len(same_town) == 1 else None

    sizes, sics, how = {}, {}, Counter()
    for key, n, c, town in regs:
        rec = pick(by_full.get(n, []), town)
        via = "exact"
        if rec is None and len(c) >= 4:
            rec = pick(by_core.get(c, []), town)
            via = "core"
        if rec is None:
            how["unmatched"] += 1
            continue
        cats[rec[1]] += 1
        if rec[4]:
            sics[key] = rec[4]
        sz = SIZE.get(rec[1])
        if not sz:
            how["matched_no_size"] += 1
            continue
        how["sized_" + via] += 1
        sizes[key] = [sz[0], rec[1].title(), rec[0]]

    counts = Counter(v[0] for v in sizes.values())
    meta = {"source": os.path.basename(ch_zip), "snapshot": snapshot, "register_date": D["meta"].get("register_date", ""),
            "orgs": len(regs), "sized": len(sizes), "small": counts["s"], "medium": counts["m"], "large": counts["l"]}
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({"meta": meta, "sizes": sizes}, f, separators=(",", ":"))
    if sic_path:
        with open(sic_path, "w", encoding="utf-8") as f:
            json.dump({"meta": {"source": meta["source"], "snapshot": snapshot, "orgs": len(regs), "with_sic": len(sics)}, "sic": sics}, f, separators=(",", ":"))
        meta_sic = len(sics)
    else:
        meta_sic = None
    print(json.dumps({"meta": meta, "with_sic": meta_sic, "how": how, "top_categories": cats.most_common(12)}, indent=1))

if __name__ == "__main__":
    main()

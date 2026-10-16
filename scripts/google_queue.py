"""Pick the next organisations to look up with Google AI Mode.

Usage: python3 -I google_queue.py <data.json> <links_dir_or_json> [--limit 25] [--place manchester] [--industry it[,health,...]] [--rating a] [--route sw]

<links_dir_or_json> is either a folder of saved database documents (one JSON file per
document, as ArtifactData's out_dir writes them) or a links.json object. Organisations
that already have any saved record (verified, checked, Google AI, AI guess) are skipped.

Prints a JSON list of {id, name, town, county, query_url}, in name order.
The id matches hash() in src/sponsor-finder.html (FNV-style over UTF-16 code units of
"lower-case name|lower-case town").
"""
import json, os, sys, urllib.parse, argparse


def js_hash(s):
    h1, h2 = 0x811C9DC5, 0x9747B28C
    units = s.encode("utf-16-le")
    for i in range(0, len(units), 2):
        c = units[i] | (units[i + 1] << 8)
        h1 = ((h1 ^ c) * 16777619) & 0xFFFFFFFF
        h2 = ((h2 ^ c) * 2246822519) & 0xFFFFFFFF
    return f"{h1:08x}{h2:08x}"


QUESTION = (
    '"{name}" {town} UK. Find its official website and its careers/jobs page. '
    "Does the careers page currently list any open roles based in the UK? "
    "Does it trade under another name? What does it do? "
    "From Companies House or its accounts, roughly how many employees does it have, "
    "and what type were its latest accounts (micro, small, medium, full, group)? "
    "End your answer with one line exactly in this format: "
    "RESULT | WEBSITE: <url or NONE> | CAREERS: <url or NONE> | UK_HIRING: YES or NO or NO_INFO | "
    "TRADING_AS: <name or NONE> | EMPLOYEES: <number or NONE> | ACCOUNTS: <micro, small, medium, full, group or NONE>"
)


def load_done(path):
    done = set()
    if os.path.isdir(path):
        for root, _, files in os.walk(path):
            for f in files:
                if f.endswith(".json"):
                    done.add(f[:-5])
    elif os.path.exists(path):
        done.update(json.load(open(path, encoding="utf-8")).keys())
    return done


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("data")
    ap.add_argument("links")
    ap.add_argument("--limit", type=int, default=25)
    ap.add_argument("--place", default="manchester")
    ap.add_argument("--industry", default="it")
    ap.add_argument("--route", default="", help="visa route key from data.json routes, e.g. sw; empty = any")
    ap.add_argument("--rating", default="", help="a = A-rated only, b = B-rated, p = provisional; empty = any")
    a = ap.parse_args()

    d = json.load(open(a.data, encoding="utf-8"))
    done = load_done(a.links)
    keys = [k for k, _ in d["industries"]]
    bit = 0
    for k in filter(None, (a.industry or "").split(",")):
        bit |= 1 << keys.index(k.strip())
    rkeys = [k for k, _ in d["routes"]]
    rbit = 1 << rkeys.index(a.route) if a.route else 0
    norm = lambda x: x.lower().replace("-", " ")
    out, remaining = [], 0
    for r in sorted(d["rows"], key=lambda r: r[0].lower()):
        town = d["towns"][r[1]] if r[1] >= 0 else ""
        county = d["counties"][r[2]] if r[2] >= 0 else ""
        if a.place and a.place not in norm(town + " " + county):
            continue
        if bit and not (r[3] & bit):
            continue
        if rbit and not (r[4] & rbit):
            continue
        if a.rating and r[5] != a.rating:
            continue
        oid = js_hash(r[0].lower() + "|" + town.lower())
        if oid in done:
            continue
        remaining += 1
        if len(out) < a.limit:
            q = QUESTION.format(name=r[0], town=town or county or "")
            out.append({"id": oid, "name": r[0], "town": town, "county": county,
                        "query_url": "https://www.google.com/search?udm=50&q=" + urllib.parse.quote_plus(q)})
    print(json.dumps({"remaining": remaining, "batch": out}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()

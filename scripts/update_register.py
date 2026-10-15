"""Download the latest gov.uk 'Register of licensed sponsors: workers' CSV and rebuild the site data.

Run by .github/workflows/update.yml every weekday. Exits without changes when gov.uk
has not published a newer register than the one in docs/data.json.

Writes:
  docs/data.json                 the data the list page loads
  data/changes/<date>.json       companies added / removed in this update
  data/history.csv               one summary line per update
Sets the GitHub Actions output `updated=true|false`.
"""
import json, os, re, subprocess, sys, tempfile, urllib.request, pathlib, csv

ROOT = pathlib.Path(__file__).resolve().parent.parent
API = "https://www.gov.uk/api/content/government/publications/register-of-licensed-sponsors-workers"
UA = {"User-Agent": "uk-visa-sponsor-list (GitHub Actions; personal job-search tool)"}


def get(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read()


def set_output(key, value):
    path = os.environ.get("GITHUB_OUTPUT")
    if path:
        with open(path, "a") as f:
            f.write(f"{key}={value}\n")
    print(f"{key}={value}")


def main():
    body = get(API).decode("utf-8")
    urls = sorted(set(re.findall(r"https://assets\.publishing\.service\.gov\.uk/[^\"'\s<>\\]+?\.csv", body)))
    cands = []
    for u in urls:
        name = urllib.request.unquote(u.rsplit("/", 1)[-1])
        if "worker" not in name.lower():
            continue
        m = re.search(r"(\d{4}-\d{2}-\d{2})", name)
        cands.append((m.group(1) if m else "", u, name))
    if not cands:
        sys.exit("No Worker and Temporary Worker CSV link found on the gov.uk page; its layout may have changed.")
    cands.sort(reverse=True)
    date, url, name = cands[0]

    prev_path = ROOT / "docs" / "data.json"
    prev_date = ""
    if prev_path.exists():
        prev_date = json.loads(prev_path.read_text(encoding="utf-8"))["meta"].get("register_date", "")
    if date and prev_date and date <= prev_date:
        print(f"Register not updated yet (still {prev_date}).")
        set_output("updated", "false")
        return

    with tempfile.TemporaryDirectory() as tmp:
        dl_dir = pathlib.Path(tmp) / "download"
        out_dir = pathlib.Path(tmp) / "out"
        dl_dir.mkdir()
        csv_path = dl_dir / name
        csv_path.write_bytes(get(url))
        prev_copy = pathlib.Path(tmp) / "prev.json"
        if prev_path.exists():
            prev_copy.write_bytes(prev_path.read_bytes())
        cmd = [sys.executable, "-I", str(ROOT / "scripts" / "build_data.py"), str(csv_path), str(out_dir)]
        if prev_copy.exists():
            cmd.append(str(prev_copy))
        subprocess.run(cmd, check=True)

        data = json.loads((out_dir / "data.json").read_text(encoding="utf-8"))
        changes = json.loads((out_dir / "changes.json").read_text(encoding="utf-8"))
        prev_path.write_bytes((out_dir / "data.json").read_bytes())

    meta = data["meta"]
    stamp = meta.get("register_date") or date
    changes_dir = ROOT / "data" / "changes"
    changes_dir.mkdir(parents=True, exist_ok=True)
    (changes_dir / f"{stamp}.json").write_text(json.dumps({"register_date": stamp, **changes}, ensure_ascii=False, indent=1), encoding="utf-8")

    hist = ROOT / "data" / "history.csv"
    new_file = not hist.exists()
    with open(hist, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new_file:
            w.writerow(["register_date", "raw_rows", "orgs", "added", "removed"])
        w.writerow([stamp, meta["raw_rows"], meta["orgs"], meta["added"], meta["removed"]])

    print(f"Updated to {stamp}: {meta['orgs']} organisations, +{meta['added']} / -{meta['removed']}")
    set_output("updated", "true")
    set_output("register_date", stamp)
    set_output("summary", f"+{meta['added']} / -{meta['removed']}")


if __name__ == "__main__":
    main()

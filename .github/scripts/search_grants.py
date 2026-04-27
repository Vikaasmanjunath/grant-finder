import requests, json, datetime, os
from bs4 import BeautifulSoup

with open("config.json") as f:
    config = json.load(f)

keywords = config["keywords"]
results = []
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}
today = datetime.date.today()

print(f"Starting grant search — {today}")
print(f"Keywords: {keywords}\n")

# ─── 1. Grants.gov — correct v1 API ──────────────────────────────
print("=== Searching Grants.gov ===")
for kw in keywords[:6]:
    try:
        r = requests.post(
            "https://api.grants.gov/v1/api/search",
            json={
                "keyword": kw,
                "oppStatuses": "posted",
                "rows": 5,
                "startRecordNum": 0
            },
            headers=HEADERS,
            timeout=20
        )
        print(f"  '{kw}' → status {r.status_code}")
        if r.ok:
            hits = r.json().get("data", {}).get("oppHits", [])
            print(f"    {len(hits)} results")
            for g in hits:
                results.append({
                    "title": g.get("oppTitle", ""),
                    "agency": g.get("agencyName", ""),
                    "deadline": g.get("closeDate", ""),
                    "status": "Open",
                    "amount": 0,
                    "keyword_match": kw,
                    "source": "Grants.gov",
                    "link": f"https://www.grants.gov/search-results-detail/{g.get('id','')}"
                })
    except Exception as e:
        print(f"  Error: {e}")

# ─── 2. NIH REPORTER — remove date filter, search all active ──────
print("\n=== Searching NIH RePORTER ===")
for kw in keywords[:5]:
    try:
        r = requests.post(
            "https://api.reporter.nih.gov/v2/projects/search",
            json={
                "criteria": {
                    "advanced_text_search": {
                        "operator": "And",
                        "search_field": "terms",
                        "search_text": kw
                    },
                    "fiscal_years": [today.year, today.year - 1]
                },
                "limit": 5,
                "offset": 0
            },
            timeout=20
        )
        print(f"  '{kw}' → status {r.status_code}")
        if r.ok:
            hits = r.json().get("results", [])
            print(f"    {len(hits)} results")
            for p in hits:
                results.append({
                    "title": p.get("project_title", ""),
                    "agency": "NIH",
                    "deadline": "",
                    "status": "Active grant — see for open calls",
                    "amount": p.get("award_amount", 0),
                    "keyword_match": kw,
                    "source": "NIH",
                    "link": f"https://reporter.nih.gov/project-details/{p.get('appl_id','')}"
                })
    except Exception as e:
        print(f"  Error: {e}")

# ─── 3. NIH Guide — scrape open funding announcements ─────────────
print("\n=== Searching NIH Guide (open FOAs) ===")
NIH_TERMS = [
    "exercise", "physical+activity", "cardiovascular",
    "vascular", "fitness"
]
for term in NIH_TERMS:
    try:
        url = f"https://grants.nih.gov/grants/guide/search_results.htm?Search_Type=Activity&Search_Parm=PA&terms={term}&active_only=true"
        r = requests.get(url, headers=HEADERS, timeout=20)
        print(f"  '{term}' → status {r.status_code}")
        if r.ok:
            soup = BeautifulSoup(r.text, "html.parser")
            links = soup.select("a[href*='grants.nih.gov/grants/guide']")
            print(f"    {len(links)} links found")
            for a in links:
                text = a.get_text(strip=True)
                if len(text) < 10:
                    continue
                href = a.get("href", "")
                full_link = href if href.startswith("http") else "https://grants.nih.gov" + href
                if not any(x["link"] == full_link for x in results):
                    results.append({
                        "title": text,
                        "agency": "NIH",
                        "deadline": "",
                        "status": "Open FOA",
                        "amount": 0,
                        "keyword_match": term,
                        "source": "NIH Guide",
                        "link": full_link
                    })
    except Exception as e:
        print(f"  Error: {e}")

# ─── 4. ACSM ──────────────────────────────────────────────────────
print("\n=== Searching ACSM ===")
ACSM_URLS = [
    "https://www.acsm.org/acsm-membership/research-grants",
    "https://www.acsm.org/education-resources/grants-fellowships"
]
for url in ACSM_URLS:
    try:
        r = requests.get(url, headers=HEADERS, timeout=20)
        print(f"  {url} → status {r.status_code}")
        if not r.ok:
            continue
        soup = BeautifulSoup(r.text, "html.parser")
        for a in soup.find_all("a", href=True):
            text = a.get_text(strip=True)
            if not text or len(text) < 15:
                continue
            is_grant = any(w in text.lower() for w in [
                "grant", "award", "fellowship", "fund", "research", "doctoral"
            ])
            if is_grant:
                href = a["href"]
                full_link = href if href.startswith("http") else "https://www.acsm.org" + href
                if not any(x["link"] == full_link for x in results):
                    results.append({
                        "title": text,
                        "agency": "ACSM Foundation",
                        "deadline": "",
                        "status": "Check website",
                        "amount": 0,
                        "keyword_match": "exercise science",
                        "source": "ACSM",
                        "link": full_link
                    })
    except Exception as e:
        print(f"  Error: {e}")

# ─── 5. AHA ───────────────────────────────────────────────────────
print("\n=== Searching AHA ===")
AHA_URLS = [
    "https://professional.heart.org/en/research-programs/aha-funding-opportunities",
    "https://professional.heart.org/en/research-programs"
]
for url in AHA_URLS:
    try:
        r = requests.get(url, headers=HEADERS, timeout=20)
        print(f"  {url} → status {r.status_code}")
        if not r.ok:
            continue
        soup = BeautifulSoup(r.text, "html.parser")
        for a in soup.find_all("a", href=True):
            text = a.get_text(strip=True)
            if not text or len(text) < 15:
                continue
            is_grant = any(w in text.lower() for w in [
                "grant", "award", "fellowship", "career", "predoctoral",
                "postdoctoral", "investigator", "scientist", "research"
            ])
            if is_grant:
                href = a["href"]
                full_link = href if href.startswith("http") else "https://professional.heart.org" + href
                if not any(x["link"] == full_link for x in results):
                    results.append({
                        "title": text,
                        "agency": "AHA",
                        "deadline": "",
                        "status": "Check website",
                        "amount": 0,
                        "keyword_match": "cardiovascular research",
                        "source": "AHA",
                        "link": full_link
                    })
    except Exception as e:
        print(f"  Error: {e}")

# ─── 6. Robert Wood Johnson Foundation ───────────────────────────
print("\n=== Searching RWJF ===")
try:
    r = requests.get(
        "https://www.rwjf.org/en/grants/grant-opportunities.html",
        headers=HEADERS, timeout=20
    )
    print(f"  Status: {r.status_code}")
    if r.ok:
        soup = BeautifulSoup(r.text, "html.parser")
        for a in soup.find_all("a", href=True):
            text = a.get_text(strip=True)
            if not text or len(text) < 15:
                continue
            is_grant = any(w in text.lower() for w in [
                "grant", "award", "fellowship", "health", "research", "fund"
            ])
            if is_grant:
                href = a["href"]
                full_link = href if href.startswith("http") else "https://www.rwjf.org" + href
                if not any(x["link"] == full_link for x in results):
                    results.append({
                        "title": text,
                        "agency": "Robert Wood Johnson Foundation",
                        "deadline": "",
                        "status": "Check website",
                        "amount": 0,
                        "keyword_match": "health research",
                        "source": "RWJF",
                        "link": full_link
                    })
except Exception as e:
    print(f"  Error: {e}")

# ─── 7. Deduplicate + sort ────────────────────────────────────────
seen = set()
unique = []
for item in results:
    if item["title"] and item["link"] not in seen:
        seen.add(item["link"])
        unique.append(item)

def sort_key(g):
    d = g.get("deadline", "")
    try:
        return datetime.datetime.strptime(d, "%m/%d/%Y")
    except:
        return datetime.datetime(9999, 1, 1)

unique.sort(key=sort_key)

os.makedirs("docs", exist_ok=True)
with open("docs/grants.json", "w") as f:
    json.dump({
        "updated": str(today),
        "results": unique
    }, f, indent=2)

# ─── Summary ──────────────────────────────────────────────────────
print(f"\n{'='*40}")
print(f"TOTAL: {len(unique)} opportunities saved")
print("Breakdown:")
for source in ["Grants.gov", "NIH", "NIH Guide", "ACSM", "AHA", "RWJF"]:
    count = sum(1 for x in unique if x["source"] == source)
    print(f"  {source}: {count}")

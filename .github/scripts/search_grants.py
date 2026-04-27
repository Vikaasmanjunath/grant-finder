import requests, json, datetime, os
from bs4 import BeautifulSoup

with open("config.json") as f:
    config = json.load(f)

keywords = config["keywords"]
results = []
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

# ─── 1. Grants.gov — fixed API call ──────────────────────────────
for kw in keywords[:5]:
    try:
        r = requests.get(
            "https://api.grants.gov/v2/api/opportunities/search",
            params={
                "keyword": kw,
                "oppStatuses": "posted",
                "rows": 10
            },
            headers=HEADERS,
            timeout=20
        )
        print(f"Grants.gov status for '{kw}': {r.status_code}")
        if r.ok:
            data = r.json()
            hits = data.get("data", {}).get("oppHits", [])
            print(f"  → {len(hits)} results")
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
        print(f"Grants.gov error for '{kw}': {e}")

# ─── 2. NIH RePORTER — open funding opportunities ─────────────────
for kw in keywords[:4]:
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
                    "project_start_date": {
                        "from_date": datetime.date.today().strftime("%Y/%m/%d"),
                        "to_date": (datetime.date.today() + datetime.timedelta(days=365)).strftime("%Y/%m/%d")
                    }
                },
                "limit": 10,
                "offset": 0
            },
            timeout=20
        )
        print(f"NIH status for '{kw}': {r.status_code}")
        if r.ok:
            hits = r.json().get("results", [])
            print(f"  → {len(hits)} results")
            for p in hits:
                results.append({
                    "title": p.get("project_title", ""),
                    "agency": "NIH — " + p.get("agency_ic_admin", {}).get("abbreviation", ""),
                    "deadline": p.get("project_start_date", ""),
                    "status": "Open",
                    "amount": p.get("award_amount", 0),
                    "keyword_match": kw,
                    "source": "NIH",
                    "link": f"https://reporter.nih.gov/project-details/{p.get('appl_id','')}"
                })
    except Exception as e:
        print(f"NIH error for '{kw}': {e}")

# ─── 3. ACSM Foundation ───────────────────────────────────────────
ACSM_URLS = [
    "https://www.acsm.org/acsm-membership/research-grants",
    "https://www.acsm.org/education-resources/grants-fellowships"
]
for url in ACSM_URLS:
    try:
        r = requests.get(url, headers=HEADERS, timeout=20)
        print(f"ACSM status ({url}): {r.status_code}")
        if not r.ok:
            continue
        soup = BeautifulSoup(r.text, "html.parser")
        for a in soup.find_all("a", href=True):
            text = a.get_text(strip=True)
            if not text or len(text) < 15:
                continue
            is_grant = any(w in text.lower() for w in [
                "grant", "award", "fellowship", "fund", "research"
            ])
            matched_kw = next((kw for kw in keywords if kw.lower() in text.lower()), None)
            if is_grant or matched_kw:
                href = a["href"]
                full_link = href if href.startswith("http") else "https://www.acsm.org" + href
                if not any(x["link"] == full_link for x in results):
                    results.append({
                        "title": text,
                        "agency": "ACSM Foundation",
                        "deadline": "",
                        "status": "Check website",
                        "amount": 0,
                        "keyword_match": matched_kw or "grant/fellowship",
                        "source": "ACSM",
                        "link": full_link
                    })
    except Exception as e:
        print(f"ACSM error: {e}")

# ─── 4. AHA ───────────────────────────────────────────────────────
AHA_URLS = [
    "https://professional.heart.org/en/research-programs/aha-funding-opportunities",
    "https://professional.heart.org/en/research-programs"
]
for url in AHA_URLS:
    try:
        r = requests.get(url, headers=HEADERS, timeout=20)
        print(f"AHA status ({url}): {r.status_code}")
        if not r.ok:
            continue
        soup = BeautifulSoup(r.text, "html.parser")
        for a in soup.find_all("a", href=True):
            text = a.get_text(strip=True)
            if not text or len(text) < 15:
                continue
            is_grant = any(w in text.lower() for w in [
                "grant", "award", "fellowship", "career", "predoctoral",
                "postdoctoral", "investigator", "scientist"
            ])
            matched_kw = next((kw for kw in keywords if kw.lower() in text.lower()), None)
            if is_grant or matched_kw:
                href = a["href"]
                full_link = href if href.startswith("http") else "https://professional.heart.org" + href
                if not any(x["link"] == full_link for x in results):
                    results.append({
                        "title": text,
                        "agency": "AHA",
                        "deadline": "",
                        "status": "Check website",
                        "amount": 0,
                        "keyword_match": matched_kw or "grant/fellowship",
                        "source": "AHA",
                        "link": full_link
                    })
    except Exception as e:
        print(f"AHA error: {e}")

# ─── 5. Robert Wood Johnson Foundation ───────────────────────────
try:
    r = requests.get(
        "https://www.rwjf.org/en/grants/grant-opportunities.html",
        headers=HEADERS, timeout=20
    )
    print(f"RWJF status: {r.status_code}")
    if r.ok:
        soup = BeautifulSoup(r.text, "html.parser")
        for a in soup.find_all("a", href=True):
            text = a.get_text(strip=True)
            if not text or len(text) < 15:
                continue
            is_grant = any(w in text.lower() for w in [
                "grant", "award", "fellowship", "health", "research"
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
    print(f"RWJF error: {e}")

# ─── 6. Deduplicate + sort by deadline ───────────────────────────
seen = set()
unique = []
for item in results:
    if item["link"] not in seen:
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
        "updated": str(datetime.date.today()),
        "results": unique
    }, f, indent=2)

print(f"\nDone. {len(unique)} total opportunities saved.")
print("Breakdown by source:")
for source in ["Grants.gov", "NIH", "ACSM", "AHA", "RWJF"]:
    count = sum(1 for x in unique if x["source"] == source)
    print(f"  {source}: {count}")

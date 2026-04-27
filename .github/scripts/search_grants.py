import requests, json, datetime, os
from bs4 import BeautifulSoup

with open("config.json") as f:
    config = json.load(f)

keywords = config["keywords"]
results = []

HEADERS = {"User-Agent": "Mozilla/5.0 (grant-finder-bot; educational use)"}

# ─── 1. NIH Reporter API ──────────────────────────────────────────
for kw in keywords[:5]:
    try:
        r = requests.post("https://api.reporter.nih.gov/v2/projects/search", json={
            "criteria": {"advanced_text_search": {
                "operator": "And", "search_field": "all", "search_text": kw
            }},
            "limit": 10, "offset": 0
        }, timeout=15)
        if r.ok:
            for p in r.json().get("results", []):
                results.append({
                    "title": p.get("project_title", ""),
                    "agency": "NIH",
                    "amount": p.get("award_amount", 0),
                    "pi": p.get("principal_investigators", [{}])[0].get("full_name", ""),
                    "keyword_match": kw,
                    "deadline": "",
                    "link": f"https://reporter.nih.gov/project-details/{p.get('appl_id', '')}"
                })
    except Exception as e:
        print(f"NIH error for '{kw}': {e}")

# ─── 2. Grants.gov API ────────────────────────────────────────────
for kw in keywords[:3]:
    try:
        r = requests.post("https://api.grants.gov/v1/api/search", json={
            "keyword": kw, "rows": 10, "startRecordNum": 0
        }, timeout=15)
        if r.ok:
            for g in r.json().get("data", {}).get("oppHits", []):
                results.append({
                    "title": g.get("oppTitle", ""),
                    "agency": g.get("agencyName", ""),
                    "deadline": g.get("closeDate", ""),
                    "amount": 0,
                    "keyword_match": kw,
                    "link": f"https://www.grants.gov/search-results-detail/{g.get('id', '')}"
                })
    except Exception as e:
        print(f"Grants.gov error for '{kw}': {e}")

# ─── 3. ACSM Foundation Grants ───────────────────────────────────
# ACSM lists grants on their foundation page — scrape the grant cards
ACSM_URLS = [
    "https://www.acsm.org/acsm-membership/research-grants",
    "https://www.acsm.org/education-resources/grants-fellowships"
]

for url in ACSM_URLS:
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        if not r.ok:
            continue
        soup = BeautifulSoup(r.text, "html.parser")

        # ACSM uses various card/list structures — catch all anchor text containing grant keywords
        for a in soup.find_all("a", href=True):
            text = a.get_text(strip=True)
            if not text or len(text) < 15:
                continue
            text_lower = text.lower()
            matched_kw = next((kw for kw in keywords if kw.lower() in text_lower), None)
            # Also grab anything that looks like a grant/fellowship/award
            is_grant_link = any(word in text_lower for word in [
                "grant", "award", "fellowship", "fund", "research support"
            ])
            if matched_kw or is_grant_link:
                href = a["href"]
                full_link = href if href.startswith("http") else "https://www.acsm.org" + href
                # Avoid duplicate links
                if not any(r2["link"] == full_link for r2 in results):
                    results.append({
                        "title": text,
                        "agency": "ACSM Foundation",
                        "amount": 0,
                        "deadline": "",
                        "keyword_match": matched_kw or "grant/fellowship",
                        "link": full_link
                    })
    except Exception as e:
        print(f"ACSM scrape error ({url}): {e}")

# ─── 4. American Heart Association (AHA) ─────────────────────────
AHA_URLS = [
    "https://professional.heart.org/en/research-programs/aha-funding-opportunities",
    "https://professional.heart.org/en/research-programs"
]

for url in AHA_URLS:
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        if not r.ok:
            continue
        soup = BeautifulSoup(r.text, "html.parser")

        for a in soup.find_all("a", href=True):
            text = a.get_text(strip=True)
            if not text or len(text) < 15:
                continue
            text_lower = text.lower()
            matched_kw = next((kw for kw in keywords if kw.lower() in text_lower), None)
            is_grant_link = any(word in text_lower for word in [
                "grant", "award", "fellowship", "career development",
                "postdoctoral", "scientist", "investigator"
            ])
            if matched_kw or is_grant_link:
                href = a["href"]
                full_link = href if href.startswith("http") else "https://professional.heart.org" + href
                if not any(r2["link"] == full_link for r2 in results):
                    results.append({
                        "title": text,
                        "agency": "AHA",
                        "amount": 0,
                        "deadline": "",
                        "keyword_match": matched_kw or "grant/fellowship",
                        "link": full_link
                    })
    except Exception as e:
        print(f"AHA scrape error ({url}): {e}")

# ─── 5. Deduplicate and save ──────────────────────────────────────
seen = set()
unique_results = []
for item in results:
    key = item["link"]
    if key not in seen:
        seen.add(key)
        unique_results.append(item)

os.makedirs("docs", exist_ok=True)
with open("docs/grants.json", "w") as f:
    json.dump({
        "updated": str(datetime.date.today()),
        "results": unique_results
    }, f, indent=2)

print(f"Done. {len(unique_results)} unique grants saved.")

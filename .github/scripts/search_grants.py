import requests, json, datetime, os
from bs4 import BeautifulSoup

with open("config.json") as f:
    config = json.load(f)

keywords = config["keywords"]
results = []
HEADERS = {"User-Agent": "Mozilla/5.0 (grant-finder-bot; educational use)"}

# ─── 1. Grants.gov — OPEN opportunities only ─────────────────────
for kw in keywords[:5]:
    try:
        r = requests.post("https://api.grants.gov/v1/api/search", json={
            "keyword": kw,
            "oppStatuses": "forecasted|posted",  # only open/upcoming
            "rows": 10,
            "startRecordNum": 0
        }, timeout=15)
        if r.ok:
            for g in r.json().get("data", {}).get("oppHits", []):
                results.append({
                    "title": g.get("oppTitle", ""),
                    "agency": g.get("agencyName", ""),
                    "deadline": g.get("closeDate", ""),
                    "status": g.get("oppStatus", ""),
                    "amount": 0,
                    "keyword_match": kw,
                    "source": "Grants.gov",
                    "link": f"https://www.grants.gov/search-results-detail/{g.get('id', '')}"
                })
    except Exception as e:
        print(f"Grants.gov error: {e}")

# ─── 2. NIH Guide — Active Funding Opportunity Announcements ──────
# These are OPEN calls for applications, not past awards
NIH_GUIDE_TERMS = [
    "exercise", "physical activity", "cardiovascular",
    "vascular", "arterial stiffness"
]
for term in NIH_GUIDE_TERMS:
    try:
        r = requests.get(
            f"https://grants.nih.gov/funding/searchGuide/#/?terms={term}&activeFunding=true",
            headers=HEADERS, timeout=15
        )
        # NIH Guide API endpoint
        r2 = requests.get(
            f"https://grants.nih.gov/grants/guide/search_results.htm?Search_Type=Activity&Search_Parm=PA&terms={term}",
            headers=HEADERS, timeout=15
        )
        if r2.ok:
            soup = BeautifulSoup(r2.text, "html.parser")
            for row in soup.select("table tr"):
                cols = row.find_all("td")
                if len(cols) >= 3:
                    title_tag = cols[0].find("a")
                    if title_tag:
                        title = title_tag.get_text(strip=True)
                        link = "https://grants.nih.gov" + title_tag["href"] if title_tag.get("href", "").startswith("/") else title_tag.get("href", "")
                        deadline = cols[2].get_text(strip=True) if len(cols) > 2 else ""
                        if not any(r3["link"] == link for r3 in results):
                            results.append({
                                "title": title,
                                "agency": "NIH",
                                "deadline": deadline,
                                "status": "Open",
                                "amount": 0,
                                "keyword_match": term,
                                "source": "NIH Guide",
                                "link": link
                            })
    except Exception as e:
        print(f"NIH Guide error for '{term}': {e}")

# ─── 3. ACSM Foundation — Open grant cycles ───────────────────────
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
        for a in soup.find_all("a", href=True):
            text = a.get_text(strip=True)
            if not text or len(text) < 15:
                continue
            text_lower = text.lower()
            is_grant = any(w in text_lower for w in ["grant", "award", "fellowship", "fund"])
            matched_kw = next((kw for kw in keywords if kw.lower() in text_lower), None)
            if is_grant or matched_kw:
                href = a["href"]
                full_link = href if href.startswith("http") else "https://www.acsm.org" + href
                if not any(r2["link"] == full_link for r2 in results):
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

# ─── 4. AHA — Open funding opportunities ─────────────────────────
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
            is_grant = any(w in text_lower for w in [
                "grant", "award", "fellowship", "career development",
                "predoctoral", "postdoctoral", "investigator"
            ])
            matched_kw = next((kw for kw in keywords if kw.lower() in text_lower), None)
            if is_grant or matched_kw:
                href = a["href"]
                full_link = href if href.startswith("http") else "https://professional.heart.org" + href
                if not any(r2["link"] == full_link for r2 in results):
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

# ─── 5. Deduplicate + sort by deadline ───────────────────────────
seen = set()
unique = []
for item in results:
    if item["link"] not in seen:
        seen.add(item["link"])
        unique.append(item)

# Sort — grants with deadlines first
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

print(f"Done. {len(unique)} open grant opportunities saved.")

import requests, json, datetime, os

with open("config.json") as f:
    config = json.load(f)

keywords = config["keywords"]
results = []

# --- NIH Reporter API ---
for kw in keywords[:5]:  # limit to avoid rate caps
    r = requests.post("https://api.reporter.nih.gov/v2/projects/search", json={
        "criteria": {"advanced_text_search": {"operator": "And", "search_field": "all", "search_text": kw}},
        "limit": 10,
        "offset": 0
    })
    if r.ok:
        for p in r.json().get("results", []):
            results.append({
                "title": p.get("project_title", ""),
                "agency": "NIH",
                "amount": p.get("award_amount", 0),
                "pi": p.get("principal_investigators", [{}])[0].get("full_name", ""),
                "keyword_match": kw,
                "link": f"https://reporter.nih.gov/project-details/{p.get('appl_id','')}"
            })

# --- Grants.gov API ---
for kw in keywords[:3]:
    r = requests.post("https://api.grants.gov/v1/api/search", json={
        "keyword": kw, "rows": 10, "startRecordNum": 0
    })
    if r.ok:
        for g in r.json().get("data", {}).get("oppHits", []):
            results.append({
                "title": g.get("oppTitle", ""),
                "agency": g.get("agencyName", ""),
                "deadline": g.get("closeDate", ""),
                "keyword_match": kw,
                "link": f"https://www.grants.gov/search-results-detail/{g.get('id','')}"
            })

# Save to JSON for the page builder
os.makedirs("docs", exist_ok=True)
with open("docs/grants.json", "w") as f:
    json.dump({"updated": str(datetime.date.today()), "results": results}, f, indent=2)

print(f"Found {len(results)} results")

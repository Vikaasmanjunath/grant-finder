import requests
import yaml
import pandas as pd
from datetime import datetime
from pathlib import Path

KEYWORDS_FILE = "keywords.yaml"
SEEN_FILE = "seen_grants.csv"
OUTPUT_FILE = "new_grants.csv"

def load_keywords():
    with open(KEYWORDS_FILE, "r") as f:
        return yaml.safe_load(f)

def score_grant(text, keywords):
    text = text.lower()
    score = 0

    for word in keywords["primary_keywords"]:
        if word.lower() in text:
            score += 2

    for word in keywords["high_priority_terms"]:
        if word.lower() in text:
            score += 4

    for word in keywords["exclude_terms"]:
        if word.lower() in text:
            score -= 5

    return score

def search_grants_gov(keywords):
    results = []

    for keyword in keywords["primary_keywords"]:
        url = "https://api.grants.gov/v1/api/search2"

        payload = {
            "keyword": keyword,
            "oppStatuses": "posted|forecasted",
            "rows": 25
        }

        try:
            r = requests.post(url, json=payload, timeout=20)
            data = r.json()

            opportunities = data.get("data", {}).get("oppHits", [])

            for opp in opportunities:
                title = opp.get("title", "")
                agency = opp.get("agency", "")
                number = opp.get("number", "")
                close_date = opp.get("closeDate", "")
                opp_id = opp.get("id", "")

                text = f"{title} {agency} {number}"

                results.append({
                    "source": "Grants.gov",
                    "title": title,
                    "agency": agency,
                    "opportunity_number": number,
                    "close_date": close_date,
                    "url": f"https://www.grants.gov/search-results-detail/{opp_id}",
                    "score": score_grant(text, keywords),
                    "date_found": datetime.today().strftime("%Y-%m-%d")
                })

        except Exception as e:
            print(f"Error searching {keyword}: {e}")

    return results

def remove_seen(grants):
    if not Path(SEEN_FILE).exists():
        return grants

    seen = pd.read_csv(SEEN_FILE)
    seen_urls = set(seen["url"].astype(str))

    return [g for g in grants if g["url"] not in seen_urls]

def save_results(new_grants):
    if not new_grants:
        print("No new grants found.")
        return

    df = pd.DataFrame(new_grants)

    # filter + sort
    df = df[df["score"] >= 4]
    df = df.sort_values("score", ascending=False)

    df.to_csv(OUTPUT_FILE, index=False)

    if Path(SEEN_FILE).exists():
        old = pd.read_csv(SEEN_FILE)
        combined = pd.concat([old, df], ignore_index=True)
    else:
        combined = df

    combined.drop_duplicates(subset=["url"]).to_csv(SEEN_FILE, index=False)

    print(df.to_string(index=False))

def main():
    keywords = load_keywords()
    grants = search_grants_gov(keywords)
    new_grants = remove_seen(grants)
    save_results(new_grants)

if __name__ == "__main__":
    main()

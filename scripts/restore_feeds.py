import json
import os
from urllib.parse import urlparse

def migrate_feeds():
    print("Migrating feeds from feeds.json to prognosticator.json...")
    
    # Load source feeds
    if not os.path.exists("feeds.json"):
        print("Error: feeds.json not found")
        return

    with open("feeds.json", "r") as f:
        old_config = json.load(f)
        old_feeds = old_config.get("feeds", [])

    # Load target config
    if not os.path.exists("prognosticator.json"):
        print("Error: prognosticator.json not found")
        return

    with open("prognosticator.json", "r") as f:
        current_config = json.load(f)

    # Prepare new feeds list
    new_feeds = []
    seen_urls = set()

    # Helper to generate name from URL
    def get_name(url, category):
        try:
            domain = urlparse(url).netloc.replace("www.", "")
            name = domain.split('.')[0].title()
            if "reddit" in domain:
                name = f"Reddit: {url.split('/r/')[-1].split('/')[0]}"
            return f"{name} ({category})"
        except:
            return "Unknown Feed"

    # Process old feeds
    for feed in old_feeds:
        url = feed.get("url")
        if not url:
            continue
            
        if url in seen_urls:
            continue
            
        category = feed.get("category", "General")
        name = get_name(url, category)
        
        new_feeds.append({
            "name": name,
            "url": url,
            "category": category # Keeping category for future use
        })
        seen_urls.add(url)

    # Update config
    if "feeds" not in current_config:
        current_config["feeds"] = {}
    
    current_config["feeds"]["rss"] = new_feeds
    
    # Save back
    with open("prognosticator.json", "w") as f:
        json.dump(current_config, f, indent=2)
        
    print(f"Successfully migrated {len(new_feeds)} feeds to prognosticator.json")

if __name__ == "__main__":
    migrate_feeds()

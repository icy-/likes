import json, re, requests
from datetime import datetime

def get_owner_repo(url):
    m = re.search("github\\.com/([^/]+)/([^/]+)$", url.strip("/"))
    return m.groups() if m else (None, None)

def to_unix_timestamp(iso_str):
    if not iso_str:
        return None
    try:
        dt = datetime.strptime(iso_str, "%Y-%m-%dT%H:%M:%SZ")
        return int(dt.timestamp())
    except Exception:
        return None

file = "cream.json"
with open(file, "r") as f:
    plugins = json.load(f)

updated = False
for plugin in plugins:
    repo_url = plugin.get("RepoUrl")
    if not repo_url:
        print(f"Skipping {plugin.get('InternalName')} - no RepoUrl")
        continue

    owner, repo = get_owner_repo(repo_url)
    if not owner or not repo:
        print(f"Skipping {plugin.get('InternalName')} - invalid RepoUrl: {repo_url}")
        continue

    # We request so many releases from the API for summation of download counts
    api_url = f"https://api.github.com/repos/{owner}/{repo}/releases?per_page=100"
    print(f"Fetching releases for {plugin.get('InternalName')} ({api_url})")
    resp = requests.get(api_url)
    if resp.status_code != 200:
        print(f"Failed to fetch {api_url}: {resp.status_code}")
        continue

    releases = resp.json()
    if not isinstance(releases, list) or not releases:
        print(f"No releases for {plugin.get('InternalName')}")
        continue
    
    total_downloads = sum(
        a.get("download_count", 0)
        for r in releases
        for a in r.get("assets", [])
    )

    # Since this is already sorted descending, the first element is latest
    last_updated_iso = releases[0].get("published_at")
    last_updated_unix = to_unix_timestamp(last_updated_iso)
    last_download_url = releases[0].get('assets', [])[0].get("browser_download_url")

    plugin["LastUpdate"] = last_updated_unix
    plugin["DownloadCount"] = total_downloads    
    plugin["DownloadLinkInstall"] = last_download_url
    plugin["DownloadLinkTesting"] = last_download_url
    plugin["DownloadLinkUpdate"] = last_download_url

    updated = True
    print(f"✔ Updated {plugin.get('InternalName')}: {total_downloads} downloads, last updated {last_updated_unix}")

if updated:
    with open(file, "w") as f:
        json.dump(plugins, f, indent=2)
else:
    print("No updates to apply.")
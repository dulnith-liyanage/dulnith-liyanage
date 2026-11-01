#!/usr/bin/env python3
import os
import re
import json
import urllib.request

USERNAME = "dulnith-liyanage"
TOKEN = os.environ.get("GITHUB_TOKEN", "")

def fetch_pinned_repos():
    query = """
    {
      user(login: "%s") {
        pinnedItems(first: 4, types: REPOSITORY) {
          nodes {
            ... on Repository {
              name
              nameWithOwner
              description
              url
              primaryLanguage {
                name
              }
              repositoryTopics(first: 3) {
                nodes {
                  topic {
                    name
                  }
                }
              }
            }
          }
        }
      }
    }
    """ % USERNAME

    headers = {
        "User-Agent": "Profile-Sync-Bot",
        "Content-Type": "application/json"
    }
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"

    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query}).encode("utf-8"),
        headers=headers
    )
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data.get("data", {}).get("user", {}).get("pinnedItems", {}).get("nodes", [])
    except Exception as e:
        print(f"Error fetching pinned repos: {e}")
        return []

def format_pinned_table(repos):
    if not repos:
        return None

    def render_cell(r):
        name_with_owner = r.get("nameWithOwner", "")
        name = name_with_owner if not name_with_owner.startswith(f"{USERNAME}/") else r.get("name", "")
        url = r.get("url", f"https://github.com/{name_with_owner}")
        desc = r.get("description") or "No description provided."
        
        # Pick relevant emoji
        lower = (name + " " + desc).lower()
        if "cane" in lower: emoji = "🦯"
        elif "desk" in lower or "yeti" in lower: emoji = "👾"
        elif "sort" in lower or "bin" in lower or "eco" in lower: emoji = "♻️"
        elif "radar" in lower or "retail" in lower: emoji = "📊"
        elif "ai" in lower or "vision" in lower: emoji = "🤖"
        elif "embedded" in lower or "esp32" in lower or "hardware" in lower: emoji = "⚡"
        else: emoji = "🚀"

        badges = []
        if r.get("primaryLanguage"):
            lang = r["primaryLanguage"]["name"]
            badges.append(f'<img src="https://img.shields.io/badge/{urllib.parse.quote(lang)}-00599C?style=flat-square" />')
        
        topics = [n["topic"]["name"] for n in r.get("repositoryTopics", {}).get("nodes", [])]
        for t in topics[:2]:
            badges.append(f'<img src="https://img.shields.io/badge/{urllib.parse.quote(t)}-blue?style=flat-square" />')
        
        badge_html = " ".join(badges)
        return f'''    <td width="50%" valign="top">
      <h4>{emoji} <a href="{url}">{name}</a></h4>
      <p>{desc}</p>
      <p>{badge_html}</p>
    </td>'''

    rows = []
    for i in range(0, len(repos), 2):
        c1 = render_cell(repos[i])
        c2 = render_cell(repos[i+1]) if i+1 < len(repos) else '    <td width="50%" valign="top"></td>'
        rows.append(f'  <tr>\n{c1}\n{c2}\n  </tr>')

    return "<table>\n" + "\n".join(rows) + "\n</table>"

def fetch_recent_activity():
    url = f"https://api.github.com/users/{USERNAME}/events/public?per_page=30"
    headers = {"User-Agent": "Profile-Sync-Bot"}
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"

    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req) as resp:
            events = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        print(f"Error fetching events: {e}")
        return None

    lines = []
    seen = set()
    for e in events:
        t = e.get("type")
        repo = e.get("repo", {}).get("name")
        repo_url = f"https://github.com/{repo}"
        key = (t, repo)

        if key in seen:
            continue
        seen.add(key)

        if t == "PushEvent":
            commits = e.get("payload", {}).get("commits", [])
            msg = commits[0]["message"].split("\n")[0] if commits else "Update code"
            if len(msg) > 60: msg = msg[:57] + "..."
            lines.append(f"1. 🚀 Pushed to [{repo}]({repo_url}): *\"{msg}\"*")
        elif t == "PullRequestEvent":
            action = e.get("payload", {}).get("action", "")
            num = e.get("payload", {}).get("number", "")
            lines.append(f"1. 🔀 {action.capitalize()} PR #{num} in [{repo}]({repo_url})")
        elif t == "IssuesEvent":
            action = e.get("payload", {}).get("action", "")
            num = e.get("payload", {}).get("issue", {}).get("number", "")
            lines.append(f"1. 💬 {action.capitalize()} issue #{num} in [{repo}]({repo_url})")
        elif t == "WatchEvent":
            lines.append(f"1. ⭐ Starred [{repo}]({repo_url})")
        elif t == "CreateEvent":
            ref_type = e.get("payload", {}).get("ref_type", "repo")
            lines.append(f"1. 📦 Created {ref_type} in [{repo}]({repo_url})")

        if len(lines) >= 8:
            break

    return "\n".join(lines) if lines else None

def update_readme():
    readme_path = os.path.join(os.path.dirname(__file__), "..", "..", "README.md")
    if not os.path.exists(readme_path):
        readme_path = "README.md"
    
    with open(readme_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Update Pinned Repos
    repos = fetch_pinned_repos()
    if repos:
        new_table = format_pinned_table(repos)
        if new_table:
            pattern = r"(<!-- START_SECTION:featured-projects -->)(.*?)(<!-- END_SECTION:featured-projects -->)"
            content = re.sub(pattern, rf"\g<1>\n{new_table}\n\g<3>", content, flags=re.DOTALL)
            print("Updated Featured Projects section.")

    # Update Activity
    activity = fetch_recent_activity()
    if activity:
        pattern = r"(<!-- START_SECTION:activity -->)(.*?)(<!-- END_SECTION:activity -->)"
        content = re.sub(pattern, rf"\g<1>\n{activity}\n\g<3>", content, flags=re.DOTALL)
        print("Updated Live Activity section.")

    with open(readme_path, "w", encoding="utf-8") as f:
        f.write(content)

if __name__ == "__main__":
    update_readme()

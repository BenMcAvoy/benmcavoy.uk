from flask import Flask, render_template, redirect, url_for, request
from datetime import datetime
from pathlib import Path
import requests
import time
from dataclasses import dataclass
from dotenv import load_dotenv
import os
import json
import ssl

load_dotenv()

CACHE_DURATION = 6 * 60 * 60  # 6 hours in seconds

NTFY_TOPIC = os.getenv("NTFY_TOPIC")

app = Flask("PortfolioSite")
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.jinja_env.auto_reload = True

benDOB = 2009 # rough DOB

timeSinceGHRequest = 0
cached_event = None

def getMostRecentlyContributed():
    global timeSinceGHRequest, cached_event
    now = time.time()
    if cached_event and (now - timeSinceGHRequest < CACHE_DURATION):
        return cached_event
    req = requests.get(
        "https://api.github.com/users/benmcavoy/events/public",
        verify=False
    )
    if req.status_code == 200:
        events = req.json()
        for event in events:
            if event["type"] == "PushEvent":
                timeSinceGHRequest = now
                repo = event.get("repo", {})
                full_name = repo.get("name", "")  # e.g. Owner/Repo
                name = full_name.split("/")[-1] if full_name else ""
                url = repo.get("url", "").replace("https://api.github.com/repos/", "https://github.com/")

                # try to find the most recent commit in this push
                payload = event.get("payload", {})
                commits = payload.get("commits", []) or []
                if commits:
                    # choose the last commit in the array (most recent in the push)
                    commit_item = commits[-1]
                    sha = commit_item.get("sha")
                    commit_msg = (commit_item.get("message") or "").split('\n', 1)[0]
                    commit_api_url = commit_item.get("url")  # API URL for the commit

                    # fetch commit details to get stats/files
                    additions = deletions = total_changes = files_changed = 0
                    commit_author = ""
                    commit_date = ""
                    commit_html_url = ""
                    if commit_api_url:
                        creq = requests.get(commit_api_url, verify=False)
                        if creq.status_code == 200:
                            cjson = creq.json()
                            stats = cjson.get("stats", {}) or {}
                            additions = stats.get("additions", 0)
                            deletions = stats.get("deletions", 0)
                            total_changes = stats.get("total", 0)
                            files_changed = len(cjson.get("files", []) or [])
                            commit_author = cjson.get("commit", {}).get("author", {}).get("name", "")
                            commit_date = cjson.get("commit", {}).get("author", {}).get("date", "")
                            commit_html_url = cjson.get("html_url") or commit_api_url.replace("https://api.github.com/repos/", "https://github.com/").replace("/commits/", "/commit/")

                    cached_event = ContributionRepo(
                        name=name,
                        url=url,
                        commit_message=commit_msg,
                        commit_sha=sha or "",
                        commit_url=commit_html_url,
                        additions=additions,
                        deletions=deletions,
                        total_changes=total_changes,
                        files_changed=files_changed,
                        author=commit_author,
                        date=commit_date,
                    )
                    return cached_event

                # fallback: no commits in payload
                cached_event = ContributionRepo(name=name, url=url)
                return cached_event
    return None


@dataclass
class ContributionRepo:
    name: str
    url: str
    commit_message: str = ""
    commit_sha: str = ""
    commit_url: str = ""
    additions: int = 0
    deletions: int = 0
    total_changes: int = 0
    files_changed: int = 0
    author: str = ""
    date: str = ""

@app.context_processor
def inject_globals():
    currentYear = datetime.now().year
    yearsOld = currentYear - benDOB
    return {
    'yearsOld': yearsOld,
    'most_recent_contribution': getMostRecentlyContributed()
    }

templates_dir = Path(app.root_path) / app.template_folder

def _make_view(template_name):
    def view():
        base = template_name.rsplit('/', 1)[-1]
        name = base.rsplit('.', 1)[0]
        title = name.replace('-', ' ').title()
        return render_template(template_name, title=title)
    return view

for tpl in sorted(templates_dir.rglob('*.html')):
    if 'fragments' in tpl.parts:
        continue
    rel = tpl.relative_to(templates_dir).as_posix()
    route = '/' if rel == 'index.html' else '/' + rel[:-5] # either / or stripped name
    endpoint = 'home' if rel == 'index.html' else Path(rel).stem.replace('-', '_')
    print(f"Registering route: {route} with endpoint: {endpoint} ({rel})")
    app.add_url_rule(route, endpoint, _make_view(rel))

@app.route('/contact', methods=['POST'])
def contactPOST():
    email = request.form.get('email')
    message = request.form.get('message')

    requests.post(f"https://ntfy.sh/{NTFY_TOPIC}",
                  data=f"New contact from {email}\n\n{message}".encode(encoding='utf-8'), verify=False)
    return redirect(url_for('home'))

if __name__ == "__main__":
    app.run(debug=True)
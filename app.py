"""
Portfolio website for Ben McAvoy.

This Flask application serves a personal portfolio with dynamic GitHub activity integration
and a contact form. It automatically registers routes for all HTML templates in the
templates directory.
"""

from flask import Flask, render_template, redirect, url_for, request
from datetime import datetime
from pathlib import Path
import requests
import time
from dataclasses import dataclass
from dotenv import load_dotenv
import os
import sys

load_dotenv()

# Cache GitHub API responses for 6 hours to respect rate limits
CACHE_DURATION = 6 * 60 * 60  # 6 hours in seconds

# Get notification topic from environment
NTFY_TOPIC = os.getenv("NTFY_TOPIC") or None

# Detect development mode based on whether running with 'uv'
ENV_DEVELOPMENT = 'uv' in sys.argv[0].lower()

print(f"Starting app in {'development' if ENV_DEVELOPMENT else 'production'} mode")

app = Flask("PortfolioSite")

if ENV_DEVELOPMENT:
    app.config['TEMPLATES_AUTO_RELOAD'] = bool(ENV_DEVELOPMENT)
    app.jinja_env.auto_reload = bool(ENV_DEVELOPMENT)

if not NTFY_TOPIC:
    raise RuntimeError("NTFY_TOPIC environment variable must be set")

ben_dob = 2009  # rough DOB

time_since_gh_request = 0
cached_event = None


def get_most_recently_contributed():
    """
    Fetch the most recent GitHub push event for the user.
    
    Uses a 6-hour cache to avoid hitting rate limits. Returns a ContributionRepo
    object with repository details and commit statistics, or None if no recent
    activity is found.
    
    Returns:
        ContributionRepo | None: Most recent push event details or None
    """
    global time_since_gh_request, cached_event

    now = time.time()
    if cached_event and (now - time_since_gh_request < CACHE_DURATION):
        return cached_event
    
    # If we get here, enough time has passed to refresh the cache

    # Check GitHub API for most recent public events
    req = requests.get("https://api.github.com/users/benmcavoy/events/public")
    if req.status_code == 200:
        events = req.json()
        for event in events:
            if event["type"] == "PushEvent":
                time_since_gh_request = now
                repo = event.get("repo", {})
                full_name = repo.get("name", "")  # e.g. Owner/Repo
                name = full_name.split("/")[-1] if full_name else ""
                url = repo.get("url", "").replace("https://api.github.com/repos/", "https://github.com/")

                # Try to find the most recent commit in this push
                payload = event.get("payload", {})
                commits = payload.get("commits", []) or []
                if commits:
                    # Choose the last commit in the array (most recent in the push)
                    commit_item = commits[-1]
                    sha = commit_item.get("sha")
                    commit_msg = (commit_item.get("message") or "").split('\n', 1)[0]
                    commit_api_url = commit_item.get("url")  # API URL for the commit

                    # Fetch commit details to get stats/files
                    additions = deletions = total_changes = files_changed = 0
                    commit_author = ""
                    commit_date = ""
                    commit_html_url = ""

                    if commit_api_url:
                        creq = requests.get(commit_api_url)
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
    """
    Represents a GitHub repository contribution with commit details.
    
    Stores information about the most recent push event including repository
    metadata and commit statistics for display on the portfolio.
    """
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
    """
    Inject global variables into all Jinja2 templates.
    
    Makes age calculation and GitHub contribution data available to all pages
    without passing them explicitly in each route.
    """
    current_year = datetime.now().year
    years_old = current_year - ben_dob
    return {
        'years_old': years_old,
        'most_recent_contribution': get_most_recently_contributed()
    }


def _make_view(template_name):
    """
    Factory function to create view functions for templates.
    
    Generates a view function that renders the specified template with an
    automatically derived page title.
    
    Args:
        template_name: Path to template relative to templates directory
        
    Returns:
        Callable view function for Flask routing
    """
    def view():
        base = template_name.rsplit('/', 1)[-1]
        name = base.rsplit('.', 1)[0]
        if name == 'index':
            title = "Ben McAvoy"
        else:
            title = name.replace('-', ' ').title()
        return render_template(template_name, title=title)
    return view


@app.route('/contact', methods=['POST'])
def contact_post():
    """
    Handle contact form submissions.
    
    Sends form data via ntfy.sh notification and redirects back to home.
    Fails gracefully if notification delivery fails.
    """
    email = request.form.get('email')
    message = request.form.get('message')

    if NTFY_TOPIC:
        try:
            requests.post(
                f"https://ntfy.sh/{NTFY_TOPIC}",
                data=f"New contact from {email}\n\n{message}".encode(encoding='utf-8'),
                timeout=5,
            )
        except Exception:
            print("Failed to send notification", file=sys.stderr)
            pass

    return redirect(url_for('home'))


if __name__ == "__main__":
    templates_dir = Path(app.root_path) / app.template_folder

    # Dynamically register routes for each HTML template
    for tpl in sorted(templates_dir.rglob('*.html')):
        if 'fragments' in tpl.parts:
            continue

        rel = tpl.relative_to(templates_dir).as_posix()
        route = '/' if rel == 'index.html' else '/' + rel[:-5]
        endpoint = 'home' if rel == 'index.html' else Path(rel).stem.replace('-', '_')
        app.add_url_rule(route, endpoint, _make_view(rel))

    app.run(debug=bool(ENV_DEVELOPMENT))
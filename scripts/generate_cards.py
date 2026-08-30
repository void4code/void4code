#!/usr/bin/env python3
"""Generates a single self-hosted dashboard SVG (terminal-window styled,
bio + live GitHub stats + dynamic badges) straight from the GitHub REST
API, so the README never depends on a third-party dashboard deployment.
"""
import json
import os
import urllib.request
from collections import Counter
from datetime import datetime, timezone

USERNAME = os.environ["GH_USERNAME"]
TOKEN = os.environ.get("GH_TOKEN")
API = "https://api.github.com"

RED = "#ff0033"
RED_DIM = "#7a0018"
DIM = "#4d0010"
BLACK = "#000000"
WHITE = "#f2f2f2"
FONT = "Consolas, Menlo, 'Courier New', monospace"

GLOW_DEFS = (
    '<defs><filter id="glow" x="-60%" y="-60%" width="220%" height="220%">'
    '<feGaussianBlur stdDeviation="2.5" result="b"/>'
    '<feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>'
    "</filter></defs>"
)


def api(path):
    req = urllib.request.Request(f"{API}{path}")
    req.add_header("User-Agent", "void4code-profile-cards")
    req.add_header("Accept", "application/vnd.github+json")
    if TOKEN:
        req.add_header("Authorization", f"Bearer {TOKEN}")
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode())


def api_list(path):
    out, page = [], 1
    while True:
        chunk = api(f"{path}{'&' if '?' in path else '?'}per_page=100&page={page}")
        if not chunk:
            break
        out.extend(chunk)
        if len(chunk) < 100:
            break
        page += 1
    return out


def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def build_dashboard(user, repos, langs, badges):
    age_days = (
        datetime.now(timezone.utc)
        - datetime.strptime(user["created_at"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    ).days
    stars = sum(r["stargazers_count"] for r in repos)
    top_lang = langs.most_common(1)[0][0] if langs else "n/a"

    bio = [
        ("whoami", "Void"),
        ("base", "London, UK"),
        ("role", "CS student -> cybersec eng."),
        ("focus", "python tooling / offsec"),
    ]
    stats = [
        ("repos", len(repos)),
        ("followers", user["followers"]),
        ("stars", stars),
        ("language", top_lang),
        ("uptime", f"{age_days}d"),
    ]

    w = 800
    chrome_h = 38
    top = chrome_h + 34
    row_h = 24
    col_bottom = top + max(len(bio), len(stats)) * row_h

    badge_rows = [[]]
    x = 40
    for b in badges:
        bw = 16 + len(b) * 8
        if x + bw > w - 40 and badge_rows[-1]:
            badge_rows.append([])
            x = 40
        badge_rows[-1].append((b, bw))
        x += bw + 12
    badges_h = (28 + len(badge_rows) * 36) if badges else 10
    h = col_bottom + 20 + badges_h

    p = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">', GLOW_DEFS]

    # outer frame + terminal chrome bar
    p.append(f'<rect x="1" y="1" width="{w-2}" height="{h-2}" rx="12" fill="{BLACK}" stroke="{RED}" stroke-width="2" filter="url(#glow)"/>')
    p.append(f'<path d="M1,{chrome_h} h{w-2}" stroke="{DIM}" stroke-width="1"/>')
    for i, c in enumerate((RED, RED_DIM, DIM)):
        p.append(f'<circle cx="{28 + i*22}" cy="{chrome_h/2}" r="6" fill="{c}"/>')
    p.append(
        f'<text x="{w/2}" y="{chrome_h/2 + 5}" text-anchor="middle" font-family="{FONT}" font-size="14" '
        f'fill="{RED_DIM}">root@{esc(USERNAME)}:~/status</text>'
    )

    # two columns
    y = top
    for label, value in bio:
        p.append(f'<text x="40" y="{y}" font-family="{FONT}" font-size="16" fill="{DIM}">&gt; {esc(label)}</text>')
        p.append(f'<text x="150" y="{y}" font-family="{FONT}" font-size="16" fill="{WHITE}">{esc(value)}</text>')
        y += row_h

    y = top
    divider_x = 430
    for label, value in stats:
        p.append(f'<text x="{divider_x+20}" y="{y}" font-family="{FONT}" font-size="16" fill="{DIM}">&gt; {esc(label)}</text>')
        p.append(f'<text x="{divider_x+150}" y="{y}" font-family="{FONT}" font-size="16" fill="{RED}" filter="url(#glow)">{esc(value)}</text>')
        y += row_h

    p.append(f'<line x1="{divider_x}" y1="{top-20}" x2="{divider_x}" y2="{col_bottom-14}" stroke="{DIM}" stroke-width="1"/>')

    if badges:
        ly = col_bottom + 6
        p.append(f'<line x1="24" y1="{ly}" x2="{w-24}" y2="{ly}" stroke="{DIM}" stroke-width="1"/>')
        y = ly + 32
        for row in badge_rows:
            x = 40
            for b, bw in row:
                p.append(f'<rect x="{x}" y="{y-20}" width="{bw}" height="26" rx="13" fill="{BLACK}" stroke="{RED}" stroke-width="1.5" filter="url(#glow)"/>')
                p.append(f'<text x="{x+bw/2}" y="{y-2}" text-anchor="middle" font-family="{FONT}" font-size="12" fill="{RED}">{esc(b)}</text>')
                x += bw + 12
            y += 34

    p.append("</svg>")
    return "\n".join(p)


def main():
    user = api(f"/users/{USERNAME}")
    repos = api_list(f"/users/{USERNAME}/repos?type=owner")

    langs = Counter()
    for r in repos:
        if r.get("fork"):
            continue
        try:
            for lang, bytes_ in api(f"/repos/{USERNAME}/{r['name']}/languages").items():
                langs[lang] += bytes_
        except Exception:
            pass

    age_days = (
        datetime.now(timezone.utc)
        - datetime.strptime(user["created_at"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    ).days
    stars = sum(r["stargazers_count"] for r in repos)

    badges = []
    badges.append("FRESH_INSTALL" if age_days < 14 else "NEW_SPAWN" if age_days < 90 else "ESTABLISHED")
    if len(repos) >= 1:
        badges.append("BUILDER")
    if len(repos) >= 10:
        badges.append("PROLIFIC")
    if stars >= 1:
        badges.append("STARGAZER")
    if user["followers"] >= 5:
        badges.append("NETWORKED")
    if langs.get("Python", 0) > 0:
        badges.append("PYTHONISTA")

    os.makedirs("assets", exist_ok=True)
    with open("assets/status.svg", "w", encoding="utf-8") as f:
        f.write(build_dashboard(user, repos, langs, badges))

    old = "assets/activity.svg"
    if os.path.exists(old):
        os.remove(old)


if __name__ == "__main__":
    main()

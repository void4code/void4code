#!/usr/bin/env python3
"""Self-hosted replacement for the (currently down) github-readme-stats /
github-profile-trophy / activity-graph vercel services. Pulls public data
straight from the GitHub REST API and renders red-team-themed SVG cards
that live in this repo, so the README never depends on a third-party
deployment.
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
DIM = "#4d0010"
BLACK = "#000000"
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
    return (
        str(s)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def build_status_card(user, repos, langs, badges):
    age_days = (
        datetime.now(timezone.utc)
        - datetime.strptime(user["created_at"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    ).days
    stars = sum(r["stargazers_count"] for r in repos)
    top_lang = langs.most_common(1)[0][0] if langs else "n/a"

    rows = [
        ("public_repos", len(repos)),
        ("followers", user["followers"]),
        ("following", user["following"]),
        ("stars_earned", stars),
        ("top_language", top_lang),
        ("account_age", f"{age_days}d"),
    ]

    w = 800

    # Pass 1: lay out badge rows (wrapping) to know the final canvas height
    # before drawing anything.
    badge_rows = [[]]
    x = 40
    for b in badges:
        bw = 18 + len(b) * 9
        if x + bw > w - 40 and badge_rows[-1]:
            badge_rows.append([])
            x = 40
        badge_rows[-1].append((b, bw))
        x += bw + 14

    body_bottom = 92 + len(rows) * 30 - 30 + 20
    badges_height = (44 + len(badge_rows) * 40) if badges else 0
    h = body_bottom + badges_height + 20

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">',
        GLOW_DEFS,
        f'<rect x="1" y="1" width="{w-2}" height="{h-2}" rx="10" fill="{BLACK}" stroke="{RED}" stroke-width="2" filter="url(#glow)"/>',
        f'<text x="28" y="42" font-family="{FONT}" font-size="20" fill="{RED}" filter="url(#glow)">'
        f'root@{esc(USERNAME)}:~$ ./status.sh</text>',
        f'<line x1="24" y1="56" x2="{w-24}" y2="56" stroke="{DIM}" stroke-width="1"/>',
    ]

    y = 92
    for label, value in rows:
        parts.append(
            f'<text x="40" y="{y}" font-family="{FONT}" font-size="17" fill="{DIM}">&gt; {esc(label)}</text>'
        )
        parts.append(
            f'<text x="260" y="{y}" font-family="{FONT}" font-size="17" fill="{RED}">{esc(value)}</text>'
        )
        y += 30

    if badges:
        y += 10
        parts.append(f'<line x1="24" y1="{y}" x2="{w-24}" y2="{y}" stroke="{DIM}" stroke-width="1"/>')
        y += 34
        for row in badge_rows:
            x = 40
            for b, bw in row:
                parts.append(
                    f'<rect x="{x}" y="{y-22}" width="{bw}" height="28" rx="14" fill="{BLACK}" stroke="{RED}" stroke-width="1.5" filter="url(#glow)"/>'
                )
                parts.append(
                    f'<text x="{x + bw/2}" y="{y-3}" text-anchor="middle" font-family="{FONT}" font-size="13" fill="{RED}">{esc(b)}</text>'
                )
                x += bw + 14
            y += 40

    parts.append("</svg>")
    return "\n".join(parts)


def build_activity_card(events):
    from datetime import date, timedelta

    days = 30
    today = date.today()
    counts = Counter()
    for e in events:
        try:
            d = datetime.strptime(e["created_at"], "%Y-%m-%dT%H:%M:%SZ").date()
        except (KeyError, ValueError):
            continue
        if (today - d).days < days:
            counts[d] += 1

    series = [counts.get(today - timedelta(days=i), 0) for i in range(days - 1, -1, -1)]
    maxv = max(series) if any(series) else 1

    w, h = 800, 220
    plot_w, plot_h = w - 80, 120
    bar_w = plot_w / days
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">',
        GLOW_DEFS,
        f'<rect x="1" y="1" width="{w-2}" height="{h-2}" rx="10" fill="{BLACK}" stroke="{RED}" stroke-width="2" filter="url(#glow)"/>',
        f'<text x="28" y="38" font-family="{FONT}" font-size="20" fill="{RED}" filter="url(#glow)">'
        f'&gt; public activity, last {days}d</text>',
        f'<line x1="24" y1="52" x2="{w-24}" y2="52" stroke="{DIM}" stroke-width="1"/>',
    ]

    base_y = 52 + plot_h + 10
    for i, v in enumerate(series):
        bh = 4 if v == 0 else 6 + (v / maxv) * (plot_h - 6)
        x = 40 + i * bar_w
        color = DIM if v == 0 else RED
        parts.append(
            f'<rect x="{x:.1f}" y="{base_y - bh:.1f}" width="{max(bar_w-3,1):.1f}" height="{bh:.1f}" fill="{color}"/>'
        )

    total = sum(series)
    parts.append(
        f'<text x="40" y="{base_y+28}" font-family="{FONT}" font-size="14" fill="{DIM}">'
        f'{today - timedelta(days=days-1)}</text>'
    )
    parts.append(
        f'<text x="{w-40}" y="{base_y+28}" text-anchor="end" font-family="{FONT}" font-size="14" fill="{DIM}">{today}</text>'
    )
    parts.append(
        f'<text x="{w/2}" y="{base_y+28}" text-anchor="middle" font-family="{FONT}" font-size="14" fill="{RED}">'
        f'{total} events</text>'
    )
    parts.append("</svg>")
    return "\n".join(parts)


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

    try:
        events = api_list(f"/users/{USERNAME}/events/public")
    except Exception:
        events = []

    os.makedirs("assets", exist_ok=True)
    with open("assets/status.svg", "w", encoding="utf-8") as f:
        f.write(build_status_card(user, repos, langs, badges))
    with open("assets/activity.svg", "w", encoding="utf-8") as f:
        f.write(build_activity_card(events))


if __name__ == "__main__":
    main()

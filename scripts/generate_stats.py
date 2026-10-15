"""Builds assets/{stats,languages,streak,activity}.svg from the GitHub GraphQL API. Stdlib only."""
import datetime as dt, json, os, urllib.request
from html import escape

USER = os.environ["GITHUB_REPOSITORY_OWNER"]
TOKEN = os.environ["GITHUB_TOKEN"]
BG, FG, ACCENT, MUTED = "#1a1b27", "#c0caf5", "#70a5fd", "#787c99"

Q = """query($u:String!){user(login:$u){
 contributionsCollection{totalCommitContributions contributionCalendar{totalContributions weeks{contributionDays{date contributionCount}}}}
 repositories(ownerAffiliations:OWNER,isFork:false,privacy:PUBLIC,first:100){totalCount nodes{stargazerCount
  languages(first:5,orderBy:{field:SIZE,direction:DESC}){edges{size node{name color}}}}}}}"""

req = urllib.request.Request(
    "https://api.github.com/graphql",
    json.dumps({"query": Q, "variables": {"u": USER}}).encode(),
    {"Authorization": f"bearer {TOKEN}"},
)
u = json.load(urllib.request.urlopen(req))["data"]["user"]
cal = u["contributionsCollection"]["contributionCalendar"]
weeks = [[d["contributionCount"] for d in w["contributionDays"]] for w in cal["weeks"]]
days = [(d["date"], d["contributionCount"]) for w in cal["weeks"] for d in w["contributionDays"]]
repos = u["repositories"]["nodes"]
stars = sum(r["stargazerCount"] for r in repos)


def svg(w, h, body, title):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
            f'role="img" aria-label="{escape(title)}"><rect width="{w}" height="{h}" rx="10" fill="{BG}"/>'
            f'<g font-family="Segoe UI,Ubuntu,sans-serif">{body}</g></svg>')


def text(x, y, s, size=14, fill=FG, weight=400, anchor="start"):
    return f'<text x="{x}" y="{y}" font-size="{size}" fill="{fill}" font-weight="{weight}" text-anchor="{anchor}">{escape(str(s))}</text>'


def write(name, s):
    os.makedirs("assets", exist_ok=True)
    open(f"assets/{name}.svg", "w", encoding="utf-8").write(s)


# stats
rows = [("Total contributions (past year)", cal["totalContributions"]),
        ("Commits (past year)", u["contributionsCollection"]["totalCommitContributions"]),
        ("Public repositories", u["repositories"]["totalCount"]),
        ("Stars earned", stars)]
b = text(25, 38, f"{USER}'s GitHub stats", 18, ACCENT, 700)
for i, (k, v) in enumerate(rows):
    b += text(25, 72 + i * 28, k, 14, MUTED) + text(375, 72 + i * 28, v, 15, FG, 700, "end")
write("stats", svg(400, 190, b, "GitHub stats"))

# languages
tot = {}
for r in repos:
    for e in r["languages"]["edges"]:
        n = e["node"]
        t = tot.setdefault(n["name"], [0, n["color"] or ACCENT])
        t[0] += e["size"]
top = sorted(tot.items(), key=lambda kv: -kv[1][0])[:5]
s = sum(v[0] for _, v in top) or 1
b = text(25, 38, "Top languages", 18, ACCENT, 700)
for i, (n, (sz, c)) in enumerate(top):
    y = 62 + i * 24
    b += (text(25, y + 11, n, 13, FG) + text(375, y + 11, f"{sz / s:.1%}", 13, MUTED, 400, "end")
          + f'<rect x="120" y="{y + 2}" width="190" height="9" rx="4.5" fill="#24283b"/>'
          + f'<rect x="120" y="{y + 2}" width="{190 * sz / s:.1f}" height="9" rx="4.5" fill="{c}"/>')
write("languages", svg(400, 190, b, "Top languages"))

# streak (within the past-year window the API returns)
today = dt.date.today().isoformat()
cur = best = run = 0
for d, c in days:
    run = run + 1 if c else 0
    best = max(best, run)
for d, c in reversed(days):
    if c:
        cur += 1
    elif d != today:
        break
b = ""
for i, (v, k) in enumerate([(cal["totalContributions"], "Contributions"), (cur, "Current streak"), (best, "Longest streak")]):
    x = 85 + i * 165
    b += text(x, 85, v, 32, ACCENT if i == 1 else FG, 700, "middle") + text(x, 115, k, 13, MUTED, 400, "middle")
b += text(250, 160, "past year", 11, MUTED, 400, "middle")
write("streak", svg(500, 190, b, "Contribution streak"))

# activity: weekly totals as an area chart
vals = [sum(w) for w in weeks]
W, H, L, T, BT = 780, 190, 40, 50, 160
mx = max(vals) or 1
pts = [(L + i * (W - L - 25) / (len(vals) - 1), BT - v / mx * (BT - T)) for i, v in enumerate(vals)]
line = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
b = (text(25, 32, "Contribution activity", 18, ACCENT, 700)
     + f'<polygon points="{L},{BT} {line} {pts[-1][0]:.1f},{BT}" fill="{ACCENT}" fill-opacity=".18"/>'
     + f'<polyline points="{line}" fill="none" stroke="{ACCENT}" stroke-width="2"/>'
     + text(L - 8, T + 4, mx, 11, MUTED, 400, "end") + text(L - 8, BT + 4, 0, 11, MUTED, 400, "end")
     + text(L, BT + 20, "weekly contributions, past year", 11, MUTED))
write("activity", svg(W, H, b, "Contribution activity"))

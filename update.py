import re, json, urllib.request, sys
from datetime import datetime
from pathlib import Path

BASE = "https://api.jolpi.ca/ergast/f1"

def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "RohanPitWall/1.0"})
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read())

def get_drivers():
    d = fetch(f"{BASE}/current/driverStandings.json")
    return d["MRData"]["StandingsTable"]["StandingsLists"][0]["DriverStandings"]

def get_constructors():
    d = fetch(f"{BASE}/current/constructorStandings.json")
    return d["MRData"]["StandingsTable"]["StandingsLists"][0]["ConstructorStandings"]

def get_last_race():
    d = fetch(f"{BASE}/current/last/results.json")
    races = d["MRData"]["RaceTable"]["Races"]
    return races[0] if races else None

TEAM_COLORS = {
    "mercedes": "var(--merc)", "ferrari": "var(--fe)",
    "mclaren": "var(--mcl)", "red_bull": "var(--rb)",
    "alpine": "var(--alp)", "haas": "var(--haas)",
    "williams": "var(--wil)", "rb": "var(--rbulls)",
    "aston_martin": "var(--am)", "sauber": "var(--audi)",
    "cadillac": "var(--cad)",
}
NAT = {
    "British":"GBR","Italian":"ITA","Dutch":"NED","Spanish":"ESP",
    "Australian":"AUS","French":"FRA","German":"DEU","Mexican":"MEX",
    "Canadian":"CAN","Monegasque":"MON","Finnish":"FIN","Danish":"DEN",
    "New Zealander":"NZL","Thai":"THA","Japanese":"JPN","Chinese":"CHN",
    "Argentine":"ARG","Brazilian":"BRA","American":"USA","Austrian":"AUT",
}

def team_color(name):
    key = name.lower().replace(" ", "_").replace("-", "_")
    return TEAM_COLORS.get(key, "var(--ink3)")

def nat_code(nat):
    return NAT.get(nat, nat[:3].upper())

def build_driver_rows(standings):
    rows = []
    leader = int(float(standings[0]["points"]))
    delays = [0, .08, .16, .24, .32, .40, .48, .56, .64, .72]
    for i, s in enumerate(standings[:10]):
        d = s["Driver"]
        c = s["Constructors"][0]
        pts = int(float(s["points"]))
        team = c["name"]
        col = team_color(team)
        code = d.get("code", d["familyName"][:3].upper())
        surname = d["familyName"]
        initial = d["givenName"][0]
        nat = nat_code(d.get("nationality",""))
        pos = str(i+1).zfill(2)
        gap = "" if i==0 else f' · <span class="gap">−{leader-pts}</span>'
        is_ham = "hamilton" in d["driverId"].lower()
        is_leader = i == 0
        row_cls = "driver-row"
        if is_leader: row_cls += " leader"
        if is_ham:    row_cls += " fav"
        dark = "color:#000;" if "mercedes" in team.lower() else ""
        delay = delays[i] if i < len(delays) else 0
        rows.append(
            f'      <div class="{row_cls}" style="--team-color:{col};animation-delay:{delay}s">'
            f'<div class="driver-pos">{pos}</div>'
            f'<div><div style="display:flex;align-items:center">'
            f'<span class="driver-name">{initial}. {surname}</span>'
            f'<span class="driver-code" style="background:{col};{dark}">{code}</span>'
            f'</div><div class="driver-team">{team} · {nat}{gap}</div></div>'
            f'<div><div class="driver-pts">{pts}</div>'
            f'<div class="driver-pts-sub">pts</div></div></div>'
        )
    return "\n".join(rows)

def build_con_rows(standings):
    rows = []
    leader = int(float(standings[0]["points"]))
    delays = [0,.08,.16,.24,.32,.40,.48,.56,.64,.72,.80]
    for i, s in enumerate(standings):
        c = s["Constructor"]
        name = c["name"]
        pts = int(float(s["points"]))
        col = team_color(name)
        pct = round(pts/leader*100) if leader else 0
        pos = str(i+1).zfill(2)
        is_fe = "ferrari" in name.lower()
        row_cls = "con-row fav-team" if is_fe else "con-row"
        star = "★" if is_fe else ""
        c_style = 'style="color:var(--fe-hot);"' if is_fe else ""
        delay = delays[i] if i < len(delays) else 0
        rows.append(
            f'      <div class="{row_cls}" style="--team-color:{col};animation-delay:{delay}s">'
            f'<div class="con-top"><div class="con-pos" {c_style}>{star}{pos}</div>'
            f'<div><div class="con-name" {c_style}>{name}</div>'
            f'<div class="con-engine">{c.get("nationality","")[:3].upper()} PU</div></div>'
            f'<div class="con-pts" {c_style}>{pts}</div></div>'
            f'<div class="con-bar"><div class="con-bar-fill" '
            f'style="width:{pct}%;animation-delay:{.5+i*.05:.2f}s"></div></div></div>'
        )
    return "\n".join(rows)

def build_podium(race):
    name = race["raceName"]
    circuit = race["Circuit"]["circuitName"]
    results = race["Results"][:3]
    medals = ["p1","p2","p3"]
    badges = ["P1","P2","P3"]
    rows = ""
    for j, r in enumerate(results):
        drv = r["Driver"]
        con = r["Constructor"]
        full = f"{drv['givenName']} {drv['familyName']}"
        team = con["name"]
        time = r.get("Time",{}).get("time", r.get("status","—"))
        rows += (
            f'          <div class="pod-row {medals[j]}">'
            f'<div class="pod-badge">{badges[j]}</div>'
            f'<div><div class="pod-driver-name">{full}</div>'
            f'<div class="pod-driver-team">{team}</div></div>'
            f'<div class="pod-time">{time}</div></div>\n'
        )
    return f'''      <div class="podium-block">
        <div class="podium-head">{name} · {circuit} · Result</div>
        <div class="podium-list">
{rows}        </div>
      </div>'''

def patch(html, drivers, constructors, race):
    # Driver rows
    html = re.sub(
        r'(<!-- DRIVERS -->.*?col-head.*?</div>\s*\n)(.*?)(</div>\s*\n\s*<!-- CONSTRUCTORS -->)',
        lambda m: m.group(1) + "\n" + build_driver_rows(drivers) + "\n    " + m.group(3),
        html, flags=re.DOTALL
    )

    # Constructor rows
    html = re.sub(
        r'(<!-- CONSTRUCTORS.*?col-head.*?</div>\s*\n)(.*?)(</div>\s*\n\s*<!-- PADDOCK)',
        lambda m: m.group(1) + "\n" + build_con_rows(constructors) + "\n    " + m.group(3),
        html, flags=re.DOTALL
    )

    # Podium
    html = re.sub(
        r'<div class="podium-block">.*?</div>\s*\n\s*</div>',
        build_podium(race),
        html, count=1, flags=re.DOTALL
    )

    # Stats ribbon - leader
    leader_d = drivers[0]["Driver"]["familyName"]
    leader_pts = int(float(drivers[0]["points"]))
    fe = next((c for c in constructors if "ferrari" in c["Constructor"]["name"].lower()), None)
    merc = next((c for c in constructors if "mercedes" in c["Constructor"]["name"].lower()), None)
    ham = next((d for d in drivers if "hamilton" in d["Driver"]["driverId"].lower()), None)
    lec = next((d for d in drivers if "leclerc" in d["Driver"]["driverId"].lower()), None)
    fe_gap = int(float(merc["points"])) - int(float(fe["points"])) if fe and merc else 0
    ham_pts = int(float(ham["points"])) if ham else 0
    ham_pos = ham["position"] if ham else "—"
    lec_pts = int(float(lec["points"])) if lec else 0
    lec_pos = lec["position"] if lec else "—"

    new_stats = f'''    <div class="stat"><div class="stat-label">Ferrari Gap to Lead</div><div class="stat-big"><em>−{fe_gap}</em> pts</div><div class="stat-sub">Ferrari vs Mercedes WCC</div></div>
    <div class="stat"><div class="stat-label">Hamilton P{ham_pos}</div><div class="stat-big">{ham_pts} <em>pts</em></div><div class="stat-sub">Season total — Forza HAM</div></div>
    <div class="stat"><div class="stat-label">Leclerc P{lec_pos}</div><div class="stat-big">{lec_pts} <em>pts</em></div><div class="stat-sub">Season total — Forza LEC</div></div>
    <div class="stat"><div class="stat-label">Championship Leader</div><div class="stat-big">{leader_pts} <em>pts</em></div><div class="stat-sub">{leader_d} — {drivers[0]["Constructors"][0]["name"]}</div></div>'''

    html = re.sub(
        r'(<div class="stats-grid">)(.*?)(</div>\s*\n</section>)',
        lambda m: m.group(1) + "\n" + new_stats + "\n  " + m.group(3),
        html, flags=re.DOTALL
    )

    # Round counter
    rounds_done = sum(1 for d in drivers if int(float(d.get("wins","0"))) >= 0)
    html = re.sub(r'After \d+ Rounds?', f'After {race["round"]} Rounds', html)
    return html

if __name__ == "__main__":
    print("Fetching F1 standings...")
    drivers = get_drivers()
    constructors = get_constructors()
    race = get_last_race()
    print(f"  Leader: {drivers[0]['Driver']['familyName']} — {drivers[0]['points']} pts")
    print(f"  Last race: {race['raceName'] if race else 'N/A'}")
    html_path = Path("index.html")
    html = html_path.read_text(encoding="utf-8")
    html = patch(html, drivers, constructors, race)
    html_path.write_text(html, encoding="utf-8")
    print("  index.html updated ✅")

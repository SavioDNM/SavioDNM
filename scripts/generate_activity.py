#!/usr/bin/env python3
"""Gera profile/activity.svg — heatmap animado de contribuições dos últimos 12 meses.

Usa a GitHub CLI (`gh api graphql`) com o token em GH_TOKEN, então funciona
tanto localmente quanto dentro de um GitHub Actions runner.

Uso:  python3 scripts/generate_activity.py [caminho-de-saida]
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

QUERY = """
query {
  user(login: "SavioDNM") {
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks {
          contributionDays { date contributionCount }
        }
      }
    }
  }
}
"""

# Paleta alinhada ao restante do perfil.
BG = "#0B0E14"
BORDER = "#222A38"
TITLE = "#F0A202"
TEXT = "#7C8494"
LEVELS = ["#1B2230", "#123B2C", "#1C6B49", "#2FA276", "#3DDC97"]

CELL = 11
STEP = 14
COLS = 53
ROWS = 7
GRID_X, GRID_Y = 29, 52
WIDTH, HEIGHT = 800, 190


def fetch_calendar() -> tuple[list[list[int]], int]:
    proc = subprocess.run(
        ["gh", "api", "graphql", "-f", f"query={QUERY}"],
        capture_output=True,
        text=True,
        check=True,
    )
    calendar = json.loads(proc.stdout)["data"]["user"]["contributionsCollection"][
        "contributionCalendar"
    ]
    weeks = [
        [day["contributionCount"] for day in week["contributionDays"]]
        for week in calendar["weeks"]
    ]
    return weeks, calendar["totalContributions"]


def level(count: int) -> int:
    if count <= 0:
        return 0
    if count == 1:
        return 1
    if count <= 3:
        return 2
    if count <= 6:
        return 3
    return 4


def longest_streak(weeks: list[list[int]]) -> int:
    flat = [count for week in weeks for count in week]
    best = current = 0
    for count in flat:
        current = current + 1 if count > 0 else 0
        best = max(best, current)
    return best


def render(weeks: list[list[int]], total: int) -> str:
    # Normaliza para exatamente COLS semanas (o GitHub pode devolver 52 ou 53).
    weeks = (weeks + [[0] * ROWS] * COLS)[:COLS]
    streak = longest_streak(weeks)

    cells: list[str] = []
    for col in range(COLS):
        week = (weeks[col] + [0] * ROWS)[:ROWS]
        for row, count in enumerate(week):
            lvl = level(count)
            x = GRID_X + col * STEP
            y = GRID_Y + row * STEP
            cls = "c hot" if lvl >= 3 else "c"
            delay = col * 16 + row * 8
            cells.append(
                f'    <rect class="{cls}" x="{x}" y="{y}" width="{CELL}" '
                f'height="{CELL}" rx="2.5" fill="{LEVELS[lvl]}" '
                f'style="animation-delay:{delay}ms"/>'
            )

    legend = []
    for i, color in enumerate(LEVELS):
        legend.append(
            f'  <rect x="{29 + i * 15}" y="164" width="11" height="11" '
            f'rx="2.5" fill="{color}"/>'
        )

    css = """  <style>
    .header { font: 700 16px 'Segoe UI', Ubuntu, Sans-Serif; fill: TITLE_COLOR; }
    .meta   { font: 600 11px 'JetBrains Mono', monospace; fill: TEXT_COLOR; }
    .c {
      animation: pop .55s ease-out both;
      transform-box: fill-box;
      transform-origin: center;
    }
    .hot { animation: pop .55s ease-out both, glow 2.8s ease-in-out .7s infinite; }
    .scan { animation: sweep 9s linear infinite; }
    @keyframes pop  { from { opacity: 0; transform: scale(.35); } to { opacity: 1; transform: scale(1); } }
    @keyframes glow { 0%, 100% { opacity: .6; } 50% { opacity: 1; } }
    @keyframes sweep { from { transform: translateX(-90px); } to { transform: translateX(SCAN_ENDpx); } }
    @media (prefers-reduced-motion: reduce) {
      .c, .hot { animation: none; opacity: 1; }
      .scan { display: none; }
    }
  </style>"""
    css = (css.replace("TITLE_COLOR", TITLE)
              .replace("TEXT_COLOR", TEXT)
              .replace("SCAN_END", str(WIDTH + 20)))

    return f'''<svg width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}"
     xmlns="http://www.w3.org/2000/svg" role="img"
     aria-labelledby="title desc">
  <title id="title">Contribuições de SavioDNM nos últimos 12 meses</title>
  <desc id="desc">{total} contribuições, maior sequência de {streak} dias.</desc>
  <defs>
    <clipPath id="gridClip">
      <rect x="{GRID_X - 2}" y="{GRID_Y - 2}" width="{COLS * STEP}" height="{ROWS * STEP + 4}" rx="6"/>
    </clipPath>
    <linearGradient id="scanGrad" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%"   stop-color="#F0A202" stop-opacity="0"/>
      <stop offset="50%"  stop-color="#F0A202" stop-opacity="0.30"/>
      <stop offset="100%" stop-color="#F0A202" stop-opacity="0"/>
    </linearGradient>
  </defs>
{css}

  <rect x="0.5" y="0.5" width="{WIDTH - 1}" height="{HEIGHT - 1}" rx="10"
        fill="{BG}" stroke="{BORDER}"/>
  <text x="25" y="32" class="header">Contribuições · últimos 12 meses</text>
  <text x="{WIDTH - 25}" y="31" text-anchor="end" class="meta">
    TOTAL {total} · MAIOR SEQUÊNCIA {streak} DIAS
  </text>

  <g clip-path="url(#gridClip)">
{chr(10).join(cells)}
    <g class="scan">
      <rect x="{GRID_X - 70}" y="{GRID_Y - 4}" width="70" height="{ROWS * STEP + 8}"
            fill="url(#scanGrad)"/>
      <rect x="{GRID_X - 1}" y="{GRID_Y - 4}" width="1.5" height="{ROWS * STEP + 8}"
            fill="#F0A202" fill-opacity="0.35"/>
    </g>
  </g>

{chr(10).join(legend)}
  <text x="112" y="174" class="meta">menos</text>
  <text x="160" y="174" class="meta">→ mais</text>
  <text x="{WIDTH - 25}" y="174" text-anchor="end" class="meta">gerado automaticamente</text>
</svg>
'''


def main() -> int:
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "profile/activity.svg")
    try:
        weeks, total = fetch_calendar()
        svg = render(weeks, total)
    except (subprocess.CalledProcessError, KeyError, json.JSONDecodeError) as exc:
        print(f"Falha ao gerar heatmap: {exc}", file=sys.stderr)
        return 1
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(svg, encoding="utf-8")
    print(f"{out}: {len(svg)} bytes, {total} contribuições, {len(weeks)} semanas")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

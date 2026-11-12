#!/usr/bin/env python3
"""Generate expanding-brain-de.svg / -en.svg (keeps both languages in step). Run: python3 brain.py"""
import math, sys
from pathlib import Path
OUT = str(Path(__file__).resolve().parent) + "/"
MONO = "Menlo, Consolas, 'DejaVu Sans Mono', monospace"
SANS = "Helvetica, Arial, sans-serif"
TXT = {
    "de": ("Expanding brain: vom SELECT * zum Plan-Check",
           "Fuenf Stufen, jede mit hellerem Bierkrug: SELECT *, SELECT col1, col2, liest den Ausfuehrungsplan, fragt die AI nach dem Plan, fragt die AI und liest den Plan - die letzte Stufe leuchtet gold.",
           ["liest den Ausführungsplan", "fragt die AI nach dem Plan", "fragt die AI und liest den Plan"]),
    "en": ("Expanding brain: from SELECT * to the plan check",
           "Five levels, each with a brighter beer mug: SELECT *, SELECT col1, col2, reads the execution plan, asks the AI for the plan, asks the AI and reads the plan - the last level glows gold.",
           ["reads the execution plan", "asks the AI for the plan", "asks the AI and reads the plan"]),
}
MUG = '''<g id="mug">
      <path d="M330 220 C 410 220, 410 360, 330 360" fill="none" stroke="#A8C8D8" stroke-width="26" stroke-linecap="round"/>
      <path d="M150 175 L150 395 A90 24 0 0 0 330 395 L330 175 Z" fill="url(#beer)"/>
      <path d="M150 175 L150 395 A90 24 0 0 0 330 395 L330 175" fill="none" stroke="#A8C8D8" stroke-width="12" stroke-linejoin="round"/>
      <text x="240" y="330" text-anchor="middle" font-family="{mono}" font-size="72" font-weight="bold" fill="#1E3446">&gt;_</text>
      <g fill="#F0F5F8">
        <ellipse cx="240" cy="175" rx="96" ry="26"/>
        <circle cx="168" cy="160" r="30"/><circle cx="210" cy="145" r="36"/><circle cx="258" cy="140" r="38"/>
        <circle cx="304" cy="156" r="32"/><circle cx="335" cy="174" r="18"/>
        <path d="M150 170 L150 222 A12 12 0 0 0 174 222 L174 180 Z"/>
      </g>
    </g>'''.replace("{mono}", MONO)

def build(lang):
    title, desc, prose = TXT[lang]
    rows = [("code", "SELECT *"), ("code", "SELECT col1, col2")] + [("prose", p) for p in prose]
    y0, h, stride = 16, 70, 74
    cx = 496
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 600 400" width="600" height="400" role="img" aria-labelledby="t d" lang="{lang}">',
         f'  <title id="t">{title}</title>', f'  <desc id="d">{desc}</desc>', '  <defs>',
         '    <linearGradient id="beer" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#FFC24A"/><stop offset="1" stop-color="#EF6C00"/></linearGradient>',
         '    <radialGradient id="gb"><stop offset="0" stop-color="#A8C8D8" stop-opacity="0.9"/><stop offset="1" stop-color="#A8C8D8" stop-opacity="0"/></radialGradient>',
         '    <radialGradient id="gw"><stop offset="0" stop-color="#FFFFFF" stop-opacity="1"/><stop offset="0.5" stop-color="#A8C8D8" stop-opacity="0.7"/><stop offset="1" stop-color="#A8C8D8" stop-opacity="0"/></radialGradient>',
         '    <radialGradient id="gg"><stop offset="0" stop-color="#FFFFFF" stop-opacity="1"/><stop offset="0.35" stop-color="#FFC24A" stop-opacity="0.95"/><stop offset="1" stop-color="#EF6C00" stop-opacity="0"/></radialGradient>',
         '    ' + MUG]
    for i in range(5):
        y = y0 + i * stride
        o.append(f'    <clipPath id="c{i}"><rect x="384" y="{y}" width="200" height="{h}" rx="12"/></clipPath>')
    o += ['  </defs>', '  <rect x="2" y="2" width="596" height="396" rx="24" fill="#1E3446" stroke="#A8C8D8" stroke-width="3"/>']
    for i, (kind, text) in enumerate(rows):
        y = y0 + i * stride
        cy = y + h / 2
        gold = i == 4
        pfill = "#FFC24A" if gold else "#F0F5F8"
        o.append(f'  <!-- level {i + 1} -->')
        o.append(f'  <rect x="16" y="{y}" width="356" height="{h}" rx="12" fill="{pfill}"/>')
        if kind == "code":
            o.append(f'  <text x="36" y="{cy + 8:.0f}" font-family="{MONO}" font-size="24" font-weight="bold" fill="#1E3446">{text}</text>')
        else:
            o.append(f'  <text x="36" y="{cy + 7:.0f}" font-family="{SANS}" font-size="21" font-weight="bold" fill="#1E3446">{text}</text>')
        cell = "#1E3446"
        o.append(f'  <g clip-path="url(#c{i})">')
        o.append(f'    <rect x="384" y="{y}" width="200" height="{h}" fill="{cell}"/>')
        if i == 1:
            o.append(f'    <circle cx="{cx}" cy="{cy}" r="34" fill="url(#gb)" opacity="0.5"/>')
        elif i == 2:
            o.append(f'    <circle cx="{cx}" cy="{cy}" r="52" fill="url(#gb)"/>')
        elif i == 3:
            o.append(f'    <ellipse cx="{cx}" cy="{cy}" rx="90" ry="60" fill="url(#gw)"/>')
        elif i == 4:
            o.append(f'    <rect x="384" y="{y}" width="200" height="{h}" fill="#B85200"/>')
            rays = []
            for k in range(16):
                a = 2 * math.pi * k / 16
                a2 = a + 2 * math.pi / 40
                r = 160
                rays.append(f'M{cx} {cy:.0f} L{cx + r * math.cos(a):.0f} {cy + r * math.sin(a):.0f} L{cx + r * math.cos(a2):.0f} {cy + r * math.sin(a2):.0f} Z')
            o.append(f'    <path d="{" ".join(rays)}" fill="#FFC24A" opacity="0.55"/>')
            o.append(f'    <circle cx="{cx}" cy="{cy}" r="60" fill="url(#gg)"/>')
        o.append('  </g>')
        o.append(f'  <rect x="384" y="{y}" width="200" height="{h}" rx="12" fill="none" stroke="{"#FFC24A" if gold else "#A8C8D8"}" stroke-width="3"/>')
        s = 0.19
        tx, ty = cx - 262 * s, cy - 268 * s
        o.append(f'  <use href="#mug" transform="translate({tx:.1f} {ty:.1f}) scale({s})"/>')
        if gold:
            for (sx, sy, r) in [(418, cy - 18, 7), (566, cy + 14, 6), (548, cy - 22, 4.5), (430, cy + 20, 4.5)]:
                o.append(f'  <path d="M{sx} {sy - r * 2:.1f} Q{sx} {sy:.1f} {sx + r * 2:.1f} {sy:.1f} Q{sx} {sy:.1f} {sx} {sy + r * 2:.1f} Q{sx} {sy:.1f} {sx - r * 2:.1f} {sy:.1f} Q{sx} {sy:.1f} {sx} {sy - r * 2:.1f} Z" fill="#FFFFFF"/>')
    o.append('</svg>')
    open(OUT + f"expanding-brain-{lang}.svg", "w").write("\n".join(o) + "\n")

for l in ("de", "en"):
    build(l)

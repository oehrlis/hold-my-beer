#!/usr/bin/env python3
"""Generate the pool-driven slide atoms of the hold-my-beer frame deck.

Reads the topic pool (single source for rounds, options, reserve and scorecard)
and writes talk-CLI atoms (``<dir>/slide.html`` + ``<dir>/meta.yaml``) into the
output directory. Hand-written atoms live in ``slides/src/``; everything that
carries a pool fact or the voting URL is generated here, so the pool stays the
only place where topic titles are maintained.

QR handover: every QR is ``<img src="{VOTING_URL}/qr.svg">`` from the live app.
If the image fails to load (app not running yet, no network), the
``onerror`` handler swaps in a static QR generated at build time for the same URL.

Run (from the repo root or anywhere):
    uv run --with pyyaml --with qrcode python slides/generate.py \
        --pool pool/doag-ak-2026.yaml --out slides/build/atoms
"""

from __future__ import annotations

import argparse
import base64
import datetime as dt
import html
import io
import os
import re
import shutil
import sys
from pathlib import Path

import yaml

try:  # optional: static fallback QR
    import qrcode
    import qrcode.image.svg

    HAVE_QR = True
except ImportError:  # pragma: no cover - reported at runtime
    HAVE_QR = False

REPO = Path(__file__).resolve().parents[1]
DEFAULT_URL = "https://hmb.oradba.ch"
PLACEHOLDER_URL = "https://voting.example.org"  # used when VOTING_URL is set but empty
IMAGE_TYPES = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".svg": "image/svg+xml"}
OWNERS = ("Stefan", "Martin", "Gemeinsam", "Offen")
NO_OWNER = "Offen"
OWNER_CLASS = {"Martin": " ring", "Gemeinsam": " ok2"}
RESERVE_CLASS = {"Martin": " acc", "Gemeinsam": " ok"}
LOGO_PX = 170
OWNER_EN = {"Gemeinsam": "Joint", "Offen": "Open"}  # Stefan/Martin stay as they are
TODO = '<span class="tag" style="background:var(--warn)">TODO</span>'
CURSOR = '<span class="cur" aria-hidden="true"></span>'
PS = '<span class="ps">$</span>'
# Leitmotiv: cover subtitle, rules slide, takeaways
MOTTO = ("AI ist kein Autopilot. Nutzt sie - gezielt, mit Kontext, und prüft, was rauskommt.",
         "AI is no autopilot. Use it - deliberately, with context, and check what comes out.")
# home-turf label per option owner on the round slides (the friendly duel)
HOME = {
    "Stefan": ("Heimspiel Stefan", "Stefan's home turf"),
    "Martin": ("Heimspiel Martin", "Martin's home turf"),
    "Gemeinsam": ("Kein Heimvorteil", "Nobody's home turf"),
}
# one punchline per scorecard category (keyed by the German pool name; unknown names get none)
SCORE_QUIP = {
    "AI richtig": ("Kommt vor. Wir zählen ehrlich mit.", "It happens. We count honestly."),
    "AI halluziniert": ("Klingt überzeugend, existiert nicht.", "Sounds convincing, does not exist."),
    "Falsches Problem gelöst": ("Schnell, elegant, am Ziel vorbei.", "Fast, elegant, wrong target."),
    "DBA-Instinkt gewinnt": ("a.k.a. Grauhaar-Bonus", "a.k.a. the grey-hair bonus"),
}
# divider tagline per round number (optional; a missing one is reported as INFO)
ROUND_TAG = {
    1: ("Die AI wärmt sich auf. Wir uns auch.", "The AI warms up. So do we."),
    2: ("Das, wofür man uns eigentlich bezahlt.", "The stuff we actually get paid for."),
    3: ("Hier wird es spannend. Vor allem für die AI.", "Where it gets interesting. Mostly for the AI."),
}
# simple line icons for the four scorecard categories (in pool order), drawn for this deck
ICONS = [
    ("ok", '<rect x="10" y="10" width="44" height="44"/><path d="M20 33l8 8 16-19"/>'),
    ("warn", ('<path d="M18 46h28a9 9 0 0 0 1-18 13 13 0 0 0-25-4 10 10 0 0 0-4 22z"/>'
             '<path d="M28 31a4 4 0 1 1 5 4v3"/><path d="M33 42v1"/><path d="M14 54l3-3M24 56l2-3"/>')),
    ("warn", ('<circle cx="26" cy="38" r="17"/><circle cx="26" cy="38" r="8"/><circle cx="26" cy="38" r="1.5"/>'
             '<path d="M58 8L49 17"/><path d="M49 17l1-7M49 17l7-1"/>')),
    ("", ('<path d="M22 56v-7c-6-4-9-10-8-17 1-10 9-17 19-17 10 0 17 7 17 16l5 9h-5v6c0 3-2 5-5 5h-5v5"/>'
         '<path d="M22 12c2-5 6-6 9-3M31 9c3-4 8-4 10 0M41 10c3-2 7 0 8 4"/>')),
]
# illustrations from slides/img/ (own SVGs, see README): (stem de, stem en, aria-label de, aria-label en)
ROUND_ILL = {
    2: ("distracted-dba", "distracted-dba",
        "Der DBA schaut der AI nach, die Oracle-Doku an seiner Hand ist fassungslos.",
        "The DBA turns to look at the AI, the Oracle docs holding his hand are stunned."),
    3: ("expanding-brain-de", "expanding-brain-en",
        "Expanding Brain: von SELECT * bis zu: fragt die AI und liest den Plan.",
        "Expanding brain: from SELECT * to: asks the AI and reads the plan."),
}
VOTING_ILL = ("phone-voting-de", "phone-voting-en",
              "Handy mit dem Abstimmungsscreen der App, der Countdown läuft als Bier.",
              "Phone with the voting screen of the app, the countdown runs as beer.")
IMG_DIR = Path(__file__).resolve().parent / "img"
WARNINGS: list[str] = []

e = html.escape


def data_uri(mime: str, payload: bytes) -> str:
    return f"data:{mime};base64,{base64.b64encode(payload).decode('ascii')}"


def fallback_qr(url: str) -> str:
    """Static QR (data URI) for ``url``, or '' when the qrcode module is missing."""
    if not HAVE_QR:
        return ""
    img = qrcode.make(url, image_factory=qrcode.image.svg.SvgPathImage, box_size=10, border=2)
    buf = io.BytesIO()
    img.save(buf)
    return data_uri("image/svg+xml", buf.getvalue())


def image_css(src_dir: Path) -> str:
    """CSS class ``img-<stem>`` per image in ``src/<atom>/`` with the image as data URI.

    Slides show photos and badges as ``<div class="img-<stem>">`` backgrounds, not ``<img>``:
    the standalone deck stays one file, and the talk CLI plan/PPTX path does not try to
    resolve a data URI as a file path.
    """
    rules = []
    for img in sorted(p for p in src_dir.glob("*/*") if p.suffix.lower() in IMAGE_TYPES):
        uri = data_uri(IMAGE_TYPES[img.suffix.lower()], img.read_bytes())
        rules.append(f".reveal section.hmb .img-{img.stem} {{ background-image: url({uri}); }}")
    return "\n".join(rules)


def ill_css(img_dir: Path) -> str:
    """CSS class ``img-<stem>`` per SVG in ``slides/img/``: data URI, aspect ratio from the viewBox and
    rounded corners from the panel rect (``rx`` of the first full-size rect), so a shadow follows the panel."""
    rules = []
    for svg in sorted(img_dir.glob("*.svg")):
        text = svg.read_text(encoding="utf-8")
        vb = re.search(r'viewBox="\s*[-\d.]+\s+[-\d.]+\s+([\d.]+)\s+([\d.]+)"', text)
        if not vb:
            WARNINGS.append(f"WARN: {svg.name}: no viewBox - skipped, slides show no image")
            continue
        w, h = float(vb.group(1)), float(vb.group(2))
        rx_m = re.search(r'<rect x="[\d.]+" y="[\d.]+" width="' + f"{w - 4:g}" + r'"[^>]*\brx="([\d.]+)"', text)
        radius = (f"; border-radius: {float(rx_m.group(1)) / w * 100:.2f}% / {float(rx_m.group(1)) / h * 100:.2f}%"
                  if rx_m else "")
        uri = data_uri(IMAGE_TYPES[".svg"], svg.read_bytes())
        rules.append(f".reveal .img-{svg.stem} {{ background-image: url({uri}); aspect-ratio: {w:g} / {h:g}{radius}; }}")
    return "\n".join(rules)


def ill(spec: tuple[str, str, str, str], cls: str = "") -> str:
    """Illustration as two ``div.ill`` (de/en, deck.css shows the active one); '' if a file is missing."""
    stem_de, stem_en, label_de, label_en = spec
    missing = [s for s in (stem_de, stem_en) if not (IMG_DIR / f"{s}.svg").is_file()]
    if missing:
        print(f"INFO: illustration {', '.join(missing)}.svg not in {IMG_DIR} - slide without image", file=sys.stderr)
        return ""
    extra = f" {cls}" if cls else ""
    return (f'<div class="ill img-{stem_de}{extra}" lang="de" role="img" aria-label="{e(label_de)}"></div>'
            f'<div class="ill img-{stem_en}{extra}" lang="en" role="img" aria-label="{e(label_en)}"></div>')


def logo_mark_css(logo: Path) -> str:
    """Logo as data URI (``--hmb-logo``) for the footer mark and closing slide of the Hold my Beer skin.

    A data-URI background, not a second inline copy of the SVG: the cover already inlines the logo,
    and a second copy would duplicate its gradient ids.
    """
    return f":root {{ --hmb-logo: url({data_uri(IMAGE_TYPES['.svg'], logo.read_bytes())}); }}"


def bi(de: str, en: str, raw: bool = False) -> str:
    """Bilingual text: both spans, deck.css shows the active language. ``raw``: no escaping."""
    if not raw:
        de, en = e(de), e(en)
    return f'<span lang="de">{de}</span><span lang="en">{en}</span>'


def en_text(obj: dict, key: str, where: str) -> str:
    """English field ``<key>_en`` of a pool entry; missing: German text plus a WARN line."""
    val = obj.get(f"{key}_en")
    if isinstance(val, str) and val.strip():
        return " ".join(val.split())
    msg = f"WARN: {where}: {key}_en missing - English slide shows the German text"
    if msg not in WARNINGS:  # one line per missing field, even if several slides use it
        WARNINGS.append(msg)
    return str(obj.get(key, ""))


def owner_bi(owner: str) -> str:
    return bi(owner, OWNER_EN.get(owner, owner))


def grid_class(n: int, default: int) -> str:
    """Theme grid class ``g2``..``g4`` for ``n`` columns, ``default`` outside that range."""
    return f"g{n if n in (2, 3, 4) else default}"


def icon(i: int) -> str:
    tone, paths = ICONS[i % len(ICONS)]
    return (
        f'<span class="ico {tone}" aria-hidden="true"><svg viewBox="0 0 64 64" fill="none" stroke="currentColor" '
        f'stroke-width="3" stroke-linecap="square" stroke-linejoin="miter">{paths}</svg></span>'
    )


def score_tiles(cats: list[tuple[str, str]], final: bool) -> str:
    """Scoreboard tiles: icon, category, punchline (intro) or an open score (final)."""
    tiles = []
    for i, (de, en) in enumerate(cats):
        if final:
            extra = '<span class="q">?</span>'
        else:
            q = SCORE_QUIP.get(de)
            extra = f'<span class="s">{bi(*q)}</span>' if q else ""
        tiles.append(
            f'    <div class="tile{" ring" if i % 2 else ""}">{icon(i)}'
            f'<span class="l">{bi(de, en)}</span>{extra}</div>'
        )
    return "\n".join(tiles)


def qr_block(voting_url: str, fallback: str, size: int = 260) -> str:
    """Live QR from the app with a static fallback, plus the URL as text."""
    onerror = f" onerror=\"this.onerror=null;this.src='{fallback}'\"" if fallback else ""
    style = (
        f"width:{size}px;height:{size}px;background:#fff;margin:0 auto;"
        "border:0;box-shadow:none;display:block"
    )
    return (
        '<div style="display:flex;flex-direction:column;align-items:center;'
        'justify-content:center;gap:0.4rem">\n'
        f'      <img class="qr" src="{e(voting_url)}/qr.svg" alt="QR-Code zur Abstimmung"'
        f' style="{style}"{onerror}>\n'
        f'      <p class="qr-url"><strong>{e(voting_url)}</strong></p>\n'
        "    </div>"
    )


def meta_yaml(title: str, description: str, tags: list[str], layout: str = "html-section") -> str:
    data = {
        "title": title,
        "description": description,
        "layout": layout,
        "tags": tags,
        "topic": "hold-my-beer",
        "version": "",
        "level": "intermediate",
        "lang": "de+en",
        "mandatory": False,
        "updated": dt.date.today().isoformat(),
        "author": "Stefan Oehrli",
        "assets": [],
        "audience": ["dba"],
        "classification": "public",
    }
    head = "# generated by slides/generate.py from the topic pool - do not edit\n"
    return head + yaml.safe_dump(data, allow_unicode=True, sort_keys=False)


def write_atom(out: Path, name: str, html_text: str, meta: str) -> None:
    d = out / name
    d.mkdir(parents=True, exist_ok=True)
    (d / "slide.html").write_text(html_text, encoding="utf-8")
    (d / "meta.yaml").write_text(meta, encoding="utf-8")


def cover(ev: dict, logo: str, css: str, js: str) -> str:
    # inline SVG, not a data-URI <img>: the talk CLI plan/PPTX path reads <img src> as a file path
    logo_html = f'<div style="width:{LOGO_PX}px;height:{LOGO_PX}px;margin:0 0 18px">{logo}</div>' if logo else ""
    title = bi(ev["title"], en_text(ev, "title", "event"))
    return f"""<!-- atom: hold-my-beer/cover (generated) -->
<section class="acn-cover" data-layout="cover">
  <style>{css}</style>
  <script>{js}</script>
  <div class="cover">
    <div class="cover-text">
      <div>
        <div class="crumb">{e(ev["name"])} · {e(ev["city"])}</div>
        <h1>{title}</h1>
        <p class="sub motto">{bi(*MOTTO)}</p>
        <p class="prompt">{PS}hmb --live --topic {bi("ihr-entscheidet", "you-decide")}{CURSOR}</p>
      </div>
      <div class="meta"><strong>Stefan Oehrli · Martin Berger</strong> · {e(ev["short"])} ·
      {e(str(ev["date"]))}, {e(ev["time"])} · {bi("Raum", "Room")} {e(ev["room"])}</div>
    </div>
    <div class="cover-visual">
      <svg class="geometry" viewBox="0 0 600 800" xmlns="http://www.w3.org/2000/svg" preserveAspectRatio="none">
        <polygon points="0,800 600,800 600,400 300,800" fill="#A100FF" opacity="0.5"/>
        <polygon points="0,800 300,800 0,500" fill="#7500C0" opacity="0.7"/>
        <line x1="0" y1="600" x2="600" y2="200" stroke="#E6DCFF" stroke-width="2" opacity="0.5"/>
      </svg>
      <div class="stamp">
        {logo_html}
        <div class="lab">HOLD MY BEER</div>
        <h3>{bi("Ihr wählt das Thema. Wir und die AI liefern - live.",
                "You pick the topic. We and the AI deliver - live.")}</h3>
        <p class="quip">{bi("Zusammen über 50 Jahre Oracle. Zu alt für Hype, neugierig genug für AI.",
                            "50+ years of Oracle between us. Too old for hype, curious enough for AI.")}</p>
      </div>
    </div>
  </div>
  <aside class="notes">Begrüssung, beide kurz auf die Bühne. Titel ist Programm: wir wissen
  wirklich nicht, welche Themen kommen. Leitmotiv einmal laut sagen: AI ist kein Autopilot.
  Sprache umschalten: Taste L, Theme Accenture / Hold my Beer: Taste T.</aside>
</section>
"""


def voting(fmt: dict, n_rounds: int, url: str, fb: str) -> str:
    secs = fmt["voting_seconds"]
    mins = fmt["challenge_minutes"]
    phone = ill(VOTING_ILL)
    return f"""<!-- atom: hold-my-beer/voting (generated) -->
<section class="hmb">
  <div class="sh"><span class="kicker">{bi("Voting-App", "Voting app")}</span><h2>{bi("Handys raus: ihr entscheidet", "Phones out: you decide")}</h2></div>
  <div class="vote-grid{" with-phone" if phone else ""}">
    <div style="display:flex;flex-direction:column;gap:0.6rem">
      <div class="steps" style="margin-top:0">
        <div class="step"><span class="snum">1</span><h4>{bi("QR scannen", "Scan the QR code")}</h4>
          <p>{bi("Kein Login, keine Namen, keine E-Mail", "No login, no names, no e-mail")}</p></div>
        <div class="sarr">&rsaquo;</div>
        <div class="step"><span class="snum">2</span><h4>{bi("Option wählen", "Pick an option")}</h4>
          <p>{bi(f"3 Optionen, {secs} s Zeit", f"3 options, {secs} s")}</p></div>
        <div class="sarr">&rsaquo;</div>
        <div class="step"><span class="snum">3</span><h4>{bi("Wir legen los", "We get going")}</h4>
          <p>{bi(f"Ergebnis live, dann {mins} min live", f"Live result, then {mins} min live")}</p></div>
      </div>
      <ul>
        <li>{bi("Eine Stimme pro Gerät und Runde", "One vote per device and round")}</li>
        <li>{bi("Gleichstand: Stichwahl. Würfeln überlassen wir der AI.", "Tie: run-off vote. We leave the dice to the AI.")}</li>
        <li>{bi(f"{n_rounds} Runden, nach jeder Runde die Scorecard",
                f"{n_rounds} rounds, the scorecard after each one")}</li>
        <li>{bi("Mobilfunk nutzen - das Konferenz-WLAN hat schon genug gelitten",
                "Use mobile data - the conference Wi-Fi has suffered enough")}</li>
      </ul>
    </div>
    {f'<div class="vote-phone">{phone}</div>' if phone else ""}
    {qr_block(url, fb)}
  </div>
  <aside class="notes">QR zeigen, kurz warten bis die ersten Handys oben sind.
  Admin: Session vorbereitet, Runde 1 noch im Zustand waiting.</aside>
</section>
"""


def scorecard(cats: list[tuple[str, str]]) -> str:
    tiles = score_tiles(cats, final=False)
    return f"""<!-- atom: hold-my-beer/scorecard (generated) -->
<section class="hmb">
  <div class="sh"><span class="kicker">Scorecard</span><h2>{bi("Nach jeder Runde: ein Strich", "After each round: one tally mark")}</h2></div>
  <div class="{grid_class(len(cats), 4)} score">
{tiles}
  </div>
  <div class="qbox"><p>{bi("Fehler werden nicht kaschiert, sie werden gezählt. Am Ende zeigt die Scorecard, wer öfter recht hatte - AI oder DBA.",
                           "Mistakes are not hidden, they are counted. At the end the scorecard shows who was right more often - AI or DBA.")}</p></div>
  <p class="quip">{bi("Nebenwertung: Security-Nerd gegen Automation-Nerd. Wird nicht gezählt, aber erwähnt.",
                      "Side bet: security nerd vs. automation nerd. Not counted, but definitely mentioned.")}</p>
  <aside class="notes">Scorecard ist der rote Faden. Grauhaar-Bonus erklären: wenn Erfahrung schneller
  ist als jedes Modell. Nebenwertung nur als Pointe, nicht auswerten.</aside>
</section>
"""


def round_divider(rnd: dict, total: int, secs: int) -> str:
    num = rnd["number"]
    name_en = en_text(rnd, "name", f"round {num}")
    tag = ROUND_TAG.get(num)
    if not tag:
        print(f"INFO: no divider tagline for round {num} ({rnd['name']}) - add one to ROUND_TAG", file=sys.stderr)
    tag_html = f'\n      <p class="tagline">{bi(*tag)}</p>' if tag else ""
    pic = ill(ROUND_ILL[num], "rill") if num in ROUND_ILL else ""  # no mapping or file: no image, no placeholder
    foam = (
        '<svg class="foam" viewBox="0 0 230 70" aria-hidden="true"><g fill="#F0F5F8">'
        '<ellipse cx="115" cy="58" rx="112" ry="14"/><circle cx="40" cy="42" r="26"/><circle cx="88" cy="30" r="30"/>'
        '<circle cx="140" cy="28" r="32"/><circle cx="188" cy="42" r="26"/></g></svg>'
    )
    bubbles = (
        '<svg class="bubbles" viewBox="0 0 120 160" aria-hidden="true" fill="none" stroke="#A8C8D8" stroke-width="3">'
        '<circle cx="30" cy="140" r="9"/><circle cx="78" cy="104" r="6"/><circle cx="44" cy="64" r="11"/>'
        '<circle cx="96" cy="26" r="7"/></svg>'
    )
    return f"""<!-- atom: hold-my-beer/runde-{num}-start (generated) -->
<section class="acn-divider hmb-round{" has-ill" if pic else ""}" data-layout="section-divider">
  <div class="rwrap">
    <div class="rnum" aria-hidden="true">{foam}{num}</div>
    <div>
      <p class="rkick">{bi(f"Runde {num} von {total}", f"Round {num} of {total}")}</p>
      <h2>{bi(rnd["name"], name_en)}</h2>{tag_html}
      <p class="prompt">{PS}hmb vote --round {num} --timeout {secs}s{CURSOR}</p>
      <p class="cue"><span class="live">LIVE</span>{bi("Abstimmung läuft gleich - Handys bereit.", "Voting opens in a moment - phones ready.")}</p>{pic}
    </div>
    {"" if pic else bubbles}
  </div>
  <aside class="notes">Runde {num} ankündigen, Rundenname und Pointe. Admin: Runde {num} bereit (waiting).
  Weiter zur Optionen-Folie mit QR.</aside>
</section>
"""


def round_slide(rnd: dict, total: int, secs: int, url: str, fb: str) -> str:
    num = rnd["number"]
    name_en = en_text(rnd, "name", f"round {num}")
    cards = []
    for opt in rnd["options"]:
        where = f"round {num} option {opt['key']}"
        owner = str(opt.get("owner", NO_OWNER))
        cls = OWNER_CLASS.get(owner, "")
        cat = bi(opt.get("category", ""), en_text(opt, "category", where)) if opt.get("category") else ""
        home = HOME.get(owner)
        home_html = bi(*home) if home else owner_bi(owner)
        cards.append(
            f'      <div class="tile opt{cls}" style="display:flex;flex-direction:column;gap:0.5rem;'
            'padding:0.9rem 0.8rem">\n'
            f'        <span class="n">{e(opt["key"])}</span>\n'
            f'        <h4>{bi(opt["title"], en_text(opt, "title", where))}</h4>\n'
            f'        <span class="l">{cat}</span>\n'
            f'        <span class="home">{home_html}</span>\n'
            "      </div>"
        )
    cards_html = "\n".join(cards)
    keys = ",".join(str(o["key"]) for o in rnd["options"])
    return f"""<!-- atom: hold-my-beer/runde-{num} (generated) -->
<section class="hmb">
  <div class="sh"><span class="kicker cmd">{PS}hmb vote --round {num}/{total} --options {e(keys)} --timeout {secs}s</span>
  <h2>{bi(f"Runde {num} - {rnd['name']}", f"Round {num} - {name_en}")}</h2></div>
  <div style="display:grid;grid-template-columns:3fr 1fr;gap:1.2rem;flex:1 1 auto;align-items:center">
    <div class="g3">
{cards_html}
    </div>
    {qr_block(url, fb)}
  </div>
  <aside class="notes">-> Fenster /screen. Admin: Runde {num} öffnen ({secs} s), Ergebnis freigeben,
  Gewinner starten. Gleichstand: Stichwahl. Gewinner nicht machbar: zweitplatzierte Option,
  Abstimmung nicht wiederholen.</aside>
</section>
"""


def reserve_topics(reserve: list[dict]) -> str:
    groups: dict[str, list[tuple[int, dict]]] = {}
    for i, t in enumerate(reserve, 1):
        groups.setdefault(str(t.get("owner", NO_OWNER)), []).append((i, t))
    cols = []
    for owner in OWNERS:
        items = groups.get(owner)
        if not items:
            continue
        lis = []
        for i, t in items:
            where = f"reserve[{i}]"
            cat = t.get("category", "")
            cat_html = f" · {bi(cat, en_text(t, 'category', where))}" if cat else ""
            lis.append(f"          <li>{bi(t['title'], en_text(t, 'title', where))}{cat_html}</li>")
        lis_html = "\n".join(lis)
        cls = RESERVE_CLASS.get(owner, "")
        cols.append(
            f'      <div class="card{cls}"><h4>{owner_bi(owner)}</h4>\n        <ul>\n{lis_html}\n        </ul></div>'
        )
    cols_html = "\n".join(cols)
    n = len(reserve)
    return f"""<!-- atom: hold-my-beer/reserve-themen (generated) -->
<section class="hmb" data-visibility="uncounted">
  <div class="sh"><span class="kicker">{bi("Reserve", "Backup")}</span><h2>{bi(f"Reserve-Themen ({n})", f"Backup topics ({n})")}</h2></div>
  <div class="{grid_class(len(cols), 3)}">
{cols_html}
  </div>
  <aside class="notes">Nur zeigen, wenn eine Option ersetzt werden muss oder Zeit übrig ist.
  Admin kann jedes Reserve-Thema einem noch nicht gespielten Slot zuweisen (Zustand waiting).</aside>
</section>
"""


def scorecard_result(cats: list[tuple[str, str]], rounds: list[dict]) -> str:
    tiles = score_tiles(cats, final=True)
    lis = "\n".join(
        f"      <li>{bi(f'Runde {r[0]} - {r[1]}: gespielt wurde ____', f'Round {r[0]} - {r[2]}: played ____')}</li>"
        for r in ((r["number"], r["name"], en_text(r, "name", f"round {r['number']}")) for r in rounds)
    )
    return f"""<!-- atom: hold-my-beer/scorecard-endstand (generated) -->
<section class="hmb">
  <div class="sh"><span class="kicker">{bi("Fazit", "Wrap-up")}</span><h2>{bi("Endstand: AI gegen DBA", "Final score: AI vs. DBA")}</h2></div>
  <div class="{grid_class(len(cats), 4)} score">
{tiles}
  </div>
  <ul>
{lis}
  </ul>
  <p class="note">{TODO} {bi("Platzhalter: Endstand live eintragen (Scorecard aus /admin bzw. Strichliste).",
                             "Placeholder: enter the final score live (scorecard from /admin or tally).")}</p>
  <aside class="notes">Welche Kategorie hat gewonnen, welches Tool war wo stark.</aside>
</section>
"""


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--pool", type=Path, default=REPO / "pool" / "doag-ak-2026.yaml")
    ap.add_argument("--out", type=Path, default=REPO / "slides" / "build" / "atoms")
    ap.add_argument("--voting-url", default=os.environ.get("VOTING_URL", DEFAULT_URL))
    ap.add_argument("--logo", type=Path, default=REPO / "assets" / "logo" / "hold-my-beer.svg")
    args = ap.parse_args()

    url = args.voting_url.rstrip("/")
    if not url:
        print(f"WARN: VOTING_URL is empty - placeholder {PLACEHOLDER_URL} on all QR slides", file=sys.stderr)
        url = PLACEHOLDER_URL
    pool = yaml.safe_load(args.pool.read_text(encoding="utf-8"))
    ev, fmt, rounds = pool["event"], pool["format"], pool["rounds"]
    reserve = pool.get("reserve") or []
    cats_de = list(fmt["scorecard"])
    cats_en = fmt.get("scorecard_en")
    if not (isinstance(cats_en, list) and len(cats_en) == len(cats_de)):
        WARNINGS.append("WARN: format: scorecard_en missing or not the same length as scorecard"
                        " - English slides show the German categories")
        cats_en = cats_de
    cats = list(zip(cats_de, cats_en))

    fb = fallback_qr(url + "/")
    if not fb:
        print("WARN: python module qrcode missing - no static fallback QR (live /qr.svg only)", file=sys.stderr)
    logo = ""
    if args.logo.is_file():
        svg = args.logo.read_text(encoding="utf-8")
        svg = svg[svg.index("<svg"):]  # drop an XML declaration, if any
        logo = svg.replace('width="512" height="512"', f'width="{LOGO_PX}" height="{LOGO_PX}"', 1)
    if not logo:
        print(f"WARN: logo not found: {args.logo} - cover without logo", file=sys.stderr)

    if args.out.exists():
        shutil.rmtree(args.out)
    args.out.mkdir(parents=True)
    tags = ["hold-my-beer", "generated"]
    here = Path(__file__).resolve().parent
    css = (here / "deck.css").read_text(encoding="utf-8") + "\n" + image_css(here / "src") + "\n" + ill_css(IMG_DIR)
    if args.logo.is_file():  # footer logo mark of the hmb skin (deck-theme.js, deck.css)
        css += "\n" + logo_mark_css(args.logo)
    js = "\n".join((here / name).read_text(encoding="utf-8") for name in ("deck-lang.js", "deck-theme.js"))
    write_atom(args.out, "cover", cover(ev, logo, css, js), meta_yaml("Cover", "Titel, Speaker, Event", tags, "cover"))
    write_atom(
        args.out, "voting", voting(fmt, len(rounds), url, fb),
        meta_yaml("So stimmt ihr ab", "Voting-App mit Live-QR", tags + ["voting"]),
    )
    write_atom(
        args.out, "scorecard", scorecard(cats),
        meta_yaml("Scorecard", "Scorecard-Kategorien aus dem Pool", tags + ["scorecard"]),
    )
    for rnd in rounds:
        write_atom(
            args.out, f"runde-{rnd['number']}-start",
            round_divider(rnd, len(rounds), fmt["voting_seconds"]),
            meta_yaml(f"Runde {rnd['number']} - Start", "Trenner vor der Runde", tags + ["round", "divider"],
                      "section-divider"),
        )
        write_atom(
            args.out, f"runde-{rnd['number']}",
            round_slide(rnd, len(rounds), fmt["voting_seconds"], url, fb),
            meta_yaml(f"Runde {rnd['number']} - {rnd['name']}", "Drei Optionen mit Live-QR", tags + ["round"]),
        )
    write_atom(
        args.out, "scorecard-endstand", scorecard_result(cats, rounds),
        meta_yaml("Scorecard - Endstand", "Platzhalter fuer den Endstand", tags + ["scorecard"]),
    )
    write_atom(
        args.out, "reserve-themen", reserve_topics(reserve),
        meta_yaml("Reserve-Themen", "Reserve-Pool aus dem Pool-YAML", tags + ["reserve"]),
    )
    n_opts = sum(len(r["options"]) for r in rounds)
    for w in WARNINGS:
        print(w, file=sys.stderr)
    print(
        f"generated {len(list(args.out.iterdir()))} atoms in {args.out} "
        f"({len(rounds)} rounds, {n_opts} options, {len(reserve)} reserve, voting url {url}, "
        f"fallback QR {'yes' if fb else 'no'}, {len(WARNINGS)} missing English text(s))"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

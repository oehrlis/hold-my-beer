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
LOGO_PX = 150
OWNER_EN = {"Gemeinsam": "Joint", "Offen": "Open"}  # Stefan/Martin stay as they are
TODO = '<span class="tag" style="background:var(--warn)">TODO</span>'
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


def score_tiles(cats: list[tuple[str, str]], numbered: bool) -> str:
    return "\n".join(
        f'    <div class="tile{" ring" if i % 2 else ""}"><span class="n">{i + 1 if numbered else "?"}</span>'
        f'<span class="l">{bi(de, en)}</span></div>'
        for i, (de, en) in enumerate(cats)
    )


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
        f'      <img src="{e(voting_url)}/qr.svg" alt="QR-Code zur Abstimmung"'
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
        <p class="sub">{bi("Live-Session ohne festgelegte Inhalte: Ihr wählt das Thema, wir und die AI liefern.",
                           "A live session without fixed content: you pick the topic, we and the AI deliver.")}</p>
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
        <h3>{bi("Oracle live, mit AI", "Oracle live, with AI")}</h3>
      </div>
    </div>
  </div>
  <aside class="notes">Begrüssung, beide kurz auf die Bühne. Titel ist Programm: wir wissen
  wirklich nicht, welche Themen kommen. Sprache umschalten: Taste L.</aside>
</section>
"""


def voting(fmt: dict, n_rounds: int, url: str, fb: str) -> str:
    secs = fmt["voting_seconds"]
    mins = fmt["challenge_minutes"]
    return f"""<!-- atom: hold-my-beer/voting (generated) -->
<section class="hmb">
  <div class="sh"><span class="kicker">{bi("Voting-App", "Voting app")}</span><h2>{bi("So stimmt ihr ab", "How to vote")}</h2></div>
  <div style="display:grid;grid-template-columns:3fr 1fr;gap:1.2rem;flex:1 1 auto">
    <div style="display:flex;flex-direction:column;gap:0.6rem">
      <div class="steps" style="margin-top:0">
        <div class="step"><span class="snum">1</span><h4>{bi("QR scannen", "Scan the QR code")}</h4>
          <p>{bi("Kein Login, keine Namen, keine E-Mail-Adressen", "No login, no names, no e-mail addresses")}</p></div>
        <div class="sarr">&rsaquo;</div>
        <div class="step"><span class="snum">2</span><h4>{bi("Option wählen", "Pick an option")}</h4>
          <p>{bi(f"3 Optionen pro Runde, {secs} s Zeit", f"3 options per round, {secs} s")}</p></div>
        <div class="sarr">&rsaquo;</div>
        <div class="step"><span class="snum">3</span><h4>{bi("Ergebnis", "Result")}</h4>
          <p>{bi("live auf dem Beamer", "live on the projector")}</p></div>
      </div>
      <ul>
        <li>{bi("Eine Stimme pro Gerät und Runde", "One vote per device and round")}</li>
        <li>{bi("Gleichstand: Stichwahl - nie Zufall", "Tie: run-off vote - never random")}</li>
        <li>{bi(f"{n_rounds} Runden, danach je {mins} min live, dann Scorecard",
                f"{n_rounds} rounds: {mins} min live each, then the scorecard")}</li>
        <li>{bi("Mobilfunk nutzen, nicht das Konferenz-WLAN", "Use mobile data, not the conference Wi-Fi")}</li>
      </ul>
    </div>
    {qr_block(url, fb)}
  </div>
  <aside class="notes">QR zeigen, kurz warten bis die ersten Handys oben sind.
  Admin: Session vorbereitet, Runde 1 noch im Zustand waiting.</aside>
</section>
"""


def scorecard(cats: list[tuple[str, str]]) -> str:
    tiles = score_tiles(cats, numbered=True)
    return f"""<!-- atom: hold-my-beer/scorecard (generated) -->
<section class="hmb">
  <div class="sh"><span class="kicker">Scorecard</span><h2>{bi("Was wir nach jeder Runde zählen", "What we count after each round")}</h2></div>
  <div class="{grid_class(len(cats), 4)}">
{tiles}
  </div>
  <div class="qbox"><p>{bi("Nach jeder Runde: kurz auswerten, ein Strich in der passenden Kategorie. "
                           "Am Ende zeigt die Scorecard, wer öfter recht hatte - AI oder DBA.",
                           "After each round: a quick review, one tally mark in the matching category. "
                           "At the end the scorecard shows who was right more often - AI or DBA.")}</p></div>
  <aside class="notes">Scorecard ist der rote Faden. Fehler werden nicht kaschiert, sie werden gezählt.</aside>
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
        cards.append(
            f'      <div class="tile opt{cls}" style="display:flex;flex-direction:column;gap:0.5rem;'
            'padding:0.9rem 0.8rem">\n'
            f'        <span class="n">{e(opt["key"])}</span>\n'
            f'        <h4>{bi(opt["title"], en_text(opt, "title", where))}</h4>\n'
            f'        <span class="l">{owner_bi(owner)} · {cat}</span>\n'
            "      </div>"
        )
    cards_html = "\n".join(cards)
    return f"""<!-- atom: hold-my-beer/runde-{num} (generated) -->
<section class="hmb">
  <div class="sh"><span class="kicker">{bi(f"Runde {num} von {total} · Abstimmung {secs} s", f"Round {num} of {total} · voting {secs} s")}</span>
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
    tiles = score_tiles(cats, numbered=False)
    lis = "\n".join(
        f"      <li>{bi(f'Runde {r[0]} - {r[1]}: gespielt wurde ____', f'Round {r[0]} - {r[2]}: played ____')}</li>"
        for r in ((r["number"], r["name"], en_text(r, "name", f"round {r['number']}")) for r in rounds)
    )
    return f"""<!-- atom: hold-my-beer/scorecard-endstand (generated) -->
<section class="hmb">
  <div class="sh"><span class="kicker">{bi("Fazit", "Wrap-up")}</span><h2>{bi("Scorecard - Endstand", "Scorecard - final score")}</h2></div>
  <div class="{grid_class(len(cats), 4)}">
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
    css = (here / "deck.css").read_text(encoding="utf-8") + "\n" + image_css(here / "src")
    js = (here / "deck-lang.js").read_text(encoding="utf-8")
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

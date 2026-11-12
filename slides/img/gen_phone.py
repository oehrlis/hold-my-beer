"""Generate phone-voting-{de,en}.svg (hand-written SVG template, two languages)."""
import sys
from pathlib import Path

OUT = Path(__file__).resolve().parent

L = {
    "de": dict(
        lang="de",
        title="Abstimmung am Handy",
        desc=("Handy mit dem Abstimmungsscreen der App: Runde 2 - DBA-Alltag, drei Themen A, B, C, "
              "Thema A ist gewaehlt, der 60-Sekunden-Countdown laeuft als Bier, das mit Schaumkrone "
              "das Glasrohr fuellt, noch 42 Sekunden."),
        eyebrow="RUNDE 2", head="DBA-Alltag", head_size=21, left="noch 42 s",
        opts=[("Unified Audit Policy", "inkl. NOAUDIT"),
              ("AWR/ASH:", "Slow Query analysieren"),
              ("Listener und", "sqlnet.ora Hardening")],
        random="Zufallsthema für mich", vote="Stimme abgeben"),
    "en": dict(
        lang="en",
        title="Voting on the phone",
        desc=("Phone showing the voting screen of the app: Round 2 - Everyday DBA work, three topics A, B, C, "
              "topic A is selected, the 60 second countdown runs as beer filling a glass tube with a "
              "foam head, 42 seconds left."),
        eyebrow="ROUND 2", head="Everyday DBA work", head_size=17.5, left="42 s left",
        opts=[("Unified Audit policy", "incl. NOAUDIT"),
              ("AWR/ASH: analyze", "a slow query"),
              ("Listener and", "sqlnet.ora hardening")],
        random="Random topic for me", vote="Cast my vote"),
}

SANS = "Helvetica, Arial, sans-serif"
MONO = "Menlo, Consolas, monospace"


def option(i, key, l1, l2, selected):
    y = 222 + i * 70
    if selected:
        card = (f'<rect x="70" y="{y}" width="180" height="60" rx="12" fill="#FFFFFF" fill-opacity="0.10" '
                f'stroke="#EF6C00" stroke-width="3.5"/>')
        disc = f'<circle cx="88" cy="{y + 30}" r="13" fill="#FFC24A"/>'
        ktxt = "#1E3446"
        tick = (f'<circle cx="243" cy="{y + 7}" r="11" fill="#EF6C00" stroke="#1E3446" stroke-width="3"/>'
                f'<path d="M238 {y + 7}l4 4 6-8" fill="none" stroke="#FFFFFF" stroke-width="3" '
                f'stroke-linecap="round" stroke-linejoin="round"/>')
    else:
        card = (f'<rect x="70" y="{y}" width="180" height="60" rx="12" fill="#FFFFFF" fill-opacity="0.06" '
                f'stroke="#A8C8D8" stroke-opacity="0.55" stroke-width="2.5"/>')
        disc = f'<circle cx="88" cy="{y + 30}" r="13" fill="#A8C8D8"/>'
        ktxt = "#1E3446"
        tick = ""
    return (f'  <g>\n    {card}\n    {disc}\n'
            f'    <text x="88" y="{y + 36}" text-anchor="middle" font-size="15" font-weight="bold" '
            f'fill="{ktxt}">{key}</text>\n'
            f'    <text x="108" y="{y + 26}" font-size="12.5" font-weight="bold" fill="#FFFFFF">{l1}</text>\n'
            f'    <text x="108" y="{y + 43}" font-size="12.5" fill="#F0F5F8">{l2}</text>\n'
            f'    {tick}\n  </g>\n')


def build(t):
    opts = "".join(option(i, "ABC"[i], a, b, i == 0) for i, (a, b) in enumerate(t["opts"]))
    # beer tube: x 72..248, y 168..190, 42 of 60 s -> 70 % full
    fill_end = 72 + round(176 * 0.70)
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 320 560" width="320" height="560" role="img" aria-labelledby="t d" xml:lang="{t["lang"]}">
  <title id="t">{t["title"]}</title>
  <desc id="d">{t["desc"]}</desc>
  <defs>
    <linearGradient id="beer" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#FFC24A"/>
      <stop offset="1" stop-color="#EF6C00"/>
    </linearGradient>
    <clipPath id="tube"><rect x="72" y="166" width="176" height="24" rx="12"/></clipPath>
  </defs>

  <!-- own panel: works on white and on navy slides -->
  <rect x="2" y="2" width="316" height="556" rx="24" fill="#1E3446" stroke="#A8C8D8" stroke-width="2"/>

  <!-- phone body (generic, no brand) -->
  <rect x="45" y="24" width="230" height="512" rx="34" fill="#F0F5F8" stroke="#A8C8D8" stroke-width="4"/>
  <rect x="41" y="120" width="5" height="38" rx="2" fill="#A8C8D8"/>
  <rect x="41" y="168" width="5" height="38" rx="2" fill="#A8C8D8"/>
  <rect x="274" y="140" width="5" height="56" rx="2" fill="#A8C8D8"/>
  <rect x="56" y="36" width="208" height="488" rx="24" fill="#1E3446"/>
  <rect x="132" y="44" width="56" height="14" rx="7" fill="#F0F5F8"/>

  <g font-family="{SANS}">
  <!-- brand bar: mini mug with >_ and a QR scan hint -->
  <g stroke-linejoin="round" stroke-linecap="round">
    <path d="M73 74h20v20a2 2 0 0 1-2 2h-16a2 2 0 0 1-2-2z" fill="url(#beer)" stroke="#A8C8D8" stroke-width="2"/>
    <path d="M93 78c7 0 7 12 0 12" fill="none" stroke="#A8C8D8" stroke-width="3"/>
    <path d="M71 74c0-5 4-7 7-5 2-4 8-4 10 0 3-2 7 0 7 5z" fill="#F0F5F8"/>
    <text x="83" y="92" text-anchor="middle" font-family="{MONO}" font-size="8" font-weight="bold" fill="#1E3446" stroke="none">&gt;_</text>
  </g>
  <text x="104" y="89" font-size="11" font-weight="bold" letter-spacing="1.5" fill="#A8C8D8">VOTE</text>
  <g fill="none" stroke="#A8C8D8" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
    <path d="M226 72h-5v5M240 72h5v5M226 96h-5v-5M240 96h5v-5"/>
    <path d="M227 84h12" stroke="#EF6C00"/>
  </g>
  <path d="M60 106h200" stroke="#A8C8D8" stroke-opacity="0.35" stroke-width="2"/>

  <!-- round header -->
  <text x="72" y="130" font-size="12" font-weight="bold" letter-spacing="2" fill="#A8C8D8">{t["eyebrow"]}</text>
  <text x="72" y="154" font-size="{t["head_size"]}" font-weight="bold" fill="#FFFFFF">{t["head"]}</text>

  <!-- 60 s countdown: beer filling a glass tube, foam head at the front -->
  <g clip-path="url(#tube)">
    <rect x="72" y="166" width="{fill_end - 72}" height="24" fill="url(#beer)"/>
    <path d="M72 175h{fill_end - 72}" stroke="#B85200" stroke-width="2" stroke-opacity="0.5"/>
    <g fill="#F0F5F8">
      <rect x="{fill_end - 12}" y="166" width="12" height="24"/>
      <circle cx="{fill_end - 2}" cy="168" r="7"/>
      <circle cx="{fill_end + 5}" cy="175" r="6"/>
      <circle cx="{fill_end + 3}" cy="184" r="6.5"/>
      <circle cx="{fill_end - 4}" cy="190" r="5"/>
      <circle cx="{fill_end - 14}" cy="166" r="4"/>
    </g>
    <g fill="#F0F5F8" opacity="0.8">
      <circle cx="{fill_end + 13}" cy="172" r="2.2"/><circle cx="{fill_end + 15}" cy="183" r="1.6"/>
    </g>
    <g fill="#FFFFFF" opacity="0.7">
      <circle cx="90" cy="183" r="2"/><circle cx="118" cy="173" r="1.6"/><circle cx="146" cy="184" r="2"/><circle cx="170" cy="174" r="1.5"/>
    </g>
  </g>
  <rect x="72" y="166" width="176" height="24" rx="12" fill="none" stroke="#A8C8D8" stroke-width="3"/>
  <text x="72" y="210" font-size="14" font-weight="bold" fill="#FFC24A">{t["left"]}</text>

  <!-- three options, A selected -->
{opts}
  <!-- actions -->
  <rect x="70" y="434" width="180" height="30" rx="10" fill="none" stroke="#A8C8D8" stroke-width="2"/>
  <text x="160" y="454" text-anchor="middle" font-size="12" font-weight="bold" fill="#F0F5F8">{t["random"]}</text>
  <rect x="70" y="472" width="180" height="36" rx="10" fill="#EF6C00"/>
  <text x="160" y="496" text-anchor="middle" font-size="15" font-weight="bold" fill="#FFFFFF">{t["vote"]}</text>
  </g>
  <rect x="130" y="514" width="60" height="4" rx="2" fill="#A8C8D8" fill-opacity="0.6"/>
</svg>
'''


for lang in sys.argv[1:] or ("de", "en"):
    (OUT / f"phone-voting-{lang}.svg").write_text(build(L[lang]), encoding="utf-8")

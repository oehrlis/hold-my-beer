# slides

Frame slides for the live talk (owner: Stefan Oehrli): cover, rules, prerequisites, speakers, voting app,
scorecard, one slide per round, conclusion, thank-you, reserve. No demo content - the rounds happen live.

## Layout

| Path | Content |
|------|---------|
| `src/<atom>/` | hand-written slide atoms (`slide.html` + `meta.yaml`, talk CLI format) |
| `generate.py` | writes the pool-driven atoms from `pool/<event>.yaml` (cover, voting, scorecard, rounds, reserve) |
| `deck.css` | talk-local size and layout overrides for `section.hmb`, inlined into the generated cover |
| `deck-lang.js` | DE/EN switch, inlined into the generated cover |
| `deck-theme.js` | theme switch Accenture / Hold my Beer, inlined into the generated cover |
| `build/atoms/` | generated atoms - git-ignored, rebuilt by every build |
| `build.sh` | generate, then assemble the deck with the `talk` CLI |
| `IMAGE-IDEAS.md` | illustration and meme ideas per slide (own variants in the logo style, nothing embedded) |
| `<event>/` | built deck per event, e.g. `doag-ak-2026/wissen-nicht-was-sie-tun.html` |

Topic titles exist only in the pool YAML. Never copy them into `src/` - change the pool and rebuild.

## Build

Prerequisites: `uv`, the `talk` CLI from ai-toolkit (`make install-cli`), and a checkout of the talks repo next to
this one (`~/Repos/own/oehrlis/talks` and `~/Repos/own/oehrlis/hold-my-beer`).

```bash
slides/build.sh # standalone HTML into slides/doag-ak-2026/
slides/build.sh --pdf # PDF instead of HTML
slides/build.sh --dry-run # slide plan only, no deck written
TALKS_DIR=~/Repos/own/oehrlis/talks-dinu slides/build.sh # use another talks checkout or worktree
```

`VOTING_URL` defaults to `https://hmb.oradba.ch`; set it to override. Set but empty (`VOTING_URL= slides/build.sh`),
the build uses the placeholder `https://voting.example.org` and says so.

## How it fits together

- The deck recipe stays in the talks repo: `talks/wissen-nicht-was-sie-tun/talk.yaml`. It lists every atom as
  `source: master/../../hold-my-beer/slides/...`. The talk CLI resolves `master/<path>` below
  `<TALKS_DIR>/master-slides/`, so the relative path lands in this repo next to the talks repo.
- `build.sh` checks that this path reaches the same checkout it runs from and stops otherwise.
- All slides are local to this repo; `speaker-stefan` replaces the master atom `mandatory/intro`.
- Photos and badges sit next to their slide in `src/<atom>/`. `generate.py` turns each into a CSS class
  `img-<file stem>` (data URI in the cover's style block), so the standalone deck stays one file.
- Reserve slides sit after the thank-you slide with `data-visibility="uncounted"`: reachable with the arrow keys,
  not counted in the slide number. The talk CLI's own `reserve: true` drops slides from HTML, so it is not used.

## Design

Accenture theme as the base (fonts, brandbar, grid, purple); the Hold my Beer look is a switchable skin on top
(see Theme). The beer colours from the logo are accents for live and
AI-warning moments only, defined as `--hmb-*` tokens in `deck.css`:

- orange and gold: round numbers (divider), `LIVE` cue, prompt sign `$`, blinking cursor
- dark orange: AI-failure labels (`.card.bad`, punchlines `.quip`, scorecard icons for AI mistakes)
- navy: terminal boxes (`.term-hmb`), the logo's ground; glass blue: divider bubbles
- terminal motif: `.prompt` lines and the round kicker as an `hmb vote ...` command, mono font as in the logo

Each round gets two generated atoms: `runde-N-start` (full-bleed divider) and `runde-N` (options + QR). Both must be
listed in the talk recipe. Fragments: rules and takeaways appear one by one; `?fragments=false` shows everything
(screenshots, review).

## Language (Sprache)

One deck, German and English. German is the default.

- Switch: key `L`, or click `DE | EN` in the top right corner
- URL parameter: `wissen-nicht-was-sie-tun.html?lang=en` (or `?lang=de`) - wins over everything else
- The last choice is kept in the browser (localStorage); the URL parameter overrides it
- Speaker notes stay German
- `L` replaces reveal's vim-style "next slide" key; arrow keys and space work as before

How it works: every visible text exists twice, `<span lang="de">...</span><span lang="en">...</span>`.
`deck-lang.js` sets `data-deck-lang` and `lang` on `<html>`, `deck.css` hides the inactive language. Both files
are inlined into the generated cover slide, which is always the first slide, so the deck stays one file.

New text:

- In `src/<atom>/slide.html`: write both spans next to each other, German first. Names, URLs and Oracle terms that
  read the same in both languages need no spans
- In `generate.py`: use `bi("Deutsch", "English")`
- Pool texts: add the `*_en` field next to the German one (`title_en`, `name_en`, `category_en`, `scorecard_en`,
  `event.title_en`). A missing field shows German on the English slide and the build prints a WARN line

Check both languages after a change: open the deck with `?lang=en` and look at every slide.

## Theme

One deck, two looks: Accenture (`acn`, default) and Hold my Beer (`hmb`, dark navy shell with the logo and the beer
colours). Switching is live - slide, fragments and language stay where they are.

- Switch: key `T`, or click `ACN | HMB` next to `DE | EN` in the top right corner
- URL parameter: `wissen-nicht-was-sie-tun.html?theme=hmb` (or `?theme=acn`), combinable with `lang`
  (`?lang=en&theme=hmb`) - wins over everything else
- The last choice is kept in the browser (localStorage); the URL parameter overrides it
- PDF (`--pdf`) and `?print-pdf` use the theme from the URL or the browser, Accenture without either

How it works: `deck-theme.js` sets `data-deck-theme` on `<html>`. The Accenture theme is the build base and stays
untouched; the skin in `deck.css` is scoped to `html[data-deck-theme="hmb"]`. It remaps the theme tokens that keep
their meaning on a dark canvas (`--dark-gray` text, `--label-gray` secondary text, `--neutral-light` surfaces,
`--divider` lines, `--purple-primary` accent = orange, `--purple-deep` highlight = gold, `--sans` system font, `--ok`)
and restyles what is not token-driven: canvas and full-bleed layouts (cover, round dividers, closing), tags, quote
box, terminal boxes, quips, scoreboard, QR (white panel), ACE badges (light plate), footer (logo mark +
"Hold my beer"), slide number, controls and progress. The logo comes from `generate.py` as `--hmb-logo`.

New components:

- Colour them with the theme tokens above - they then follow both themes without extra rules
- A hard-coded colour, a light background or `--purple-plum` / `--lavender` / `--white` (they mean background in one
  place and text in another) needs its own `html[data-deck-theme="hmb"] ...` rule in the theme block of `deck.css`
- Check both themes and both languages: `?theme=hmb&lang=en`, `?theme=acn&lang=de`, ... - text contrast WCAG AA
  (4.5:1, large text 3:1) on the navy canvas `#1E3446` and the card surface `#253D52`

## QR code

Every QR on the slides is the live image `<VOTING_URL>/qr.svg` from the voting app (the app encodes its
`PUBLIC_BASE_URL`). If the image does not load, the slide switches to a static QR for `<VOTING_URL>/` generated
at build time. The URL is also shown as text. Live and static QR only match if `VOTING_URL` equals the app's
`PUBLIC_BASE_URL`.

## Presenting

- Round slide: show the options and the QR, then switch the projector to the app window `/screen`
  (speaker note on every round slide). Admin control in `/admin` on the laptop, not on the projector.
- `S` opens the speaker notes, `F` full screen, `L` switches DE/EN, `T` switches Accenture / Hold my Beer.

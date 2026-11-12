# slides

Frame slides for the live talk (owner: Stefan Oehrli): cover, rules, prerequisites, speakers, voting app,
scorecard, one slide per round, conclusion, thank-you, reserve. No demo content - the rounds happen live.

## Layout

| Path | Content |
|------|---------|
| `src/<atom>/` | hand-written slide atoms (`slide.html` + `meta.yaml`, talk CLI format) |
| `generate.py` | writes the pool-driven atoms from `pool/<event>.yaml` (cover, voting, scorecard, rounds, reserve) |
| `deck.css` | talk-local size and layout overrides for `section.hmb`, inlined into the generated cover |
| `build/atoms/` | generated atoms - git-ignored, rebuilt by every build |
| `build.sh` | generate, then assemble the deck with the `talk` CLI |
| `<event>/` | built deck per event, e.g. `doag-ak-2026/wissen-nicht-was-sie-tun.html` |

Topic titles exist only in the pool YAML. Never copy them into `src/` - change the pool and rebuild.

## Build

Prerequisites: `uv`, the `talk` CLI from ai-toolkit (`make install-cli`), and a checkout of the talks repo next to
this one (`~/Repos/own/oehrlis/talks` and `~/Repos/own/oehrlis/hold-my-beer`).

```bash
VOTING_URL=https://<voting-domain> slides/build.sh # standalone HTML into slides/doag-ak-2026/
VOTING_URL=https://<voting-domain> slides/build.sh --pdf # PDF instead of HTML
slides/build.sh --dry-run # slide plan only, no deck written
TALKS_DIR=~/Repos/own/oehrlis/talks-dinu slides/build.sh # use another talks checkout or worktree
```

Without `VOTING_URL` the build uses the placeholder `https://voting.example.org` and says so.

## How it fits together

- The deck recipe stays in the talks repo: `talks/wissen-nicht-was-sie-tun/talk.yaml`. It lists every atom as
  `source: master/../../hold-my-beer/slides/...`. The talk CLI resolves `master/<path>` below
  `<TALKS_DIR>/master-slides/`, so the relative path lands in this repo next to the talks repo.
- `build.sh` checks that this path reaches the same checkout it runs from and stops otherwise.
- Stefan's bio comes from the shared master atom `mandatory/intro`; everything else is local to this repo.
- Reserve slides sit after the thank-you slide with `data-visibility="uncounted"`: reachable with the arrow keys,
  not counted in the slide number. The talk CLI's own `reserve: true` drops slides from HTML, so it is not used.

## QR code

Every QR on the slides is the live image `<VOTING_URL>/qr.svg` from the voting app (the app encodes its
`PUBLIC_BASE_URL`). If the image does not load, the slide switches to a static QR for `<VOTING_URL>/` generated
at build time. The URL is also shown as text. Live and static QR only match if `VOTING_URL` equals the app's
`PUBLIC_BASE_URL`.

## Presenting

- Round slide: show the options and the QR, then switch the projector to the app window `/screen`
  (speaker note on every round slide). Admin control in `/admin` on the laptop, not on the projector.
- `S` opens the speaker notes, `F` full screen.

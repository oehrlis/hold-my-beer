# Handover App - Slides

What the voting app (`app/`, owner Martin) and the frame slides (`slides/`, owner Stefan) agree on.
Change any point here only together.

## Single source: the pool file

- `pool/<event>.yaml` (first: `pool/doag-ak-2026.yaml`) holds rounds, options, reserve topics, voting
  duration, challenge time and scorecard categories. Schema: [`pool/README.md`](../pool/README.md)
- The app seeds from it (`flask seed-data`, file via `POOL_FILE`), the slide generator builds the round
  slides from it. Nobody copies topic titles by hand
- Changes to the pool after the seed need a fresh seed on the app server - check `/admin` before the talk

## QR code and URL

- The app delivers the QR: `<PUBLIC_BASE_URL>/qr.svg` points to the participant page `/`
- The slides embed exactly that image and show the URL as text; a static QR from the slide build is the
  fallback when the live image does not load (no network on the presenter laptop)
- `PUBLIC_BASE_URL` (app) and `VOTING_URL` (slide build) must be the same value - the public HTTPS domain,
  not the conference WLAN, not an IP. Open: domain

## Projector flow per round

| Step | Screen | Who |
|------|--------|-----|
| Round slide: three options, QR, URL | deck | presenter |
| Open voting (60 s), live tally, close | app `/screen` | admin in `/admin` |
| Publish result, choose challenge topic | app `/screen` | admin |
| Challenge (5 min timer) | terminal / IDE, timer on `/screen` | both |
| Scorecard for the round | app `/screen` | admin |
| Next round slide | deck | presenter |

Window switch, no iframe: the app keeps `frame-ancestors 'none'`. Deck and `/screen` run in two full-screen
windows on the projector; the admin view runs on the second laptop or a phone.

## Fallback

- App unreachable: show of hands on the round slide, the round slide lists all options
- Tie: run-off in the app or choose by hand - the app never draws at random on a tie
- Topic does not work: the admin assigns a reserve topic to a slot of a round not yet played
- Network gone: reserve slides "Fehlermuster-Katalog" in the deck

## Open

- [x] Subdomain `prost.oradba.ch` (decided 2026-11-12) - `PUBLIC_BASE_URL` = `VOTING_URL` =
  `https://prost.oradba.ch`
- [ ] Cloudflare for `prost.oradba.ch`: Tunnel (preferred) or proxied DNS, see `app/README.md`
- [x] Lab DB: Oracle AI Database 26ai, CDB/PDB
- [ ] Who runs `/admin` during the talk (second laptop or phone)
- [ ] Rehearsal with one complete round incl. window switch
- [ ] Martin reviews the app changes after the move (seed from the pool file, deploy defaults)

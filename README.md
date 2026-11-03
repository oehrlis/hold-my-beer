# live-voting

Mini web app for audience-driven live talks: attendees scan a QR code and either vote on the next topic or let
the app draw one at random. The result shows live on the projector.

First use: DOAG Anwenderkonferenz 2026, "Denn sie wissen nicht was sie tun - Oracle live mit Oehrli, Berger und KI"
(Stefan Oehrli, Martin Berger). Topic pool and round format live in the talks repo
(`talks/wissen-nicht-was-sie-tun/themen-pool.md`).

Status: private, made public after the talk.

## Requirements

- **Attendee view (mobile)**: open via QR code, no login, no personal data; one vote per device and round
  (anonymous cookie or token)
- **Two modes per round**: vote (3 options, about 60 s) or random draw from the topic pool
- **Projector view**: live result, animated random draw
- **Presenter control**: open / close a round, trigger the draw, reset - protected by an admin token
- **Public URL**: attendees use mobile data, not the conference WLAN
- **Load**: a few hundred devices in one room, short bursts
- **Fallback**: show of hands or a local random draw on the laptop if the app is down

## Open Decisions

- Stack and hosting (e.g. ORDS on an Always Free Autonomous DB, APEX, a small Python service)
- Topic pool format (YAML/JSON in this repo, loaded per talk)
- Domain and QR code

## License

Apache License 2.0 - see [LICENSE](LICENSE).

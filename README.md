# Hold my beer

<img src="assets/logo/hold-my-beer.svg" alt="Hold my beer logo" width="160" align="right">

Oracle live, with AI. The audience picks the task by QR-code vote or random draw, two DBAs and their AI tools
(Claude Code, Codex, GitHub Copilot, ChatGPT, Microsoft Copilot) deliver - live, no safety net. What works, what
the AI hallucinates, and where decades of DBA experience still win.

By Stefan Oehrli and Martin Berger. First run: DOAG Anwenderkonferenz 2026, Nuernberg, "Denn sie wissen nicht was
sie tun - Oracle live mit Oehrli, Berger und KI".

Status: private while in preparation, public after the talk. Nothing customer-related and no credentials in here.

## Layout

| Path | Content | Owner |
|------|---------|-------|
| `app/` | voting and random-draw web app | Martin |
| `pool/` | topic pool per event - source for app and slides | both |
| `rounds/` | per topic: task, prompts, expected AI failures, solution, reset | both |
| `env/` | lab environment and reset script | both |
| `slides/` | frame slides (built in the talks repo for now, sources may move here) | Stefan |
| `docs/` | format, storyline, roles, rehearsal notes | both |
| `assets/` | logo and images | both |

Terminal recordings (fallback when the network fails) stay out of git - too large, kept on OneDrive.

## Voting App - Requirements

- **Attendee view (mobile)**: open via QR code, no login, no personal data; one vote per device and round
- **Two modes per round**: vote (3 options, about 60 s) or random draw from the topic pool
- **Projector view**: live result, animated random draw
- **Presenter control**: open / close a round, trigger the draw, reset - protected by an admin token
- **Public URL**: attendees use mobile data, not the conference WLAN
- **Load**: a few hundred devices in one room, short bursts
- **Fallback**: show of hands or a local random draw on the laptop

Open: stack and hosting, pool format, domain and QR code.

## License

Apache License 2.0 - see [LICENSE](LICENSE).

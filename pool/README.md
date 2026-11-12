# pool

Topic pool per event - the single source for the app (seed: rounds, options, reserve) and the slides
(round slides). Contract between both: [`docs/handover-app-slides.md`](../docs/handover-app-slides.md).

| File | Content |
|------|---------|
| `doag-ak-2026.yaml` | DOAG AK 2026: 3 rounds, 12 reserve topics - read by app and slide build |
| `doag-ak-2026.md` | draft table and rationale (4-round draft, the YAML wins) |

## Schema (`schema: 1`)

| Key | Content |
|-----|---------|
| `event` | `name`, `short`, `city`, `date`, `time`, `room`, `duration_min`, `lang`, `title` |
| `format` | `voting_seconds`, `challenge_minutes`, `scorecard` (list of categories) |
| `rounds[]` | `number`, `name`, `options[]` |
| `rounds[].options[]` | `key` (A-C), `title`, `owner`, `category`, `difficulty`, `risk`, `ai_pitfall` |
| `reserve[]` | `title`, `owner`, `category` |

Values: `owner` Stefan, Martin, Gemeinsam or Offen; `difficulty` Leicht, Mittel, Schwer; `risk` Niedrig,
Mittel, Hoch. Titles are shown as written in app and slides - umlauts, no "ß".

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
| `event` | `name`, `short`, `city`, `date`, `time`, `room`, `duration_min`, `lang`, `title`, `title_en` |
| `format` | `voting_seconds`, `challenge_minutes`, `scorecard` (list of categories), `scorecard_en` (same length) |
| `rounds[]` | `number`, `name`, `name_en`, `options[]` |
| `rounds[].options[]` | `key` (A-C), `title`, `title_en`, `owner`, `category`, `category_en`, `difficulty`, `risk` |
| | `ai_pitfall` |
| `reserve[]` | `title`, `title_en`, `owner`, `category`, `category_en` |
| `event.result` | optional after the talk: `note`, `note_en` (participation line on the final score slide) |
| `rounds[].result` | optional after the talk: `votes` (`{A: n, ...}`), `played` or `winner` (option key), `outcome`, |
| | `outcome_en`, `scorecard` (list of scorecard categories; tiles are shown only when a round has one) |

Values: `owner` Stefan, Martin, Gemeinsam or Offen; `difficulty` Leicht, Mittel, Schwer; `risk` Niedrig,
Mittel, Hoch. Titles are shown as written in app and slides - umlauts, no "ß".

`result` is read only by the slide build (final score slide); once every round has one, the TODO placeholder
is gone. The app ignores it.

English (`*_en`): optional, used only by the slide build for the English deck - the app ignores them. A missing
`*_en` field shows the German text on the English slide, and the build prints one WARN line per missing field.
Owners stay German in the file; the slides show `Gemeinsam` as Joint and `Offen` as Open.

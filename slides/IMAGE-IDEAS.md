# Image ideas for the frame deck

Ideas for illustrations, not commitments. No third-party image or meme is embedded in the deck. Meme ideas are
meant as **own variants in the hold-my-beer logo style** (flat, navy `#1E3446` ground, beer orange `#EF6C00` and
gold `#FFC24A`, foam `#F0F5F8`, glass blue `#A8C8D8`, `>_` prompt), never as copies of the original meme images.

Every slide already looks finished without an image. Where a slot is named below, the image would replace or sit
next to an existing element; nothing on the slides is reserved as an empty box.

## Sources

- **own**: draw in the logo style (SVG, same palette and stroke weight as the scorecard icons in `generate.py`)
- **visuals**: reuse from `~/Repos/own/oehrlis/visuals` (catalog `catalog/index.html`)
- **licensed**: search a licensed stock source, check the licence for conference and Accenture use

## Per slide

<!-- markdownlint-disable MD013 MD060 -->
| Slide | Idea | Purpose | Source | Priority |
|-------|------|---------|--------|----------|
| Cover | Mug with two straws labelled "Stefan" and "Martin", a robot arm reaching for the handle | Duo plus AI in one picture, sets the tone | own | P2 |
| Spielregeln | "This is fine" variant: the beer mug sits calmly in front of a burning `alert.log` | Rule 3 ("every mistake is called out"), visual punchline | own | P1 |
| Voraussetzungen | Small conference Wi-Fi icon with a bandage next to "Netz" | Supports the Wi-Fi joke without words | own | P3 |
| Speaker Stefan | none - photo and ACE Director badge are set | - | visuals (badges already in `src/`) | - |
| Speaker Martin | none - photo and ACE Pro badge are set | - | visuals (badges already in `src/`) | - |
| ACE program | Official ACE program logo instead of the three text tiles | Brand recognition | visuals `library/brand/oracle-ace/oracle-ace-program-ace-rgb.png` | P3 |
| Voting | Phone outline with the voting app screen, beer foam as the progress bar | Shows what the audience will see | own (screenshot of `/` from the app plus frame) | P2 |
| Scorecard | Four icons are drawn; optional chalk tally marks behind the tiles | Scoreboard feel | own | P3 |
| Round dividers | "Distracted boyfriend" variant: DBA looks at the AI, the Oracle docs look offended | Divider round 2 or 3, live laugh before the vote | own | P1 |
| Round dividers | Expanding brain: `SELECT *` -> `SELECT` with columns -> reads the plan -> asks the AI for the plan -> asks the AI and reads the plan | Divider round 3 ("Bruchstelle") | own | P1 |
| Endstand | Two beer mugs as a scale, AI vs. DBA, tipped by the result | Final score as one picture, filled live | own | P2 |
| Fazit | Autopilot switch in "OFF" position with a hand on the stick | Leitmotiv "AI ist kein Autopilot" | own | P2 |
| Danke | Empty mug with a foam ring and `$ exit` on the glass | Closing punchline "hold my beer" | own | P2 |
| Reserve divider | Classic error dialog box with `ORA-00600` and an "OK" button that does nothing | Emergency slide | own | P3 |
| Fehlermuster 1 | Package box labelled `DBMS_MAGIC` that is empty inside | Hallucinated packages | own | P2 |
| Fehlermuster 2 | Calendar page "2009" stuck on a 26ai server | Version syntax | own | P3 |
| Fehlermuster 3 | Archery target with the arrow in the neighbour's target | Solved the wrong problem (matches the scorecard icon) | own | P3 |
| Any | CommitStrip strips about AI coding | Humour | visuals `library/third-party/commitstrip` - **non-commercial licence only**, not usable on an Accenture-branded deck without permission | do not use |
<!-- markdownlint-restore -->

## Top 5

All five are done (2026-11-12) - SVGs in `img/`, placement in `README.md` (Illustrations).

1. Done: "This is fine" mug before a burning `alert.log` (rules slide) - `img/this-is-fine.svg`
2. Done: Expanding brain from `SELECT *` to "asks the AI for the plan" (divider round 3) - `img/expanding-brain-de.svg`,
   `img/expanding-brain-en.svg`
3. Done: Distracted boyfriend: DBA, the AI, the docs (divider round 2) - `img/distracted-dba.svg`
4. Done: Phone with the voting screen and a foam progress bar (voting slide) - `img/phone-voting-de.svg`,
   `img/phone-voting-en.svg`
5. Done: Autopilot switch "OFF" (takeaways) - `img/autopilot-off.svg`

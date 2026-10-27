# Prior work declaration

Everything in this repository written by team OSEF was created during the Open Agent Hackathon 2026, after 22 October 2026, 00:00 UTC. The first commit of the shared repository is dated 23 October 2026 (16:00 Paris, `d98df20`, the project skeleton); Steward's code was written from 22 October (evening) onward and imported into this repository on 27 October with its history.

Third-party material, declared as such:

| Component | Where | License | Use |
| --- | --- | --- | --- |
| Meterless H-MEM reference implementation and conformance suite | `hmem-service/vendor/` (fetched by `hmem-service/setup.sh` from github.com/Meterless/Meterless) | Apache-2.0 (`NOTICE`, `hmem-service/vendor/LICENSE-meterless`) | Vendored unchanged; `hmem-service/server.ts` wraps it |
| Zetaris getting-started repository | read, not vendored (`scripts/zetaris/*.sql` follow its recipes) | its own | SQL recipes for datasources, REST tables, filestores and the USL |
| Archivo and Chivo Mono fonts | `app/static/brand/fonts/` | SIL Open Font License 1.1 | the Steward brand kit |
| Skills from github.com/obra/superpowers (commit `2ce8aa1`) | `.claude/skills/` | MIT | instructions for the review agents, no code |
| Python and Node packages | `requirements.txt`, `hmem-service/package.json` | their own | runtime |

No dataset is real: Brikk, its people, its figures, the Atlas project and Orion are synthetic and were written for the event.

# Submission checklist (HackOS, before 28 October 00:45 Paris / 27 October 23:45 UTC)

Fill in this order. Texts to paste: `docs/SUBMISSION.md` (name, one sentence, description, sponsor usage, prior work) and `docs/submission/hackos-form.md` (team table, limitations).

- [ ] **Team locked?** Open hackathon.genai.works/dashboard and check that the team OSEF lists Ryan Dalier-Dulys (lead), Adam Semlali, Alexandre Bouchet before the first Submit (the team locks at the first submission).
- [x] **Repository link**: `https://github.com/abouchet109-del/Hackathon-GenAI-public` — `main` = `unify` since pull request #2 was merged (27 October 22:13 Paris, `20cd3b9`); the form points at the repository.
- [ ] **Repository is public** (it is) and `git clone` + the README's three commands work from a fresh folder (verified 27/10 20:10 on `unify`; CI run 40568677619 green).
- [ ] **Video** (1 to 4 minutes, target 3:00): record with `docs/SUBMISSION.md` ("Video script") or `for-repo/docs/VIDEO.md` from session C if it exists; upload to YouTube (unlisted) or Drive (anyone with the link); paste the link.
- [ ] **Deck**: export the deck artifact (https://claude.ai/artifact/8SnkV2StL6ipGMn5ygHjRZ, updated by session C if it ran) as PDF; upload or link it.
- [ ] **Project name**: `Steward`. **Track**: 03 Reasoning Architecture.
- [ ] **One-sentence description**: from `docs/SUBMISSION.md`.
- [ ] **Description**: from `docs/SUBMISSION.md` ("Short description").
- [ ] **Sponsor technologies**: Zetaris, Meterless H-MEM, Meterless Nightshift, NVIDIA Nemotron, Cursor — texts in `docs/SUBMISSION.md` ("Sponsor technology"); say what did NOT run live if it still has not (Zetaris registration of Brikk, Nemotron run) rather than implying it did.
- [ ] **Pre-existing work declaration**: from `docs/SUBMISSION.md` ("Prior work declaration").
- [ ] **metadata.json** is in the repository root (it is).
- [ ] **Secrets**: `.env` is not in the repository (checked); the NVIDIA key lives only in Nightshift.
- [ ] **Submit**, then open the submission page once more to check that every link opens in a private window.
- [ ] After the event: delete the `transport` branch (bundle + import workflow) and, if wanted, `docs/team/ci-tests.yml` (a copy of the CI workflow carried by the transport push).

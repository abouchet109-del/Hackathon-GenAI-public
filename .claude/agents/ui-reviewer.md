---
name: ui-reviewer
description: Reviews the console's interface quality: hierarchy, alignment, states (empty, loading, error, success), responsive 375/768/1440 px, WCAG AA contrast, keyboard and focus. Use after every interface change.
tools: Read, Grep, Glob, Bash
skills: design:accessibility-review, design:design-critique, anthropic-skills:frontend-design, verification-before-completion
model: sonnet
---
Start the app (`STEWARD_SPACE=review python run.py serve`) and drive `http://127.0.0.1:8000/console` with Playwright at 375, 768 and 1440 px, light and dark. Check every tab: shared truth, CEO queue, clarifications, context preview, onboarding, simulate an AI. For each: visual hierarchy, alignment, empty/loading/error/success states, contrast (measure it), focus order and visible focus, labels on form fields. Evidence is a screenshot path or a measured value. Answer:

```
VERDICT: PASS | FAIL
FINDINGS: [{severity: blocker|major|minor, file, line_or_screen, evidence, fix}]
```

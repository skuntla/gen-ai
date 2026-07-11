# Explainer Visuals

NotebookLM-style hand-drawn explainer images for phase notes.

## Quick start

```bash
cd tools/explainer-visuals
npm install
npx playwright install chromium
npm run export:phase-01
npm run export:statelessness
```

Outputs:
- `docs/PHASE-NOTES/phase-01/visuals/messages-format.png`
- `docs/PHASE-NOTES/phase-01/visuals/statelessness.png`

## How it works

1. **Scene JSON** (`scenes/`) — table content, illustration positions, path
2. **HTML template** (`templates/analogy-table.html`) — layout + Rough.js rendering
3. **Illustration library** (`lib/illustrations.js`) — reusable sketchy icons
4. **Playwright export** (`export.js`) — screenshots `.scene` at 2× resolution

## Add another scene

1. Copy `scenes/phase-01-messages.json` and edit rows/illustrations.
2. Export:

```bash
node export.js scenes/your-scene.json ../../docs/PHASE-NOTES/phase-01/visuals/your-scene.png
```

## Preview in browser

Open `templates/analogy-table.html` after embedding scene data, or run export and check the PNG.

## Sample scenes

**Phase 01 — LLM Messages Format**

| Role | Analogy | Purpose |
|------|---------|---------|
| system | The Director's Brief | Persona, rules, format |
| user | The Question | What you ask |
| assistant | The Performance | What the model returns |

**Phase 01 — Why LLMs Are Stateless**

| Concept | Analogy | What it means |
|---------|---------|---------------|
| Stateless API | A Vending Machine | Each call starts fresh |
| Message history | Your Shopping Receipt | You resend past turns yourself |
| Context window | Bag Size Limit | Only so much history fits |

# Orynth · AeroLab — Phase 1 Review Deck

Self-contained HTML presentation (reveal.js 5.1). No internet needed at runtime.

## Open locally

The deck works straight from `file://` in Chromium-based browsers:

```bash
xdg-open docs/presentation/index.html
```

Firefox blocks some relative-path loads over `file://` — if slides render without
styling, start a tiny local server instead:

```bash
cd docs/presentation
python3 -m http.server 8765
# then visit http://localhost:8765/
```

## Keyboard controls

| Key | Action |
|---|---|
| `→` / `Space` | Next slide |
| `←` | Previous slide |
| `Esc` / `O` | Overview mode (all slides) |
| `F` | Fullscreen |
| `S` | Speaker-notes window |
| `?` | Full help overlay |

## Export to PDF

Open the deck with `?print-pdf` appended, then print to PDF from the browser:

```
http://localhost:8765/?print-pdf
```

Chrome/Chromium gives the cleanest output. Set paper size to **A4 Landscape**,
margins **None**, **Background graphics ON**.

## Share with colleagues

Everything the deck needs is inside `docs/presentation/`. Zip the whole folder
and send it — they just unzip and double-click `index.html`.

## Structure

```
presentation/
├── index.html          · the deck
├── theme.css           · Orynth dark theme
├── assets/
│   └── banner.png      · hero image (Orynth wordmark + drone swarm)
└── vendor/
    └── reveal.js/      · reveal.js 5.1 (dist + plugins only)
```

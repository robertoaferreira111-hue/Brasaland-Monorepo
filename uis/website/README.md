# Brasaland website

Static public site for Milestone 1. Facts, field order, and messages come from the root `CONTEXT.md`.

## Run

From this folder:

```bash
npx http-server . -p 3000 -a 0.0.0.0
```

Open `http://127.0.0.1:3000`.

## Files

- `index.html` — landing page, including the Restaurant JSON-LD.
- `application.html` — Brasa Points registration form.
- `validation.js` — real-time checks, blocked submit, focus on the first invalid field, and Clear.
- `styles.css` — precompiled, minified Tailwind stylesheet. The file starts with a comment that it is Tailwind CLI output.
- `story.svg` and `favicon.svg` — the story illustration and icon.

Styling is Tailwind utility classes only. The pages load `styles.css`. They do not load the Tailwind browser runtime.

## Rebuild the stylesheet

`tailwind.css` is the Tailwind CLI input. It contains only the Tailwind directives. `tailwind.config.js` scans `index.html` and `application.html`, so the stylesheet includes only the utility classes already in those pages.

This command is dev-time only. Serving the site does not run it.

```bash
npm install
npm run build:css
```

`npm run build:css` runs `tailwindcss -i ./tailwind.css -o ./styles.css --minify`.

Locations, Menu, and Contact are sections on the landing page. The header links to those sections. Brasa Points opens the registration form. No dishes or prices are listed, because the briefing does not provide them.

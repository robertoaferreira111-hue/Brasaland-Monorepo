# Brasaland backoffice

Internal desk for Brasaland Digital. Facts on the page come from the root `CONTEXT.md`. This app does not share layout files with `uis/website`.

## Stack

Static HTML and Tailwind utility classes, compiled to `styles.css`. The page loads that file. It does not load the Tailwind browser runtime. No backend is required for the entry view.

`uis/website` is the public site and uses the same kind of stack. This folder has its own `package.json`, Tailwind input, and stylesheet. Nothing here is imported from `uis/website`.

## Run

From this folder:

```bash
npm install
npm run build:css
npx http-server . -p 3010 -a 0.0.0.0
```

Open `http://127.0.0.1:3010`.

Port 3010 keeps this app off the public site's port 3000. `npm run build:css` is dev-time only. Serving the page does not run it.

`npm run build:css` runs `tailwindcss -i ./tailwind.css -o ./styles.css --minify`. `tailwind.config.js` scans `index.html`.

`http-server` is not a dependency in `package.json`. The command above uses `npx`, the same way `uis/website` does.

## Files

- `index.html` — entry view at `/`: locations by country, departments and owners, and the Monday 7am executive report.
- `styles.css` — precompiled Tailwind stylesheet for this app only.
- `favicon.svg` — icon for this app only.

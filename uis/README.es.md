# Carpeta `uis`

Esta carpeta contiene **todos los proyectos con interfaz de usuario** para el proyecto transversal de AI Engineering de la compañía — por ejemplo: un sitio web público, un frontend de panel de administración, una interfaz de ecommerce, portales para clientes, aplicaciones Streamlit/Gradio u otras herramientas sólo-frontend.

Los dos proyectos principales que se almacenan aquí son:

- **`website`** — la presencia web pública de la compañía.
- **`backoffice`** — la aplicación interna de administración. Es el lugar ideal para desarrollar múltiples soluciones dentro de un mismo proyecto: autenticación, gestión de personas, gestión de operaciones, comunicación interna y otras capacidades de back-office.

Organiza `uis/` por **distintas áreas de la compañía** — cada subcarpeta agrupa un ámbito diferente (por ejemplo, web pública frente a operaciones internas) e incluye su propia documentación técnica y funcional.

- **Propósito principal**: centralizar en un único lugar todas las aplicaciones frontend que dan soporte a los casos de uso de la compañía.
- **Recomendación**: documenta en este archivo (o en sub-READMEs) las aplicaciones que vayas añadiendo, su objetivo, tecnología usada y cómo ejecutarlas.

## `website` — sitio público de Brasaland

Sitio corporativo del hito 1. HTML estático, clases de utilidad de Tailwind y `validation.js`. Idioma base: inglés. Los datos salen de `CONTEXT.md` en la raíz.

```bash
cd uis/website
npx http-server . -p 3000 -a 0.0.0.0
```

Detalle en [website/README.md](./website/README.md).

## `backoffice` — aplicación del personal

Aplicación Next.js para el inicio de sesión del personal. No modifica el sitio público.

```bash
cd uis/backoffice
npm install
npm run dev
```

Abre `http://127.0.0.1:3001`. `/login` y `/register` son públicas. `/account` redirige a `/login` si no hay un JWT en `localStorage`. La URL de la API es `http://127.0.0.1:8000` por defecto (`NEXT_PUBLIC_API_URL`).

Detalle en [backoffice/README.md](./backoffice/README.md).

> _These instructions are also available in [English](./README.md)._

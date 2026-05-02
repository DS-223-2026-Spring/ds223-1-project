# MkDocs Setup

This project uses **MkDocs Material** for published documentation and
`mkdocstrings` for Python API references.

---

## Local setup

Create and activate a virtual environment, then install the docs dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install mkdocs mkdocs-material "mkdocstrings[python]" pillow cairosvg
```

---

## Local preview

From the repository root:

```bash
mkdocs serve
```

Default local docs URL:

```text
http://127.0.0.1:8000
```

---

## Current documentation pages

- `index.md`
- `demo.md`
- `governance.md`
- `database.md`
- `etl.md`
- `modeling.md`
- `ds_data_spec.md`
- `api.md`
- `app.md`
- `pm_endpoint_review.md`

---

## Deployment

GitHub Actions configuration lives in:

```text
.github/workflows/ci.yaml
```

The pipeline installs MkDocs dependencies, builds the docs site, and deploys
to GitHub Pages.

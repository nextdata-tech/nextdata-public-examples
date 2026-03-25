# Pre-commit docs tools

This directory contains helper scripts used by pre-commit checks for docs.

## md_link_check.py

Validates relative Markdown links under `data_products/`.

What it checks:
- Target files exist (including `README.md` resolution where applicable).
- Anchors resolve to Markdown headers or HTML anchors using `id` only (for example, `<a id="section">`).
- Markdown links like `[text](path.md#anchor)` and autolinks like `<path.md#anchor>` are checked.
- HTML anchor links like `<a href="path.md#anchor">` are checked.
- Links inside single-line HTML comments are ignored.
- `EXCLUDED_FILES` and `EXCLUDED_LINKS` allow explicit opt-outs.
- Optional external URL checks for fully qualified `http`/`https` links.
- External checks can skip any URL that starts with a prefix in `EXCLUDED_EXTERNAL_PREFIXES`.

Run it:
```bash
python .pre-commit-hooks/md_link_check.py
```

Run it with pre-commit:
```bash
pre-commit run docs-link-check-internal --files $(git ls-files 'data_products/**/*.md')
pre-commit run docs-link-check-external --files $(git ls-files 'data_products/**/*.md')
```

Run it for a subset:
```bash
python .pre-commit-hooks/md_link_check.py data_products/market-announcements/README.md
```

Run it with external link checks:
```bash
python .pre-commit-hooks/md_link_check.py --check-external-links data_products/market-announcements/README.md
```

Self-test:
```bash
python .pre-commit-hooks/md_link_check.py --self-test
```

Warning-only mode (prints problems, exits 0):
```bash
python .pre-commit-hooks/md_link_check.py --warn
```

## md_sentence_case.py

Normalizes Markdown headings to sentence case for files under `data_products`.

Behavior:
- Converts Title Case headings to sentence case.
- Preserves all-caps acronyms and allow-listed proper nouns.
- Protects specific product phrases (see `PROPER_PHRASES`).
- Skips content inside fenced code blocks.

Run it on specific files:
```bash
python .pre-commit-hooks/md_sentence_case.py data_products/market-announcements/README.md
```

Run it with pre-commit (single hook):
```bash
pre-commit run docs-sentence-case --files $(git ls-files 'data_products/*.md')
```

Run it on all docs:
```bash
python .pre-commit-hooks/md_sentence_case.py $(git ls-files 'data_products/*.md')
```

Note: This script edits files in place and exits non-zero when it makes changes.

## check_spec_imports.py

Ensures that all `spec.py` files contain **at most one import line**.

### Purpose
This hook enforces the DSL pattern of consolidating imports for demo purposes, making spec files more readable and focused on the data product definition rather than import boilerplate.

### How it works
- Scans all `spec.py` files for lines starting with `from` or `import`
- Passes if 0 or 1 import lines are found
- Fails if more than 1 import line is found

### Example: Valid spec.py
```python
# ruff: noqa: F403, F405
from nxd_spec import *

spec = data_product(...)
```

### Example: Invalid spec.py
```python
from nxd.spec import data_product
from nxd.spec import storage
from nxd.spec.conditions import scheduled

spec = data_product(...)
```

### Solution
Create a local `nxd_spec.py` or `dsl.py` file that re-exports all needed symbols:

```python
# nxd_spec.py
from nxd.spec import *
from nxd.spec.conditions import *
```

Then import everything from that single module:
```python
from nxd_spec import *
```
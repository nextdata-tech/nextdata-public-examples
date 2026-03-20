# Pre-commit Hooks

## check-spec-imports

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

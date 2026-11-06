# tests

```bash
python -m pip install pytest pyyaml ruff
python -m pytest -q                 # 93 tests, no Home Assistant needed
python tools/check_boundaries.py    # constraint probes C-06 / C-08 / C-09
```

| Directory | Level | Needs |
|-----------|-------|-------|
| `unit/` | Pure logic: bridge plan/apply, pricing, adapters, ledger, telemetry, executor, boundaries | Python only |
| `schema/` | Site-profile schema against the three worked examples and broken variants | Python + PyYAML |
| `contract/adapters/` | Shared suite every adapter must pass (stubs today, vendor adapters later) | Python only |
| `contract/haeo/` | Live HA + pinned HAEO instance; `-m live` | HA runtime, HAEO, highspy, numpy |
| `integration/` | HA test harness (`pytest-homeassistant-custom-component` hoisted fixture) | HA runtime |

Rules:

- Tests must not import Home Assistant unless they live in `integration/` or
  `contract/haeo/`. `tests/unit/test_boundaries.py` proves the core package
  imports with HA absent.
- A test that needs an unverified HAEO fact is marked `xfail(strict=True)` with
  the OQ id, so resolving the OQ forces the test to be updated.

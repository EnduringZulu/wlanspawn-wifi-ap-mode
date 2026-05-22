# Contributing to wlanspawn

First off, thank you for considering contributing! 🎉

## Quick start

```bash
git clone https://github.com/yourusername/wlanspawn.git
cd wlanspawn
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Verify everything works
make test
make lint
```

## Project layout

```
wlanspawn/
├── wlanspawn/
│   ├── cli.py              Main CLI (Click commands + Rich output)
│   ├── config.py           TOML config management & init wizard
│   ├── detector.py         OS/backend/interface auto-detection
│   ├── doctor.py           Dependency health checks
│   ├── logger.py           Logging setup (Rich)
│   ├── backends/           One file per backend (NM, hostapd, Windows)
│   └── utils/              Network and system helpers
├── tests/                  pytest test suite
├── scripts/                install.sh / uninstall.sh
└── .github/                CI workflows, issue templates
```

## Adding a new backend

1. Create `wlanspawn/backends/mybackend.py`
2. Subclass `HotspotBackend` from `wlanspawn.backends.base`
3. Implement all abstract methods: `is_available`, `is_running`, `up`, `down`, `status`, `clients`
4. Register it in `wlanspawn/backends/__init__.py`'s `candidates` dict
5. Add detection logic in `wlanspawn/detector.py::Detector.suggest_backend()`
6. Add doctor checks in `wlanspawn/doctor.py`
7. Write tests in `tests/test_backends.py`

## Code style

- **black** for formatting (line length 100)
- **ruff** for linting
- **mypy** for type checking (soft enforcement for now)

Run all checks: `make lint`

## Tests

- Use `pytest` with `unittest.mock` for patching
- Never run real system commands in tests — patch `wlanspawn.utils.system.run`
- Name tests descriptively: `test_<what>_<when>_<expected>`
- Aim for >80% coverage on new code

Run: `make test`

## Commit messages

Use conventional commits style:

```
feat: add QR code generation command
fix: handle missing dnsmasq lease file gracefully
docs: update Windows installation steps
test: add hostapd config generation tests
refactor: extract _write_conf helpers from HostapdBackend
ci: add Windows smoke test job
```

## Releasing (maintainers)

1. Update `CHANGELOG.md`
2. Bump `__version__` in `wlanspawn/__init__.py` and `pyproject.toml`
3. `git tag v0.x.y && git push origin v0.x.y`
4. GitHub Actions publishes to PyPI automatically

## Code of Conduct

Be kind, patient, and welcoming. We're all here to learn and build something useful.

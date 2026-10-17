# Contributing

Report reproducible bugs in [Issues](https://github.com/eigger/hass-niimbot/issues); use [Discussions](https://github.com/eigger/hass-niimbot/discussions) for questions and feature ideas. Remove Bluetooth addresses, serial numbers, network addresses, credentials and private label contents from reports.

## Implementation and dependencies

The HACS package lives in `custom_components/niimbot/`. Follow the [Core-aligned module and lifecycle rules](https://github.com/eigger/hass-repo-standards/blob/7acd9cab6ac774e4695f2c962e3d88b5faa4620d/docs/home-assistant.md): config flow manages configuration, platform modules own entities, `entity.py` shares registry binding, `data.py` holds typed entry runtime state, and `niimprint/` handles printer protocol. Keep existing domain, entry and entity unique IDs stable. Background work and connections must be released on unload and failed setup. Use public HA APIs supported by the declared minimum.

Runtime requirements come from `custom_components/niimbot/manifest.json`. Preserve requirement extras and operators. Follow the [dependency addition procedure](https://github.com/eigger/hass-repo-standards/blob/7acd9cab6ac774e4695f2c962e3d88b5faa4620d/docs/dependencies.md) when changing them; test exact library lower bounds as well as resolver-selected versions. HA component dependencies are distinct from PyPI requirements. Test and lint tools belong in their own requirements files. Do not raise minimum HA or library versions merely to accommodate newer test tooling.

## Reproduce the test environments

Run from the repository root, using a separate virtual environment for each row:

| Scope | Python | Home Assistant | pytest-homeassistant-custom-component | Requirements |
|---|---|---|---|---|
| Current | 3.14 | 2026.10.2 | 0.13.373 | `requirements_test.txt` |
| Declared HA minimum | 3.13 | 2025.1.0 | 0.13.201 | `requirements_test_min.txt` |

The existing runtime library versions require Python 3.13 or later. HA 2025.1 running Python 3.12 cannot install them. The support minimum in `hacs.json` remains 2025.1.0. Current testing and the support minimum are independent policies.

For current testing:

```bash
python3.14 -m venv .venv
source .venv/bin/activate
python -c 'import json; from pathlib import Path; print("\n".join(json.loads(Path("custom_components/niimbot/manifest.json").read_text())["requirements"]))' > /tmp/niimbot-runtime-requirements.txt
python -m pip install -r requirements_test.txt -r requirements_lint.txt -r /tmp/niimbot-runtime-requirements.txt
python scripts/ha_component_requirements.py bluetooth bluetooth_adapters recorder > /tmp/niimbot-ha-components.txt
python -m pip install -r requirements_test.txt -r requirements_lint.txt -r /tmp/niimbot-runtime-requirements.txt -r /tmp/niimbot-ha-components.txt
python -m pip check
python -m ruff check .
python -m ruff format --check .
python -m pytest tests/components/niimbot/ -q --timeout 120
```

Bootstrap HA to read its component manifests, then resolve the complete requirement set together as shown above; do not install component pins in isolation.

For minimum HA, create a separate Python 3.13 virtual environment and substitute `requirements_test_min.txt`. To test exact library minimums in either HA environment, add `blesession==0.9.0` and `imagespec[datamatrix]==1.1.0` constraints to installation, confirm installed versions and rerun `pip check` and the same test suite. The Tests workflow runs both dependency modes for both HA environments.

Tests follow the [real HA testing policy](https://github.com/eigger/hass-repo-standards/blob/7acd9cab6ac774e4695f2c962e3d88b5faa4620d/docs/testing.md). `tests/components/niimbot/` uses actual HA fixtures, config flow/entry loading, platform entities and unloading. Mock external Bluetooth transport or cloud responses, not HA core modules. Protocol regression tests supplement these integration tests. See [ADOPTION_CHECKLIST.md](ADOPTION_CHECKLIST.md) for actual executed versions, results and limitations; the table above is the environment contract, not an assertion that every check has run.

## Validation and releases

CI runs Ruff, the actual HA tests, Hassfest and HACS validation through SHA-pinned shared workflows. Validate release tag and manifest version agreement, user-visible changes and migration requirements before releasing. Standards adoption does not create a new integration version or release. Automated tests do not replace a physical printer/proxy test: include the model, firmware, adapter/proxy and print outcome when reporting one.

## Dependency update PR checks

The shared updater tests the changed manifest with exact proposed lower bounds before synchronizing one bot PR. PRs created with `GITHUB_TOKEN` do not automatically trigger further push/PR workflows. After a proposal is created, run **Tests** and **Validate** with `workflow_dispatch` on `bot/manifest-dependencies` and inspect their results on the same proposed commit before merging. A failed dispatch or validator is still pending work. There is currently no branch protection on `master`; review checks explicitly. Do not automatically merge, tag or release dependency proposals.

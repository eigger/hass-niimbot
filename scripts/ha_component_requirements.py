"""Print the pinned requirements of Home Assistant components the tests load.

pytest-homeassistant-custom-component installs Home Assistant core but not the
requirements of individual components. bluetooth_adapters (and the bluetooth
stack it pulls in) and the recorder are needed to set this integration up.
Reading them from the installed HA keeps the pins in step with whatever HA
version the test package brings. Dependencies are walked too: bluetooth imports
usb, and usb's aiousbwatcher pin is not on the bluetooth manifest.

    python scripts/ha_component_requirements.py bluetooth bluetooth_adapters recorder
"""

from __future__ import annotations

import json
from pathlib import Path
import sys

import homeassistant.components

components_dir = Path(homeassistant.components.__file__).parent
requirements: set[str] = set()


def collect(name: str, seen: set[str]) -> None:
    """Add one component's requirements and those of its dependencies."""
    if name in seen:
        return
    seen.add(name)
    manifest_path = components_dir / name / "manifest.json"
    if not manifest_path.is_file():
        return
    manifest = json.loads(manifest_path.read_text())
    requirements.update(manifest.get("requirements", []))
    for dependency in manifest.get("dependencies", []):
        collect(dependency, seen)


seen: set[str] = set()
for name in sys.argv[1:]:
    collect(name, seen)
print("\n".join(sorted(requirements)))

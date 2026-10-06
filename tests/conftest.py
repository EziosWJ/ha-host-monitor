"""Test configuration.

Adds the integration directory to ``sys.path`` so the pure ``data`` module can
be imported without going through the package ``__init__`` (which imports Home
Assistant).
"""

import sys
from pathlib import Path

INTEGRATION_DIR = (
    Path(__file__).resolve().parent.parent / "custom_components" / "host_monitor"
)

if str(INTEGRATION_DIR) not in sys.path:
    sys.path.insert(0, str(INTEGRATION_DIR))

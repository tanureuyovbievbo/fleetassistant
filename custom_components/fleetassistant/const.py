"""Constants shared by the integration and the pure-Python core.

Pure module: no Home Assistant imports (keeps core testable, C-08).
"""

from __future__ import annotations

DOMAIN = "fleetassistant"
NAME = "fleetassistant"
VERSION = "0.1.0"

#: Site profile schema version understood by this build (see profile/schema.py).
PROFILE_SCHEMA_VERSION = 1

#: Telemetry envelope schema version (see telemetry.py).
TELEMETRY_SCHEMA_VERSION = 1

#: HAEO versions the bridge is contract-tested against (C-07, ADR-0004).
#: Working target v0.5.0 — re-confirm the latest release before each bump (F-011).
SUPPORTED_HAEO_VERSIONS: tuple[str, ...] = ("0.5.0",)

#: Default for HAEO's "Relax impossible plans" hub setting (ADR-0007).
#: The option key itself is UNVERIFIED until the e04 spike (OQ-006).
DEFAULT_RELAX_IMPOSSIBLE_PLANS = True

#: Options key that arms the first live write. Off by default: until a live HAEO
#: instance accepts our element payloads (OQ-017), provisioning must not fire.
#: RL-14: when it is on, provisioning runs once per setup — no drift repair yet.
CONF_APPLY_HAEO_PLAN = "apply_haeo_plan"
DEFAULT_APPLY_HAEO_PLAN = False

#: Domain collision guard (C-03).
HAEO_DOMAIN = "haeo"

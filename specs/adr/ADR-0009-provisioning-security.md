# ADR-0009 — Provisioning and connectivity security baseline

| Field | Value |
|-------|-------|
| Status | accepted |
| Date | 2026-11-05 |
| Source | Project brief |
| Constraints | C-17, C-18, C-20 |

## Context
Fleet sites must be provisioned headlessly without shared secrets and without exposing homes to inbound traffic.

## Decision
- Per-site device identity and client certificates.
- WireGuard client-only: the gateway dials out. No inbound ports.
- Scoped OAuth2 through HA Application Credentials for vendor APIs.
- Headless provisioning through the HA config-flow REST API.
- No shared admin tokens anywhere.
- Nabu Casa cloud is not our relay.

## Consequences
A certificate authority and lifecycle tooling are needed (D08). All API shapes must be verified (C-23).

## Rejected alternatives
- **Shared long-lived admin tokens:** a single leak exposes the whole fleet.
- **Port forwarding or inbound VPN:** adds attack surface.
- **Nabu Casa remote UI as the relay:** it is not our service, and it has brand and ToS issues.

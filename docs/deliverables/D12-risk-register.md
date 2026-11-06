# D12 — Risk Register

| Field | Value |
|-------|-------|
| ID | D12 |
| Epic | e12-risk-register |
| Version | 0.1.0 (seeded at bootstrap; the full register is D12 work) |
| Status | not-started (seed only) |
| Owner role | architect + claims-auditor |
| Last updated | 2026-11-05 |
| Depends on | All deliverables. Update this register at every gate. |

## Scoring

Likelihood (L) and Impact (I) use a scale of 1–5. Score = L × I. The seed scores below are **provisional** and must be re-assessed in D12.

## Seed risks

| ID | Category | Risk | L | I | Mitigation | Owner role | Links |
|----|----------|------|---|---|-----------|------------|-------|
| R-001 | Technical | HAEO config-flow fields change between versions and break the bridge. | 4 | 4 | Pin the version (ADR-0004). Contract tests per version. Upgrade only through the OTA matrix. | engineer | C-07, D04 |
| R-002 | Technical | Elements/connections are subentries, or otherwise not drivable headlessly. | 3 | 5 | Spike first (e04 S1). Fallback: the in-process flow manager from our integration. | engineer | OQ-009 |
| R-003 | Technical | highspy wheels are not available on some architectures (for example armv7/musl). | 3 | 4 | Publish a supported-platform list. Install docs (D02). | architect | OQ-001, OQ-010 |
| R-004 | Vendor | Cloud vendor ToS forbids commercial or aggregated use, or the quota is too small for the promised cadence. | 4 | 4 | ToS review and quota math per vendor (C-24). Prefer local control on dispatch sites. | source-verifier | OQ-005 |
| R-005 | Operational | HA event loop overloaded (entities plus HAEO solve) in a tenant container. | 2 | 4 | Tenant per container (C-01). Measure entity count and solve time (OQ-015). | engineer | D08 |
| R-006 | Regulatory | Over-claiming performance or certification. | 2 | 5 | C-12, C-21, `/verify-claims`, claims-auditor gate. | claims-auditor | D09, D10 |
| R-007 | Safety | A bad control write damages equipment or leaves the home uncomfortable. | 2 | 5 | Safety pipeline, hardware fail-safe, read-back, audit (D06). | engineer | C-09, C-15 |
| R-008 | Legal | A GPL-3 community integration enters the paid fleet without review. | 3 | 3 | License audit (C-19). | architect | D08 |
| R-009 | Security | Tenant secret leakage or a shared credential. | 2 | 5 | C-17, C-18, SECURITY_PLAN. | engineer | D08 |
| R-010 | Technical | Unpriced battery cycling voids warranties. | 3 | 4 | Degradation term required (C-14). | architect | D05 |

## Top 10 numbers to verify before committing capital (placeholder list)

Each number MUST be filled in from a primary source (S-ID) or remain **UNVERIFIED**. Do not estimate.

| # | Number | Source required | Value | Status |
|---|--------|-----------------|-------|--------|
| 1 | Compute cost per tenant container at the target solve cadence | Benchmark (OQ-015) | — | UNVERIFIED |
| 2 | Vendor API request quotas per site (each cloud vendor) | Vendor developer terms (OQ-005) | — | UNVERIFIED |
| 3 | Program capacity minimums for the first target program | Program primary source (OQ-014) | — | UNVERIFIED |
| 4 | Program payment rates ($/kW or $/kWh) | Program primary source | — | UNVERIFIED |
| 5 | Certification cost and lead time (OpenADR 2.0b VEN) | OpenADR Alliance / test house | — | UNVERIFIED |
| 6 | Partner aggregator revenue share | Partner contract / quote | — | UNVERIFIED |
| 7 | Gateway hardware bill of materials per site | Supplier quotes | — | UNVERIFIED |
| 8 | Installer labor per gateway-primary site | Installer quotes | — | UNVERIFIED |
| 9 | Battery degradation cost per kWh throughput for target chemistries | Manufacturer warranty terms | — | UNVERIFIED |
| 10 | Customer acquisition cost for cloud-primary self-serve | Pilot measurement | — | UNVERIFIED |

## Required outline for the full D12

1. Method and scoring.
2. Technical, operational, regulatory, and vendor-dependency risks (≥ 8 per category or a justified smaller count).
3. Mitigations, triggers, and owners.
4. Top 10 numbers with sources.
5. Open questions · Constraint compliance · Change log.

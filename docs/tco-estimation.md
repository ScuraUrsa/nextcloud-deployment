# Total Cost of Ownership (TCO) — Nextcloud 50-User Full-Feature Deployment

**Currency:** Polish PLN (złoty)
**Date:** June 2026
**Assumptions:** All components open-source, self-hosted. 50 active users. All features enabled: SSO (Keycloak), Collabora CODE, Nextcloud Talk, Elasticsearch full-text search, Prometheus+Grafana monitoring, BorgBackup with offsite replication, ClamAV antivirus.

---

## 1. Infrastructure Sizing for 50 Users

| Resource | Allocation | Notes |
|----------|-----------|-------|
| **vCPU** | 6 total | 4 Nextcloud + 2 sidecars |
| **RAM** | 12 GB total | See breakdown below |
| **NVMe SSD** | 200 GB | OS, DB, ES, Docker, logs, buffer |
| **Bulk Storage** | 2 TB | 50 users × 40 GB average |
| **Backup Storage** | 3 TB | BorgBackup deduplicated (offsite) |
| **Bandwidth** | 100 Mbps unmetered | |

### RAM Breakdown

| Component | RAM |
|-----------|-----|
| Nextcloud PHP-FPM | 4 GB |
| PostgreSQL | 2 GB |
| Redis | 512 MB |
| Elasticsearch | 1 GB |
| Keycloak | 512 MB |
| Collabora CODE | 2 GB |
| ClamAV | 1 GB |
| OS overhead | 1 GB |
| **Total** | **12 GB** |

### SSD Breakdown (200 GB NVMe)

| Purpose | Size |
|---------|------|
| OS + base system | 30 GB |
| PostgreSQL data | 50 GB |
| Elasticsearch indices | 20 GB |
| Docker images + volumes | 20 GB |
| Logs (rotated) | 30 GB |
| Buffer / headroom | 50 GB |
| **Total** | **200 GB** |

---

## 2. Scenario A — Self-Hosted Bare Metal (Home/Office)

One-time hardware purchase amortized over 36 months. Electricity and internet are recurring.

### Hardware (One-Time, Amortized)

| Item | One-Time Cost | Monthly (÷36) |
|------|--------------|---------------|
| Server: refurbished Dell/HP Xeon E5 or new Ryzen 7 Mini PC (6+ cores, 32 GB RAM) | 2,000–4,000 PLN | ~85 PLN |
| 500 GB NVMe SSD (OS + fast data) | 300 PLN | ~8 PLN |
| 2× 4 TB NAS HDD (RAID1, bulk storage) | 1,200 PLN | ~33 PLN |
| UPS (600 VA line-interactive) | 400 PLN | ~11 PLN |
| **Hardware subtotal** | **3,900–5,900 PLN** | **~137 PLN** |

### Recurring Monthly Costs

| Item | Monthly Cost | Notes |
|------|-------------|-------|
| Electricity: ~100 W × 24h × 30d × 1.10 PLN/kWh | ~80 PLN | Average Polish residential rate |
| Internet: 100 Mbps fiber (incremental) | ~0–80 PLN | Near zero if already paying for home fiber; ~80 PLN if dedicated |
| Domain: .pl registration | ~5 PLN | dns.pl / OVH / nazwa.pl |
| TLS certificates | 0 PLN | Let's Encrypt (automated) |
| Offsite backup: Hetzner Storage Box 5 TB (BX21) | ~50 PLN | BorgBackup repo, deduplicated |
| **Recurring subtotal** | **~135 PLN** | (assuming internet already exists) |

### Scenario A Total

| Category | Monthly |
|----------|---------|
| Hardware (amortized) | ~137 PLN |
| Recurring (electricity, backup, domain) | ~135 PLN |
| **TOTAL** | **~272 PLN/mo** |
| **Per user** | **~5.44 PLN/user/mo** |

**Notes:**
- No labor cost included (self-administered).
- Hardware can last 5+ years; 36-month amortization is conservative.
- If internet is already paid for, effective cost drops to ~192 PLN/mo (~3.84 PLN/user/mo).
- UPS battery replacement every 3 years adds ~5 PLN/mo.

---

## 3. Scenario B — Hetzner Cloud

Hetzner Cloud (Nuremberg/Falkenstein/Helsinki). Prices in EUR converted at 1 EUR ≈ 4.50 PLN.

| Resource | Hetzner Product | EUR/mo | PLN/mo |
|----------|----------------|--------|--------|
| Compute: 8 vCPU, 16 GB RAM | CX41 | €40 | ~180 PLN |
| Block storage: 200 GB NVMe (local) | Included in CX41 | €0 | 0 PLN |
| Bulk storage: 2 TB Volume | Volume 2 TB | €10 | ~45 PLN |
| Offsite backup: 5 TB Storage Box | BX21 | €10 | ~45 PLN |
| Snapshots (daily, 3 retained) | ~€2 | ~10 PLN |
| Floating IP | €3.40 | ~15 PLN |
| Traffic: 20 TB included | Free | 0 PLN |
| Domain: .pl | ~€1.10 | ~5 PLN |
| TLS: Let's Encrypt | Free | 0 PLN |
| **TOTAL** | | **~€66.50** | **~300 PLN/mo** |
| **Per user** | | | **~6.00 PLN/user/mo** |

**Notes:**
- CX41 (8 vCPU, 16 GB) slightly overprovisioned vs. the 6 vCPU/12 GB target — headroom for spikes.
- 20 TB traffic is generous; 50 users rarely exceed 2–3 TB/mo.
- No long-term commitment; cancel anytime.
- Snapshots provide fast disaster recovery (not a substitute for offsite Borg backups).
- Floating IP enables zero-downtime failover if using two instances (not budgeted here).

---

## 4. Scenario C — OVH / Netcup Budget Cloud

Budget VPS providers. OVH VPS Comfort or netcup RS series. EUR at 4.50 PLN.

| Resource | Product | EUR/mo | PLN/mo |
|----------|---------|--------|--------|
| Compute: 4 vCPU, 8 GB RAM | OVH VPS Comfort / netcup RS 2000 | ~€20 | ~90 PLN |
| Bulk storage: 2 TB Object Storage | OVH Object Storage / netcup S3 | ~€10 | ~45 PLN |
| Backup: 1 TB Object Storage | OVH / netcup S3 | ~€5.50 | ~25 PLN |
| Traffic: unmetered | Included | €0 | 0 PLN |
| Domain: .pl | ~€1.10 | ~5 PLN |
| TLS: Let's Encrypt | Free | 0 PLN |
| **TOTAL** | | **~€36.60** | **~165 PLN/mo** |
| **Per user** | | | **~3.30 PLN/user/mo** |

**⚠️ Caveats:**
- **Undersized:** 4 vCPU / 8 GB RAM is below the 6 vCPU / 12 GB target. Collabora CODE and Elasticsearch will contend for resources. Acceptable for light office use; may degrade under concurrent editing + search + Talk.
- Object storage latency is higher than local NVMe/Volume — PostgreSQL and Elasticsearch must run on the VPS's local disk (typically 50–100 GB SSD included). The 200 GB NVMe requirement is partially met by the VPS local disk; bulk user files go to Object Storage via Nextcloud External Storage app.
- Backup storage reduced to 1 TB (vs. 3 TB target) — relies on Borg deduplication efficiency. May need to increase if retention is long.
- No snapshots, no floating IP — simpler but less resilient.
- **Performance-constrained.** Suitable for budget-conscious deployments where occasional slowdown is acceptable.

---

## 5. Sidecar Cost Breakdown (Shared Across All Users)

Marginal cost of each supporting service, independent of user count (fixed overhead).

| Sidecar | RAM | vCPU | Cloud Cost/mo | Bare Metal Cost/mo |
|---------|-----|------|--------------|-------------------|
| Keycloak (SSO) | 512 MB | 0.5 | ~15 PLN | ~2 PLN |
| Collabora CODE | 2 GB | 1.0 | ~30 PLN | ~4 PLN |
| Elasticsearch | 1 GB | 0.5 | ~15 PLN | ~2 PLN |
| ClamAV | 1 GB | 0.3 | ~10 PLN | ~2 PLN |
| Prometheus + Grafana | 512 MB | 0.3 | ~10 PLN | ~2 PLN |
| BorgBackup offsite storage | — | — | ~45 PLN | ~50 PLN |
| **Total sidecars** | **5 GB** | **2.6** | **~125 PLN** | **~62 PLN** |

**Notes:**
- Cloud sidecar costs are embedded in the scenario totals (CX41 covers all compute; Storage Box covers Borg).
- Bare metal sidecar costs are electricity + amortized hardware share (very low marginal cost once the server is running).
- BorgBackup offsite storage is the single largest sidecar cost in both scenarios.

---

## 6. Per-Feature Marginal Cost

What it costs to add one feature for **one additional user** (beyond the baseline Nextcloud core).

| Feature | Marginal Cost/user/mo | Rationale |
|---------|----------------------|-----------|
| +10 GB storage | ~0.50 PLN | HDD/Object Storage at ~0.05 PLN/GB/mo |
| Nextcloud Talk (HPB) | ~0.20 PLN | Light CPU for TURN/STUN; mostly bandwidth |
| Collabora CODE (online editing) | ~1.00 PLN | 2 GB RAM / 1 vCPU shared; ~30 PLN ÷ 50 users |
| Full-text search (Elasticsearch) | ~0.30 PLN | 1 GB RAM / 0.5 vCPU shared; ~15 PLN ÷ 50 |
| Photos + Recognize (AI tagging) | ~0.50 PLN | Extra CPU cycles for image recognition |
| SSO (Keycloak) | ~0.30 PLN | 512 MB / 0.5 vCPU shared; ~15 PLN ÷ 50 |
| Mail (Nextcloud Mail app) | ~0.10 PLN | IMAP proxy, negligible overhead |
| External storage (S3/NFS) | ~0 PLN | User brings own S3 bucket; Nextcloud just proxies |
| End-to-end encryption | ~0.20 PLN | CPU overhead for encrypt/decrypt operations |
| **Total Enterprise marginal** | **~3.10 PLN** | Above baseline Nextcloud core |

**Baseline Nextcloud core** (files, sharing, basic Talk, no Collabora, no ES, no SSO):
- ~2.50 PLN/user/mo on bare metal
- ~3.00 PLN/user/mo on Hetzner
- ~1.50 PLN/user/mo on OVH budget

**Full Enterprise** (all features): baseline + 3.10 PLN marginal.

---

## 7. Pricing Floor & Package Validation

### Break-Even Analysis

| Scenario | Full Enterprise Cost/user/mo | Break-Even Price |
|----------|----------------------------|-----------------|
| Bare Metal | ~5.44 PLN | ~6 PLN (10% margin) |
| Hetzner Cloud | ~6.00 PLN | ~7 PLN (15% margin) |
| OVH Budget | ~3.30 PLN | ~4 PLN (20% margin) |

### Package Pricing Validation

Assuming a managed Nextcloud hosting business with three tiers:

| Tier | Price/user/mo | Cost (Hetzner) | Margin | Multiple |
|------|--------------|----------------|--------|----------|
| **Enterprise** (all features) | 120 PLN | ~6.00 PLN | ~114 PLN | **20×** |
| **Pro** (files + Talk + Collabora) | 50 PLN | ~4.50 PLN | ~45.50 PLN | **11×** |
| **Basic** (files + sharing only) | 20 PLN | ~3.00 PLN | ~17 PLN | **6.7×** |

**Interpretation:**
- At 120 PLN Enterprise price, the infrastructure cost is only ~5% of revenue — extremely healthy margin.
- The 20× multiple comfortably covers: admin labor (~15–20 PLN/user/mo for 50 users = 1 part-time admin), support desk, growth capex, and profit.
- Even at aggressive discounting (e.g., 30 PLN Enterprise), margin remains ~5×.
- The OVH budget scenario at 3.30 PLN/user/mo enables a "freemium" or cost-leadership play at ~10 PLN/user/mo with 3× margin.

### Sensitivity: Scaling to 500 Users

| Resource | 50 Users | 500 Users | Scaling Factor |
|----------|---------|-----------|----------------|
| Compute | 6 vCPU / 12 GB | ~24 vCPU / 48 GB | ~4× (sublinear) |
| Storage | 2 TB | 20 TB | 10× (linear) |
| Backup | 3 TB | 30 TB | 10× (linear) |
| Cost/user (Hetzner) | ~6.00 PLN | ~3.50 PLN | Economies of scale |

At 500 users, per-user cost drops ~40% due to shared sidecar overhead and volume storage discounts.

---

## 8. Summary Table

| | Bare Metal | Hetzner Cloud | OVH Budget |
|---|-----------|--------------|------------|
| **Monthly total** | ~272 PLN | ~300 PLN | ~165 PLN |
| **Per user/month** | ~5.44 PLN | ~6.00 PLN | ~3.30 PLN |
| **Compute** | Owned (amortized) | CX41 (8 vCPU/16 GB) | VPS Comfort (4 vCPU/8 GB) |
| **Storage** | Local NVMe + HDD RAID1 | Volume + Storage Box | Object Storage |
| **Backup** | Hetzner BX21 offsite | Hetzner BX21 | Object Storage (1 TB) |
| **Resilience** | UPS, RAID1, offsite backup | Snapshots, offsite backup | Offsite backup only |
| **Performance** | Excellent (dedicated) | Excellent (dedicated vCPU) | Constrained (undersized) |
| **Commitment** | 3,900–5,900 PLN upfront | Monthly, cancel anytime | Monthly, cancel anytime |
| **Best for** | Long-term, full control | Balanced, professional | Budget, low expectations |

---

## 9. Recommendations

1. **For a business charging 120 PLN/user/mo:** Hetzner Cloud is the sweet spot — ~6 PLN/user/mo infrastructure cost leaves enormous margin for labor, support, and profit. The 20× multiple is rare in hosting and gives room to invest in quality.

2. **For a nonprofit / internal IT department:** Bare metal at ~5.44 PLN/user/mo is cheapest long-term (break-even vs. Hetzner at ~20 months). The upfront 4,000 PLN is recouped quickly.

3. **For a hobby project / friends & family:** OVH budget at ~3.30 PLN/user/mo is viable if you accept occasional slowdowns. Upgrade path: migrate to Hetzner when user count or expectations grow.

4. **The single largest cost driver** is offsite backup storage (~45–50 PLN/mo across all scenarios). This is non-negotiable for production use. Second-largest is compute (cloud) or electricity (bare metal).

5. **All scenarios assume self-administration.** Adding a part-time sysadmin at ~2,000 PLN/mo adds ~40 PLN/user/mo — this dominates infrastructure cost and should be the primary focus for margin planning.

---

*Generated by Hermes Agent research task. All prices are estimates based on publicly available pricing as of June 2026. Exchange rate: 1 EUR ≈ 4.50 PLN. Electricity: 1.10 PLN/kWh (Polish average).*

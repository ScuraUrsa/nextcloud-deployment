# Linux Distribution Comparison for Nextcloud Self-Hosted Deployment (50 Users)

## Executive Summary

This document evaluates four Linux distributions for hosting a full-spectrum Nextcloud deployment serving 50 users. Each distribution is scored on eight criteria relevant to Nextcloud operations, long-term maintenance, and security. **Ubuntu Server 24.04 LTS is the recommended distribution.**

---

## Distribution Profiles

### 1. Ubuntu Server 24.04 LTS (Noble Numbat)

| Attribute | Detail |
|-----------|--------|
| **Release date** | April 25, 2024 |
| **Default PHP** | **8.3** (official repos) |
| **Default PostgreSQL** | 16 |
| **Default Redis** | Available in universe repo |
| **Elasticsearch** | Not in official repos; requires Elastic APT repo |
| **Docker / Collabora CODE** | Excellent support; `docker.io` and `docker-ce` available |
| **Let's Encrypt / certbot** | Available via apt |
| **MAC framework** | AppArmor (path-based, enabled by default) |
| **Package manager** | apt / dpkg |
| **LTS lifecycle** | 5 years standard (until April 2029); up to 12 years with Ubuntu Pro (until 2036) |
| **Ansible** | First-class target; vast collection ecosystem |
| **Nextcloud community** | Largest deployment base; #1 server app on Snap Store (36K+ active installs); most tutorials and forum posts |

**Key strengths:**
- PHP 8.3 ships by default — exceeds Nextcloud 30's PHP 8.2+ requirement with no third-party repos needed.
- Ubuntu Pro extends security coverage to 12 years, the longest practical support window of any candidate.
- Largest Nextcloud community means fastest help for troubleshooting.
- `ppa:ondrej/php` available for co-installable PHP versions if future Nextcloud releases require PHP 8.4+ before Ubuntu upgrades.

**Key weaknesses:**
- AppArmor is less granular than SELinux (though easier to administer).
- Snap-based Nextcloud package exists but is not recommended for custom deployments; manual LAMP/LEMP stack is standard.

---

### 2. Debian 12 Bookworm

| Attribute | Detail |
|-----------|--------|
| **Release date** | June 10, 2023 |
| **Default PHP** | **8.2** (official repos) |
| **Default PostgreSQL** | 15 |
| **Default Redis** | Available in main repo |
| **Elasticsearch** | Not in official repos; requires Elastic APT repo |
| **Docker / Collabora CODE** | Good support; `docker.io` available |
| **Let's Encrypt / certbot** | Available via apt |
| **MAC framework** | AppArmor (path-based, enabled by default) |
| **Package manager** | apt / dpkg |
| **LTS lifecycle** | 3 years full security support (until June 10, 2026) + 2 years LTS (until June 30, 2028) = 5 years total |
| **Ansible** | First-class target; shares ecosystem with Ubuntu |
| **Nextcloud community** | Strong; many guides and active forum presence |

**Key strengths:**
- PHP 8.2 meets Nextcloud 30 minimum requirement from official repos.
- Rock-solid stability; Debian's release policy ensures thoroughly tested packages.
- Same apt ecosystem as Ubuntu; Ansible roles are highly portable between the two.
- No corporate vendor lock-in; community-governed.

**Key weaknesses:**
- **CRITICAL TIMING ISSUE:** Regular security support ends **June 10, 2026** — mere days from now (as of mid-June 2026). A new deployment would immediately enter the LTS phase with reduced security coverage and a smaller volunteer security team.
- PHP 8.2 is the minimum, not the latest; PHP 8.3+ requires `deb.sury.org` third-party repo.
- PostgreSQL 15 is one major version behind Ubuntu 24.04's PostgreSQL 16.
- Debian 13 (Trixie) is already released (August 2025), making Bookworm the "oldstable" — community attention and package updates are shifting to Trixie.

---

### 3. Rocky Linux 9 / AlmaLinux 9

| Attribute | Detail |
|-----------|--------|
| **Release date** | Rocky 9: July 2022; Alma 9: May 2022 |
| **Default PHP** | 8.0 (default AppStream); **8.1 and 8.2 available as module streams** |
| **Default PostgreSQL** | 13 (AppStream); newer versions require external PostgreSQL repo |
| **Default Redis** | 6 (AppStream); newer versions require Remi/EPEL |
| **Elasticsearch** | Not in official repos; requires Elastic RPM repo |
| **Docker / Collabora CODE** | Good support; `docker-ce` available via Docker's repo |
| **Let's Encrypt / certbot** | Available via EPEL |
| **MAC framework** | **SELinux** (label-based, enforcing by default) |
| **Package manager** | dnf / rpm |
| **LTS lifecycle** | Tracks RHEL 9 lifecycle: full support until May 2027, maintenance until **May 2032** (~10 years) |
| **Ansible** | Supported; `ansible.posix` and built-in modules work; fewer community roles than Debian/Ubuntu |
| **Nextcloud community** | Small but growing; official Rocky Linux documentation exists for Nextcloud; AlmaLinux has active Nextcloud forum threads |

**Key strengths:**
- **SELinux enforcing by default** — the most granular MAC framework, providing defense-in-depth that AppArmor cannot match. Pre-built policies exist for httpd, PostgreSQL, and PHP-FPM.
- Longest support lifecycle (~10 years, until 2032) — ideal for "set and forget" enterprise deployments.
- RHEL compatibility means enterprise-grade stability and extensive third-party vendor support.
- DNF module streams allow switching PHP versions without third-party repos (8.0 → 8.1 → 8.2).

**Key weaknesses:**
- PHP 8.2 is available but **not the default**; requires explicit module stream enablement (`dnf module enable php:8.2`). PHP 8.3+ requires the **Remi third-party repo** — a dependency on an external maintainer.
- PostgreSQL 13 is the AppStream default — two major versions behind Ubuntu's 16. Newer PostgreSQL requires the official PostgreSQL RPM repo (external).
- Redis 6 is the AppStream default; Redis 7+ requires Remi or EPEL.
- SELinux adds administrative complexity; misconfigured policies are a common source of "it works on Ubuntu but not on RHEL" issues.
- Smaller Nextcloud-specific community means fewer pre-built Ansible roles and troubleshooting resources.

---

### 4. openSUSE Leap 15.6

| Attribute | Detail |
|-----------|--------|
| **Release date** | June 12, 2024 |
| **Default PHP** | **8.2** |
| **Default PostgreSQL** | 16 |
| **Default Redis** | 7.2 |
| **Elasticsearch** | Not in official repos |
| **Docker / Collabora CODE** | Good support |
| **Let's Encrypt / certbot** | Available |
| **MAC framework** | AppArmor (enabled by default) |
| **Package manager** | zypper / rpm |
| **LTS lifecycle** | **18 months — EOL December 2025** (already past) |
| **Ansible** | Supported (`community.general.zypper`); limited community content |
| **Nextcloud community** | Very small; official Nextcloud package in repos is outdated (v24.0.8); Reddit threads report compatibility issues |

**Key strengths:**
- Ships modern package versions: PHP 8.2, PostgreSQL 16, Redis 7.2 — all from official repos.
- YaST provides a graphical administration tool (niche benefit).
- SUSE Package Hub extends available packages.
- Based on SUSE Linux Enterprise (SLE) source, providing enterprise-grade stability.

**Key weaknesses:**
- **HARD DEAL-BREAKER: End of Life was December 2025.** No further security updates. Running this in production is indefensible.
- Leap 15.6 is the **final release in the 15.x series**; the future is Leap 16 (based on Adaptable Linux Platform), which is a significant architectural shift.
- Smallest Nextcloud community; few guides, few forum posts, outdated official package.
- Least Ansible community content; zypper-based roles are rare and less tested.
- Package ecosystem is the smallest of the four candidates.

---

## Scored Comparison Table

Each criterion is scored **1 (worst) to 5 (best)**.

| # | Criterion | Ubuntu 24.04 LTS | Debian 12 Bookworm | Rocky/Alma 9 | openSUSE Leap 15.6 |
|---|-----------|:---:|:---:|:---:|:---:|
| 1 | **PHP 8.2+ package availability** | **5** | 4 | 3 | 4 |
| 2 | **Security update cadence** | **5** | 4 | 4 | 2 |
| 3 | **Ansible module support** | **5** | **5** | 3 | 2 |
| 4 | **Community Nextcloud deployment prevalence** | **5** | 4 | 2 | 1 |
| 5 | **SELinux/AppArmor policy availability** | 4 | 4 | **5** | 3 |
| 6 | **Package ecosystem breadth** | **5** | **5** | 3 | 3 |
| 7 | **Long-term support lifecycle** | **5** | 3 | **5** | 1 |
| 8 | **Ease of administration** | **5** | 4 | 3 | 2 |
| | **TOTAL (max 40)** | **39** | **33** | **28** | **18** |

### Criterion Details

#### 1. PHP 8.2+ Package Availability
Nextcloud 30 requires PHP 8.2 or newer. Scoring reflects whether PHP 8.2+ is available from **official distribution repositories** without third-party repos.

- **Ubuntu 24.04 (5):** Ships PHP 8.3 by default. Exceeds the requirement. No third-party repo needed. `ppa:ondrej/php` available as a well-trusted option for co-installable future versions.
- **Debian 12 (4):** Ships PHP 8.2 by default. Meets the minimum requirement exactly. PHP 8.3+ requires `deb.sury.org` (third-party, but well-maintained by the same maintainer as `ppa:ondrej`).
- **Rocky/Alma 9 (3):** PHP 8.2 is available as an AppStream module stream but is **not the default** (default is 8.0). Requires explicit `dnf module enable php:8.2`. PHP 8.3+ requires the Remi third-party repo.
- **openSUSE Leap 15.6 (4):** Ships PHP 8.2 by default. Meets the minimum requirement. PHP 8.3+ availability is limited.

#### 2. Security Update Cadence
How quickly are CVEs patched and distributed?

- **Ubuntu 24.04 (5):** Canonical's dedicated security team provides fast CVE response. Ubuntu Pro offers extended security maintenance for universe packages. Well-documented security notice system (USNs).
- **Debian 12 (4):** Debian Security Team is responsive but volunteer-driven. LTS phase (starting June 2026) has a separate, smaller team with reduced coverage. Security coverage is narrowing right now.
- **Rocky/Alma 9 (4):** Tracks RHEL security errata. Good cadence but there is an inherent rebuild lag (hours to days) behind Red Hat's published fixes. AlmaLinux has sometimes been faster than Rocky at rebuilds.
- **openSUSE Leap 15.6 (2):** EOL was December 2025. No new security patches are being issued. Score of 2 (not 1) only because existing patches up to EOL are available.

#### 3. Ansible Module Support
Availability of well-maintained Ansible collections and community roles.

- **Ubuntu 24.04 (5):** The most-targeted distribution in Ansible Galaxy and community roles. `ansible.builtin.apt` is the most-tested package module. Vast collection of Nextcloud-specific playbooks target Ubuntu.
- **Debian 12 (5):** Shares the apt ecosystem with Ubuntu. Most Ubuntu-targeted roles work on Debian with minimal changes. Equally strong Ansible support.
- **Rocky/Alma 9 (3):** `ansible.builtin.dnf` works well, but community roles targeting RHEL-family for Nextcloud are far fewer. SELinux context management adds Ansible complexity.
- **openSUSE Leap 15.6 (2):** `community.general.zypper` exists but is less tested. Very few Nextcloud playbooks target openSUSE. Most roles would need significant adaptation.

#### 4. Community Nextcloud Deployment Prevalence
How many people run Nextcloud on this distribution? Affects troubleshooting resources, forum help, and guide availability.

- **Ubuntu 24.04 (5):** Dominant platform. #1 server app on Ubuntu Snap Store. Vast majority of Nextcloud installation guides target Ubuntu. Largest forum presence.
- **Debian 12 (4):** Strong second. Many guides (howtoforge, digitalocean, etc.) cover Debian. Active forum community.
- **Rocky/Alma 9 (2):** Small but growing. Official Rocky Linux documentation includes a Nextcloud guide. AlmaLinux has active forum threads. Still a minority platform.
- **openSUSE Leap 15.6 (1):** Very few deployments. Official Nextcloud package is outdated (v24.0.8). Reddit threads report compatibility issues. Minimal community resources.

#### 5. SELinux/AppArmor Policy Availability
Availability of pre-built Mandatory Access Control policies for web/database stacks.

- **Ubuntu 24.04 (4):** AppArmor is enabled by default with profiles for common services. Easier to administer than SELinux. Less granular — path-based rather than label-based.
- **Debian 12 (4):** Same AppArmor framework as Ubuntu. Similar profile coverage.
- **Rocky/Alma 9 (5):** SELinux enforcing by default. Label-based MAC provides the most granular security. Pre-built policies exist for `httpd`, `postgresql`, `redis`, and PHP-FPM. The gold standard for defense-in-depth. However, complexity is higher.
- **openSUSE Leap 15.6 (3):** AppArmor enabled by default. Less community policy work than Ubuntu/Debian.

#### 6. Package Ecosystem Breadth
Are Redis, PostgreSQL, Elasticsearch, coturn, and other Nextcloud dependencies readily available?

- **Ubuntu 24.04 (5):** Largest ecosystem. Universe repo + PPAs + Snaps. PostgreSQL 16, Redis, MariaDB, coturn all in official repos. Elasticsearch via Elastic's APT repo (well-documented).
- **Debian 12 (5):** ~59,000 packages in main/contrib/non-free. PostgreSQL 15, Redis, MariaDB, coturn all available. Elasticsearch via Elastic's APT repo.
- **Rocky/Alma 9 (3):** AppStream + BaseOS + EPEL provide core packages, but versions lag (PostgreSQL 13, Redis 6). Newer versions require multiple external repos (PostgreSQL official repo, Remi, EPEL). Elasticsearch via Elastic's RPM repo.
- **openSUSE Leap 15.6 (3):** Package Hub extends the base. PostgreSQL 16 and Redis 7.2 are current. Overall ecosystem is smaller. Elasticsearch requires external repo.

#### 7. Long-Term Support Lifecycle
How long will the OS receive security updates?

- **Ubuntu 24.04 (5):** 5 years standard (until April 2029). Ubuntu Pro extends to 10 years (2034) for main, 12 years (2036) with Legacy Support add-on. Free Pro subscription for up to 5 machines.
- **Debian 12 (3):** 5 years total, but regular security support ends **June 10, 2026** (days away). LTS phase (June 2026–June 2028) has reduced coverage and a volunteer team. Debian 13 (Trixie) is already the current stable release.
- **Rocky/Alma 9 (5):** Tracks RHEL 9 lifecycle. Full support until May 2027, maintenance support until **May 2032**. ~10 years of coverage. The longest of any candidate.
- **openSUSE Leap 15.6 (1):** EOL was **December 2025**. No further updates. This alone disqualifies it for any production deployment.

#### 8. Ease of Administration
Package manager quality, documentation, and overall administrative experience.

- **Ubuntu 24.04 (5):** apt is familiar to most administrators. Vast documentation (official + community). Largest StackOverflow/forum presence. Straightforward LAMP/LEMP setup.
- **Debian 12 (4):** Same apt ecosystem. Excellent documentation (Debian Administrator's Handbook). Slightly less hand-holding than Ubuntu; expects more administrator knowledge.
- **Rocky/Alma 9 (3):** dnf is modern and capable. SELinux adds significant administrative overhead (policy debugging, context labeling). Less Nextcloud-specific documentation. RHEL documentation is excellent but often paywalled.
- **openSUSE Leap 15.6 (2):** zypper is capable but less familiar to most admins. YaST is a unique GUI tool. Smallest community for troubleshooting. Least Nextcloud-specific documentation.

---

## Deal-Breakers

| Distribution | Deal-Breaker | Severity |
|-------------|-------------|----------|
| **openSUSE Leap 15.6** | EOL December 2025. No security updates. | **FATAL** — Cannot be used in production. |
| **Debian 12 Bookworm** | Regular security support ends June 10, 2026 (days away). New deployment enters LTS phase immediately with reduced coverage. Debian 13 is already stable. | **HIGH** — Viable only if upgrading to Debian 13 within weeks. |
| **Rocky/Alma 9** | PHP 8.2 is not default; PHP 8.3+ requires Remi (third-party). PostgreSQL 13 and Redis 6 are defaults (old). Multiple external repos needed for modern stack. | **MEDIUM** — Workable but adds dependency risk and administrative complexity. |
| **Ubuntu 24.04 LTS** | No deal-breakers. | **NONE** |

---

## Recommendation

### Primary Recommendation: Ubuntu Server 24.04 LTS

**Total score: 39/40**

Ubuntu Server 24.04 LTS is the clear winner across all evaluated criteria. It is the only distribution with **zero deal-breakers** and the highest score in 6 of 8 categories.

**Justification:**

1. **PHP 8.3 by default** — exceeds Nextcloud 30's PHP 8.2+ requirement with no third-party repos. The `ppa:ondrej/php` repository (maintained by a Debian developer) provides a well-trusted path to PHP 8.4+ when future Nextcloud versions require it.

2. **Longest practical support window** — 5 years standard, extendable to 12 years with Ubuntu Pro (free for up to 5 machines). This means the OS will outlive multiple Nextcloud major version upgrades.

3. **Largest Nextcloud community** — the most guides, forum posts, Ansible playbooks, and troubleshooting resources. When something breaks at 2 AM, you will find answers fastest on Ubuntu.

4. **Best Ansible support** — the vast majority of Nextcloud Ansible roles and collections target Ubuntu/Debian. Minimal adaptation needed.

5. **Modern package versions** — PostgreSQL 16, Redis 7.x, and PHP 8.3 all from official repos. Only Elasticsearch requires an external repo (Elastic's official APT repo, which is well-maintained).

6. **No timing pressure** — unlike Debian 12 (security support ending now) and openSUSE Leap 15.6 (already EOL), Ubuntu 24.04 has years of full support ahead.

### Secondary Recommendation: Rocky Linux 9 / AlmaLinux 9

**Total score: 28/40**

If SELinux enforcement is a **hard organizational requirement** (e.g., government, defense, or strict compliance environments), Rocky/Alma 9 is the appropriate choice. Its ~10-year support lifecycle and SELinux enforcing-by-default posture are unmatched. However, be prepared for:
- Enabling PHP 8.2 module stream explicitly
- Adding the Remi repo for PHP 8.3+ (when needed)
- Adding the official PostgreSQL repo for PostgreSQL 16+
- Investing time in SELinux policy management
- Adapting Ubuntu/Debian-oriented Ansible playbooks

### Not Recommended

- **Debian 12 Bookworm:** Too late in its lifecycle for a new deployment. If Debian is preferred, deploy **Debian 13 Trixie** (released August 2025) instead — it was not in the evaluation scope but would score similarly to Ubuntu 24.04.
- **openSUSE Leap 15.6:** EOL. Do not use. If openSUSE is preferred, evaluate **openSUSE Leap 16** when it stabilizes, or use **openSUSE Tumbleweed** (rolling release, not recommended for production servers).

---

## Summary Table: Key Package Versions

| Package | Ubuntu 24.04 | Debian 12 | Rocky/Alma 9 | openSUSE Leap 15.6 |
|---------|:---:|:---:|:---:|:---:|
| PHP (default) | **8.3** | 8.2 | 8.0 (8.2 via module) | 8.2 |
| PHP 8.3+ without third-party | **Yes** | No (needs sury) | No (needs Remi) | No |
| PostgreSQL (default) | **16** | 15 | 13 | **16** |
| Redis (default) | 7.x | 7.x | 6 | **7.2** |
| Elasticsearch in official repos | No | No | No | No |
| certbot / Let's Encrypt | Yes | Yes | Yes (EPEL) | Yes |
| Docker | Yes | Yes | Yes | Yes |
| MAC framework | AppArmor | AppArmor | **SELinux** | AppArmor |
| Support end | **Apr 2029 (2036 w/Pro)** | Jun 2028 (LTS) | **May 2032** | Dec 2025 (EOL) |

---

## Next Steps

1. Copy this file to the target repository at `docs/distribution-selection.md`:
   ```
   cp /tmp/hermes-research-2-distribution.md /home/ubuntu/nextcloud-deployment/docs/distribution-selection.md
   ```

2. Proceed with Ubuntu Server 24.04 LTS as the base OS for the Nextcloud deployment playbook.

3. If organizational policy mandates SELinux, pivot to Rocky Linux 9 or AlmaLinux 9 and account for the additional repository and policy configuration work.

---

*Research conducted: June 14, 2026. Package versions reflect current state as of this date.*

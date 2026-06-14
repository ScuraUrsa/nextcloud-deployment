# Nextcloud 3-Tier Feature Packaging & Monetization Model

> **Target Repository**: `/home/ubuntu/nextcloud-deployment` (ScuraUrsa/nextcloud-deployment)
> **Output File**: `docs/packaging-monetization.md`
> **Date**: 2026-06-14
> **Scope**: Commercially viable 3-tier feature packaging, pricing rationale, billing enforcement architecture, feature separability matrix, and revenue projections for a 50-user self-hosted Nextcloud instance using only open-source components.

---

## Table of Contents

1. [Tier Structure & Pricing](#1-tier-structure--pricing)
2. [Pricing Rationale](#2-pricing-rationale)
3. [Billing Enforcement Architecture](#3-billing-enforcement-architecture)
4. [Feature Separability Matrix](#4-feature-separability-matrix)
5. [Revenue Projections](#5-revenue-projections)
6. [Implementation Roadmap](#6-implementation-roadmap)

---

## 1. Tier Structure & Pricing

All prices in Polish PLN (złoty), monthly per user. All components open-source and self-hosted.

### Tier 1: Basic — 20 PLN/user/month

**Target user**: Individual who needs secure file storage and basic sync. Light collaboration consumer.

| Feature Category | Included Features |
|-----------------|-------------------|
| **Storage** | 10 GB per user |
| **File Sync & Share** | WebDAV sync, desktop/mobile clients, chunked uploads, public/private shares, share links with password/expiry |
| **Versioning** | 30-day retention (auto-purge older versions) |
| **Trashbin** | 30-day retention (auto-purge deleted files) |
| **Activity Stream** | User activity feed (90-day retention) |
| **Notifications** | Email notifications (SMTP) |
| **Calendar** | Read-only CalDAV access (view shared calendars; cannot create/edit events) |
| **Contacts** | Read-only CardDAV access (view shared address books; cannot create/edit contacts) |
| **Security** | TOTP 2FA (Time-based One-Time Password), password policy enforcement |
| **Antivirus** | ClamAV on-access scanning (shared infrastructure, all files scanned) |
| **Support** | Community forum + email ticket (best-effort, 24h response target) |

**Excluded (upsell to Pro/Enterprise)**: Talk, Deck, Notes, Mail, Calendar/Contacts full access, Forms, Polls, Collabora, ONLYOFFICE, Photos+Recognize, Music, News, Bookmarks, Maps, Social, External Storage, Full-text Search, Encryption, LDAP, File ACLs, WebAuthn, SSO, Push Notifications, SLA.

---

### Tier 2: Pro — 50 PLN/user/month

**Target user**: Professional knowledge worker. Needs full collaboration suite, communication tools, and productivity apps.

| Feature Category | Included Features |
|-----------------|-------------------|
| **Storage** | 50 GB per user |
| **Everything in Basic** | All Basic features, plus: |
| **Calendar** | Full CalDAV access — create/edit events, scheduling (free/busy), resource booking, email invitations |
| **Contacts** | Full CardDAV access — create/edit contacts, Circles (custom groups), system address book |
| **Nextcloud Talk** | Text chat, voice/video calls, screen sharing — up to 10 participants per call (HPB-backed) |
| **Deck** | Kanban boards, card assignments, due dates, attachments, calendar integration |
| **Notes** | Markdown editor, category tagging, WebDAV sync |
| **Mail** | Web-based IMAP/SMTP client — 1 email account per user, Sieve filtering, PGP support |
| **Forms** | Survey creation, share via link, CSV export |
| **Polls** | Voting, date polling, anonymous polls, calendar integration |
| **Security** | WebAuthn 2FA (FIDO2/Passkeys), TOTP 2FA, SSO via Keycloak (SAML 2.0 + OpenID Connect) |
| **Notifications** | Email + Push notifications (Notify Push service for instant mobile alerts) |
| **Support** | Email ticket with 8h response target (business hours) |

**Excluded (upsell to Enterprise)**: Talk unlimited participants, Collabora, ONLYOFFICE, Photos+Recognize, Music, News, Bookmarks, Maps, Social, External Storage, Full-text Search, Encryption, LDAP, File ACLs, Retention Policies, U2F 2FA, SLA 4h.

---

### Tier 3: Enterprise — 120 PLN/user/month

**Target user**: Power user, executive, or compliance-required role. Full platform access with advanced security, administration, and premium support.

| Feature Category | Included Features |
|-----------------|-------------------|
| **Storage** | 250 GB per user |
| **Everything in Pro** | All Pro features, plus: |
| **Nextcloud Talk** | Unlimited participants (full HPB: signaling + NATS + Janus WebRTC gateway), SIP bridge, federation |
| **Collabora Online** | Full office suite (Writer, Calc, Impress) — browser-based editing via CODE server |
| **ONLYOFFICE** | Alternative office suite — better .docx/.xlsx/.pptx fidelity, coexists with Collabora |
| **Photos + Recognize** | Photo gallery with timeline, albums, AI face/object recognition (on-premises), EXIF extraction |
| **Music** | Audio streaming, playlists, Ampache API for external players |
| **News** | RSS/Atom feed reader, folder organization, full-text article search |
| **Bookmarks** | Tagged bookmark storage, dead link detection, browser extension |
| **Maps** | Geolocation from photos, GPX tracks, OpenStreetMap tiles |
| **Social** | Federated social networking via ActivityPub (Mastodon/Pleroma interop) |
| **External Storage** | Mount S3, SFTP, SMB/CIFS, Google Drive, Dropbox, SharePoint, WebDAV, FTP as folders |
| **Full-text Search** | Elasticsearch-backed search across all files, comments, tags |
| **Encryption** | Server-Side Encryption (AES-256-GCM) at rest; End-to-End Encryption (client-side) |
| **LDAP Integration** | LDAP/Active Directory user backend (hybrid with Keycloak SSO) |
| **File Access Control** | Advanced ACLs (per-file, per-group permissions beyond standard shares) |
| **Retention Policies** | Automated file retention/deletion policies (compliance) |
| **Security** | U2F 2FA (hardware security keys), WebAuthn, TOTP, SSO, brute-force protection, suspicious login detection |
| **Support** | SLA: 4-hour response, 24/7, phone + email + ticket, priority queue |

---

### Tier Comparison Summary

| Dimension | Basic (20 PLN) | Pro (50 PLN) | Enterprise (120 PLN) |
|-----------|---------------|-------------|----------------------|
| Storage | 10 GB | 50 GB | 250 GB |
| File Sync/Share | Full | Full | Full |
| Versioning | 30 days | 30 days | 30 days |
| Trashbin | 30 days | 30 days | 30 days |
| Calendar | Read-only | Full | Full |
| Contacts | Read-only | Full | Full |
| Talk | — | 10 participants | Unlimited + SIP |
| Office Suite | — | — | Collabora + ONLYOFFICE |
| Mail | — | 1 account | 1 account |
| Deck/Notes/Forms/Polls | — | Full | Full |
| Photos+Recognize | — | — | Full |
| Music/News/Bookmarks/Maps/Social | — | — | Full |
| External Storage | — | — | Full |
| Full-text Search | — | — | Elasticsearch |
| Encryption | — | — | SSE + E2EE |
| 2FA | TOTP | TOTP + WebAuthn | TOTP + WebAuthn + U2F |
| SSO | — | Keycloak SAML/OIDC | Keycloak SAML/OIDC |
| LDAP | — | — | Full |
| File ACLs | — | — | Advanced |
| Antivirus | Shared | Shared | Shared |
| Support | Best-effort 24h | 8h business hours | SLA 4h 24/7 |

---

## 2. Pricing Rationale

### 2.1 Cost-Plus Analysis

Infrastructure cost baseline from the TCO analysis (see `/tmp/hermes-research-6-tco.md`):

| Scenario | Total Monthly Cost | Per-User Cost |
|----------|-------------------|---------------|
| Bare Metal (self-hosted) | ~272 PLN | ~5.44 PLN |
| Hetzner Cloud (CX41) | ~300 PLN | ~6.00 PLN |
| OVH Budget (VPS Comfort) | ~165 PLN | ~3.30 PLN |

**Recommended baseline**: Hetzner Cloud at ~6.00 PLN/user/mo — best balance of performance, reliability, and cost predictability.

**Per-feature marginal costs** (from TCO analysis, Section 6):

| Feature | Marginal Cost/user/mo | Included In |
|---------|----------------------|-------------|
| Baseline Nextcloud core (files, sharing, basic auth) | ~3.00 PLN | All tiers |
| +10 GB storage increment | ~0.50 PLN | Tier differentiation |
| Nextcloud Talk (HPB) | ~0.20 PLN | Pro, Enterprise |
| Collabora CODE (online editing) | ~1.00 PLN | Enterprise |
| Full-text search (Elasticsearch) | ~0.30 PLN | Enterprise |
| Photos + Recognize (AI tagging) | ~0.50 PLN | Enterprise |
| SSO (Keycloak) | ~0.30 PLN | Pro, Enterprise |
| Mail (Nextcloud Mail app) | ~0.10 PLN | Pro, Enterprise |
| End-to-end encryption | ~0.20 PLN | Enterprise |
| ONLYOFFICE Document Server | ~0.80 PLN | Enterprise |
| **Total Enterprise marginal** | **~3.10 PLN** | Above baseline |

**Cost-plus tier breakdown**:

| Tier | Infrastructure Cost/user | Admin Labor/user* | Total Cost/user | Price | Margin (PLN) | Margin (%) |
|------|-------------------------|-------------------|-----------------|-------|---------------|------------|
| Basic | ~3.00 PLN | ~5.00 PLN | ~8.00 PLN | 20 PLN | 12 PLN | 60% |
| Pro | ~4.00 PLN | ~7.00 PLN | ~11.00 PLN | 50 PLN | 39 PLN | 78% |
| Enterprise | ~6.00 PLN | ~10.00 PLN | ~16.00 PLN | 120 PLN | 104 PLN | 87% |

*\*Admin labor: estimated at 1 part-time sysadmin (~2,000 PLN/mo) distributed across users. Basic users require less support; Enterprise users require more (SLA, LDAP troubleshooting, encryption key recovery).*

**Key insight**: The 20× multiple on Enterprise tier (120 PLN price vs. ~6 PLN infrastructure cost) is sustainable because:
- Infrastructure is only ~5% of revenue — the real cost is labor, support, and expertise
- Enterprise users pay for trust, compliance, and guaranteed response times — not raw compute
- The margin funds continuous improvement, security patching, and backup verification

### 2.2 Competitive Analysis

#### Direct Competitors

| Competitor | Product | Price/user/mo (PLN) | Notes |
|------------|---------|---------------------|-------|
| **Nextcloud Enterprise (official)** | Enterprise Basic (100 users min) | ~13.50 PLN (€36/user/year ÷ 12) | Minimum 100 users; proprietary license; includes support portal, enterprise apps, SLA |
| **tab.digital** | Nextcloud hosting (50 users) | ~27 PLN (€5.95/mo) | Managed Nextcloud; all features; German hosting |
| **Hetzner Storage Share** | Managed Nextcloud (NX11) | ~19 PLN (€4.29/mo) for 1 TB shared | No per-user pricing; shared storage pool; limited app control; no SSO, no Collabora, no Talk HPB |
| **Hetzner Storage Share** | Managed Nextcloud (NX31) | ~123 PLN (€27.39/mo) for 10 TB shared | Same limitations as NX11; just more storage |

**Positioning vs. official Nextcloud Enterprise**:
- Our Enterprise tier (120 PLN) is ~9× more expensive than official Enterprise Basic (~13.50 PLN)
- BUT: official Enterprise requires 100-user minimum (our target is 50), and our price includes the full infrastructure, not just the license
- Official Enterprise is a software subscription; we provide a fully managed service
- For organizations under 100 users, official Enterprise is not available — we capture that market

#### Indirect Competitors (Cloud Office Suites)

| Competitor | Product | Price/user/mo (PLN) | Key Features |
|------------|---------|---------------------|--------------|
| **Google Workspace** | Business Starter | ~25 PLN | 30 GB pooled storage, Gmail, Meet (100 participants), Calendar, Docs/Sheets/Slides |
| **Google Workspace** | Business Standard | ~50 PLN | 2 TB pooled storage, Meet recordings, appointment scheduling, shared drives |
| **Google Workspace** | Business Plus | ~76 PLN | 5 TB pooled, eDiscovery, retention, advanced endpoint management |
| **Microsoft 365** | Business Basic | ~25 PLN | 1 TB OneDrive, Teams, Exchange 50 GB, web Office apps only |
| **Microsoft 365** | Business Standard | ~50-60 PLN | 1 TB OneDrive, desktop Office apps, Teams, Exchange, SharePoint |
| **Microsoft 365** | Business Premium | ~87 PLN | All Standard + Intune, Azure Information Protection, Defender |

**Positioning vs. Google/Microsoft**:

| Our Tier | Price | Closest Competitor | Competitor Price | Our Advantage |
|----------|-------|--------------------|------------------|---------------|
| Basic (20 PLN) | 20 PLN | Google Business Starter | 25 PLN | 20% cheaper; data sovereignty; no AI training on your files; GDPR-compliant EU hosting |
| Pro (50 PLN) | 50 PLN | Google Business Standard / M365 Business Standard | 50-60 PLN | Price parity; full data control; no vendor lock-in; open-source stack; customizable |
| Enterprise (120 PLN) | 120 PLN | Google Business Plus / M365 Business Premium | 76-87 PLN | 38-58% premium justified by: on-premises AI (Recognize, no data leaves server), full encryption (SSE+E2EE), hardware 2FA (U2F), SLA 4h, no US CLOUD Act exposure |

**Competitive moat**: Our offering is not competing on price alone. The value proposition is:
1. **Data sovereignty**: All data stays on EU servers (Hetzner Nuremberg/Falkenstein/Helsinki). No US CLOUD Act exposure. No AI training on customer data.
2. **Open-source transparency**: Every component is auditable. No black-box proprietary code.
3. **No vendor lock-in**: Export all data via standard protocols (WebDAV, CalDAV, CardDAV, IMAP). Migrate away at any time.
4. **GDPR compliance by architecture**: Encryption at rest, on-premises AI, EU-only data centers.
5. **Customizability**: Add/remove apps, configure retention policies, integrate with existing LDAP/AD.

### 2.3 Storage Cost Breakdown

Storage is the primary tier differentiator. Cost analysis:

| Storage Tier | GB/user | Total GB (50 users) | Storage Type | Cost/GB/mo | Total Storage Cost/mo |
|-------------|---------|---------------------|--------------|------------|----------------------|
| Basic (10 GB) | 10 | 500 GB | Hetzner Volume (€0.044/GB) | ~0.20 PLN | ~100 PLN |
| Pro (50 GB) | 50 | 2,500 GB | Hetzner Volume | ~0.20 PLN | ~500 PLN |
| Enterprise (250 GB) | 250 | 12,500 GB | Hetzner Volume + Storage Box | ~0.15 PLN (volume discount) | ~1,875 PLN |

At 50 users with mixed tiers (20 Basic + 20 Pro + 10 Enterprise = 5,500 GB total), storage cost is ~1,100 PLN/mo — well within the ~2,600 PLN/mo revenue.

### 2.4 Price Anchoring Strategy

The tier structure uses classic SaaS price anchoring:

- **Basic at 20 PLN**: Entry point. Low enough to attract individuals and small teams. The read-only Calendar/Contacts creates natural friction that drives upgrades.
- **Pro at 50 PLN**: The "best value" anchor. 2.5× Basic price for 5× storage + full collaboration suite. Most users should land here.
- **Enterprise at 120 PLN**: Premium anchor. Makes Pro look affordable by comparison. Captures high-value users who need compliance, encryption, and SLA.

The 20 → 50 → 120 progression follows a ~2.5× multiplier between tiers, which is standard in B2B SaaS (Salesforce, Slack, Zoom all use similar ratios).

---

## 3. Billing Enforcement Architecture

All components are open-source and self-hosted. No proprietary SaaS dependencies in the billing pipeline.

### 3.1 Component Stack

```
┌─────────────────────────────────────────────────────────────┐
│                    BILLING ARCHITECTURE                       │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────┐    ┌──────────────┐    ┌───────────────┐      │
│  │  Lago    │    │ BTCPay Server │    │ InvoicePlane  │      │
│  │ (AGPL)   │    │    (MIT)      │    │    (MIT)      │      │
│  │          │    │               │    │               │      │
│  │ Subscrip-│    │ Payment       │    │ PDF Invoice   │      │
│  │ tion mgmt│    │ Processing    │    │ Generation    │      │
│  │ Plans    │    │ Bitcoin+      │    │ Recurring     │      │
│  │ Usage    │    │ Lightning     │    │ Templates     │      │
│  │ Tracking │    │ Webhooks      │    │ Tax handling  │      │
│  │ Invoicing│    │               │    │               │      │
│  └────┬─────┘    └──────┬───────┘    └───────┬───────┘      │
│       │                 │                    │               │
│       └────────┬────────┴────────────────────┘               │
│                │                                             │
│         ┌──────▼──────┐                                      │
│         │  Webhook    │                                      │
│         │  Dispatcher │  (Python/Flask, custom)              │
│         │  + Ansible  │                                      │
│         └──────┬──────┘                                      │
│                │                                             │
│    ┌───────────┼───────────┐                                 │
│    │           │           │                                 │
│ ┌──▼───┐  ┌───▼────┐  ┌──▼──────┐                           │
│ │Keycloak│ │Nextcloud│  │Notification│                        │
│ │(SSO)   │ │(Features│  │(Email to   │                        │
│ │Group   │ │ + Quota)│  │user)       │                        │
│ │Assign. │ │         │  │            │                        │
│ └───────┘  └────────┘  └───────────┘                         │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 Component Details

#### Lago (AGPL-3.0) — Subscription Management

**Repository**: `github.com/getlago/lago`
**Role**: Central billing brain. Manages plan definitions, customer subscriptions, usage tracking, and invoice generation.

**Key capabilities used**:
- **Plan definitions**: Three billable metrics (storage_gb, talk_participants, support_sla) with tiered pricing
- **Subscription lifecycle**: Trial → Active → Past Due → Canceled → Archived
- **Usage tracking**: API endpoint for Nextcloud to report per-user storage consumption, Talk participant counts
- **Invoice generation**: Calculates charges, applies taxes (23% VAT in Poland), generates invoice JSON
- **Webhook emissions**: `subscription.started`, `subscription.terminated`, `invoice.paid`, `invoice.payment_failed`, `subscription.overdue`
- **Dunning management**: Configurable overdue steps with actions

**Deployment**: Docker container alongside Nextcloud. PostgreSQL backend (shared with Nextcloud DB server, separate database `lago`). API accessible only from internal network.

**Plan configuration example** (Lago API):
```json
{
  "plan": {
    "name": "Pro",
    "code": "pro_monthly",
    "interval": "monthly",
    "amount_cents": 5000,
    "amount_currency": "PLN",
    "charges": [
      {
        "billable_metric_code": "storage_gb",
        "charge_model": "volume",
        "properties": {
          "volume_ranges": [
            {"from_value": 0, "to_value": 50, "flat_amount": "0"},
            {"from_value": 50, "to_value": null, "per_unit_amount": "0.50"}
          ]
        }
      }
    ]
  }
}
```

#### BTCPay Server (MIT) — Payment Processing

**Repository**: `github.com/btcpayserver/btcpayserver`
**Role**: Self-hosted payment gateway. Processes Bitcoin on-chain and Lightning Network payments. Emits webhooks on payment confirmation.

**Key capabilities used**:
- **Bitcoin on-chain**: Standard BTC payments with configurable confirmation requirements (1 confirmation for subscriptions)
- **Lightning Network**: Instant, near-zero-fee payments via LND or c-lightning
- **Webhooks**: `InvoiceReceivedPayment`, `InvoicePaymentSettled`, `InvoiceProcessing`, `InvoiceExpired`
- **Greenfield API**: REST API for creating invoices, checking payment status
- **Point of Sale**: Optional — can generate payment pages for manual invoice payment
- **Crowdfund**: Optional — for annual pre-payment campaigns

**Deployment**: Docker (BTCPay Server includes Bitcoin node + Lightning node). Requires ~600 GB disk for full Bitcoin node (pruned to ~10 GB acceptable for payment-only use). Alternatively, use BTCPay Server in "light" mode connecting to an external Bitcoin node.

**Payment flow**:
1. Lago generates invoice → InvoicePlane creates PDF
2. BTCPay Server creates payment request (Lightning invoice or on-chain address)
3. Customer pays via Bitcoin/Lightning wallet
4. BTCPay Server confirms payment → webhook to Lago
5. Lago marks invoice as paid → webhook to Ansible provisioner

#### InvoicePlane (MIT) — PDF Invoice Generation

**Repository**: `github.com/InvoicePlane/InvoicePlane`
**Role**: Generates professional PDF invoices with proper tax handling, recurring invoice templates, and payment tracking.

**Key capabilities used**:
- **Recurring invoices**: Monthly subscription invoices generated automatically
- **PDF generation**: Professional templates with company logo, VAT ID, line items
- **Tax handling**: 23% Polish VAT, reverse charge for EU B2B, tax-exempt for non-EU
- **Payment tracking**: Manual marking of bank transfers as paid
- **Multi-currency**: PLN primary, EUR for EU customers
- **Email delivery**: Send PDF invoices directly to customer email
- **Client portal**: Customers can view invoice history

**Integration**: Lago triggers InvoicePlane via API to generate PDF when invoice is created. InvoicePlane stores invoice PDFs and provides customer-facing portal.

### 3.3 Webhook Flow — Subscription Lifecycle

```
STEP 1: SIGNUP
  User signs up via Nextcloud registration form
  → Lago API: create customer + create subscription (trial: 14 days)
  → Ansible: provision user in Keycloak (group: trial_users)
  → Nextcloud: create user account with trial quota (10 GB)

STEP 2: TRIAL → ACTIVE
  User enters payment method (Bitcoin wallet or bank transfer details)
  → Lago: subscription status = 'active', first invoice generated
  → InvoicePlane: generate PDF invoice
  → BTCPay Server: create payment request
  → Email: invoice sent to user

STEP 3: PAYMENT CONFIRMED
  BTCPay Server webhook: InvoicePaymentSettled
  → Lago: mark invoice as paid, subscription.active = true
  → Lago webhook: subscription.started
  → Ansible provisioner:
      - Keycloak: move user from trial_users to tier group (basic_users / pro_users / enterprise_users)
      - Nextcloud: set quota via occ, enable/disable apps per group
      - Email: "Your subscription is active!"

STEP 4: MONTHLY RENEWAL
  Lago cron: generate renewal invoice (day -3 before period end)
  → InvoicePlane: generate PDF
  → BTCPay Server: create payment request
  → Email: renewal invoice sent

STEP 5: PAYMENT FAILED (DUNNING)
  Day +1: Lago marks invoice as past_due → email warning
  Day +3: Second warning email
  Day +7: Final warning email + SMS (if configured)
  Day +14: Lago webhook: subscription.overdue
  → Ansible: disable user in Keycloak, set Nextcloud quota to 0 (read-only)
  → Email: "Account suspended — data preserved for 30 days"
  Day +30: Lago webhook: subscription.terminated
  → Ansible: archive user data, remove Keycloak account
  → Email: "Account archived — contact support for data export"

STEP 6: UPGRADE/DOWNGRADE
  User requests tier change via portal
  → Lago: subscription upgrade/downgrade (prorated)
  → Ansible: adjust Keycloak group + Nextcloud quota + app access
  → Email: "Your plan has been updated"

STEP 7: CANCELLATION
  User cancels subscription
  → Lago: subscription status = 'canceled' (active until period end)
  → At period end: Lago webhook: subscription.terminated
  → Ansible: archive user, 30-day grace period for data export
```

### 3.4 Dunning Policy

| Days Overdue | Action | User Impact |
|-------------|--------|-------------|
| Day 1 | Email warning: "Payment overdue — please settle within 7 days" | Full access maintained |
| Day 3 | Second email: "Reminder: payment 3 days overdue" | Full access maintained |
| Day 7 | Final email: "Final notice — account will be suspended in 7 days" | Full access maintained |
| Day 14 | **Account disabled**: Keycloak login blocked, Nextcloud quota set to 0 (read-only, no new uploads) | Cannot log in; existing data preserved |
| Day 30 | **Account archived**: User data compressed and moved to cold storage. Keycloak account removed. | Data retained for 90 days; recoverable with support ticket + payment of arrears |
| Day 90+ | **Data purged**: Permanent deletion. | Irreversible |

### 3.5 Payment Methods

| Method | Type | Status | Notes |
|--------|------|--------|-------|
| **Bitcoin on-chain** | Open-source, self-hosted | Primary | BTCPay Server. 1 confirmation (~10 min). No chargebacks. |
| **Lightning Network** | Open-source, self-hosted | Primary | BTCPay Server + LND. Instant, near-zero fees. Ideal for micro-subscriptions. |
| **Bank transfer (PLN)** | Manual | Secondary | Polish bank transfer. Manually marked as paid in InvoicePlane. No automation. |
| **BLIK** | Proprietary | Optional | Polish mobile payment system. Requires commercial BLIK gateway (e.g., Przelewy24, Tpay). Not open-source. |
| **Przelewy24** | Proprietary | Optional | Polish online payment aggregator. 200+ banks + BLIK. ~1.5-2.5% fee. Not open-source. |
| **Stripe** | Proprietary | Exception | Credit/debit cards. ~1.4% + 1 PLN European cards. Not open-source. Only if card payments are business-critical. |

**Recommendation**: Bitcoin + Lightning as primary (fully open-source, self-hosted, zero processing fees). Bank transfer as fallback for non-crypto users. Add Przelewy24 only if customer demand for BLIK/card payments is strong enough to justify the ~2% processing fee and proprietary dependency.

### 3.6 Ansible Provisioner — Tier Enforcement

The webhook dispatcher (custom Python/Flask service) receives Lago webhooks and triggers Ansible playbooks:

```yaml
# playbooks/nextcloud_tier_enforcement.yml
- name: Enforce tier for user
  hosts: localhost
  vars:
    user_id: "{{ webhook_user_id }}"
    tier: "{{ webhook_tier }}"
    action: "{{ webhook_action }}"  # provision, suspend, archive, upgrade, downgrade
  tasks:
    - name: Set Keycloak group
      keycloak_group:
        user: "{{ user_id }}"
        group: "{{ tier }}_users"
        state: "{{ 'present' if action in ['provision','upgrade'] else 'absent' }}"

    - name: Set Nextcloud quota
      nextcloud_quota:
        user: "{{ user_id }}"
        quota: "{{ tier_quotas[tier] }}"
      # Basic: 10GB, Pro: 50GB, Enterprise: 250GB

    - name: Enable/disable apps per group
      nextcloud_app_access:
        group: "{{ tier }}_users"
        enabled_apps: "{{ tier_apps[tier] }}"
```

### 3.7 Tax Handling (Polish VAT)

- **Polish customers (B2C)**: 23% VAT added to invoice
- **Polish businesses (B2B)**: 23% VAT (standard), reverse charge if applicable
- **EU businesses (B2B, non-PL)**: Reverse charge (0% VAT) with valid VAT ID (VIES check)
- **Non-EU customers**: 0% VAT (export of services)
- **InvoicePlane** handles tax rate per customer configuration
- **Lago** stores tax rate per customer; InvoicePlane applies it at PDF generation

---

## 4. Feature Separability Matrix

Which features can be gated per-user/per-group vs. are globally coupled and affect all users.

### 4.1 Gating Categories

| Category | Definition | Enforcement Mechanism |
|----------|-----------|----------------------|
| **Per-User** | Feature can be enabled/disabled for individual users independently | Nextcloud app group restriction, Keycloak group membership, `occ user:setting` |
| **Per-Group** | Feature enabled for a Nextcloud/Keycloak group; all members get it | Nextcloud app "Limit to groups" setting, Keycloak group-based SSO claims |
| **Global** | Feature is instance-wide; enabling it affects all users | `config.php` setting, infrastructure component (e.g., Elasticsearch is either running or not) |
| **Hybrid** | Core infrastructure is global, but access can be gated per-group | Service runs for everyone, but UI access restricted by group |

### 4.2 Full Separability Matrix

| Feature | Gating Type | Enforcement | Notes |
|---------|------------|-------------|-------|
| **Storage quota** | Per-User | `occ user:setting quota` | Native Nextcloud per-user quota. Trivial to enforce. |
| **File sync & share** | Global | Core feature | Cannot disable — it's the platform. All tiers get it. |
| **Versioning retention** | Global | `config.php` `versions_retention_obligation` | Instance-wide setting. All users get same retention. Could be made per-user with custom app. |
| **Trashbin retention** | Global | `config.php` `trashbin_retention_obligation` | Instance-wide. Same as versioning. |
| **Activity stream** | Per-User | Built-in | Each user sees own activity. No gating needed. |
| **Email notifications** | Per-User | User preferences | Each user configures own notification settings. SMTP is global. |
| **Push notifications** | Per-Group | Notify Push service + Talk app group restriction | Notify Push runs globally; access gated by group. |
| **Calendar (read-only)** | Per-Group | Calendar app "Limit to groups" + CalDAV ACL | Read-only enforced via CalDAV permissions. Write access requires group membership. |
| **Calendar (full)** | Per-Group | Calendar app group restriction | Full CalDAV access for group members. |
| **Contacts (read-only)** | Per-Group | Contacts app "Limit to groups" + CardDAV ACL | Same pattern as Calendar. |
| **Contacts (full)** | Per-Group | Contacts app group restriction | Full CardDAV access. |
| **Nextcloud Talk** | Per-Group | Talk app "Limit to groups" | App hidden from non-group users. HPB infrastructure is global. |
| **Talk participant limit** | Per-Group | HPB signaling server config | Signaling server can enforce per-room participant caps based on group. |
| **Deck** | Per-Group | Deck app "Limit to groups" | App hidden from non-group users. |
| **Notes** | Per-Group | Notes app "Limit to groups" | App hidden. |
| **Mail** | Per-Group | Mail app "Limit to groups" | App hidden. Account count limit enforced per-user via app config. |
| **Forms** | Per-Group | Forms app "Limit to groups" | App hidden. |
| **Polls** | Per-Group | Polls app "Limit to groups" | App hidden. |
| **Collabora CODE** | Hybrid | Office app "Limit to groups" + CODE server global | CODE server runs for all; UI access gated by group. Documents stored in Nextcloud regardless. |
| **ONLYOFFICE** | Hybrid | ONLYOFFICE app "Limit to groups" + Document Server global | Same pattern as Collabora. |
| **Photos** | Per-Group | Photos app "Limit to groups" | App hidden. |
| **Recognize (AI)** | Global | Recognize app processes all users' photos | Cannot gate per-user — it scans the entire data directory. Privacy concern: Enterprise users' photos get AI-tagged even if they don't want it. Mitigation: disable Recognize per-user via app config (opt-out). |
| **Music** | Per-Group | Music app "Limit to groups" | App hidden. |
| **News** | Per-Group | News app "Limit to groups" | App hidden. |
| **Bookmarks** | Per-Group | Bookmarks app "Limit to groups" | App hidden. |
| **Maps** | Per-Group | Maps app "Limit to groups" | App hidden. |
| **Social** | Per-Group | Social app "Limit to groups" | App hidden. Federation is global if enabled. |
| **External Storage** | Per-Group | External Storage app "Limit to groups" + per-user mount permissions | Admin assigns mounts to specific users/groups. Fine-grained. |
| **Full-text Search** | Hybrid | Elasticsearch global + fulltextsearch app "Limit to groups" | Elasticsearch indexes all files (global). Search UI gated by group. Non-Enterprise users' files are still indexed (privacy consideration). Mitigation: exclude non-Enterprise user directories from ES indexing. |
| **Server-Side Encryption** | Global | `occ encryption:enable` | Instance-wide. Once enabled, all files encrypted. Cannot gate per-user. **CRITICAL**: SSE is incompatible with SAML/OIDC SSO — causes data loss. If Enterprise tier includes both SSE and SSO, this is a contradiction. Resolution: Enterprise users get E2EE (client-side, compatible with SSO); SSE is offered as an alternative to SSO for compliance-only deployments. |
| **End-to-End Encryption** | Per-User | Client-side; user enables per-folder | Users choose which folders to E2EE encrypt. No server-side enforcement needed. |
| **LDAP Integration** | Global | `config.php` `ldapProviderFactory` | Instance-wide auth backend. Cannot gate per-user. If LDAP is enabled, all users authenticate via LDAP. Hybrid with Keycloak: Keycloak federates to LDAP; Nextcloud uses Keycloak SAML/OIDC. LDAP is a Keycloak concern, not Nextcloud. |
| **File ACLs** | Per-Group | File Access Control app "Limit to groups" | Admin UI gated; ACLs themselves apply to all files regardless of tier. |
| **Retention Policies** | Global | Retention app + `occ` commands | Instance-wide policies. Can tag specific folders for retention. |
| **TOTP 2FA** | Per-User | User enables in security settings | Available to all users. No gating needed (it's a security baseline). |
| **WebAuthn 2FA** | Per-Group | Two-Factor WebAuthn app "Limit to groups" | App hidden from non-group users. |
| **U2F 2FA** | Per-Group | Two-Factor U2F app "Limit to groups" | App hidden. |
| **SSO (Keycloak)** | Global | `config.php` SAML/OIDC config | Instance-wide auth. All users can use SSO if configured. Gating via Keycloak: only users in tier groups get SSO claims; others use local password. |
| **Antivirus (ClamAV)** | Global | ClamAV daemon + Antivirus app | All files scanned. Cannot gate per-user. |
| **Theming** | Global | Admin settings | One theme per instance. |
| **Federation** | Global | `config.php` federation flags | Instance-wide. |
| **Support SLA** | Per-User | Ticket system priority queue | Manual enforcement. Enterprise users get priority routing. |

### 4.3 Gating Implementation Summary

**Trivially gateable (per-group app restriction)**: Talk, Deck, Notes, Mail, Forms, Polls, Photos, Music, News, Bookmarks, Maps, Social, Calendar full, Contacts full, WebAuthn, U2F, Collabora UI, ONLYOFFICE UI, External Storage UI, Full-text Search UI, File ACLs UI.

**Gateable with custom logic**: Storage quota (per-user `occ`), Talk participant limit (HPB signaling config), Mail account count (app config), Calendar/Contacts read-only (CalDAV/CardDAV ACLs).

**Globally coupled (cannot gate)**: Versioning retention, Trashbin retention, Server-Side Encryption, LDAP backend, Antivirus, Theming, Federation, Recognize AI processing, Elasticsearch indexing.

**Mitigation for global features**:
- **Versioning/Trashbin**: Set to 30 days for all users (Basic tier expectation). Enterprise users don't get longer retention — this is a deliberate simplification. If longer retention is needed, offer it as an add-on (custom `config.php` override per-user not natively supported).
- **SSE + SSO conflict**: Enterprise tier offers E2EE (client-side) as the encryption solution when SSO is enabled. SSE is documented as available but mutually exclusive with SSO — Enterprise customers choose one.
- **Recognize AI**: Offer opt-out per user. Enterprise users get it by default; others can request opt-out.
- **Elasticsearch indexing**: Configure Elasticsearch ingest pipeline to skip non-Enterprise user directories. Enterprise users' files are indexed; others' are not. This requires custom logic in the fulltextsearch app or a proxy filter.

### 4.4 Keycloak Group Mapping

| Keycloak Group | Nextcloud Group | Tier | Features Enabled |
|----------------|-----------------|------|-----------------|
| `basic_users` | `basic_users` | Basic | Core apps only; Calendar/Contacts read-only |
| `pro_users` | `pro_users` | Pro | Basic + Talk, Deck, Notes, Mail, Forms, Polls, Calendar/Contacts full, WebAuthn, Push |
| `enterprise_users` | `enterprise_users` | Enterprise | Pro + Collabora, ONLYOFFICE, Photos, Music, News, Bookmarks, Maps, Social, External Storage, Full-text Search, U2F, File ACLs |
| `trial_users` | `trial_users` | Trial (14-day) | Pro features for 14 days, then downgrade to Basic if no payment |
| `suspended_users` | `suspended_users` | Suspended | Login blocked, data read-only |
| `admin_users` | `admin` | Admin | Full access regardless of tier |

---

## 5. Revenue Projections

### 5.1 Scenario Assumptions

All scenarios assume Hetzner Cloud infrastructure (~300 PLN/mo base + storage scaling). Admin labor: 1 part-time sysadmin at ~2,000 PLN/mo (scales to full-time at 100 users).

### 5.2 Scenario A — Conservative (30 Users)

**Tier mix**: 15 Basic + 10 Pro + 5 Enterprise

| Metric | Value |
|--------|-------|
| **Users** | 30 |
| **Revenue** | (15 × 20) + (10 × 50) + (5 × 120) = 300 + 500 + 600 = **1,400 PLN/mo** |
| **Infrastructure cost** | ~300 PLN (Hetzner CX41 base) + ~200 PLN (storage for 30 users) = **~500 PLN/mo** |
| **Admin labor** | ~2,000 PLN/mo (part-time) |
| **Total cost** | ~2,500 PLN/mo |
| **Net profit** | **-1,100 PLN/mo (LOSS)** |

**Analysis**: At 30 users, the business runs at a loss. The admin labor cost dominates. This is a "lifestyle business" or subsidized internal IT scenario — not commercially viable as a standalone business. Break-even requires ~45 users at this tier mix.

**Mitigation strategies**:
- Reduce admin labor: automate more (Ansible playbooks, self-service portal, monitoring alerts)
- Increase Enterprise mix: each Enterprise user contributes ~104 PLN margin vs. ~12 PLN for Basic
- Raise Basic price to 25 PLN: adds 75 PLN/mo
- Offer annual pre-payment discount (10% off for annual = better cash flow, lower churn)

### 5.3 Scenario B — Target (50 Users)

**Tier mix**: 20 Basic + 20 Pro + 10 Enterprise

| Metric | Value |
|--------|-------|
| **Users** | 50 |
| **Revenue** | (20 × 20) + (20 × 50) + (10 × 120) = 400 + 1,000 + 1,200 = **2,600 PLN/mo** |
| **Infrastructure cost** | ~300 PLN (Hetzner CX41) + ~500 PLN (storage: 20×10GB + 20×50GB + 10×250GB = 3,700 GB) = **~800 PLN/mo** |
| **Admin labor** | ~2,000 PLN/mo (part-time, ~20h/week) |
| **Payment processing** | ~0 PLN (Bitcoin/Lightning) or ~52 PLN (2% if all via Przelewy24) |
| **Domain + misc** | ~20 PLN/mo |
| **Total cost** | ~2,820-2,872 PLN/mo |
| **Net profit** | **-220 to -272 PLN/mo (near break-even)** |

**Analysis**: At 50 users with this tier mix, the business hovers near break-even. The 2,600 PLN revenue barely covers infrastructure + part-time admin. This is sustainable as a side business or internal IT department budget, but not as a primary income source.

**Path to profitability at 50 users**:
- Shift tier mix to 10 Basic + 25 Pro + 15 Enterprise: Revenue = 200 + 1,250 + 1,800 = **3,250 PLN/mo** → Profit ~380 PLN/mo
- Reduce admin labor to 1,500 PLN/mo (10h/week, heavy automation): Profit ~880 PLN/mo
- Raise prices 10%: Basic 22 PLN, Pro 55 PLN, Enterprise 132 PLN → Revenue = 2,860 PLN/mo → Profit ~40 PLN/mo

### 5.4 Scenario C — Optimistic (100 Users)

**Tier mix**: 30 Basic + 40 Pro + 30 Enterprise

| Metric | Value |
|--------|-------|
| **Users** | 100 |
| **Revenue** | (30 × 20) + (40 × 50) + (30 × 120) = 600 + 2,000 + 3,600 = **6,200 PLN/mo** |
| **Infrastructure cost** | ~600 PLN (Hetzner CX51 or 2× CX41) + ~1,200 PLN (storage: 30×10 + 40×50 + 30×250 = 9,800 GB) = **~1,800 PLN/mo** |
| **Admin labor** | ~4,000 PLN/mo (full-time sysadmin) |
| **Payment processing** | ~0-124 PLN/mo |
| **Domain + misc** | ~30 PLN/mo |
| **Total cost** | ~5,830-5,954 PLN/mo |
| **Net profit** | **~246-370 PLN/mo** |

**Analysis**: At 100 users, the business becomes modestly profitable. Per-user infrastructure cost drops due to economies of scale (shared sidecars). Admin labor scales sub-linearly (one full-time admin can handle 100 users with good automation).

**Optimized 100-user scenario** (shift to higher tiers):
- Mix: 20 Basic + 40 Pro + 40 Enterprise
- Revenue: 400 + 2,000 + 4,800 = **7,200 PLN/mo**
- Profit: **~1,200-1,400 PLN/mo** (viable small business)

### 5.5 Revenue Projection Summary

| Scenario | Users | Monthly Revenue | Monthly Cost | Monthly Profit | Profit Margin |
|----------|-------|----------------|--------------|----------------|---------------|
| Conservative | 30 | 1,400 PLN | ~2,500 PLN | -1,100 PLN | -79% (loss) |
| Target (default mix) | 50 | 2,600 PLN | ~2,850 PLN | -250 PLN | -10% (loss) |
| Target (optimized mix) | 50 | 3,250 PLN | ~2,850 PLN | +400 PLN | +12% |
| Optimistic (default mix) | 100 | 6,200 PLN | ~5,850 PLN | +350 PLN | +6% |
| Optimistic (optimized mix) | 100 | 7,200 PLN | ~5,850 PLN | +1,350 PLN | +19% |
| Optimistic (Enterprise-heavy) | 100 | 9,600 PLN | ~6,200 PLN | +3,400 PLN | +35% |

*\*Optimistic Enterprise-heavy mix: 10 Basic + 30 Pro + 60 Enterprise = 200 + 1,500 + 7,200 = 8,900 PLN. Infrastructure cost higher due to storage (60 × 250 GB = 15 TB).*

### 5.6 Key Revenue Insights

1. **The business is not a get-rich-quick scheme.** At 50 users, it's a break-even side business. Profitability requires either 100+ users or a high Enterprise mix.

2. **Enterprise users are the profit engine.** Each Enterprise user contributes ~104 PLN margin vs. ~12 PLN for Basic. A single Enterprise user is worth 8.7 Basic users in profit terms.

3. **Admin labor is the dominant cost**, not infrastructure. At 50 users, admin labor (~2,000 PLN) is 2.5× the infrastructure cost (~800 PLN). Automation is the highest-leverage investment.

4. **Annual pre-payment improves cash flow.** Offering 10% discount for annual payment (e.g., Enterprise 1,296 PLN/year instead of 1,440 PLN) reduces monthly revenue by 10% but locks in customers for 12 months and reduces churn-driven admin overhead.

5. **The 20× infrastructure multiple is healthy.** Even at Enterprise tier (120 PLN price, ~6 PLN cost), the 20× multiple leaves room for labor, support, and profit. This is rare in hosting businesses and reflects the value of expertise, trust, and compliance — not raw compute.

6. **Break-even at ~45 users** with the default tier mix. Below this, the business requires subsidy (internal IT budget, grant funding, or founder subsidy).

### 5.7 Annual Revenue Projection (Target Scenario, 50 Users)

| Month | Revenue | Cumulative | Notes |
|-------|---------|------------|-------|
| 1 | 650 PLN | 650 PLN | Ramp-up: 25% of target users onboarded |
| 2 | 1,300 PLN | 1,950 PLN | 50% onboarded |
| 3 | 1,950 PLN | 3,900 PLN | 75% onboarded |
| 4 | 2,600 PLN | 6,500 PLN | Full capacity reached |
| 5-12 | 2,600 PLN/mo | +20,800 PLN | Steady state |
| **Year 1 Total** | | **27,300 PLN** | |
| **Year 1 Costs** | | ~34,200 PLN | 12 × 2,850 PLN |
| **Year 1 Net** | | **-6,900 PLN** | First-year loss due to ramp-up |

Year 2 (steady state, 50 users all 12 months): Revenue 31,200 PLN, Costs ~34,200 PLN, Net **-3,000 PLN**.

Year 2 with optimized mix (10/25/15): Revenue 39,000 PLN, Costs ~34,200 PLN, Net **+4,800 PLN**.

---

## 6. Implementation Roadmap

### Phase 1: Foundation (Weeks 1-2)
- Deploy Lago, BTCPay Server, InvoicePlane as Docker containers
- Configure Lago plans (Basic, Pro, Enterprise) with billable metrics
- Set up InvoicePlane templates with Polish VAT handling
- Configure BTCPay Server with Lightning node
- Deploy webhook dispatcher (Python/Flask)

### Phase 2: Integration (Weeks 3-4)
- Integrate Lago webhooks → Ansible provisioner
- Implement Keycloak group mapping for tiers
- Configure Nextcloud app group restrictions per tier
- Set up dunning cron jobs
- Test full subscription lifecycle (signup → trial → payment → active → overdue → suspend → archive)

### Phase 3: Polish (Weeks 5-6)
- Customer-facing signup portal
- Self-service tier upgrade/downgrade
- Invoice history portal (InvoicePlane client view)
- Email notification templates (welcome, invoice, dunning, suspension)
- Admin dashboard (Lago analytics + Nextcloud metrics)

### Phase 4: Launch (Week 7+)
- Soft launch with 5-10 beta users
- Monitor billing pipeline end-to-end
- Gather feedback on pricing, features, payment methods
- Adjust tier definitions based on real usage patterns
- Public launch

---

## Appendix A: Competitive Pricing Data (June 2026)

| Service | Plan | Price (PLN/user/mo) | Source |
|---------|------|---------------------|--------|
| Nextcloud Enterprise (official) | Basic (100+ users) | ~13.50 PLN | nextcloud.com/pricing (€36/user/year) |
| tab.digital | Private (50 users) | ~27 PLN | tab.digital/en/pricing (€5.95/mo) |
| Google Workspace | Business Starter | ~25 PLN | workspace.google.com/pricing |
| Google Workspace | Business Standard | ~50 PLN | workspace.google.com/pricing |
| Google Workspace | Business Plus | ~76 PLN | workspace.google.com/pricing |
| Microsoft 365 | Business Basic | ~25 PLN | microsoft.com |
| Microsoft 365 | Business Standard | ~50-60 PLN | microsoft.com |
| Microsoft 365 | Business Premium | ~87 PLN | microsoft.com |
| Hetzner Storage Share | NX11 (1 TB shared) | ~19 PLN (€4.29) | hetzner.com |
| Hetzner Storage Share | NX21 | ~64 PLN (€14.19) | hetzner.com |
| Hetzner Storage Share | NX31 (10 TB shared) | ~123 PLN (€27.39) | hetzner.com |

Exchange rate: 1 EUR ≈ 4.50 PLN (June 2026).

---

## Appendix B: Open-Source License Summary

| Component | License | Commercial Use | Key Restriction |
|-----------|---------|---------------|-----------------|
| Nextcloud Server | AGPL-3.0 | Yes | Source must be provided to network users |
| Lago | AGPL-3.0 | Yes | Same as Nextcloud |
| BTCPay Server | MIT | Yes | No restrictions |
| InvoicePlane | MIT | Yes | No restrictions |
| Keycloak | Apache-2.0 | Yes | No restrictions |
| Collabora CODE | MPL-2.0 | Yes | File-level copyleft |
| ONLYOFFICE | AGPL-3.0 | Yes | Same as Nextcloud |
| Elasticsearch | Elastic License 2.0 / SSPL | Yes (self-hosted) | Cannot offer Elasticsearch as a service |
| ClamAV | GPL-2.0 | Yes | Standard GPL |
| PostgreSQL | PostgreSQL License | Yes | Permissive |
| Redis | BSD-3-Clause / RSALv2 | Yes (self-hosted) | RSALv2 restricts selling Redis as a service |
| Coturn (TURN) | BSD-3-Clause | Yes | Permissive |
| Ansible | GPL-3.0 | Yes | Standard GPL |

**Compliance note**: All components are used for self-hosting our own service, not reselling the software itself. AGPL requirements are satisfied because we do not modify Nextcloud/Lago source; if we do, modified source must be made available to our users (which aligns with our open-source ethos).

---

*Generated by Hermes Agent research task. All prices are estimates based on publicly available pricing as of June 2026. Exchange rate: 1 EUR ≈ 4.50 PLN. Electricity: 1.10 PLN/kWh (Polish average). VAT: 23% (Poland standard rate).*

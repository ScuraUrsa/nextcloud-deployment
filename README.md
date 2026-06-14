# Nextcloud Self-Hosted Deployment

Full-spectrum, production-grade Nextcloud deployment for 50 users with SSO, tiered feature packaging, open-source billing, and complete infrastructure-as-code automation.

## What This Repository Provides

- **Research Report** — 14 Architectural Decision Records, identity architecture, feature separability matrix, TCO estimation for 3 scenarios, packaging & monetization model
- **Ansible Playbooks** — 13 playbooks, 16 roles, full IaC from bare metal to fully operational Nextcloud with all features
- **Python Test Suite** — 150+ pytest tests validating every feature, SSO flows, tier gating, and billing lifecycle
- **GitHub Actions CI/CD** — 7 workflows: continuous testing, staging/production deployment, backup verification, security scanning, billing health checks
- **Open-Source Billing Stack** — Lago (subscriptions) + BTCPay Server (payments) + InvoicePlane (invoices)

## Target Architecture

- **50 users** with per-user isolation
- **SSO via Keycloak** (SAML 2.0 + OpenID Connect) with local password fallback
- **Three feature tiers**: Basic (20 PLN/mo), Pro (50 PLN/mo), Enterprise (120 PLN/mo)
- **All open-source, self-hosted components** — no proprietary SaaS dependencies

## Quick Start

```bash
# 1. Clone the repository
git clone https://github.com/ScuraUrsa/nextcloud-deployment.git
cd nextcloud-deployment

# 2. Set up Ansible Vault secrets
cp .env.example .env
# Edit .env with your actual secrets
ansible-vault encrypt_string --vault-password-file <(echo "$ANSIBLE_VAULT_PASSWORD") 'your-secret' --name 'vault_nextcloud_admin_pass'

# 3. Deploy to staging
ansible-playbook -i inventory/staging/hosts.yml playbooks/nextcloud_full_deploy.yml

# 4. Run smoke tests
pip install -r tests/requirements-test.txt
NEXTCLOUD_URL=https://your-instance.com pytest -m smoke

# 5. Provision users
ansible-playbook -i inventory/production/hosts.yml playbooks/nextcloud_user_management.yml \
  -e "user_manifest_file=users.csv"
```

## Repository Structure

```
├── NEXTCLOUD_DEPLOYMENT_REPORT.md   # Comprehensive research report (70+ pages)
├── ansible/                         # Infrastructure as Code
│   ├── inventory/                   # Production and staging inventories
│   ├── playbooks/                   # 13 deployment playbooks
│   ├── roles/                       # 16 Ansible roles
│   └── library/                     # Custom Ansible modules
├── tests/                           # Python test suite (150+ tests)
│   ├── utils/                       # API wrappers (Nextcloud, Keycloak, Lago)
│   ├── test_core/                   # WebDAV, sharing, versioning
│   ├── test_collaboration/          # Calendar, Contacts, Talk, Deck, Mail
│   ├── test_content/                # Photos, Music, News, Bookmarks, Maps
│   ├── test_admin/                  # LDAP, SAML, 2FA, antivirus, ACLs
│   ├── test_identity/               # SSO flows, dual auth, provisioning
│   ├── test_tiers/                  # Feature gating, quotas, tier changes
│   ├── test_billing/                # Lago, BTCPay, subscription lifecycle
│   ├── test_performance/            # Upload speed, search latency, concurrency
│   └── test_security/               # Headers, TLS, brute-force, permissions
├── .github/workflows/               # 7 CI/CD pipelines
├── docs/                            # Research artifacts
├── users.csv.example                # Example user manifest for bulk provisioning
└── .env.example                     # All environment variables (no real values)
```

## License

MIT — see [LICENSE](LICENSE) for details.

## Author

Filip Kaźmierczak & Hermes Orchestrator, 2026

# Staging: Nextcloud "personal core"

First real deployment of this repo (2026-10-11): a single VirtualBox VM on Filip's laptop.

| | |
|---|---|
| VM | `nextcloud-staging` (VirtualBox, headless) |
| Address | `192.168.56.111` on the host-only network (VirtualBox DHCP reservation) |
| Size | 4 GB RAM, 2 vCPU, 30 GB disk |
| OS | Ubuntu 22.04 cloud image (see "Ubuntu version" below) |
| URL | `https://192.168.56.111/` (self-signed certificate) |
| Playbook | `ansible/playbooks/nextcloud_core.yml` |
| Inventory | `ansible/inventory/staging/` |

## Scope

Roles: `common`, `postgresql`, `redis`, `php_fpm`, `nginx`, `nextcloud`.
Apps: files (bundled), calendar, contacts, spreed (Talk, no TURN server yet), enabled for all users
(`nextcloud_app_tier_gating: false`).

Not deployed yet: keycloak, elasticsearch, collabora, talk (coturn), billing, hardening, backup, monitoring.

## How the VM was created

Same path the Hermes host daemon uses (`terraforge-stacks/local/scripts/manage-local-vm.ps1`
with `-UseDhcp`, then `manage-dhcp-reservation.ps1 -Action Add`), from the base image
`terraforge-stacks/local/generated/base-image/ubuntu-jammy-22.04-cloudimg.ovf`.
cloud-init user-data only sets the hostname and the `ubuntu` user's SSH key.

## Secrets

Never in git. On the VM: `~/.nc-staging-secrets.yml` (mode 0600, user `ubuntu`) holds
`vault_nextcloud_admin_pass` and `vault_postgresql_password` (random, 24 characters).
Read them on the VM only; do not paste them into chat or commits.

## Running the playbook

There is no WSL distro on the laptop, so Ansible runs on the VM itself (`-c local`):

```bash
# on the VM, from a copy of this repo in ~/nextcloud-deployment
cd ~/nextcloud-deployment/ansible
python3 -m pip install --user "ansible>=10,<11"   # once
~/.local/bin/ansible-playbook -i inventory/staging/hosts.yml -c local -l nextcloud-staging \
  playbooks/nextcloud_core.yml -e @$HOME/.nc-staging-secrets.yml
```

From a Linux control node, drop `-c local -l nextcloud-staging`.

## Ubuntu version

The ADR (`docs/distribution-selection.md`) picks Ubuntu 24.04. The local base image is 22.04,
so staging runs 22.04. The core roles take PHP 8.3 from `ppa:ondrej/php` and PostgreSQL 16
from PGDG, so the stack is the same on both; `nextcloud_core.yml` accepts both releases
(`site.yml` still requires 24.04).

## Smoke tests

```bash
# on the VM (the admin password never leaves it)
cd ~/nextcloud-deployment
python3 -m pip install --user -r tests/requirements-test.txt
NEXTCLOUD_URL=https://192.168.56.111 NEXTCLOUD_ADMIN_USER=admin \
NEXTCLOUD_ADMIN_PASS="$(sed -n 's/^vault_nextcloud_admin_pass: "\(.*\)"/\1/p' ~/.nc-staging-secrets.yml)" \
REQUESTS_CA_BUNDLE=/etc/ssl/nextcloud/fullchain.pem \
python3 -m pytest -m smoke
```

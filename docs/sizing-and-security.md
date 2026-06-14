# Nextcloud Infrastructure Sizing & Security Hardening Baseline

## Document Purpose
This document provides infrastructure sizing recommendations for 4 deployment tiers and a comprehensive security hardening baseline for Nextcloud on Linux (Ubuntu 24.04 LTS / Debian 12). Target deployment: Medium tier (10-50 users, 1TB storage).

---

## PART 1: INFRASTRUCTURE SIZING RECOMMENDATIONS

### Sizing Philosophy
Nextcloud's official documentation specifies per-process minimums: 128 MB RAM minimum, 512 MB RAM recommended per PHP process. Real-world sizing must account for all co-resident services: PHP-FPM workers, PostgreSQL/MariaDB, Redis, Elasticsearch (full-text search), Collabora CODE (office), Keycloak (SSO), ClamAV (antivirus), and OS overhead. Each concurrent user typically needs 1-2 PHP-FPM workers.

---

### Tier 1: Small (1-10 users, ~100 GB bulk storage)

**Use case:** Personal cloud, family file sharing, small team.

| Resource | Specification | Notes |
|----------|--------------|-------|
| vCPU | 2 cores | Shared between Nextcloud, DB, Redis |
| RAM | 4 GB | Minimum for functional deployment |
| SSD (OS + Nextcloud) | 40-50 GB | OS (~15 GB), Nextcloud app (~2 GB), DB (~5 GB), logs |
| Bulk Storage | 100 GB | Data directory, user files |
| Bandwidth | 100 Mbps | Sufficient for 1-10 users |

**Component breakdown:**
- PHP-FPM: 4-6 workers (pm=ondemand, max_children=8), ~2 GB
- PostgreSQL: shared_buffers=512MB, ~700 MB total
- Redis: maxmemory 256MB, ~300 MB
- Elasticsearch: NOT recommended at this tier (use built-in search)
- Collabora CODE: NOT recommended (use built-in CODE server or skip)
- Keycloak: NOT recommended (use built-in auth or skip)
- ClamAV: clamav-daemon, ~300 MB (can run on-demand scans instead)
- OS overhead: ~500 MB

**Deployment model:** Single VM or VPS. All services on one host. Docker Compose optional but adds overhead.

---

### Tier 2: Medium (10-50 users, ~1 TB bulk storage) — TARGET TIER

**Use case:** Small business, department, school, organization with moderate concurrent usage.

| Resource | Specification | Notes |
|----------|--------------|-------|
| vCPU | 4-6 cores | 4 minimum, 6 recommended for Collabora |
| RAM | 16 GB | 8 GB absolute minimum, 16 GB recommended |
| SSD (OS + services) | 100-150 GB NVMe | OS, Nextcloud, DB, logs, temp |
| Bulk Storage | 1 TB | Data directory; consider RAID-1 or ZFS mirror |
| Bandwidth | 250-500 Mbps | Depends on file sizes and sync frequency |

#### Detailed Component Breakdown (16 GB RAM target)

| Component | RAM Allocation | vCPU Share | Configuration Notes |
|-----------|---------------|------------|---------------------|
| **PHP-FPM workers** | 4-5 GB | 2-3 cores | 15-20 workers (pm=static or ondemand, max_children=25). Each worker ~180-250 MB real-world. Set pm.max_children=25, pm.start_servers=8, pm.min_spare_servers=5, pm.max_spare_servers=15. Use PHP 8.2+ with OPcache (opcache.memory_consumption=256, opcache.interned_strings_buffer=32, opcache.max_accelerated_files=20000). |
| **PostgreSQL 15/16** | 3-4 GB | 1 core | shared_buffers=4GB (25% of RAM), effective_cache_size=12GB, work_mem=32MB, maintenance_work_mem=512MB, max_connections=50, random_page_cost=1.1 (SSD). Use pg_stat_statements for monitoring. |
| **Redis 7** | 512 MB - 1 GB | 0.25 core | maxmemory 512mb, maxmemory-policy allkeys-lru. Used for: file locking (critical), distributed cache, session storage. Configure in config.php: 'memcache.locking' => '\OC\Memcache\Redis', 'memcache.distributed' => '\OC\Memcache\Redis'. |
| **Elasticsearch 8** | 2 GB heap | 1 core | -Xms2g -Xmx2g (never exceed 50% of container RAM, cap at 31 GB absolute). For full-text search via nextcloud/fulltextsearch app. OS needs 2 GB for filesystem cache. Total Elasticsearch RAM: ~4 GB. |
| **Collabora CODE** | 2 GB | 1-2 cores | Docker container. Minimum: 1 GB + 100 MB per concurrent user. For 10 concurrent editors: ~2 GB. Use built-in CODE server (richdocumentscode app) for simpler deployment, or separate Docker container for isolation. |
| **Keycloak 26** | 1-1.5 GB | 0.5 core | Base memory ~1250 MB for realm data + 10K cached sessions. For 50 users: 1 GB heap sufficient. Use PostgreSQL backend (same DB server, separate database). |
| **ClamAV daemon** | 300-500 MB | 0.25 core | clamav-daemon loads signature DB into RAM (~200-300 MB). Configure MaxThreads=2, ScanOnAccess off (on-demand via Nextcloud app). Can reduce to on-demand clamscan if RAM is tight. |
| **OS overhead** | 1-2 GB | — | Ubuntu 24.04 minimal: ~500 MB idle. With monitoring agents, cron, systemd-journald: ~1 GB. Reserve 2 GB for filesystem cache (critical for DB and file performance). |
| **Nginx/Apache** | 200-400 MB | 0.25 core | Nginx recommended (lower memory). 2-4 worker processes. |
| **Total** | **~16 GB** | **~5-6 cores** | All services fit on a single host at this tier. |

#### Storage Layout (Medium Tier)
```
/                  SSD 100-150 GB  (OS, /var/www/nextcloud, /var/lib/postgresql, /var/lib/redis, /var/log)
/data              Bulk 1 TB       (Nextcloud data directory — mount point or separate disk)
/backup            External/NAS    (Daily backups of DB + config + data)
```

#### Network & Bandwidth
- 250 Mbps minimum for 50 users with moderate file sync
- 500 Mbps recommended if large files (100MB+) are regularly synced
- Consider traffic shaping to prevent sync storms from saturating uplink

---

### Tier 3: Large (50-500 users, ~10 TB+ bulk storage)

**Use case:** Medium-large organization, university department, multi-team deployment.

| Resource | Specification | Notes |
|----------|--------------|-------|
| vCPU | 8-16 cores (split across nodes) | Dedicated nodes for DB, Redis, Search |
| RAM | 32-64 GB (split across nodes) | See node breakdown below |
| SSD (OS + DB) | 200-500 GB NVMe | Separate DB disk recommended |
| Bulk Storage | 10-50 TB | NAS/SAN, ZFS pool, or S3-compatible object store |
| Bandwidth | 1 Gbps | Dedicated or shared uplink |

#### Multi-Node Architecture

**Node 1: Web/App Server (Nextcloud + PHP-FPM)**
- 4-8 vCPU, 16-32 GB RAM
- PHP-FPM: 50-80 workers (pm=static), ~12-20 GB
- Nginx reverse proxy with caching
- OPcache: opcache.memory_consumption=512

**Node 2: Database Server (PostgreSQL dedicated)**
- 4-8 vCPU, 16-32 GB RAM
- shared_buffers=8-16GB, effective_cache_size=24-48GB
- work_mem=64MB, max_connections=200
- WAL on separate SSD, consider streaming replication to standby

**Node 3: Cache & Search (Redis + Elasticsearch)**
- 2-4 vCPU, 8-16 GB RAM
- Redis: maxmemory 4-8 GB, separate instance for locking vs cache
- Elasticsearch: 4-8 GB heap, dedicated for full-text search
- Consider Elasticsearch cluster (3 nodes) for redundancy

**Node 4: Collabora CODE (dedicated)**
- 4-8 vCPU, 8-16 GB RAM
- Docker or bare-metal. 1 GB + 100 MB per concurrent user
- For 50 concurrent editors: ~6 GB. Scale horizontally with multiple CODE instances behind load balancer.

**Node 5: Keycloak (dedicated)**
- 2-4 vCPU, 4-8 GB RAM
- Heap: 2-4 GB. Use PostgreSQL backend.
- Consider Keycloak cluster for HA if auth is critical path.

**Storage:**
- Primary data directory on NAS/SAN (NFSv4 with Kerberos, or iSCSI)
- Alternatively: S3-compatible object store as primary storage (Nextcloud supports S3 as primary backend)
- Database on local NVMe; backups to NAS

---

### Tier 4: Enterprise (500+ users)

**Use case:** Large enterprise, university, government, service provider.

| Resource | Specification | Notes |
|----------|--------------|-------|
| vCPU | 32+ cores (across HA cluster) | Redundancy at every layer |
| RAM | 128+ GB (across HA cluster) | Headroom for peak loads |
| SSD | 1 TB+ NVMe (DB cluster) | Galera cluster nodes |
| Bulk Storage | 50 TB - PB scale | S3-compatible object store (MinIO, Ceph, AWS S3) |
| Bandwidth | 10 Gbps | Redundant uplinks |

#### HA Cluster Architecture

**Web/App Tier:**
- 3+ Nextcloud application nodes behind HAProxy/NGINX load balancer
- Each node: 8 vCPU, 32 GB RAM, 80-120 PHP-FPM workers
- Session stickiness via Redis (shared session store)
- Static assets cached at CDN/edge

**Database Tier — Galera Cluster (MariaDB) or Patroni (PostgreSQL):**
- 3-node Galera Cluster (MariaDB 10.11+) or 3-node Patroni + etcd (PostgreSQL 16+)
- Each node: 8-16 vCPU, 32-64 GB RAM, dedicated NVMe
- Synchronous replication, automatic failover
- Read/write split: write to primary, reads distributed

**Cache Tier — Redis Sentinel:**
- 3 Redis instances + 3 Sentinel nodes (can co-locate)
- Redis maxmemory 8-16 GB per instance
- Automatic failover with Sentinel
- Separate instances for locking, cache, sessions

**Search Tier — Elasticsearch Cluster:**
- 3+ Elasticsearch nodes, 8-16 GB heap each
- Index replication for HA
- Dedicated master nodes for large clusters

**Collabora CODE — HA Pool:**
- 3+ CODE instances behind load balancer
- Each: 4 vCPU, 8 GB RAM
- Shared WOPI configuration

**Keycloak — HA Cluster:**
- 2+ Keycloak nodes with Infinispan distributed cache
- Shared PostgreSQL backend (same Galera/Patroni cluster)
- Load-balanced via HAProxy

**Storage — S3 Object Store as Primary:**
- MinIO cluster (multi-node, erasure-coded) or Ceph RGW
- Nextcloud configured with S3 as primary storage backend
- Benefits: infinite scalability, built-in redundancy, no NFS bottlenecks
- Local cache on app nodes for hot files

**Monitoring & Observability:**
- Prometheus + Grafana for metrics
- ELK/Loki stack for centralized logging
- Uptime Kuma or Zabbix for alerting

---

## PART 2: SECURITY HARDENING BASELINE

### 1. CIS Benchmarks for Ubuntu 24.04 LTS

The Center for Internet Security (CIS) publishes prescriptive configuration benchmarks. Ubuntu 24.04 LTS has official CIS Benchmark profiles available via the `ubuntu-security-guide` package.

**Key CIS Level 1 (Server Profile) controls relevant to Nextcloud:**

| Category | Key Controls |
|----------|-------------|
| **Filesystem Partitioning** | Separate partitions for /tmp (nosuid,nodev,noexec), /var, /var/log, /var/log/audit, /home |
| **Package Management** | Uninstall unnecessary packages (X11, compilers, avahi, cups). Keep only required services. Enable automatic security updates (`unattended-upgrades`). |
| **SSH Hardening** | Disable root login (PermitRootLogin no), Protocol 2 only, MaxAuthTries ≤ 4, Idle timeout (ClientAliveInterval 300, ClientAliveCountMax 0), AllowUsers/AllowGroups whitelist. Use SSH keys, disable password auth. |
| **Firewall** | Enable UFW: deny incoming by default, allow only SSH (rate-limited), HTTP/HTTPS. `ufw default deny incoming`, `ufw default allow outgoing`, `ufw limit ssh`, `ufw allow 80/tcp`, `ufw allow 443/tcp`. |
| **Kernel Hardening** | sysctl: net.ipv4.ip_forward=0, net.ipv4.conf.all.send_redirects=0, net.ipv4.conf.all.accept_source_route=0, kernel.randomize_va_space=2, fs.suid_dumpable=0. Enable ASLR, disable core dumps for setuid. |
| **Audit Logging** | Install and enable auditd. Configure rules for sensitive files (see Section 9). |
| **File Permissions** | Verify permissions on /etc/passwd (644), /etc/shadow (640), /etc/group (644), /etc/gshadow (640). Cron allowed/denied files: /etc/cron.allow exists, /etc/cron.deny removed or empty. |
| **User Accounts** | Enforce strong password policy (PAM pwquality: minlen=14, dcredit=-1, ucredit=-1, ocredit=-1, lcredit=-1). Set shell to /usr/sbin/nologin for service accounts. Lock unused accounts. |
| **Time Synchronization** | Configure systemd-timesyncd or chrony with trusted NTP servers. |
| **Logging** | Configure rsyslog or systemd-journald with persistent storage. Remote log forwarding recommended. |

**Automation:** Ubuntu 24.04 provides `ubuntu-security-guide` (USG) for automated CIS hardening:
```bash
sudo apt install ubuntu-security-guide
sudo usg audit cis_level1_server    # Audit current compliance
sudo usg fix cis_level1_server      # Apply Level 1 fixes
```

---

### 2. Nextcloud Security Scanner (scan.nextcloud.com)

The official Nextcloud Security Scan is a free external service that evaluates your publicly accessible Nextcloud instance. It checks:

**What the scanner evaluates:**
1. **Nextcloud version** — checks if you're running the latest stable release (no known CVEs)
2. **PHP version** — must be a supported, non-EOL version (PHP 8.1+ as of 2025)
3. **HTTPS enforcement** — checks for valid TLS certificate, redirect from HTTP to HTTPS
4. **HSTS header** — `Strict-Transport-Security` must be set to at least 15552000 seconds (180 days)
5. **X-Content-Type-Options** — must be `nosniff`
6. **X-Frame-Options** — must be `SAMEORIGIN` or `DENY`
7. **X-Robots-Tag** — should be `none` (prevents indexing of login pages)
8. **Referrer-Policy** — should be `no-referrer` or `strict-origin`
9. **Content-Security-Policy** — Nextcloud sets its own CSP; scanner verifies it's present
10. **X-XSS-Protection** — deprecated but still checked: should be `1; mode=block`
11. **Permissions-Policy** — checks for restrictive feature policy
12. **Database** — checks for supported DB (MySQL 8+ / MariaDB 10.5+ / PostgreSQL 13+)
13. **Server software** — checks web server version disclosure (should be suppressed)

**How to achieve A+ rating:**
- Run the latest Nextcloud stable release
- Use PHP 8.2 or 8.3 (actively supported)
- Enforce HTTPS with valid certificate (Let's Encrypt or commercial)
- Set all security headers correctly (see Section 5)
- Suppress web server version tokens (`server_tokens off;` in Nginx)
- Use PostgreSQL or MariaDB 10.11+
- Keep all Nextcloud apps updated
- Run `occ security:scan` periodically to check internal security state

**Self-check command:**
```bash
sudo -u www-data php /var/www/nextcloud/occ security:scan
```

---

### 3. OWASP Top 10 — Relevance to Nextcloud

The OWASP Top 10 (2021) represents the most critical web application security risks. Here's how each applies to Nextcloud and recommended mitigations:

| OWASP Risk | Relevance to Nextcloud | Mitigation |
|-----------|----------------------|------------|
| **A01: Broken Access Control** | File sharing permissions, group folders, app access. Misconfigured shares can leak data. | Enforce least privilege. Audit share permissions regularly. Use `occ` to verify. Enable brute-force protection. Use 2FA. |
| **A02: Cryptographic Failures** | TLS configuration, password hashing, encryption at rest. | TLS 1.3 with strong ciphers (Section 4). Enable server-side encryption (`occ encryption:enable`) if required. Use HTTPS-only cookies (`'force_ssl' => true` in config.php). |
| **A03: Injection** | SQL injection via apps, LDAP injection, command injection via external storage. | Keep Nextcloud and all apps updated. Use prepared statements (Nextcloud core uses Doctrine DBAL). Validate all user input. Run WAF (ModSecurity) in front. |
| **A04: Insecure Design** | Overly permissive default app settings, missing rate limiting. | Review app permissions before enabling. Enable rate limiting in Nginx (`limit_req_zone`). Use security.txt and responsible disclosure policy. |
| **A05: Security Misconfiguration** | Default config.php settings, verbose error pages, directory listing. | Harden config.php (Section 6). Set `'debug' => false` in production. Disable directory indexing in Nginx (`autoindex off`). Remove default accounts. |
| **A06: Vulnerable Components** | Outdated Nextcloud version, unmaintained third-party apps, old PHP/DB versions. | Automated updates (`occ upgrade`). Monitor apps for deprecation. Use only official/verified apps. Subscribe to security advisories. |
| **A07: Auth Failures** | Weak password policy, no 2FA, session fixation, brute force. | Enforce password policy (occ config:app:set password_policy). Require 2FA (TOTP, WebAuthn, U2F). Set short session lifetime. Enable brute-force protection (built-in). |
| **A08: Software & Data Integrity** | Compromised app store packages, unsigned updates, deserialization attacks. | Nextcloud apps are code-signed. Verify integrity with `occ integrity:check-core`. Use official app store only. Verify checksums of downloaded updates. |
| **A09: Logging & Monitoring** | Insufficient audit trail for file access, login attempts, admin actions. | Enable Nextcloud audit log (`occ config:app:set admin_audit`). Ship logs to centralized SIEM. Configure auditd (Section 9). Monitor with fail2ban (Section 8). |
| **A10: SSRF** | External storage connectors, Collabora WOPI requests, app integrations. | Restrict outbound connections at firewall. Use allowlists for external storage hosts. Validate URLs in app configurations. Run Collabora on isolated network segment. |

**Additional PHP-specific OWASP recommendations:**
- Disable dangerous PHP functions: `disable_functions = exec,passthru,shell_exec,system,proc_open,popen,curl_exec,curl_multi_exec,parse_ini_file,show_source`
- Set `expose_php = Off` (hide PHP version)
- Set `allow_url_fopen = Off` and `allow_url_include = Off`
- Set `open_basedir` to restrict PHP file access to `/var/www/nextcloud:/tmp:/var/lib/php/sessions`
- Enable `session.cookie_httponly = 1` and `session.cookie_secure = 1`
- Set `session.cookie_samesite = "Strict"`

---

### 4. TLS 1.3 Configuration — Mozilla Intermediate Profile

Use the Mozilla SSL Configuration Generator (ssl-config.mozilla.org) for up-to-date configurations. The **Intermediate** profile balances security with compatibility (supports TLS 1.2 + 1.3, works with older clients).

**Nginx configuration (Mozilla Intermediate, OpenSSL 3.x):**

```nginx
# /etc/nginx/conf.d/ssl-hardening.conf

ssl_protocols TLSv1.2 TLSv1.3;
ssl_ecdh_curve X25519:prime256v1:secp384r1;

ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305:DHE-RSA-AES128-GCM-SHA256:DHE-RSA-AES256-GCM-SHA384:DHE-RSA-CHACHA20-POLY1305;

ssl_prefer_server_ciphers off;  # Let client choose among allowed ciphers

# TLS 1.3 cipher suites (OpenSSL 3.x syntax)
ssl_conf_command Ciphersuites TLS_AES_128_GCM_SHA256:TLS_AES_256_GCM_SHA384:TLS_CHACHA20_POLY1305_SHA256;

# OCSP Stapling
ssl_stapling on;
ssl_stapling_verify on;
resolver 1.1.1.1 8.8.8.8 valid=300s;
resolver_timeout 5s;

# Session resumption (improves performance)
ssl_session_cache shared:SSL:50m;
ssl_session_timeout 1d;
ssl_session_tickets off;  # Disable session tickets (PFS)

# DH parameters (if using DHE ciphers)
ssl_dhparam /etc/nginx/dhparam.pem;  # Generate: openssl dhparam -out dhparam.pem 2048

# HSTS (must be in the server block that serves HTTPS)
add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload" always;
```

**Certificate recommendations:**
- Use ECDSA certificates (P-256) for better performance
- Let's Encrypt with certbot auto-renewal
- Minimum key size: RSA 2048-bit, ECDSA P-256
- Monitor certificate expiry (check_ssl_cert or Uptime Kuma)

**Verify with:**
```bash
# Test TLS configuration
curl -sI https://your-nextcloud.example.com | grep -i strict-transport
# External scan
# Submit to https://www.ssllabs.com/ssltest/
```

---

### 5. HTTP Security Headers

Nextcloud sets its own Content-Security-Policy (CSP) from the application layer. Do NOT override it at the web server level — this will break Collabora Online, Talk, and third-party apps. Set all other security headers at the Nginx level.

**Nginx security headers configuration:**

```nginx
# /etc/nginx/conf.d/nextcloud-security-headers.conf

# HSTS — enforce HTTPS (set in SSL block, repeated here for clarity)
add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload" always;

# X-Frame-Options — prevent clickjacking
# Nextcloud needs SAMEORIGIN (not DENY) for some internal iframes
add_header X-Frame-Options "SAMEORIGIN" always;

# X-Content-Type-Options — prevent MIME sniffing
add_header X-Content-Type-Options "nosniff" always;

# Referrer-Policy — control referrer information leakage
add_header Referrer-Policy "strict-origin-when-cross-origin" always;

# Permissions-Policy — restrict browser features
add_header Permissions-Policy "camera=(self), microphone=(self), geolocation=(), interest-cohort=(), autoplay=(self), fullscreen=(self), clipboard-read=(self), clipboard-write=(self)" always;

# X-Robots-Tag — prevent search engine indexing of Nextcloud
add_header X-Robots-Tag "none" always;

# X-Permitted-Cross-Domain-Policies — restrict Adobe Flash/PDF cross-domain
add_header X-Permitted-Cross-Domain-Policies "none" always;

# Cross-Origin-Resource-Policy — control resource sharing
add_header Cross-Origin-Resource-Policy "same-origin" always;

# Cross-Origin-Opener-Policy — process isolation
add_header Cross-Origin-Opener-Policy "same-origin" always;

# Hide Nginx version
server_tokens off;
more_clear_headers Server;  # Requires ngx_headers_more module
```

**Important notes:**
- Always use the `always` parameter so headers are attached even on 4xx/5xx responses
- Do NOT add CSP at Nginx level — Nextcloud manages its own CSP dynamically
- If you must add CSP, use `Content-Security-Policy-Report-Only` first and monitor violation reports
- Test headers with: `curl -sI https://your-nextcloud.example.com` or https://securityheaders.com

**Nextcloud config.php security settings:**
```php
'force_ssl' => true,                    // Redirect all HTTP to HTTPS
'htaccess.RewriteBase' => '/',          // Required for clean URLs
'overwriteprotocol' => 'https',         // Force HTTPS protocol detection
'overwrite.cli.url' => 'https://...',   // HTTPS URL for CLI operations
```

---

### 6. File Permissions Hardening

**Critical file and directory permissions:**

| Path | Owner:Group | Permissions | Notes |
|------|-------------|-------------|-------|
| `/var/www/nextcloud/config/config.php` | www-data:www-data | **640** | Contains DB passwords, secrets, instance ID. NEVER world-readable. |
| `/var/www/nextcloud/config/` | www-data:www-data | 750 | Config directory |
| `/var/www/nextcloud/` | www-data:www-data | 750 | Nextcloud root |
| `/var/www/nextcloud/data/` | www-data:www-data | 750 | Data directory — should be OUTSIDE web root if possible |
| `/var/www/nextcloud/apps/` | www-data:www-data | 750 | Apps directory (except writable apps dir) |
| `/var/www/nextcloud/occ` | www-data:www-data | 750 | CLI tool — executable by www-data only |
| `/var/www/nextcloud/3rdparty/` | www-data:www-data | 750 | Third-party libraries |
| `/var/www/nextcloud/themes/` | www-data:www-data | 750 | Custom themes |

**Data directory outside web root (recommended):**
```bash
# Move data directory outside /var/www
sudo mkdir -p /data/nextcloud
sudo chown www-data:www-data /data/nextcloud
sudo chmod 750 /data/nextcloud
# Update config.php: 'datadirectory' => '/data/nextcloud'
```

**occ command restrictions:**
- occ MUST be run as the HTTP user (www-data), never as root
- Running occ as root creates files owned by root in the data directory, breaking Nextcloud
- Always use: `sudo -u www-data php /var/www/nextcloud/occ <command>`
- Consider creating a wrapper script `/usr/local/bin/occ` that enforces this:
```bash
#!/bin/bash
sudo -u www-data php /var/www/nextcloud/occ "$@"
```

**config.php secrets protection:**
- Database password, Redis password, secret keys, instance ID are in config.php
- 640 permissions prevent other system users from reading these
- Consider moving secrets to environment variables (Nextcloud 27+ supports `NC_*` env vars)
- Backup config.php securely (encrypted backup, restricted access)

**Additional hardening:**
```bash
# Remove write permission from core files after installation
sudo chmod -R u+w,go-w /var/www/nextcloud
sudo chmod -R u+w,go-w /var/www/nextcloud/config
sudo chmod 640 /var/www/nextcloud/config/config.php

# Ensure .htaccess files are present (Apache) or Nginx rules are in place
# Prevent access to hidden files and directories
# Nginx:
location ~ /\. {
    deny all;
    access_log off;
    log_not_found off;
}
```

---

### 7. Container Isolation Considerations — Docker vs. Bare-Metal

**Collabora CODE:**

| Aspect | Docker | Bare-Metal |
|--------|--------|------------|
| **Isolation** | Strong — container has its own filesystem, network namespace, seccomp profile. Collabora Docker image enables Seccomp by default. | Weak — shares OS with Nextcloud. A CODE compromise could affect the host. |
| **Resource control** | Docker limits (--memory, --cpus) prevent resource exhaustion. | Must rely on systemd cgroups or nice values. |
| **Updates** | `docker pull collabora/code` — simple, reproducible. | Manual package updates, dependency management. |
| **Network isolation** | Can run on internal Docker network, only exposed via reverse proxy. | Runs on host network; must firewall carefully. |
| **Recommendation** | **Strongly recommended.** Docker provides defense-in-depth. Run CODE in its own container, on an internal Docker network, with only the WOPI port exposed to Nextcloud. | Only if Docker is not available. Use systemd service with PrivateTmp=true, ProtectSystem=strict, NoNewPrivileges=true. |

**Keycloak:**

| Aspect | Docker | Bare-Metal |
|--------|--------|------------|
| **Isolation** | Container isolation. Keycloak runs as Java process inside container. | Java process on host. JVM security manager can provide some isolation. |
| **Resource control** | Docker memory/cpu limits prevent JVM from consuming all host resources. | JVM heap must be manually tuned; can OOM host if misconfigured. |
| **Updates** | `docker pull keycloak/keycloak:26` — versioned, reproducible. | Manual download and configuration. |
| **Recommendation** | **Recommended.** Docker simplifies deployment and provides resource boundaries. Keycloak's official image is well-maintained. | Acceptable for simpler deployments. Use a dedicated system user, systemd service with sandboxing. |

**Nextcloud itself:**

| Aspect | Docker (AIO / custom compose) | Bare-Metal |
|--------|------------------------------|------------|
| **Isolation** | Each component (Nextcloud, DB, Redis) in separate containers. Network isolation between services. | All services share OS. A compromise of any service can affect others. |
| **Complexity** | Higher — Docker networking, volume management, container orchestration. | Lower — standard Linux package management. |
| **Performance** | ~5-10% overhead from containerization. Negligible for most deployments. | Native performance, no abstraction overhead. |
| **Security** | Defense in depth. Each service in its own security context. Read-only root filesystems possible. | Simpler attack surface but less compartmentalization. |
| **Recommendation** | **Recommended for Medium+ tiers.** Nextcloud AIO provides A+ security scan rating out of the box. | Acceptable for Small tier or when Docker is not desired. Use systemd sandboxing. |

**Container hardening best practices:**
- Run containers as non-root user (USER directive)
- Use read-only root filesystem where possible (`read_only: true`)
- Drop all capabilities, add only required ones (`cap_drop: ALL`)
- Enable seccomp and AppArmor profiles
- Use `--security-opt=no-new-privileges:true`
- Never expose Docker socket to containers
- Scan images for vulnerabilities (Trivy, Docker Scout)
- Use specific image tags (not `:latest`) for reproducibility

---

### 8. fail2ban Configuration for Nextcloud

fail2ban monitors log files for authentication failures and bans offending IP addresses via firewall rules.

**Installation:**
```bash
sudo apt install fail2ban
```

**Nextcloud jail configuration — `/etc/fail2ban/jail.d/nextcloud.local`:**

```ini
[nextcloud]
enabled = true
port = 80,443
protocol = tcp
filter = nextcloud
logpath = /data/nextcloud/nextcloud.log
maxretry = 5
bantime = 3600        # 1 hour ban
findtime = 600        # 10 minute window
backend = polling      # Use polling for files outside /var/log
```

**Filter definition — `/etc/fail2ban/filter.d/nextcloud.conf`:**

```ini
[Definition]
_groupsre = (?:(?:,?\s*"\w+":(?:"[^"]+"|\w+|\{[^}]*\})))
failregex = ^\{%(_groupsre)s,?\s*"remoteAddr":"<HOST>"%(_groupsre)s,?\s*"message":"Login failed:
            ^\{%(_groupsre)s,?\s*"remoteAddr":"<HOST>"%(_groupsre)s,?\s*"message":"Trusted domain error.
            ^\{%(_groupsre)s,?\s*"remoteAddr":"<HOST>"%(_groupsre)s,?\s*"message":"Two-factor challenge failed.
ignoreregex =
```

**Additional jails for Nextcloud ecosystem:**

```ini
# /etc/fail2ban/jail.d/nextcloud-extra.local

[nginx-http-auth]
enabled = true
port = 80,443
filter = nginx-http-auth
logpath = /var/log/nginx/error.log
maxretry = 3
bantime = 3600

[nginx-botsearch]
enabled = true
port = 80,443
filter = nginx-botsearch
logpath = /var/log/nginx/access.log
maxretry = 5
bantime = 7200

[sshd]
enabled = true
port = ssh
filter = sshd
logpath = /var/log/auth.log
maxretry = 3
bantime = 3600
findtime = 600

[keycloak]
enabled = true
port = 80,443
filter = keycloak
logpath = /var/log/keycloak/keycloak.log
maxretry = 5
bantime = 3600
```

**Keycloak filter — `/etc/fail2ban/filter.d/keycloak.conf`:**
```ini
[Definition]
failregex = ^.*type=LOGIN_ERROR.*ipAddress=<HOST>.*$
ignoreregex =
```

**Verification:**
```bash
sudo fail2ban-client status nextcloud
sudo fail2ban-client set nextcloud unbanip <IP>  # Manual unban
sudo fail2ban-regex /data/nextcloud/nextcloud.log /etc/fail2ban/filter.d/nextcloud.conf  # Test filter
```

**Important:** Nextcloud has built-in brute-force protection since v15. fail2ban adds a network-layer defense that blocks attackers before they reach the application. Use both.

---

### 9. auditd Rules for Monitoring Sensitive Files

auditd (Linux Audit Daemon) monitors file access, modifications, and system calls. Essential for detecting unauthorized changes to Nextcloud configuration and data.

**Installation:**
```bash
sudo apt install auditd audispd-plugins
sudo systemctl enable --now auditd
```

**auditd rules — `/etc/audit/rules.d/nextcloud.rules`:**

```bash
# Delete any existing rules
-D

# Set buffer size (increase for busy systems)
-b 8192

# Monitor Nextcloud config.php — any write or attribute change
-w /var/www/nextcloud/config/config.php -p wa -k nextcloud_config

# Monitor Nextcloud config directory
-w /var/www/nextcloud/config/ -p wa -k nextcloud_config_dir

# Monitor Nextcloud data directory — writes and attribute changes
-w /data/nextcloud/ -p wa -k nextcloud_data

# Monitor Nextcloud application files — writes (detect unauthorized modifications)
-w /var/www/nextcloud/ -p wa -k nextcloud_app

# Monitor occ command execution
-w /var/www/nextcloud/occ -p x -k nextcloud_occ_exec

# Monitor web server configuration
-w /etc/nginx/ -p wa -k nginx_config
-w /etc/apache2/ -p wa -k apache_config

# Monitor PHP configuration
-w /etc/php/ -p wa -k php_config

# Monitor SSL/TLS certificates
-w /etc/letsencrypt/ -p wa -k ssl_certs
-w /etc/ssl/ -p wa -k ssl_config

# Monitor system authentication files
-w /etc/passwd -p wa -k system_auth
-w /etc/shadow -p wa -k system_auth
-w /etc/group -p wa -k system_auth
-w /etc/sudoers -p wa -k system_auth

# Monitor SSH configuration
-w /etc/ssh/sshd_config -p wa -k ssh_config

# Monitor cron jobs
-w /etc/crontab -p wa -k cron_changes
-w /etc/cron.d/ -p wa -k cron_changes
-w /etc/cron.daily/ -p wa -k cron_changes

# Monitor fail2ban configuration
-w /etc/fail2ban/ -p wa -k fail2ban_config

# Monitor auditd configuration itself
-w /etc/audit/ -p wa -k audit_config

# Monitor database files (PostgreSQL)
-w /var/lib/postgresql/ -p wa -k postgresql_data

# Make rules immutable (requires reboot to change)
-e 2
```

**Apply rules:**
```bash
sudo augenrules --load
sudo auditctl -l  # List active rules
```

**Search audit logs:**
```bash
# Search for config.php modifications
sudo ausearch -k nextcloud_config

# Search for today's events
sudo ausearch -ts today -k nextcloud_data

# Generate report of all Nextcloud-related events
sudo aureport -f -i --summary | grep nextcloud

# Real-time monitoring
sudo ausearch -k nextcloud_config -i --raw | sudo aureport -f -i
```

**Log rotation:** auditd logs can grow large. Configure rotation in `/etc/audit/auditd.conf`:
```
max_log_file = 100
max_log_file_action = ROTATE
num_logs = 10
```

---

### 10. AIDE (File Integrity Monitoring)

AIDE (Advanced Intrusion Detection Environment) creates a cryptographic baseline of file attributes and detects unauthorized changes. Essential for detecting rootkits, backdoors, and unauthorized configuration changes.

**Installation:**
```bash
sudo apt install aide aide-common
```

**Initialization:**
```bash
# Initialize the AIDE database (creates baseline snapshot)
sudo aideinit
# This creates /var/lib/aide/aide.db.new
# Rename it to activate:
sudo mv /var/lib/aide/aide.db.new /var/lib/aide/aide.db
```

**AIDE configuration — `/etc/aide/aide.conf` (add Nextcloud-specific rules):**

```
# Nextcloud application files — monitor all attributes
/var/www/nextcloud/config/config.php   CONTENT_EXISTS
/var/www/nextcloud/config/             DIR_ATTRS
/var/www/nextcloud/occ                 CONTENT_EXISTS
/var/www/nextcloud/apps/               DIR_ATTRS
/var/www/nextcloud/3rdparty/           DIR_ATTRS

# Nextcloud data directory — monitor for new/deleted files
/data/nextcloud/                       DIR_ATTRS

# Web server configuration
/etc/nginx/                            DIR_ATTRS
/etc/apache2/                          DIR_ATTRS

# PHP configuration
/etc/php/                              DIR_ATTRS

# SSL certificates
/etc/letsencrypt/live/                 DIR_ATTRS
/etc/ssl/                              DIR_ATTRS

# System authentication
/etc/passwd                            CONTENT_EXISTS
/etc/shadow                            CONTENT_EXISTS
/etc/group                             CONTENT_EXISTS
/etc/sudoers                           CONTENT_EXISTS
/etc/sudoers.d/                        DIR_ATTRS

# SSH
/etc/ssh/sshd_config                   CONTENT_EXISTS

# Cron
/etc/crontab                           CONTENT_EXISTS
/etc/cron.d/                           DIR_ATTRS
/etc/cron.daily/                       DIR_ATTRS

# fail2ban
/etc/fail2ban/                         DIR_ATTRS

# auditd
/etc/audit/                            DIR_ATTRS

# Database configuration
/etc/postgresql/                       DIR_ATTRS

# Exclude directories that change legitimately
!/var/www/nextcloud/data/updater-*/
!/var/www/nextcloud/data/appdata_*/
!/var/log/
!/var/spool/
!/tmp/
!/proc/
!/sys/
!/dev/
!/run/
```

**Regular checks:**
```bash
# Manual check
sudo aide --check

# After legitimate changes (updates, config changes), update the baseline:
sudo aide --update
sudo mv /var/lib/aide/aide.db.new /var/lib/aide/aide.db

# Automate with cron (daily check at 3 AM):
echo '0 3 * * * root /usr/bin/aide --check | /usr/bin/mail -s "AIDE Report $(hostname)" admin@example.com' | sudo tee /etc/cron.d/aide-check
```

**Integration with monitoring:**
- Pipe AIDE output to centralized logging (ELK, Loki)
- Configure alerting for any AIDE changes
- Run AIDE check after every Nextcloud upgrade and update the baseline

---

## Summary Checklist — Medium Tier (10-50 users)

### Infrastructure
- [ ] 4-6 vCPU, 16 GB RAM, 100 GB SSD, 1 TB bulk storage
- [ ] PHP-FPM: 15-20 workers, OPcache enabled
- [ ] PostgreSQL: shared_buffers=4GB, effective_cache_size=12GB
- [ ] Redis: maxmemory 512MB, configured for locking + cache
- [ ] Elasticsearch: 2 GB heap (if full-text search needed)
- [ ] Collabora CODE: Docker container, 2 GB RAM
- [ ] Keycloak: 1 GB heap, PostgreSQL backend
- [ ] ClamAV: daemon mode, 300-500 MB
- [ ] Data directory outside web root (/data/nextcloud)

### Security
- [ ] CIS Level 1 hardening applied (USG or manual)
- [ ] UFW firewall: deny incoming, allow SSH/HTTP/HTTPS
- [ ] SSH: key-only auth, no root login
- [ ] TLS 1.3 Mozilla Intermediate profile
- [ ] All HTTP security headers set (HSTS, X-Frame-Options, X-Content-Type-Options, Referrer-Policy, Permissions-Policy)
- [ ] config.php: 640 permissions, data dir outside web root
- [ ] occ run only as www-data user
- [ ] PHP hardening: dangerous functions disabled, expose_php=Off
- [ ] fail2ban: Nextcloud jail + nginx + sshd jails active
- [ ] auditd: rules monitoring config.php, data dir, system files
- [ ] AIDE: baseline initialized, daily integrity checks
- [ ] Automatic security updates enabled (unattended-upgrades)
- [ ] Nextcloud security scan: A+ rating verified
- [ ] 2FA enforced for all users
- [ ] Brute-force protection enabled
- [ ] Server version tokens suppressed
- [ ] Regular backups: DB dump + config + data (daily)

---

## References

1. Nextcloud Administration Manual — System Requirements: https://docs.nextcloud.com/server/stable/admin_manual/installation/system_requirements.html
2. Nextcloud Administration Manual — Server Tuning: https://docs.nextcloud.com/server/stable/admin_manual/installation/server_tuning.html
3. Nextcloud Administration Manual — Hardening Guide: https://docs.nextcloud.com/server/stable/admin_manual/installation/harden_server.html
4. Nextcloud Security Scanner: https://scan.nextcloud.com
5. CIS Benchmarks — Ubuntu Linux: https://www.cisecurity.org/benchmark/ubuntu_linux
6. Mozilla SSL Configuration Generator: https://ssl-config.mozilla.org
7. OWASP Top 10 (2021): https://owasp.org/www-project-top-ten/
8. Keycloak High Availability Guide — CPU/Memory Sizing: https://www.keycloak.org/high-availability/multi-cluster/concepts-memory-and-cpu-sizing
9. Collabora Online System Requirements: https://www.collaboraonline.com/faqs/
10. MassiveGRID — Nextcloud Security Hardening Guide: https://massivegrid.com/blog/nextcloud-security-hardening-complete-guide/
11. MassiveGRID — Scaling Nextcloud to 1000+ Users: https://massivegrid.com/blog/nextcloud-scale-1000-users-enterprise-architecture/

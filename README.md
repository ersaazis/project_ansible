# HomeLab Ansible Configuration

This repository contains the Ansible playbooks and inventory for managing the HomeLab infrastructure across multiple environments. The architecture is designed to be highly modular and automated, specifically built to integrate seamlessly with an Ansible Semaphore UI.

## Directory Structure

- `inventories/`: Environment-specific inventories.
    - `development/`, `staging/`, `mirror/`, `production/`.
    - Each environment has `group_vars` and `host_vars`.
- `host_vars/<hostname>/`: Host-specific variables.
    - `vars.yml`: General (non-sensitive) host variables.
    - `vault.yml`: Sensitive host variables (SSH user, passwords, DB root passwords). **Encrypt these with `ansible-vault`!**
- `roles/`: Modular Ansible roles:
    - `*_install`: Role for package/binary installation.
    - `*_service`: Role for service lifecycle management (start, stop, restart, reload).
    - `*_config`: Role for configuration and templating.
    - `*_backup`: Role for database backup logic (MySQL/Postgres).
- `playbooks/`: Organized logic divided into explicit execution categories.
    - `setup/`: Initial provisioning and configuration (e.g., `setup-docker.yml`).
    - `service/`: Service management using tags (e.g., `service-mysql.yml`).
    - `configure/`: Configuration tuning (e.g., `config-postgres.yml`).
    - `other/`: Auxiliary operations like Database Backups (e.g., `backup-mysql.yml`).
- `provision/`: Contains `provision-semaphore.py` for automated Semaphore UI configuration.

## Automated Provisioning

This project uses a custom Python script to synchronize playbooks with [Ansible Semaphore](https://ansible-semaphore.com/):

```bash
# Script is automatically run by the 'provisioner' container in docker-compose.yml
docker compose restart provisioner
```

The script manages views, task templates, and schedules based on the `playbooks/` subdirectory structure.
## Automated Vault Encryption

To simplify secret management, use the `./vault-encrypt.sh` script:
1.  Set `ANSIBLE_VAULT_PASSWORD` in `.env.vault`.
2.  Run `./vault-encrypt.sh`.
    - If `vault.yml.temp` exists, it will re-encrypt your changes into `vault.yml`.
    - If `vault.yml.temp` is missing, it will decrypt `vault.yml` so you can edit it via `vault.yml.temp`.

## Security

- Sensitive data MUST be managed at the host level in `host_vars/<hostname>/vault.yml`.
- Never commit plain-text internal secrets.
- Global secrets are in `group_vars/vault.yml`.

## Configuration & Standards

- **Timezone**: Set to `Asia/Jakarta` globally in `group_vars/all.yml`.
- **Monitoring**: Controlled by `enable_monitoring` flag in `host_vars`.
- **Backup**: Controlled by `enable_backup` flag in `host_vars`. Triggered via `playbooks/other/` calling respective backup tags.

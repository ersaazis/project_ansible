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
    - `docker`: Official Docker Engine installation.
    - `mysql` & `postgres`: Database setup with environment-specific passwords and built-in backup tasks.
    - `alloy_setup` & `alloy_config`: Modular Grafana Alloy installation and dynamic configuration.
    - `terraform` & `ansible_install`: Tools for the control node.
    - `openinfraquote`: Application repository and deployment logic.
- `playbooks/`: Organized logic divided into explicit execution categories.
    - `setup/`: Initial provisioning and configuration.
    - `restart/`: Restarts services cleanly.
    - `other/`: Specific operations like Database Backups (e.g., `mysql.yml`, `postgres.yml`).
- `site.yml`: Master playbook that orchestrates the entire deployment.

## Deployment

To deploy the entire stack:
```bash
ansible-playbook -i inventories/staging/hosts.yml site.yml
```

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

## AI Assistant Guidelines

> **🚨 CRITICAL INSTRUCTION FOR AI ASSISTANTS 🚨**
> If the user asks you to "update context", "pelajari project ini", or requests an update to the project's documentation/rules, you **MUST** use the `mcp:sequential-thinking` (Sequential Thinking) tool to meticulously study the project's directory structure, roles, playbooks, variables, and scripts from scratch. Do this to capture the latest architecture, flow, and pattern changes, and then update both `GEMINI.md` and `README.md` to reflect the new state accurately.

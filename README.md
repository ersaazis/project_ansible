# HomeLab Ansible Configuration

This repository contains the Ansible playbooks and inventory for managing the HomeLab infrastructure across multiple environments.

## Directory Structure

- `inventories/`: Environment-specific inventories.
    - `development/`, `staging/`, `mirror/`, `production/`.
    - Each environment has `group_vars` and `host_vars`.
- `host_vars/<hostname>/`: Host-specific variables.
    - `vars.yml`: General (non-sensitive) host variables.
    - `vault.yml`: Sensitive host variables (SSH user, passwords, DB root passwords). **Encrypt these with `ansible-vault`!**
- `roles/`: Modular Ansible roles:
    - `docker`: Official Docker Engine installation.
    - `mysql`: Database setup with environment-specific passwords.
    - `alloy_setup` & `alloy_config`: Modular Grafana Alloy installation and dynamic configuration.
    - `terraform` & `ansible_install`: Tools for the control node.
    - `openinfraquote`: Application repository and deployment logic.
- `playbooks/`: Individual playbooks for each service.
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
    - If `vault.yml.temp` is missing, it will decrypt `vault.yml` so you can edit it.

## Security

- Sensitive data is managed at the host level in `host_vars/<hostname>/vault.yml`.
- Use `ansible-vault encrypt` on all `vault.yml` files before committing.
- Global secrets are in `group_vars/vault.yml`.

## Configuration

- **Timezone**: Set to `Asia/Jakarta` globally in `group_vars/all.yml`.
- **Monitoring**: Controlled by `enable_monitoring` flag in `host_vars`.
- **Backup**: Controlled by `enable_backup` flag in `host_vars`.

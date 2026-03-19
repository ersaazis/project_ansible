# Gemini Knowledge & Project Preferences

This file documents key architectural decisions and user preferences for this project.

## User Preferences
- **YAML Formatting**: DO NOT use `---` at the beginning of Ansible/YAML files unless multiple documents are in the same file.
- **Variable Placement**: 
    - Secrets (SSH user, passwords, DB root passwords) MUST be in `host_vars/<hostname>/vault.yml`.
    - Non-sensitive host vars (monitoring flags, DB types) MUST be in `host_vars/<hostname>/vars.yml`.
    - Global non-sensitive vars go to `group_vars/all.yml`.
- **Vault Automation**: 
    - Use `./vault-encrypt.sh` for bidirectional sync.
    - If `.temp` exists: Updates and encrypts `vault.yml` based on it.
    - If `.temp` is missing: Decrypts `vault.yml` to create a new `.temp` for editing.
    - The vault password must be retrieved from `.env.vault` (`ANSIBLE_VAULT_PASSWORD`).
- **Timezone**: Default project timezone is `Asia/Jakarta`.

## Project Architecture
- **Environment Separation**: Four distinct environments (`development`, `staging`, `mirror`, `production`).
- **Alloy Configuration**:
    - Modularized into `alloy_setup` and `alloy_config`.
    - Config fragments stored in `ansible/config/alloy/<env>/`.
    - Alloy runs as **root** via systemd override for full system visibility.
    - Uses `Environment=` in systemd override to supply variables for `sys.env()` in fragments.
- **Database Logic**:
    - Variable `database_server` defines the type (`mysql` or `postgres`).
    - Used in Alloy templates to include the correct monitoring fragment.

## Host Variables Reference
- `enable_monitoring`: boolean (all hosts).
- `enable_backup`: boolean (DB hosts).
- `database_server`: 'mysql' or 'postgres'.

# Gemini Knowledge & Project Preferences

This file documents key architectural decisions, rules, and user preferences for this project. **AI Models MUST read AND strictly adhere to these rules before suggesting or making changes.**

> **🚨 CRITICAL INSTRUCTION FOR AI ASSISTANTS 🚨**
> If the user asks you to "update context", "pelajari project ini", or requests an update to the project's documentation/rules, you **MUST** use the `mcp:sequential-thinking` (Sequential Thinking) tool to meticulously study the project's directory structure, roles, playbooks, variables, and scripts from scratch. Do this to capture the latest architecture, flow, and pattern changes, and then update both `GEMINI.md` and `README.md` to reflect the new state accurately. Do not make assumptions without analyzing the workspace first.

## Strict User Preferences & AI Guidelines
- **YAML Formatting**: DO NOT use `---` at the beginning of Ansible/YAML files unless multiple documents are in the same file.
- **Variable Placement Rules**: 
    - **Secrets** (SSH user, passwords, DB root passwords): MUST be placed in `host_vars/<hostname>/vault.yml`.
    - **Non-sensitive host vars** (monitoring flags, DB types): MUST be placed in `host_vars/<hostname>/vars.yml`.
    - **Global non-sensitive vars**: MUST go to `group_vars/all.yml` or global `group_vars/`.
- **Vault Automation**: 
    - NEVER edit `vault.yml` directly if encrypted. Use `./vault-encrypt.sh` for bidirectional sync.
    - If `<file>.temp` exists: The script updates and encrypts `vault.yml` based on the `.temp` file.
    - If `<file>.temp` is missing: The script decrypts `vault.yml` to create a new `.temp` for editing.
    - Submitting changes: Run the script to apply edits from `.temp` into the encrypted `vault.yml`.
    - The vault password must be retrieved from `.env.vault` (`ANSIBLE_VAULT_PASSWORD`).
- **Timezone**: Default project timezone is `Asia/Jakarta`.

## Project Architecture & Playbook Structure
- **Environment Separation**: Four distinct environments (`development`, `staging`, `mirror`, `production`).
- **Playbook Organization** (within `playbooks/` directory):
    - `setup/`: Initial installation and configuration (e.g., `setup-docker.yml`).
    - `restart/`: Service restarts (e.g., `restart-mysql.yml`).
    - `configure/`: Configuration updates and tuning (e.g., `config-postgres.yml`).
    - `other/`: Auxiliary operations, primarily `Backup` (e.g., `backup-mysql.yml`).
    - `build/`: Reserved for CI/CD build tasks.
    - `deploy/`: Reserved for application deployment tasks.
- **Explicit Naming**: All playbooks within subdirectories MUST follow the `<category>-<service>.yml` naming convention to ensure clarity and avoid ambiguity.
- **Semaphore Automation**: The `./provision/provision-semaphore.py` script automatically manages Semaphore configuration:
    - Scans `playbooks/` subdirectories to create corresponding Views and Task Templates.
    - Automatically cleans up orphaned Task Templates when local playbooks are removed.
    - Configures automated schedules for `Backup` playbooks in the `other/` category.
- **Role Structure Conventions**:
    - **Modular Roles**: For complex services (e.g., databases), functionality is split into separate roles: `_install`, `_config`, `_service`, and `_backup`.
    - **Simple Roles**: Kept as a single role (e.g., `openinfraquote`).
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

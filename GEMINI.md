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
    - The vault password must be retrieved from `.env.vault` (`ANSIBLE_VAULT_PASSWORD`).
- **SSH Connectivity**: 
    - The project uses standard SSH keys extracted from Vault before each playbook run.
    - `ansible_ssh_private_key_file` path is globally set to `/tmp/ssh_key_{{ inventory_hostname }}.pem`.
- **Timezone**: Default project timezone is `Asia/Jakarta`.

## Project Architecture & Playbook Structure
- **Environment Separation**: Four distinct environments (`development`, `staging`, `mirror`, `production`).
- **Playbook Organization** (within `playbooks/` directory):
    - `common/`: Shared tasks/playbooks (e.g. `extract-ssh-key.yml`). Added to 'Common' view in Semaphore.
    - `setup/`: Initial installation/core configuration (e.g., `setup-semaphore.yml`, `setup-observability.yml`).
    - `service/`: Service lifecycle management (e.g., `service-semaphore.yml`).
    - `configure/`: Fine-tuning configuration (e.g., `config-mysql.yml`).
    - `other/`: Auxiliary operations like `Backup` (e.g., `backup-mysql.yml`).
- **Explicit Naming**: All playbooks in category subdirectories MUST follow the `<category>-<service>.yml` naming convention.
- **Semaphore Automation**: The `./provision/provision-semaphore.py` script automatically manages Semaphore configuration:
    - Scans `playbooks/` subdirectories to create corresponding Views and Task Templates.
    - **Service Category**: Task Templates in the `service` category default to the `start` tag (`--tags start`).
    - **Tag Documentation**: Service template descriptions explicitly list supported tags (`start`, `stop`, `restart`, `reload`).
    - Automatically cleans up orphaned Task Templates when local playbooks are removed.
    - Configures automated schedules for `Backup` playbooks in the `other/` category.
- **Role Structure Conventions**:
    - **Modular Roles**: Complex services are split into single-responsibility roles: `_install`, `_config`, `_service`, and `_backup`.
    - **Service Actions**: ALL `_service` roles MUST support standard tags: `start`, `stop`, `restart`, and `reload`.
    - **Default Start**: `_service` roles implement logic (`when: ansible_run_tags | length == 0 or 'start' in ansible_run_tags`) to ensure the `start` task runs by default.
- **Template Robustness (Semaphore Compatibility)**:
    - ALWAYS use `# {{ role_path }}/templates/` prefix in `template` or `copy` `src` to avoid file resolution errors in Semaphore containers.
- **Postgres Handling**:
    - `apt` tasks for Postgres installation MUST include `retries`, `delay`, and `cache_valid_time` to mitigate frequent locking by `unattended-upgrades`.
- **Alloy Configuration**:
    - Modularized into `alloy_install`, `alloy_config`, and `alloy_service`.
    - Config fragments stored in `ansible/roles/alloy_config/templates/fragment/<env>/`.
    - **Dynamic Resolution**: Fragments are included based on environment name (`inventory_dir | basename`).
    - Alloy runs as **root** via systemd override for full system visibility (e.g., Docker socket, system logs).
    - Uses `EnvironmentFile=` in systemd override to supply variables for `sys.env()` in fragments.
- **Global Configuration**:
    - A global `ansible.cfg` in the project root defines `roles_path = ./roles` to ensure correct role discovery by Semaphore when running playbooks from subdirectories.

## Host Variables Reference
- `enable_monitoring`: boolean (all hosts).
- `enable_backup`: boolean (DB hosts).
- `database_server`: 'mysql' or 'postgres'.
- `database_server` is also used in `alloy_config` to dynamically include DB monitoring fragments.

## Host Variables Reference
- `enable_monitoring`: boolean (all hosts).
- `enable_backup`: boolean (DB hosts).
- `database_server`: 'mysql' or 'postgres'.

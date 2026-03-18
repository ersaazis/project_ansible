# Ansible Semaphore Development Stack

This directory contains the Ansible configuration and Semaphore UI setup for the homelab environment. It features automated provisioning and secure environment management.

## Directory Structure

- `docker-compose.yml`: Manages the Semaphore and Postgres services.
- `inventory.yml`: Ansible inventory with hierarchical grouping (tagging).
- `scripts/`:
  - `provision-semaphore.py`: Automated setup script for Semaphore projects and environments.
- `roles/`: Ansible roles.
- `config/`: Configuration templates (e.g., Alloy).

## Setup & Deployment

### 1. Environment Configuration
The stack uses split environment files for security. Before starting, create your `.env` files from the templates:
```bash
cp .env.semaphore.example .env.semaphore
cp .env.db.example .env.db
cp .env.provisioner.example .env.provisioner
```
Edit the `.env.*` files with your actual credentials.

### 2. Start the Stack
```bash
docker compose up -d
```
The `provisioner` service will automatically:
- Create the **HomeLab** project in Semaphore.
- Register the local repository and `inventory.yml`.
- Inject environment variables detected from `inventory.yml`.

## How to use "Tags" (Groups)

Target hosts in your commands or playbooks using group names:
- `development`: All development nodes.
- `app_servers`: Application-specific nodes.
- `db_servers`: Database-specific nodes.

Example:
```bash
ansible -i inventory.yml app_servers -m ping
```

## Security Note

- **Passphrases & Secrets**: These are stored in `.env.provisioner` and injected into Semaphore's "Environment" variables.
- **Git**: The `.gitignore` prevents your active `.env.*` files from being committed.

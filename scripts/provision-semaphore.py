import json
import os
import time
import urllib.request
import re
import urllib.error
import glob

"""
Semaphore Provisioning Script
=============================

This script automates the initial setup of Ansible Semaphore.
It scans the 'playbooks' directory to create Task Templates for:
1. Setup
2. Restart
3. Schedule (with cron)
"""

SEMAPHORE_URL = os.getenv("SEMAPHORE_URL", "http://semaphore:3000/api")
ADMIN_USER = os.getenv("SEMAPHORE_ADMIN", "admin")
ADMIN_PASS = os.getenv("SEMAPHORE_ADMIN_PASSWORD", "admin")

# Default cron schedules for specific playbooks in the 'other' category
DEFAULT_SCHEDULES = {
    "mysql.yml": "0 2 * * *",    # Daily at 2 AM
    "postgres.yml": "0 3 * * *", # Daily at 3 AM
}

def api_call(path, method="GET", data=None, headers=None):
    if headers is None:
        headers = {"Content-Type": "application/json"}
    
    url = f"{SEMAPHORE_URL}{path}"
    req_data = json.dumps(data).encode("utf-8") if data else None
    
    req = urllib.request.Request(url, data=req_data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as res:
            if res.status == 204:
                return True
            content = res.read().decode("utf-8")
            return json.loads(content) if content else True
    except urllib.error.HTTPError as e:
        print(f"Error calling {url}: {e}")
        try:
            error_body = e.read().decode("utf-8")
            print(f"Response body: {error_body}")
        except:
            pass
        return None
    except Exception as e:
        print(f"Error calling {url}: {e}")
        return None

def wait_for_semaphore():
    print(f"Waiting for Semaphore at {SEMAPHORE_URL}...")
    for _ in range(30):
        try:
            with urllib.request.urlopen(f"{SEMAPHORE_URL}/auth/login", timeout=2):
                print("Semaphore is up!")
                return True
        except:
            time.sleep(2)
    return False

def create_task_template(project_id, name, playbook, inventory_id, repo_id, env_id, key_id, vault_key_id, tag, headers):
    """Creates or updates a Task Template and returns its ID."""
    templates = api_call(f"/project/{project_id}/templates", headers=headers) or []
    template = next((t for t in templates if t["name"] == name), None)
    
    views = api_call(f"/project/{project_id}/views", headers=headers) or []
    view_id = views[0]["id"] if views else None

    # Determine if this should run with become
    is_setup = "Setup" in name
    
    data = {
        "project_id": project_id,
        "inventory_id": inventory_id,
        "repository_id": repo_id,
        "environment_id": env_id,
        "ssh_key_id": key_id,
        "view_id": view_id,
        "app": "ansible",
        "name": name,
        "playbook": playbook,
        "arguments": "[]",
        "allow_override_args_in_task": True,
        "description": f"Automated template for {playbook}",
        "task_params": {"allow_debug": True, "tags": [tag]},
        "vaults": [{"project_id": project_id, "vault_key_id": vault_key_id, "type": "password"}] if vault_key_id else []
    }

    if not template:
        print(f"Creating Task Template: {name}")
        res = api_call(f"/project/{project_id}/templates", method="POST", data=data, headers=headers)
        return res["id"] if res and isinstance(res, dict) else None
    else:
        print(f"Updating Task Template: {name}")
        data["id"] = template["id"]
        if vault_key_id:
            data["vaults"][0]["template_id"] = template["id"]
        api_call(f"/project/{project_id}/templates/{template['id']}", method="PUT", data=data, headers=headers)
        return template["id"]

def create_schedule(project_id, template_id, name, cron, repo_id, headers):
    """Creates or updates a schedule for a template."""
    schedules = api_call(f"/project/{project_id}/schedules", headers=headers) or []
    schedule = next((s for s in schedules if s["template_id"] == template_id), None)
    
    data = {
        "project_id": project_id,
        "template_id": template_id,
        "name": name,
        "cron_format": cron,
        "active": True,
        "run_once": False,
        "delete_after_run": False,
        "task_params": {
            "params": {},
            "environment": "{}"
        },
        "run_at": None,
        "type": ""
    }
    
    if not schedule:
        print(f"Creating Schedule for {name}: {cron}")
        return api_call(f"/project/{project_id}/schedules", method="POST", data=data, headers=headers)
    else:
        # Check if update is needed
        existing_cron = schedule.get("cron_format")
        if existing_cron != cron or schedule.get("name") != name or not schedule.get("active"):
            print(f"Updating Schedule for {name}: {cron}")
            data["id"] = schedule["id"]
            return api_call(f"/project/{project_id}/schedules/{schedule['id']}", method="PUT", data=data, headers=headers)
        return schedule

def main():
    if not wait_for_semaphore():
        print("Semaphore did not start in time. Exiting.")
        return

    # 1. Login
    print("Logging in...")
    auth_req = urllib.request.Request(f"{SEMAPHORE_URL}/auth/login", 
                                      data=json.dumps({"auth": ADMIN_USER, "password": ADMIN_PASS}).encode("utf-8"),
                                      headers={"Content-Type": "application/json"},
                                      method="POST")
    try:
        with urllib.request.urlopen(auth_req) as res:
            cookie = res.info().get("Set-Cookie")
            if not cookie:
                print("No cookie received.")
                return
            session_cookie = cookie.split(";")[0]
            print("Successfully authenticated.")
    except Exception as e:
        print(f"Login failed: {e}")
        return

    headers = {"Content-Type": "application/json", "Cookie": session_cookie}

    # 2. Project Setup
    projects = api_call("/projects", headers=headers) or []
    project = next((p for p in projects if p["name"] == "HomeLab"), None)
    if not project:
        print("Creating project 'HomeLab'...")
        project = api_call("/projects", method="POST", data={"name": "HomeLab"}, headers=headers)
    
    if not project:
        print("Failed to find or create project 'HomeLab'.")
        return
    project_id = project["id"]

    # 3. Keys Setup
    keys = api_call(f"/project/{project_id}/keys", headers=headers) or []
    
    # Repo Key (None for local)
    key_id = next((k["id"] for k in keys if k["name"] == "None"), None)
    if not key_id:
        print("Creating 'None' SSH Key...")
        res = api_call(f"/project/{project_id}/keys", method="POST", 
                        data={"project_id": project_id, "name": "None", "type": "none"}, headers=headers)
        key_id = res["id"] if res else None

    def read_vault_pass():
        env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env.vault")
        if os.path.exists(env_path):
            with open(env_path, "r") as f:
                for line in f:
                    if line.startswith("ANSIBLE_VAULT_PASSWORD="):
                        return line.split("=", 1)[1].strip()
        return os.environ.get("ANSIBLE_VAULT_PASSWORD", "change_me")

    vault_password = read_vault_pass()

    # Vault Key
    vault_key_name = "Ansible Vault Password"
    vault_key = next((k for k in keys if k["name"] == vault_key_name), None)
    vault_key_data = {
        "project_id": project_id,
        "name": vault_key_name, 
        "type": "login_password", 
        "login_password": {"password": vault_password, "username": "vault"}
    }
    
    if not vault_key:
        print(f"Creating '{vault_key_name}' Key...")
        res = api_call(f"/project/{project_id}/keys", method="POST", data=vault_key_data, headers=headers)
        vault_key_id = res["id"] if res else None
    else:
        print(f"Updating '{vault_key_name}' Key...")
        vault_key_data["id"] = vault_key["id"]
        api_call(f"/project/{project_id}/keys/{vault_key['id']}", method="PUT", data=vault_key_data, headers=headers)
        vault_key_id = vault_key["id"]

    # 4. Repo Setup
    repos = api_call(f"/project/{project_id}/repositories", headers=headers) or []
    repo = next((r for r in repos if r["name"] == "HomeLab Ansible"), None)
    if not repo:
        print("Registering Ansible Repository...")
        repo = api_call(f"/project/{project_id}/repositories", method="POST",
                        data={"project_id": project_id, "name": "HomeLab Ansible", "git_url": "/home/semaphore/ansible", "git_branch": "master", "ssh_key_id": key_id}, headers=headers)
    repo_id = repo["id"]

    # 5. Environments Setup
    environments = ["development", "staging", "production", "mirror"]
    inventories = api_call(f"/project/{project_id}/inventory", headers=headers) or []
    envs = api_call(f"/project/{project_id}/environment", headers=headers) or []

    # Local playbook discovery
    current_script = os.path.abspath(__file__)
    script_dir = os.path.dirname(current_script)
    
    # Try different possible locations for playbooks
    # On host: ansible/scripts -> ansible/playbooks
    # In container: /home/semaphore/ansible/scripts -> /home/semaphore/ansible/playbooks
    # If run via mount: /scripts -> /playbooks
    possible_roots = [
        os.path.abspath(os.path.join(script_dir, "..", "playbooks")),
        "/home/semaphore/ansible/playbooks",
        "/playbooks"
    ]
    
    playbook_root = None
    for root in possible_roots:
        if root and os.path.isdir(root):
            playbook_root = root
            break
            
    if not playbook_root:
        print(f"CRITICAL: Could not find playbooks directory. Looked in: {possible_roots}")
        return

    print(f"Found playbooks at: {playbook_root}")
    
    categories = {
        "setup": "Setup",
        "restart": "Restart",
        "other": "Backup"
    }

    for env_name in environments:
        env_title = env_name.capitalize()
        
        # Inventory
        inv_name = f"HomeLab {env_title} Inventory"
        inventory = next((i for i in inventories if i["name"] == inv_name), None)
        inv_data = {"project_id": project_id, "name": inv_name, "type": "file", "inventory": f"inventories/{env_name}/hosts.yml", "repository_id": repo_id, "ssh_key_id": key_id}
        if not inventory:
            inventory = api_call(f"/project/{project_id}/inventory", method="POST", data=inv_data, headers=headers)
        else:
            inv_data["id"] = inventory["id"]
            api_call(f"/project/{project_id}/inventory/{inventory['id']}", method="PUT", data=inv_data, headers=headers)
        inventory_id = inventory["id"]

        # Environment (Extra Vars)
        # SEMA_TIP: Environments in Semaphore ARE effectively Variable Groups.
        env_vars = next((e for e in envs if e["name"] == env_title), None)
        env_data = {"project_id": project_id, "name": env_title, "json": "{}", "env": "{}"}
        if not env_vars:
            env_vars = api_call(f"/project/{project_id}/environment", method="POST", data=env_data, headers=headers)
        else:
            env_data["id"] = env_vars["id"]
            api_call(f"/project/{project_id}/environment/{env_vars['id']}", method="PUT", data=env_data, headers=headers)
        env_id = env_vars["id"]

        print(f"Setting up Task Templates for {env_title}...")
        
        for cat_dir, cat_label in categories.items():
            path = os.path.join(playbook_root, cat_dir)
            if not os.path.exists(path):
                print(f"  - Category folder not found: {path}")
                continue
            
            pb_files = glob.glob(os.path.join(path, "*.yml")) + glob.glob(os.path.join(path, "*.yaml"))
            print(f"  - Found {len(pb_files)} playbooks in {cat_dir}")
            
            for pb_file in pb_files:
                pb_name = os.path.basename(pb_file)
                print(f"    - Processing: {pb_name}")
                pb_title = os.path.splitext(pb_name)[0].replace("_", " ").capitalize()
                
                # Full Template Name: [Env] Category - Service
                # e.g. [Production] Setup - Docker
                template_name = f"[{env_title}] {cat_label} - {pb_title}"
                playbook_rel_path = f"playbooks/{cat_dir}/{pb_name}"
                
                tag = cat_dir if cat_dir != "other" else "backup"
                template_id = create_task_template(
                    project_id=project_id,
                    name=template_name,
                    playbook=playbook_rel_path,
                    inventory_id=inventory_id,
                    repo_id=repo_id,
                    env_id=env_id,
                    key_id=key_id,
                    vault_key_id=vault_key_id,
                    tag=tag,
                    headers=headers
                )

                # If category is other (Backup), create a schedule
                if cat_dir == "other" and template_id:
                    cron = DEFAULT_SCHEDULES.get(pb_name)
                    if cron:
                        create_schedule(
                            project_id=project_id,
                            template_id=template_id,
                            name=f"{template_name} (Cron)",
                            cron=cron,
                            repo_id=repo_id,
                            headers=headers
                        )

    print("-" * 40)
    print("Provisioning complete for all environments!")
    print("-" * 40)

if __name__ == "__main__":
    main()

import json
import os
import time
import urllib.request
import re
import urllib.error

"""
Semaphore Provisioning Script
=============================

This script automates the initial setup of Ansible Semaphore.
It follows the Semaphore domain model:

1.  **Project**: The main container for your work (e.g., "HomeLab").
2.  **Key Store**: Stores credentials (SSH keys, passwords, sudo passwords).
3.  **Inventory**: Defines your hosts (from a static file or script).
4.  **Repository**: Points to your Ansible code (Git or local directory).
5.  **Environment**: Extra variables passed to Ansible (JSON format).
6.  **Task Template**: The "Runnable" object. It links a Playbook file 
    from a Repository to an Inventory and an Environment with a specific Key.

Without a Task Template, you won't see any "Tasks" to run in the UI.
"""

SEMAPHORE_URL = os.getenv("SEMAPHORE_URL", "http://semaphore:3000/api")
ADMIN_USER = os.getenv("SEMAPHORE_ADMIN", "admin")
ADMIN_PASS = os.getenv("SEMAPHORE_ADMIN_PASSWORD", "admin")

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
            return json.loads(res.read().decode("utf-8"))
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

def create_task_template(project_id, name, playbook, inventory_id, repo_id, env_id, key_id, vault_key_id, headers):
    """
    Creates or updates a Task Template.
    """
    templates = api_call(f"/project/{project_id}/templates", headers=headers) or []
    template = next((t for t in templates if t["name"] == name), None)
    
    # Some versions require 'app' to be set (usually 'ansible')
    # and 'view_id' (sometimes referred to as 'app id' in error messages)
    views = api_call(f"/project/{project_id}/views", headers=headers) or []
    view_id = views[0]["id"] if views else None

    data = {
        "project_id": project_id,
        "inventory_id": inventory_id,
        "repository_id": repo_id,
        "environment_id": env_id,
        "ssh_key_id": key_id,
        "view_id": view_id,
        "app": "ansible",  # Targeted fix
        "name": name,
        "playbook": playbook,
        "arguments": "[]",
        "allow_override_args_in_task": False,
        "description": f"Automatically created template for {playbook}"
    }

    # If the API accepts vault_key_id, we send it
    if vault_key_id:
        data["vault_key_id"] = vault_key_id

    if not template:
        print(f"Creating Task Template: {name} ({playbook})")
        return api_call(f"/project/{project_id}/templates", method="POST", data=data, headers=headers)
    else:
        print(f"Updating Task Template: {name} ({playbook})")
        data["id"] = template["id"]
        return api_call(f"/project/{project_id}/templates/{template['id']}", method="PUT", data=data, headers=headers)

def main():
    if not wait_for_semaphore():
        print("Semaphore did not start in time. Exiting.")
        return

    # 1. Login and get session cookie
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

    headers = {
        "Content-Type": "application/json",
        "Cookie": session_cookie
    }

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

    # 3. Key Setup (None key for local repo)
    keys = api_call(f"/project/{project_id}/keys", headers=headers) or []
    none_key = next((k for k in keys if k["name"] == "None"), None)
    if not none_key:
        print("Creating 'None' SSH Key (for local repository access)...")
        none_key = api_call(f"/project/{project_id}/keys", method="POST", data={"name": "None", "type": "none"}, headers=headers)
    
    if not none_key:
        print("Failed to find or create key 'None'.")
        return
    key_id = none_key["id"]

    # Vault Password Key
    vault_key = next((k for k in keys if k["name"] == "Ansible Vault Password"), None)
    if not vault_key:
        print("Creating 'Ansible Vault Password' Key...")
        vault_key = api_call(f"/project/{project_id}/keys", method="POST", data={"name": "Ansible Vault Password", "type": "login_password", "login_password": {"password": "change_me", "username": "vault"}}, headers=headers)
    
    vault_key_id = vault_key["id"] if vault_key else None

    # 4. Repo Setup
    repos = api_call(f"/project/{project_id}/repositories", headers=headers) or []
    repo = next((r for r in repos if r["name"] == "HomeLab Ansible"), None)
    if not repo:
        print("Registering Ansible Repository...")
        repo = api_call(f"/project/{project_id}/repositories", method="POST",
                        data={
                            "project_id": project_id,
                            "name": "HomeLab Ansible",
                            "git_url": "/home/semaphore/ansible",
                            "git_branch": "master",
                            "ssh_key_id": key_id
                        }, headers=headers)
    
    if not repo:
        print("Failed to find or create repository 'HomeLab Ansible'.")
        return
    repo_id = repo["id"]

    environments = ["development", "staging", "production", "mirror"]
    
    inventories = api_call(f"/project/{project_id}/inventory", headers=headers) or []
    envs = api_call(f"/project/{project_id}/environment", headers=headers) or []

    for env_name in environments:
        env_title = env_name.capitalize()
        
        # 5. Inventory Setup
        inv_name = f"HomeLab {env_title} Inventory"
        inventory = next((i for i in inventories if i["name"] == inv_name), None)
        inv_data = {
            "project_id": project_id,
            "name": inv_name,
            "type": "file",
            "inventory": f"inventories/{env_name}/hosts.yml",
            "repository_id": repo_id,
            "ssh_key_id": key_id
        }

        if not inventory:
            print(f"Creating Inventory '{inv_name}'...")
            inventory = api_call(f"/project/{project_id}/inventory", method="POST", data=inv_data, headers=headers)
        else:
            print(f"Updating Inventory '{inv_name}'...")
            inv_data["id"] = inventory["id"]
            api_call(f"/project/{project_id}/inventory/{inventory['id']}", method="PUT", data=inv_data, headers=headers)
        
        if not inventory:
            print(f"Failed to find or create inventory '{inv_name}'.")
            continue
        inventory_id = inventory["id"]

        # 6. Environment Setup (Empty vars)
        env_vars = next((e for e in envs if e["name"] == env_title), None)
        env_data = {
            "project_id": project_id,
            "name": env_title,
            "json": "{}", # Extra vars empty, we use Vault now
            "env": "{}" # OS env vars empty
        }

        if not env_vars:
            print(f"Creating '{env_title}' Environment...")
            env_vars = api_call(f"/project/{project_id}/environment", method="POST", data=env_data, headers=headers)
        else:
            print(f"Updating '{env_title}' Environment...")
            env_data["id"] = env_vars["id"]
            api_call(f"/project/{project_id}/environment/{env_vars['id']}", method="PUT", data=env_data, headers=headers)
        
        if not env_vars:
            print(f"Failed to find or create environment '{env_title}'.")
            continue
        env_id = env_vars["id"]

        # 7. Task Template Setup
        print(f"Setting up Task Templates for {env_title}...")
        
        create_task_template(
            project_id=project_id,
            name=f"{env_title} - 1. Full Deployment",
            playbook="playbooks/site.yml",
            inventory_id=inventory_id,
            repo_id=repo_id,
            env_id=env_id,
            key_id=key_id, # SSH Key for Repo
            vault_key_id=vault_key_id, # Target vault key
            headers=headers
        )

        create_task_template(
            project_id=project_id,
            name=f"{env_title} - 2. Docker Setup",
            playbook="playbooks/setup_docker.yml",
            inventory_id=inventory_id,
            repo_id=repo_id,
            env_id=env_id,
            key_id=key_id,
            vault_key_id=vault_key_id,
            headers=headers
        )

    print("-" * 40)
    print("Provisioning complete for all environments!")
    print("-" * 40)

if __name__ == "__main__":
    main()

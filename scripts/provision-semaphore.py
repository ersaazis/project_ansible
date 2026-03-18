import re
import urllib.error

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

def get_env_vars_from_inventory(file_path):
    """
    Parses inventory.yml to find all lookup('env', 'VAR_NAME') entries.
    Returns a dictionary of VAR_NAME: value from os.environ.
    """
    env_vars = {}
    if not os.path.exists(file_path):
        print(f"Warning: {file_path} not found.")
        return env_vars

    with open(file_path, 'r') as f:
        content = f.read()
        # Find all occurrences of lookup('env', 'SOME_VAR')
        matches = re.findall(r"lookup\(['\"]env['\"],\s*['\"]([^'\"]+)['\"]\)", content)
        for var in matches:
            env_vars[var] = os.getenv(var, "")
            
    # Also include some static ones if needed, but the regex should cover it.
    return env_vars

def main():
    if not wait_for_semaphore():
        print("Semaphore did not start in time. Exiting.")
        return

    # Login and get session cookie
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
    except Exception as e:
        print(f"Login failed: {e}")
        return

    headers = {
        "Content-Type": "application/json",
        "Cookie": session_cookie
    }

    # Project Setup
    projects = api_call("/projects", headers=headers) or []
    project = next((p for p in projects if p["name"] == "HomeLab"), None)
    if not project:
        project = api_call("/projects", method="POST", data={"name": "HomeLab"}, headers=headers)
    
    if not project:
        print("Failed to find or create project 'HomeLab'.")
        return
    project_id = project["id"]

    # Key Setup (None key for local repo)
    keys = api_call(f"/project/{project_id}/keys", headers=headers) or []
    none_key = next((k for k in keys if k["name"] == "None"), None)
    if not none_key:
        none_key = api_call(f"/project/{project_id}/keys", method="POST", data={"name": "None", "type": "none"}, headers=headers)
    
    if not none_key:
        print("Failed to find or create key 'None'.")
        return
    key_id = none_key["id"]

    # Repo Setup
    repos = api_call(f"/project/{project_id}/repositories", headers=headers) or []
    repo = next((r for r in repos if r["name"] == "HomeLab Ansible"), None)
    if not repo:
        repo = api_call(f"/project/{project_id}/repositories", method="POST",
                        data={
                            "name": "HomeLab Ansible",
                            "git_url": "/home/semaphore/ansible",
                            "git_branch": "master",
                            "ssh_key_id": key_id
                        }, headers=headers)
    
    if not repo:
        print("Failed to find or create repository 'HomeLab Ansible'.")
        print("Note: Semaphore requires the Git URL to be a valid Git repository.")
        print("Make sure you have run 'git init' in your ansible directory.")
        return
    repo_id = repo["id"]

    # Inventory Setup
    inventories = api_call(f"/project/{project_id}/inventory", headers=headers) or []
    inv_name = "HomeLab Inventory"
    inventory = next((i for i in inventories if i["name"] == inv_name), None)
    if not inventory:
        inventory = api_call(f"/project/{project_id}/inventory", method="POST",
                             data={
                                 "name": inv_name,
                                 "type": "file",
                                 "inventory": "inventory.yml",
                                 "repository_id": repo_id,
                                 "ssh_key_id": key_id
                             }, headers=headers)

    # Environment Setup
    # Path inside the container for inventory is /home/semaphore/ansible/inventory.yml 
    # but the provisioner might have it at /home/semaphore/ansible/ if we mount it same way.
    # In docker-compose, provisioner has . mounted to /home/semaphore/ansible
    inventory_path = "/home/semaphore/ansible/inventory.yml"
    extra_vars = get_env_vars_from_inventory(inventory_path)
    
    envs = api_call(f"/project/{project_id}/environment", headers=headers) or []
    env_vars = next((e for e in envs if e["name"] == "Development"), None)
    
    env_data = {
        "name": "Development",
        "json": json.dumps(extra_vars)
    }

    if not env_vars:
        api_call(f"/project/{project_id}/environment", method="POST", data=env_data, headers=headers)
    else:
        api_call(f"/project/{project_id}/environment/{env_vars['id']}", method="PUT", data=env_data, headers=headers)

    print(f"Provisioning complete! Detected {len(extra_vars)} variables from inventory.")

if __name__ == "__main__":
    main()

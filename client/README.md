# PiPush Client CLI & Python SDK

The `pipush` client allows you to push files, sync entire folder structures, download files, and execute commands on your Raspberry Pi directly from your local terminal or Python scripts.

## Installation / Requirements

Install the client dependencies:
```bash
pip install requests
```
Or install in editable mode from the repository root:
```bash
pip install -e .
```

## Configuring the Target Pi

You can either pass `--url` to any command or export the `PI_PUSH_URL` environment variable:

```bash
# In Bash / Zsh
export PI_PUSH_URL="http://192.168.1.100:8000"

# In Windows PowerShell
$env:PI_PUSH_URL = "http://192.168.1.100:8000"
```

---

## CLI Usage Examples

### 1. Push Files / Folders
```bash
# Upload a single file to the default base directory
python client/pipush.py upload script.py

# Upload a single file to a specific destination folder
python client/pipush.py upload config.json /etc/myapp/

# Upload an entire directory recursively (preserves folder hierarchy)
python client/pipush.py upload ./my-project /home/pi/projects/
```

### 2. Write Direct Content / Scripts
```bash
# Push inline text directly to a file
python client/pipush.py write /home/pi/hello.txt --content "Hello Raspberry Pi!"

# Push a script and make it executable (+x)
python client/pipush.py write /home/pi/run.sh --content "#!/bin/bash\necho 'Running!'" --executable

# Pipe local command output directly into a remote file
cat local.conf | python client/pipush.py write /home/pi/app.conf --stdin
```

### 3. Run Remote Commands
```bash
# Run any shell command on the Raspberry Pi
python client/pipush.py exec "uname -a"
python client/pipush.py run "ls -la /home/pi"

# Run command inside a specific directory with timeout
python client/pipush.py exec "npm install && npm start" --cwd /home/pi/my-app --timeout 120

# Restart a service after pushing configuration
python client/pipush.py exec "sudo systemctl restart nginx"
```

### 4. Browse & Manage Remote Files
```bash
# List files in base directory
python client/pipush.py ls

# List specific remote directory
python client/pipush.py ls /home/pi

# View file content directly in terminal (like cat)
python client/pipush.py cat /home/pi/hello.txt

# Download a file from the Pi to your local machine
python client/pipush.py download /home/pi/data.csv ./local_data.csv

# Delete a remote file or folder
python client/pipush.py rm /home/pi/old_file.txt
python client/pipush.py rm /home/pi/old_folder -r
```

### 5. Check System Health & Diagnostics
```bash
python client/pipush.py status
```

---

## Programmatic Python Usage

```python
from client.pipush import PiPushClient

client = PiPushClient(base_url="http://192.168.1.100:8000")

# Push a file
client.upload_file("app.py", target_dir="/home/pi/myapp")

# Run a remote command
res = client.execute("python3 /home/pi/myapp/app.py")
print("Exit Code:", res["exit_code"])
print("Output:\n", res["stdout"])

# Get system health
stats = client.system_status()
print(f"Pi CPU Usage: {stats['cpu']['usage_percent']}%")
```

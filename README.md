# 🥧 PiPush API: Remote File Push & Command Runner for Raspberry Pi

A lightweight, zero-authentication REST API and companion CLI tool designed to push files, synchronize directories, and execute shell commands on your Raspberry Pi (or any Linux server) directly from your local development machine.

---

## ⚡ Features

- **No API Keys Needed**: Instant plug-and-play access across your local network or VPN.
- **Push Files & Folders**: Single file uploads, bulk uploads, and recursive directory synchronization with structure preservation.
- **Direct String/Script Write**: Push code snippets or config files with automatic permissions (`chmod +x`).
- **Remote Command Execution**: Execute arbitrary bash/shell commands remotely and stream stdout, stderr, execution time, and exit codes.
- **Directory Browser & Downloader**: Browse files, check sizes, timestamps, and download files from the Pi.
- **Raspberry Pi Diagnostics**: Real-time CPU, RAM, Disk, Uptime, and IP address reporting.
- **Systemd Integration**: Automatic setup script (`install.sh`) configuring auto-restart on boot.
- **Interactive Swagger Docs**: Visual API explorer accessible at `http://<pi-ip>:8000/docs`.

---

## 🚀 Quick Setup on Raspberry Pi (Server)

### 1-Step Setup
Run the following commands on your Raspberry Pi:

```bash
# 1. Clone the repository onto your Raspberry Pi
git clone https://github.com/your-username/pi-push-api.git
cd pi-push-api

# 2. Run the automated installer
chmod +x deploy/install.sh
./deploy/install.sh
```

The installer will:
1. Create a Python virtual environment (`venv`).
2. Install all required dependencies (`fastapi`, `uvicorn`, `psutil`, etc.).
3. Register and start the `pi-push` systemd service so it runs continuously and restarts on reboot.

### Managing the Service
```bash
sudo systemctl status pi-push      # Check service status
sudo systemctl restart pi-push     # Restart server
sudo journalctl -u pi-push -f      # View live server logs
```

---

## 💻 Client CLI (`pipush`)

You can control your Raspberry Pi from your local machine using the Python CLI.

### 1. Configure the Target Pi URL
```bash
# Option A: Set environment variable (recommended)
export PI_PUSH_URL="http://192.168.1.150:8000"     # Linux / macOS
$env:PI_PUSH_URL = "http://192.168.1.150:8000"      # Windows PowerShell

# Option B: Pass --url to any command
python client/pipush.py --url http://192.168.1.150:8000 status
```

### 2. Push Files & Folders
```bash
# Upload a single file to the base directory
python client/pipush.py upload script.py

# Upload a single file to a specific path
python client/pipush.py upload config.json /etc/myapp/

# Upload an entire directory recursively
python client/pipush.py upload ./my-project /home/pi/projects/
```

### 3. Run Remote Commands
```bash
# Run any command and print output
python client/pipush.py exec "uname -a"
python client/pipush.py exec "ls -la /home/pi"

# Run command inside a specific directory
python client/pipush.py exec "git pull && npm install" --cwd /home/pi/my-app

# Restart a service after pushing files
python client/pipush.py exec "sudo systemctl restart nginx"
```

### 4. Push Direct Text / Inline Scripts
```bash
# Write text directly to a file
python client/pipush.py write /home/pi/hello.txt --content "Hello from workstation!"

# Write a script and make it executable (+x)
python client/pipush.py write /home/pi/test.sh --content $'#!/bin/bash\necho "Running test..."' --executable
```

### 5. Browse, Inspect & Download
```bash
# List directory contents
python client/pipush.py ls /home/pi

# View file content in terminal
python client/pipush.py cat /home/pi/hello.txt

# Download a file from the Pi to local machine
python client/pipush.py download /home/pi/results.csv ./local_results.csv

# Delete remote file or folder
python client/pipush.py rm /home/pi/old_file.txt
python client/pipush.py rm /home/pi/old_folder -r
```

### 6. View Raspberry Pi Health
```bash
python client/pipush.py status
```

---

## 📡 REST API & `curl` Examples

If you prefer using `curl`, Python `requests`, or custom scripts:

### 1. Upload File (`POST /upload`)
```bash
curl -X POST "http://<PI_IP>:8000/upload" \
  -F "files=@app.py" \
  -F "target_dir=/home/pi/myapp"
```

### 2. Direct Write (`POST /write`)
```bash
curl -X POST "http://<PI_IP>:8000/write" \
  -H "Content-Type: application/json" \
  -d '{
    "path": "/home/pi/start.sh",
    "content": "#!/bin/bash\necho Starting...",
    "make_executable": true
  }'
```

### 3. Execute Command (`POST /exec`)
```bash
curl -X POST "http://<PI_IP>:8000/exec" \
  -H "Content-Type: application/json" \
  -d '{
    "command": "python3 /home/pi/start.sh",
    "cwd": "/home/pi",
    "timeout": 30
  }'
```
**Response:**
```json
{
  "success": true,
  "exit_code": 0,
  "stdout": "Starting...\n",
  "stderr": "",
  "duration_ms": 15.4,
  "timed_out": false,
  "command": "python3 /home/pi/start.sh",
  "cwd": "/home/pi"
}
```

### 4. Browse Directory (`GET /browse`)
```bash
curl "http://<PI_IP>:8000/browse?path=/home/pi"
```

### 5. Download File (`GET /download`)
```bash
curl -O -J "http://<PI_IP>:8000/download?path=/home/pi/data.csv"
```

### 6. System Diagnostics (`GET /system`)
```bash
curl "http://<PI_IP>:8000/system"
```

---

## ⚙️ Configuration Variables

Configuration can be set via `.env` or system environment variables:

| Variable | Default | Description |
| :--- | :--- | :--- |
| `PI_PUSH_HOST` | `0.0.0.0` | IP interface to bind to |
| `PI_PUSH_PORT` | `8000` | Port for the API server |
| `PI_PUSH_BASE_DIR` | `./uploads` | Default root directory for uploads |
| `PI_PUSH_ALLOW_ABSOLUTE_PATHS` | `true` | Allow writing outside `BASE_DIR` (e.g. `/home/pi/`) |
| `PI_PUSH_ENABLE_EXEC` | `true` | Allow running shell commands via `/exec` |
| `PI_PUSH_DEFAULT_EXEC_TIMEOUT` | `60` | Default timeout for `/exec` in seconds |

---

## 🐳 Docker Deployment (Optional)

If you prefer running via Docker Compose:

```bash
docker compose up -d
```

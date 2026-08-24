---
description: Raspberry Pi remote push and execution tool rules
always_apply: true
---

# Raspberry Pi Environment & PiPush API

The Raspberry Pi is running the `pi-push-api` server.

## Connection Details
- **Base URL**: `http://pi.local:8000` (Fallback IP: `http://192.168.1.234:8000`)
- **Interactive Docs**: `http://pi.local:8000/docs`
- **Default Uploads Directory**: `/home/admin/pi-push-api/uploads`
- **Client Script Path**: `client/pipush.py`

## Usage for Raspberry Pi Tasks
Whenever asked to push files, run scripts, or execute commands on the Raspberry Pi:

1. **Execute Shell Commands**:
   ```bash
   py -3 client/pipush.py --url http://pi.local:8000 exec "<command>"
   ```

2. **Upload Files / Directories**:
   ```bash
   py -3 client/pipush.py --url http://pi.local:8000 upload <local_path> <remote_dir>
   ```

3. **Directly Write / Push Scripts with Execution Permissions**:
   ```bash
   py -3 client/pipush.py --url http://pi.local:8000 write <remote_path> --content "<text>" --executable
   ```

4. **Check Pi System Diagnostics**:
   ```bash
   py -3 client/pipush.py --url http://pi.local:8000 status
   ```

# Agent Instructions: Raspberry Pi Environment & PiPush API

## Environment & Connection
- **Raspberry Pi URL**: `http://pi.local:8000` (IP: `192.168.1.234`)
- **Interactive OpenAPI/Swagger**: `http://pi.local:8000/docs`
- **Default Upload Path on Pi**: `/home/admin/pi-push-api/uploads`
- **Client Tool**: `client/pipush.py`

## Common Commands
- **Run command on Pi**:
  ```bash
  py -3 client/pipush.py --url http://pi.local:8000 exec "<command>"
  ```
- **Upload file or folder**:
  ```bash
  py -3 client/pipush.py --url http://pi.local:8000 upload <local_path> [remote_dir]
  ```
- **Write script or config with chmod +x**:
  ```bash
  py -3 client/pipush.py --url http://pi.local:8000 write <remote_path> --content "<text>" --executable
  ```
- **Get Pi status**:
  ```bash
  py -3 client/pipush.py --url http://pi.local:8000 status
  ```

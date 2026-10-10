# Local logs

Written by the running backend and by `python check_all.py`. Ignored by Git except this file.

| File | Contents |
|---|---|
| `api_access.log` | One line per API request: method, path, status, duration |
| `backend.log` | Application and server messages |
| `errors.log` | Warnings and errors with full tracebacks; start here when something fails |
| `checks/` | Reports from `python check_all.py`, one folder per run |

No request bodies, headers, credentials or query strings are logged. Paths can contain Evidence IDs, so do not share these files outside the project. Files rotate at 5 MB (5 backups).

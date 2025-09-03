Quickstart

1. Create venv and install

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e .
```

2. Configure env vars (.env)

```
FIREBASE_DATABASE_URL=https://<project-id>-default-rtdb.firebaseio.com
FIREBASE_PATH=/
GOOGLE_SERVICE_ACCOUNT_FILE=/absolute/path/to/service-account.json
# or
# GOOGLE_ACCESS_TOKEN=ya29....
```

3. Run listener

```bash
python -m kommo_command
```

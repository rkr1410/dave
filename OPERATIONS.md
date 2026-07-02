# Operations

```bash
cd /Users/pafau/sandbox/dave
./install.sh
```

`install.sh` is idempotent. It:

- creates `.venv` if it does not exist,
- runs `python -m pip install --upgrade pip`,
- runs `python -m pip install -e .`,
- creates or replaces `$HOME/bin/dave` if the existing wrapper is managed by this repo.

Verify:

```bash
dave --version
dave
```

```bash
cd /Users/pafau/sandbox/dave
./uninstall.sh
```

`uninstall.sh` is idempotent. It removes:

- `$HOME/bin/dave`, only if it is managed by this repo,
- `.venv`.

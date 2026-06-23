# dave

Run without installing:

```bash
python3 -m dave_agent --port 8002
```

Or through the wrapper:

```bash
python3 agent.py --port 8002
```

Install as a local editable command:

```bash
python3 -m pip install -e .
dave --port 8002
```

Run TUI:

```bash
dave-tui --port 8002
```

Useful options:

```bash
dave --port 8002 --debug --think low --system "Jesteś pomocnym asystentem. Odpowiadaj zawsze po polsku"
dave --port 8002 --tools "list-files, read-file"
dave-tui --port 8002 --debug --think low
```

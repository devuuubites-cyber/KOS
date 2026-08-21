# KOS — Personal Knowledge OS

Local-first knowledge infrastructure for turning books into structured, searchable memory.

## Run it on an iPad

KOS is a Python/FastAPI application. The repository itself is not a hosted application, so opening the GitHub repository does not start KOS.

### Recommended zero-cost route

Use an iPad Python environment that can install packages and run a local HTTP server. KOS stores its database and book files in its configured local data directory.

1. Download/clone this repository into that Python environment.
2. Open a terminal in the repository directory.
3. Install dependencies:

```bash
python -m pip install -r requirements.txt
```

4. Start KOS:

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

5. Open the local address shown by the environment, normally:

```text
http://127.0.0.1:8000
```

### Important iPadOS limitation

A normal iPad app cannot expose an unrestricted desktop-style localhost service to every other app. Whether `127.0.0.1:8000` is reachable from Safari depends on the particular Python runtime/app and its sandbox. KOS therefore does not assume that localhost access is universally available on iPadOS.

If the Python environment provides an in-app browser/web preview, use that. If it provides a terminal but blocks Safari from reaching localhost, the backend can still run inside that environment, but a separate bridge is required to expose it to Safari/other apps.

### Storage

The original PDF/EPUB is preserved. KOS keeps processed data and SQLite storage local to the runtime. The default design does not require PostgreSQL or a cloud database.

### AI providers

External LLM processing is optional. Provider/model selection is kept behind provider interfaces; do not put API keys in source code.

### Exports

The application exposes portable JSON and Markdown exports under Settings/API. The JSON export contains books, chapters, sections, chunks, knowledge objects and relationships.

# Oasis OS — React Frontend

React + TypeScript frontend for the Oasis OS Multi-Agent Calendar Assistant.

## Setup

From the project root (`To-do-and-calender-syncer/`):

```bash
cd frontend
npm install
```

## Development

1. **Start the backend**:

   ```bash
   cd backend
   pip install -r requirements.txt
   uvicorn api.main:api --reload --host 0.0.0.0 --port 8000
   ```

2. **Start the frontend**:

   ```bash
   cd frontend
   npm run dev
   ```

3. Open [http://localhost:5173](http://localhost:5173).

The Vite dev server proxies `/api` to `http://localhost:8000`.

## API Base URL

- Default: `/api` (proxied to backend in dev)
- Override: set `VITE_API_BASE` in `.env`, e.g. `VITE_API_BASE=http://localhost:8000`

## Build

```bash
npm run build
```

Static files are output to `dist/`.

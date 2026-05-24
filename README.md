# Vision Studio

Local FastAPI + React workspace for image annotation, dataset splitting, YOLO training, and model export.

## Backend

```powershell
cd <path-to>\vision_studio
.\run_backend.ps1
```

If port `8000` is already occupied:

```powershell
$env:VISION_STUDIO_PORT = "8010"
.\run_backend.ps1
```

If dependencies need to be recreated:

```powershell
python -m pip install --target backend\.deps -r backend\requirements.txt
```

## Frontend

```powershell
cd <path-to>\vision_studio
.\run_frontend.ps1
```

If dependencies need to be recreated:

```powershell
cd <path-to>\vision_studio\frontend
npm install
```

Open `http://localhost:5173`.

If Vite picks another free port such as `5174`, that is fine now. The frontend sends API requests to the current origin by default and the dev server proxies `/api` to the backend.

Use the import form to add any absolute dataset path, or place demo data under this project as `images`, `labels`, and `yolo-pose/data.yaml`, then call `POST /api/demo/import-current`.

Environment variables:

- `VISION_STUDIO_HOST`: backend host, default `127.0.0.1`
- `VISION_STUDIO_PORT`: backend port, default `8000`
- `VISION_STUDIO_API_PROXY_TARGET`: backend target for the frontend dev proxy, default `http://127.0.0.1:8000`
- `VISION_STUDIO_CORS_ORIGINS`: comma-separated CORS allowlist for direct browser access; default `*`
- `VITE_API_BASE`: optional absolute API base URL when you do not want to use the relative-path default

When using a custom backend port with the Vite frontend, point the dev proxy at the same port before starting the frontend:

```powershell
$env:VISION_STUDIO_API_PROXY_TARGET = "http://127.0.0.1:8010"
.\run_frontend.ps1
```

## Working Rule

After each change, update `README.md` when behavior or usage changes, then stage and commit the change locally.

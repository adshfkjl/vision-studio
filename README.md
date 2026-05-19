# Vision Studio

Local FastAPI + React workspace for image annotation, dataset splitting, YOLO training, and model export.

## Backend

```powershell
cd <path-to>\vision_studio
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

Use the import form to add any absolute dataset path, or place demo data under this project as `images`, `labels`, and `yolo-pose/data.yaml`, then call `POST /api/demo/import-current`.

## Working Rule

After each change, update `README.md` when behavior or usage changes, then stage and commit the change locally.

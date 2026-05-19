# Vision Studio

Local FastAPI + React workspace for image annotation, dataset splitting, YOLO training, and model export.

## Backend

```powershell
cd D:\projects\2\vision_studio
.\run_backend.ps1
```

If dependencies need to be recreated:

```powershell
python -m pip install --target backend\.deps -r backend\requirements.txt
```

## Frontend

```powershell
cd D:\projects\2\vision_studio
.\run_frontend.ps1
```

If dependencies need to be recreated:

```powershell
cd D:\projects\2\vision_studio\frontend
npm install
```

Open `http://localhost:5173`.

Use `POST /api/demo/import-current` or the import form to add the current `D:\projects\2\images` + `D:\projects\2\labels` pose project.

## Working Rule

After each change, update `README.md` when behavior or usage changes, then stage and commit the change locally.

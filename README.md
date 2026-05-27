# Vision Studio

Local FastAPI + React workspace for image annotation, dataset splitting, YOLO training, and model export.
The app also includes a standalone model workbench for running single-image predictions with trained artifacts or local `.pt` / `.onnx` models.

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

For GPU training on Windows, use the conda environment `vision-studio-gpu` and start the backend with:

```powershell
.\run_backend_gpu.ps1
```

This skips `backend\.deps` so the CUDA-enabled PyTorch installed in the conda environment is used instead of the bundled CPU-only torch package.

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

On the annotation canvas, use the mouse wheel to zoom around the cursor and hold the left button to pan the image. Click-based marking still works on the canvas itself. Annotation shortcuts: `V`/`M` mouse mode, `B` box mode, `P` polygon mode, `K` keypoint mode, `[`/`]` previous or next keypoint, `+`/`-` zoom, `0` reset zoom, arrow keys switch images, `Ctrl+S` saves, and `Ctrl+Z`/`Ctrl+Y` undo or redo.

Use the project center import form to create a project from a backend-accessible image directory, or choose local image files/folders in the browser and upload them into a new project. Annotation files can be chosen directly from the browser or entered as backend-accessible paths. After entering a project, use the `数据/导入` page to import or rematch annotations into that current project. Supported annotation sources include YOLO TXT label folders, CVAT XML, COCO JSON, LabelMe JSON, and Pascal VOC XML; matching uses exact image names, basenames, or stems.

Use the `模型工作台` button in the top bar to run prediction outside the project annotation/training tabs. Select a project to reuse its trained `best.pt`, `last.pt`, or exported ONNX artifacts, or switch to a local model path. Prediction can run against a project image or an image path that the backend can access.

Use the import form to add any absolute dataset path, or place demo data under this project as `images`, `labels`, and `yolo-pose/data.yaml`, then call `POST /api/demo/import-current`. The import form can match existing YOLO label folders by image stem, or read a CVAT 1.1 XML file such as `annotations.xml` and materialize matched annotations into the project. In the annotation page, `删除当前图片` removes the selected image from the project and clears its internal annotation without deleting the original source image file.

The training page detects server-side CUDA devices through the backend and defaults to the recommended GPU when available. Running training jobs can be paused, resumed, or stopped from the UI. Training disables Ultralytics plot generation by default to reduce Matplotlib memory pressure during final validation. If CUDA is not detected, confirm the backend Python environment is using a CUDA-enabled PyTorch build.

After training, model files are collected from `vision_studio_data/projects/<project_id>/runs/<task>/<run_name>/weights/`. The training page shows available artifacts under `模型文件 / 训练产物`; `best.pt` and `last.pt` can be downloaded directly, and ONNX exports are copied to `vision_studio_data/projects/<project_id>/exports/`. If training exits after saving weights but fails during final validation or plotting, the saved model artifacts are still collected and exposed in the UI.

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

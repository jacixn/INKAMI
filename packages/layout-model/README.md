# Layout Model

Training assets + instructions for the panel/bubble detector.

## Quickstart
```bash
conda create -n inkami-layout python=3.11
pip install ultralytics==8.3.6 roboflow
python train.py --data data/bubble.yaml --img 1536 --epochs 80
```

## Folder Structure
- `images/` – raw page images
- `labels/` – YOLO txt annotations (matching file names)
- `data/bubble.yaml` – dataset config referencing train/val splits
- `notebooks/` – experimentation

Use Roboflow or CVAT to export YOLOv8-friendly labels. Keep `bubble_*` classes separate for dialogue vs narration vs thoughts so the classifier can learn type hints.


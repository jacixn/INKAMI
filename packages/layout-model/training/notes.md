# Training Notes

- Start with 200 annotated pages (70% train / 15% val / 15% test).
- Use image size 1536 for vertical strips; augment with mosaic=0.5, hsv=0.1.
- Track mean average precision per class; ensure narration boxes reach ≥0.7 mAP to avoid misclassifying.
- Export ONNX or TensorRT for inference inside FastAPI worker once accuracy stabilises.


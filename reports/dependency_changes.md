# Dependency changes

## Installed in project `.venv`

| Package | Version/source | Reason |
|---|---|---|
| torch | 2.6.0+cu124, official PyTorch cu124 index | CUDA inference on Python 3.13 and driver 555.97 |
| torchvision | 0.21.0+cu124, official PyTorch cu124 index | Image processor/runtime compatibility |
| diffusers | 0.41.0 | Stable Diffusion pipeline |
| accelerate | 1.15.0 | Diffusers CPU offload support |
| imageio | 2.38.1 | Video utilities |
| imageio-ffmpeg | 0.6.0 | Diffusers video export dependency |
| importlib-metadata / zipp | 9.0.1 / 4.1.1 | Diffusers dependencies |

Existing Transformers 5.18.0, safetensors 0.8.0 and Pillow 12.3.0 were preserved. Sympy changed from 1.14.0 to the PyTorch-required 1.13.1. `pip check` reports no broken requirements.

## Model

- Downloaded `segmind/tiny-sd` from Hugging Face to `models/tiny-sd`.
- Size on disk: approximately 0.99 GB.
- License declared by the model card: CreativeML OpenRAIL-M.
- The model contains legacy PyTorch `.bin` weights rather than safetensors; this is recorded as a limitation.

No system-wide Python package was changed. No paid API or credential was introduced. Snapshots are in `reports/pip-freeze-before.txt` and `reports/pip-freeze-after-install.txt`.

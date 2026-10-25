"""Pre-download iteration-2 models: IP-Adapter (SD1.5) + CLIP image encoder, RT-DETR detector."""
from huggingface_hub import snapshot_download
r = snapshot_download("h94/IP-Adapter", allow_patterns=["models/ip-adapter_sd15.bin",
      "models/image_encoder/config.json", "models/image_encoder/model.safetensors"])
print("got IP-Adapter", r, flush=True)
for repo in ("PekingU/rtdetr_r101vd_coco_o365",):
    r = snapshot_download(repo, allow_patterns=["*.json", "*.safetensors"])
    print("got", repo, r, flush=True)
print("PREFETCH2_DONE", flush=True)

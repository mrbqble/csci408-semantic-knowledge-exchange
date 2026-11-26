"""Pre-download the receiver models (OMEN): two ControlNets and Stable Diffusion 1.5 fp16."""
from huggingface_hub import snapshot_download

for repo in ("lllyasviel/sd-controlnet-canny", "lllyasviel/sd-controlnet-seg"):
    snapshot_download(repo, allow_patterns=["*.json", "*.safetensors"])
    print("got", repo, flush=True)

for repo in ("runwayml/stable-diffusion-v1-5", "stable-diffusion-v1-5/stable-diffusion-v1-5"):
    try:
        snapshot_download(repo, allow_patterns=["*.json", "*.txt", "*.fp16.safetensors"],
                          ignore_patterns=["safety_checker/*"])
        print("got", repo, flush=True)
        break
    except Exception as e:
        print("could not get", repo, "-", type(e).__name__, str(e)[:120], flush=True)
print("PREFETCH_DONE", flush=True)

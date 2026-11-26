import io, time
from PIL import Image
from google import genai
from google.genai import types
import vlm_judge as v
client = genai.Client(api_key=v.api_key(), http_options=types.HttpOptions(timeout=60000))
def test(label, contents, model="gemma-4-31b-it"):
    t = time.time()
    try:
        r = client.models.generate_content(model=model, contents=contents)
        print(f"{label} [{model}]: OK in {time.time()-t:.1f}s -> {(r.text or '')[:80]!r}", flush=True)
    except Exception as e:
        print(f"{label} [{model}]: FAIL in {time.time()-t:.1f}s -> {type(e).__name__}: {str(e)[:140]}", flush=True)
test("text only", ["Reply with the single word: ready"])
small = io.BytesIO(); Image.open(r"C:\carla_multicam_kit\output\carla_dataset_v3_ids\case1\cam1.jpg").convert("RGB").resize((512, 288)).save(small, "JPEG", quality=85)
test("text + 1 inline image (512x288)", ["How many cars are in this image? Answer with a number.", types.Part.from_bytes(data=small.getvalue(), mime_type="image/jpeg")])
print("models visible containing 'gemma':", [m.name for m in client.models.list() if "gemma" in m.name][:12], flush=True)

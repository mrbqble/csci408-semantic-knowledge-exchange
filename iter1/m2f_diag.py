"""Diagnose Mask2Former's accuracy gap: processor resize settings and weights that failed to load (OMEN)."""
from transformers import AutoImageProcessor, Mask2FormerForUniversalSegmentation
import transformers

MODEL = "facebook/mask2former-swin-large-cityscapes-semantic"
proc = AutoImageProcessor.from_pretrained(MODEL)
print("transformers", transformers.__version__)
print("processor:", type(proc).__name__, "| do_resize", getattr(proc, "do_resize", None), "| size", getattr(proc, "size", None),
      "| size_divisor", getattr(proc, "size_divisor", None))
model, info = Mask2FormerForUniversalSegmentation.from_pretrained(MODEL, output_loading_info=True)
for k in ("missing_keys", "unexpected_keys", "mismatched_keys"):
    keys = list(info.get(k, []))
    norm = [x for x in keys if "norm" in x]
    print(f"{k}: {len(keys)} total, {len(norm)} with 'norm'; first: {keys[:6]}")
    if norm:
        print("   norm keys:", norm[:10])

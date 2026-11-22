# Reference copy of Damir Assylbek's VLM-judge script (received via Telegram, 11-12 Nov 2026).
# iter2/vlm_judge.py copies its prompts, model name and score parsing. The API key is read from GEMINI_API_KEY; none is stored here.

#!/usr/bin/env python3
"""
Batch Evaluation Script for Generated Images

This script evaluates all generated images against their originals using Gemma 3 Vision API.

Input structure:
- Originals:      generated_components_{cityscapes,rlvd}/{image_name}/{image_name}.png
- Reconstructions: generated_final_images_new/{image_name}_blip_generated.png  (regular edge map)
                   generated_final_images_new/{image_name}_blip_adaptive.png   (adaptive edge map)

For each original, it compares:
- Original vs BLIP generated (regular edge map)
- Original vs BLIP adaptive  (adaptive edge map)

Uses binary scoring (0 or 1) based on preservation of main objects and attributes.

Requires the GEMINI_API_KEY environment variable.
"""

import os
import sys
import json
import re
from pathlib import Path
from google import genai
from google.genai import errors as genai_errors
from google.genai import types as genai_types
import random
import time
from datetime import datetime

# Configuration
BASE_DIR = Path(__file__).resolve().parent.parent  # repo root
COMPONENTS_DIRS = {
    "cityscapes": BASE_DIR / "generated_components_cityscapes",
    "rlvd": BASE_DIR / "generated_components_rlvd",
}
GENERATED_DIR = BASE_DIR / "generated_final_images_new"
RESULTS_DIR = BASE_DIR

# Reconstruction variants: label -> filename suffix in GENERATED_DIR
VARIANTS = {
    "BLIP_generated": "_blip_generated.png",
    "BLIP_adaptive": "_blip_adaptive.png",
}

MODEL_NAME = "gemma-4-31b-it"

# Evaluation prompts
PROMPT_CAR_POSITIONS = """You are evaluating a pair of images: the first image is the original image, and the second image is a reconstructed image generated using semantic segmentation, edge maps, and a textual description.

Please compare the two images and focus only on the spatial positions of cars.

Assign a score of 1 if:
- The positions of cars in the reconstructed image are largely consistent with their positions in the original image (e.g., relative locations, left/right placement, front/back placement).

Assign a score of 0 if:
- The positions of cars in the reconstructed image are clearly incorrect, significantly shifted, missing, or inconsistent with the original image.

Ignore minor visual differences such as color, texture, or background details.
Provide a brief explanation for your decision.
Finally, output a single overall score of either 0 or 1 on the last line, in the format "Score: X"."""

PROMPT_CAR_NUMBERS = """You are evaluating a pair of images: the first image is the original image, and the second image is a reconstructed image generated using semantic segmentation, edge maps, and a textual description.

Please compare the two images and focus only on the number of cars present.

Assign a score of 1 if:
- The number of cars in the reconstructed image matches the number of cars in the original image.

Assign a score of 0 if:
- The reconstructed image contains more or fewer cars than the original image.

Ignore differences in car appearance, position, size, or background details.
Provide a brief explanation for your decision.
Finally, output a single overall score of either 0 or 1 on the last line, in the format "Score: X"."""

# Parameters
MAX_IMAGES = None  # Set to None to process all images, or specify a number for testing
START_FROM = 0     # Index to start from (for resuming)
DELAY_SECONDS = 3  # Delay between API calls to avoid rate limiting
MAX_RETRIES = 8    # Attempts per API call on failure (e.g. rate limit, 500/503)
RETRY_DELAY_SECONDS = 30       # First wait; doubles after each failure (30, 60, 120, ...)
MAX_RETRY_DELAY_SECONDS = 300  # Cap on a single wait
MAX_RETRY_TOTAL_SECONDS = 1200 # Give up on a call after this much total time (20 min)
REQUEST_TIMEOUT_SECONDS = 180  # Abort a single request if the server doesn't answer
# 4xx errors other than these mean the request itself is wrong, so retrying won't help
RETRYABLE_CLIENT_CODES = {408, 429}


def setup_client():
    """Initialize Gemma API client"""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        sys.exit("Error: GEMINI_API_KEY environment variable is not set")
    return genai.Client(
        api_key=api_key,
        http_options=genai_types.HttpOptions(timeout=REQUEST_TIMEOUT_SECONDS * 1000),  # ms
    )


def discover_image_pairs():
    """Discover all originals that have at least one generated reconstruction"""

    if not GENERATED_DIR.exists():
        print(f"Error: Directory not found: {GENERATED_DIR}")
        return []

    image_pairs = []
    seen_names = set()

    for dataset, components_dir in COMPONENTS_DIRS.items():
        if not components_dir.exists():
            print(f"Warning: Directory not found, skipping: {components_dir}")
            continue

        print(f"Scanning directory: {components_dir}")
        found = 0
        missing_original = 0

        # Sorted so START_FROM gives a stable order when resuming
        for image_folder in sorted(components_dir.iterdir()):
            if not image_folder.is_dir():
                continue

            base_name = image_folder.name
            original_file = image_folder / f"{base_name}.png"
            if not original_file.exists():
                missing_original += 1
                continue

            generated = {}
            for variant, suffix in VARIANTS.items():
                generated_file = GENERATED_DIR / f"{base_name}{suffix}"
                if generated_file.exists():
                    generated[variant] = str(generated_file)

            if not generated:
                continue

            if base_name in seen_names:
                print(f"  Warning: {base_name} exists in more than one dataset; "
                      f"generated images are shared in {GENERATED_DIR.name}/")
            seen_names.add(base_name)

            image_pairs.append({
                'base_name': base_name,
                'dataset': dataset,
                'original': str(original_file),
                'generated': generated,
            })
            found += 1

        print(f"  {dataset}: {found} images with reconstructions"
              + (f" ({missing_original} folders without original)" if missing_original else ""))

    print(f"Found {len(image_pairs)} images in total")
    for variant in VARIANTS:
        count = sum(1 for p in image_pairs if variant in p['generated'])
        print(f"  - {variant}: {count}")

    return image_pairs


def with_retries(fn, description):
    """Call fn(), retrying with exponential backoff on transient errors
    (rate limits, 5xx, timeouts). Gives up after MAX_RETRIES attempts or
    MAX_RETRY_TOTAL_SECONDS, whichever comes first."""
    start = time.monotonic()
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            return fn()
        except Exception as e:
            code = getattr(e, 'code', None)
            if isinstance(e, genai_errors.ClientError) and code not in RETRYABLE_CLIENT_CODES:
                raise  # e.g. 400 bad request, 403 permission: not transient

            delay = min(RETRY_DELAY_SECONDS * 2 ** (attempt - 1), MAX_RETRY_DELAY_SECONDS)
            delay += random.uniform(0, delay * 0.1)  # jitter
            elapsed = time.monotonic() - start
            if attempt == MAX_RETRIES or elapsed + delay > MAX_RETRY_TOTAL_SECONDS:
                print(f"  {description} giving up after {attempt} attempts ({elapsed:.0f}s)")
                raise
            print(f"  {description} failed (attempt {attempt}/{MAX_RETRIES}): {e}")
            print(f"  Retrying in {delay:.0f}s...")
            time.sleep(delay)


def delete_uploaded(client, files):
    """Delete uploaded files so they don't accumulate in the Files API storage"""
    for f in files:
        try:
            client.files.delete(name=f.name)
        except Exception as e:
            print(f"  Warning: could not delete uploaded file {f.name}: {e}")


def evaluate_image_pair(client, original_img, generated_path, pair, variant, prompt):
    """Evaluate a single image pair using Gemma 3 Vision API.

    original_img is an already-uploaded file, so it is shared across variants.
    """
    base_name = pair['base_name']
    result = {
        'caption_type': variant,
        'dataset': pair['dataset'],
        'base_name': base_name,
        'original_path': pair['original'],
        'generated_path': generated_path,
    }
    generated_img = None

    try:
        print(f"  Uploading {variant} image...")
        generated_img = with_retries(
            lambda: client.files.upload(file=generated_path), "Upload")

        print(f"  Generating evaluation...")
        response = with_retries(
            lambda: client.models.generate_content(
                model=MODEL_NAME,
                contents=[prompt, original_img, generated_img],
            ),
            "Generation",
        )

        evaluation_text = response.text
        if not evaluation_text:
            raise ValueError("Empty response from model")

        result.update(success=True, evaluation=evaluation_text)

    except Exception as e:
        print(f"  Error evaluating {variant}: {e}")
        result.update(success=False, error=str(e))

    finally:
        if generated_img is not None:
            delete_uploaded(client, [generated_img])

    result['timestamp'] = datetime.now().isoformat()
    return result


def save_results(results, filename="evaluation_results.json", output_dir=None):
    """Save evaluation results to JSON file"""
    if output_dir is None:
        output_dir = RESULTS_DIR / "evaluation_results"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / filename

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"Results saved to: {output_path}")
    return output_path


def batch_evaluate_all(client, image_pairs, prompt, output_dir, max_images=None, start_from=0, delay_seconds=3):
    """Evaluate all image pairs"""

    if not image_pairs:
        print("No image pairs to evaluate")
        return []

    # Apply limits
    if start_from > 0:
        image_pairs = image_pairs[start_from:]
        print(f"Starting from image {start_from}")

    if max_images and len(image_pairs) > max_images:
        image_pairs = image_pairs[:max_images]
        print(f"Processing {len(image_pairs)} images (limited by max_images)")

    print(f"\nStarting batch evaluation for {len(image_pairs)} images...")
    print("=" * 70)

    all_results = []
    start_time = time.time()

    for i, pair in enumerate(image_pairs, 1):
        base_name = pair['base_name']
        print(f"\n[{i}/{len(image_pairs)}] Processing: {base_name} ({pair['dataset']})")

        # Upload the original once and reuse it for every variant
        try:
            original_img = with_retries(
                lambda: client.files.upload(file=pair['original']), "Upload")
        except Exception as e:
            print(f"  Error uploading original: {e}")
            for variant, generated_path in pair['generated'].items():
                all_results.append({
                    'success': False,
                    'caption_type': variant,
                    'dataset': pair['dataset'],
                    'base_name': base_name,
                    'error': f"Original upload failed: {e}",
                    'timestamp': datetime.now().isoformat(),
                })
            continue

        try:
            for variant, generated_path in pair['generated'].items():
                print(f"  Evaluating {variant} image...")
                result = evaluate_image_pair(
                    client, original_img, generated_path, pair, variant, prompt)
                all_results.append(result)

                if result['success']:
                    print(f"  {variant} evaluation completed")

                # Delay to avoid rate limiting
                time.sleep(delay_seconds)
        finally:
            delete_uploaded(client, [original_img])

        # Save intermediate results every 10 images
        if i % 10 == 0:
            save_results(all_results, f"intermediate_results_{start_from + i}.json", output_dir)
            print(f"  Saved intermediate results ({i} images processed)")

    total_time = time.time() - start_time

    print(f"\n{'=' * 70}")
    print(f"Batch evaluation complete!")
    print(f"Total evaluations: {len(all_results)}")
    print(f"Total time: {total_time:.1f}s ({total_time/60:.1f} min)")
    if all_results:
        print(f"Average per evaluation: {total_time/len(all_results):.1f}s")

    return all_results


def extract_score_from_evaluation(evaluation_text):
    """Extract binary score (0 or 1) from evaluation text"""
    if not evaluation_text:
        return None

    # Matches "Score: 1", "**Score:** 0", "overall score of 1", "final score is 0", etc.
    # The last match is used, since the model restates the rubric before giving its verdict.
    matches = re.findall(
        r'score\W*(?:of|is|=)?\W*([01])(?!\d|\.\d)', evaluation_text, re.IGNORECASE)
    if matches:
        return int(matches[-1])

    # Last resort: a line containing only 0 or 1 (possibly with markdown)
    matches = re.findall(r'^\W*([01])\W*$', evaluation_text, re.MULTILINE)
    if matches:
        return int(matches[-1])

    return None


def analyze_results(results):
    """Analyze evaluation results with binary scoring"""

    successful_results = [r for r in results if r['success']]

    print(f"\n{'=' * 70}")
    print("ANALYSIS RESULTS")
    print("=" * 70)
    print(f"Total evaluations: {len(results)}")
    print(f"Successful: {len(successful_results)}")
    print(f"Failed: {len(results) - len(successful_results)}")

    # Extract scores
    print("\nExtracting binary scores...")

    for result in successful_results:
        score = extract_score_from_evaluation(result['evaluation'])
        result['score'] = score
        if score is None:
            print(f"  Warning: Could not extract score for {result['base_name']} ({result['caption_type']})")

    # Calculate statistics
    def calc_stats(results_list, label):
        if not results_list:
            return

        print(f"\n{label} Statistics:")
        print("=" * 50)

        scores = [r['score'] for r in results_list if r.get('score') is not None]

        if scores:
            total = len(scores)
            ones = sum(scores)
            zeros = total - ones

            print(f"  Total evaluated: {total}")
            print(f"  Score 1 (preserved): {ones} ({ones/total*100:.1f}%)")
            print(f"  Score 0 (not preserved): {zeros} ({zeros/total*100:.1f}%)")
        else:
            print("  No valid scores extracted")

    for variant in VARIANTS:
        variant_results = [r for r in successful_results if r['caption_type'] == variant]
        calc_stats(variant_results, f"{variant} (all datasets)")
        for dataset in COMPONENTS_DIRS:
            calc_stats(
                [r for r in variant_results if r['dataset'] == dataset],
                f"{variant} ({dataset})",
            )

    return successful_results


def run_evaluation(client, image_pairs, title, prompt, output_dir):
    """Run one evaluation round and save raw + analyzed results"""
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)
    print(f"Output directory: {output_dir}")

    results = batch_evaluate_all(
        client,
        image_pairs,
        prompt,
        output_dir,
        max_images=MAX_IMAGES,
        start_from=START_FROM,
        delay_seconds=DELAY_SECONDS
    )

    if not results:
        print(f"No results to save for {title}.")
        return

    final_output = save_results(results, "final_evaluation_results.json", output_dir)
    print(f"\nFinal results saved to: {final_output}")

    analyzed_results = analyze_results(results)
    save_results(analyzed_results, "analyzed_results_with_scores.json", output_dir)

    print(f"\n{'=' * 70}")
    print(f"{title} complete!")
    print("=" * 70)


def main():
    """Main execution function"""
    print("Batch Evaluation Script for Generated Images")
    print("=" * 70)
    for dataset, components_dir in COMPONENTS_DIRS.items():
        print(f"Originals ({dataset}): {components_dir}")
    print(f"Generated images: {GENERATED_DIR}")
    print(f"Variants: {', '.join(VARIANTS)}")
    print(f"Max images: {MAX_IMAGES if MAX_IMAGES else 'All'}")
    print(f"Start from: {START_FROM}")
    print(f"Delay between calls: {DELAY_SECONDS}s")
    print("=" * 70)

    client = setup_client()

    image_pairs = discover_image_pairs()
    if not image_pairs:
        print("No image pairs found. Exiting.")
        return

    output_dir_positions = RESULTS_DIR / "evaluation_results_cars_positions"
    output_dir_numbers = RESULTS_DIR / "evaluation_results_cars_numbers"

    run_evaluation(client, image_pairs, "EVALUATION 1: CAR POSITIONS",
                   PROMPT_CAR_POSITIONS, output_dir_positions)
    run_evaluation(client, image_pairs, "EVALUATION 2: CAR NUMBERS",
                   PROMPT_CAR_NUMBERS, output_dir_numbers)

    print(f"\n{'=' * 70}")
    print("ALL EVALUATIONS COMPLETE!")
    print("=" * 70)
    print(f"Car positions results: {output_dir_positions}")
    print(f"Car numbers results: {output_dir_numbers}")
    print("=" * 70)


if __name__ == "__main__":
    main()

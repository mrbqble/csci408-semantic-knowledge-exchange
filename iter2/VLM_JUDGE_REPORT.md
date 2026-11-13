# VLM judge results

Judge: `gemma-4-31b-it` through the Gemini API, prompts and score parsing unchanged from Damir's `batch_evaluation.py`. Each pair is the original photo of the reference camera (cam1) and its reconstruction; two separate requests per pair (car numbers, car positions), each scored 0/1. Joint = both 1. 95% Wilson intervals in brackets.

Reference: seed paper (Table 6, MMSD single camera): numbers 86.9-88.9%, positions 94.4-97.6%, joint 86.1-86.9%.

| setup | what it is | pairs | numbers preserved | positions preserved | joint |
|---|---|---|---|---|---|
| v3_default | all cameras' captions, 1024x576, Cityscapes palette (current receiver) | 112 | 36.6% [28-46] | 88.4% [81-93] | 36.6% [28-46] |
| v3_k1 | reference camera only, 1024x576, Cityscapes palette | 112 | 33.9% [26-43] | 86.6% [79-92] | 33.0% [25-42] |
| v3_both_fixes | all cameras' captions, 896x512 working size, ADE20K palette | 112 | 46.4% [37-56] | 90.2% [83-94] | 43.8% [35-53] |
| v3_k1_both_fixes | reference camera only, 896x512 working size, ADE20K palette | 112 | 49.1% [40-58] | 89.3% [82-94] | 46.4% [37-56] |
| v3_cn07_15 | current receiver with ControlNet canny 0.7 / seg 1.5 | 112 | 50.9% [42-60] | 93.8% [88-97] | 49.1% [40-58] |
| v3_resolution_only | 896x512 working size, Cityscapes palette | 111 | 39.6% [31-49] | 89.2% [82-94] | 37.8% [29-47] |
| v3_palette_only | 1024x576, ADE20K palette | 112 | 38.4% [30-48] | 89.3% [82-94] | 37.5% [29-47] |
| rw_default | all cameras' captions, 1024x576, Cityscapes palette (current receiver) | 60 | 28.3% [19-41] | 91.7% [82-96] | 28.3% [19-41] |
| rw_k1 | reference camera only, 1024x576, Cityscapes palette | 59 | 27.1% [17-40] | 91.5% [82-96] | 27.1% [17-40] |
| rw_both_fixes | all cameras' captions, 896x512 working size, ADE20K palette | 61 | 47.5% [36-60] | 95.1% [87-98] | 45.9% [34-58] |
| rw_k1_both_fixes | reference camera only, 896x512 working size, ADE20K palette | 61 | 54.1% [42-66] | 95.1% [87-98] | 54.1% [42-66] |
| rw_cn07_15 | current receiver with ControlNet canny 0.7 / seg 1.5 | 61 | 34.4% [24-47] | 96.7% [89-99] | 34.4% [24-47] |
| rw_resolution_only | 896x512 working size, Cityscapes palette | 61 | 44.3% [33-57] | 96.7% [89-99] | 44.3% [33-57] |
| rw_palette_only | 1024x576, ADE20K palette | 61 | 29.5% [20-42] | 96.7% [89-99] | 29.5% [20-42] |
| cs_authors | Cityscapes (the seed paper's kind of data), authors' receiver settings: 2048x1024, Cityscapes palette, single camera (iteration 1) | 100 | 44.0% [35-54] | 77.0% [68-84] | 41.0% [32-51] |
| cs_ade | Cityscapes, authors' settings with the ADE20K palette (iteration 1) | 100 | 42.0% [33-52] | 82.0% [73-88] | 41.0% [32-51] |
| v3_identity | calibration: the original photo judged against itself (the judge's ceiling) | 112 | 100.0% [97-100] | 100.0% [97-100] | 100.0% [97-100] |
| rw_identity | calibration: the original photo judged against itself (the judge's ceiling) | 61 | 100.0% [94-100] | 100.0% [94-100] | 100.0% [94-100] |
| v3_both_fixes_cn | both fixes + ControlNet canny 0.7 / seg 1.5 | 112 | 43.8% [35-53] | 94.6% [89-98] | 43.8% [35-53] |
| v3_k1_both_fixes_cn | reference camera only, both fixes + canny 0.7 / seg 1.5 | 112 | 55.4% [46-64] | 92.9% [87-96] | 52.7% [43-62] |
| rw_both_fixes_cn | both fixes + ControlNet canny 0.7 / seg 1.5 | 61 | 50.8% [39-63] | 95.1% [87-98] | 50.8% [39-63] |
| rw_k1_both_fixes_cn | reference camera only, both fixes + canny 0.7 / seg 1.5 | 61 | 57.4% [45-69] | 96.7% [89-99] | 57.4% [45-69] |

## Paired comparisons (same cases; McNemar exact test on the joint score)

| dataset | comparison | pairs | joint B | joint A | change | B better / A better | p |
|---|---|---|---|---|---|---|---|
| v3 | Damir's two fixes (working resolution + ADE20K palette) vs current receiver | 112 | 43.8% | 36.6% | +7.1 pts | 24 / 16 | 0.268 |
| v3 | multi-camera captions vs reference camera only (current receiver) | 112 | 36.6% | 33.0% | +3.6 pts | 17 / 13 | 0.585 |
| v3 | multi-camera captions vs reference camera only (with both fixes) | 112 | 43.8% | 46.4% | -2.7 pts | 17 / 20 | 0.743 |
| v3 | working resolution alone | 111 | 37.8% | 36.9% | +0.9 pts | 19 / 18 | 1.000 |
| v3 | ADE20K palette alone | 112 | 37.5% | 36.6% | +0.9 pts | 14 / 13 | 1.000 |
| v3 | ControlNet canny 0.7 / seg 1.5 | 112 | 49.1% | 36.6% | +12.5 pts | 22 / 8 | 0.016 |
| v3 | canny 0.7 / seg 1.5 on top of both fixes | 112 | 43.8% | 43.8% | +0.0 pts | 23 / 23 | 1.000 |
| v3 | multi-camera captions vs reference camera only (both fixes + canny 0.7 / seg 1.5) | 112 | 43.8% | 52.7% | -8.9 pts | 16 / 26 | 0.164 |
| rw | Damir's two fixes (working resolution + ADE20K palette) vs current receiver | 60 | 46.7% | 28.3% | +18.3 pts | 15 / 4 | 0.019 |
| rw | multi-camera captions vs reference camera only (current receiver) | 58 | 29.3% | 27.6% | +1.7 pts | 2 / 1 | 1.000 |
| rw | multi-camera captions vs reference camera only (with both fixes) | 61 | 45.9% | 54.1% | -8.2 pts | 2 / 7 | 0.180 |
| rw | working resolution alone | 60 | 43.3% | 28.3% | +15.0 pts | 13 / 4 | 0.049 |
| rw | ADE20K palette alone | 60 | 30.0% | 28.3% | +1.7 pts | 4 / 3 | 1.000 |
| rw | ControlNet canny 0.7 / seg 1.5 | 60 | 35.0% | 28.3% | +6.7 pts | 7 / 3 | 0.344 |
| rw | canny 0.7 / seg 1.5 on top of both fixes | 61 | 50.8% | 45.9% | +4.9 pts | 10 / 7 | 0.629 |
| rw | multi-camera captions vs reference camera only (both fixes + canny 0.7 / seg 1.5) | 61 | 50.8% | 57.4% | -6.6 pts | 8 / 12 | 0.503 |
| cs | ADE20K palette vs Cityscapes palette (authors' settings, 2048x1024) | 100 | 41.0% | 41.0% | +0.0 pts | 14 / 14 | 1.000 |

Answers whose score could not be parsed (counted as unfinished and retried): 0.

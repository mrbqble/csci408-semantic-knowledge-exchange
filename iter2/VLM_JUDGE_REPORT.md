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
| v3_resolution_only | 896x512 working size, Cityscapes palette | 112 | 39.3% [31-49] | 89.3% [82-94] | 37.5% [29-47] |
| v3_palette_only | 1024x576, ADE20K palette | 112 | 38.4% [30-48] | 89.3% [82-94] | 37.5% [29-47] |
| rw_default | all cameras' captions, 1024x576, Cityscapes palette (current receiver) | 61 | 27.9% [18-40] | 91.8% [82-96] | 27.9% [18-40] |
| rw_k1 | reference camera only, 1024x576, Cityscapes palette | 61 | 26.2% [17-38] | 91.8% [82-96] | 26.2% [17-38] |
| rw_both_fixes | all cameras' captions, 896x512 working size, ADE20K palette | 61 | 47.5% [36-60] | 95.1% [87-98] | 45.9% [34-58] |
| rw_k1_both_fixes | reference camera only, 896x512 working size, ADE20K palette | 61 | 54.1% [42-66] | 95.1% [87-98] | 54.1% [42-66] |
| rw_cn07_15 | current receiver with ControlNet canny 0.7 / seg 1.5 | 61 | 34.4% [24-47] | 96.7% [89-99] | 34.4% [24-47] |
| rw_resolution_only | 896x512 working size, Cityscapes palette | 61 | 44.3% [33-57] | 96.7% [89-99] | 44.3% [33-57] |
| rw_palette_only | 1024x576, ADE20K palette | 61 | 29.5% [20-42] | 96.7% [89-99] | 29.5% [20-42] |
| cs_authors | Cityscapes (the seed paper's kind of data), authors' receiver settings: 2048x1024, Cityscapes palette, single camera (iteration 1) | 100 | 44.0% [35-54] | 77.0% [68-84] | 41.0% [32-51] |
| cs_ade | Cityscapes, authors' settings with the ADE20K palette (iteration 1) | 100 | 42.0% [33-52] | 82.0% [73-88] | 41.0% [32-51] |
| cs2_paper_seg1024 | Cityscapes, seed paper's single-camera MMSD rebuilt with the segmenter at full input size (1024x2048), 2048x1024, Cityscapes palette | 100 | 43.0% [34-53] | 84.0% [76-90] | 41.0% [32-51] |
| v3_paper_k1 | seed paper's single-camera MMSD at its own settings: reference camera only, generated at the photo's resolution (1920x1088), Cityscapes palette, map at half resolution, edges at full resolution | 112 | 57.1% [48-66] | 88.4% [81-93] | 56.2% [47-65] |
| v3_paper_multi | same settings, all cameras' captions (our multi-camera receiver) | 112 | 50.9% [42-60] | 96.4% [91-99] | 50.0% [41-59] |
| rw_paper_k1 | seed paper's single-camera MMSD at its own settings: reference camera only, generated at the photo's resolution (1920x1088), Cityscapes palette, map at half resolution, edges at full resolution | 61 | 77.0% [65-86] | 95.1% [87-98] | 75.4% [63-84] |
| rw_paper_multi | same settings, all cameras' captions (our multi-camera receiver) | 61 | 73.8% [62-83] | 95.1% [87-98] | 73.8% [62-83] |
| rw_fuse | Damir's fusion: img2img from the main reconstruction (paper settings, strength 0.5), main seg+edge on the ControlNets, supporting reconstructions on the IP-Adapter (scale 1.0), global caption | 61 | 80.3% [69-88] | 96.7% [89-99] | 80.3% [69-88] |
| rw_fuse_noip | control: the same img2img pass without the IP-Adapter | 61 | 63.9% [51-75] | 93.4% [84-97] | 63.9% [51-75] |
| v3_fuse | Damir's fusion (as rw_fuse) | 112 | 69.6% [61-77] | 93.8% [88-97] | 69.6% [61-77] |
| v3_fuse_noip | control: the same img2img pass without the IP-Adapter | 112 | 63.4% [54-72] | 92.9% [87-96] | 61.6% [52-70] |
| v3_identity | calibration: the original photo judged against itself (the judge's ceiling) | 112 | 100.0% [97-100] | 100.0% [97-100] | 100.0% [97-100] |
| rw_identity | calibration: the original photo judged against itself (the judge's ceiling) | 61 | 100.0% [94-100] | 100.0% [94-100] | 100.0% [94-100] |
| v3_both_fixes_cn | both fixes + ControlNet canny 0.7 / seg 1.5 | 112 | 43.8% [35-53] | 94.6% [89-98] | 43.8% [35-53] |
| v3_k1_both_fixes_cn | reference camera only, both fixes + canny 0.7 / seg 1.5 | 112 | 55.4% [46-64] | 92.9% [87-96] | 52.7% [43-62] |
| rw_both_fixes_cn | both fixes + ControlNet canny 0.7 / seg 1.5 | 61 | 50.8% [39-63] | 95.1% [87-98] | 50.8% [39-63] |
| rw_k1_both_fixes_cn | reference camera only, both fixes + canny 0.7 / seg 1.5 | 61 | 57.4% [45-69] | 96.7% [89-99] | 57.4% [45-69] |
| v3_fuseF | fusion with full-resolution supporting reconstructions (strength 0.5, IP scale 1.0) | 112 | 59.8% [51-68] | 95.5% [90-98] | 59.8% [51-68] |
| v3_fuseF_st0.3 | tuning: strength 0.3, IP scale 1.0 (full-resolution supports) | 56 | 55.4% [42-68] | 91.1% [81-96] | 55.4% [42-68] |
| v3_fuseF_st0.4 | tuning: strength 0.4, IP scale 1.0 (full-resolution supports) | 112 | 61.6% [52-70] | 95.5% [90-98] | 61.6% [52-70] |
| v3_fuseF_st0.6 | tuning: strength 0.6, IP scale 1.0 (full-resolution supports) | 56 | 62.5% [49-74] | 92.9% [83-97] | 62.5% [49-74] |
| v3_fuseF_ip0.5 | tuning: strength 0.5, IP scale 0.5 (full-resolution supports) | 56 | 57.1% [44-69] | 91.1% [81-96] | 55.4% [42-68] |
| v3_fuseF_ip0.75 | tuning: strength 0.5, IP scale 0.75 (full-resolution supports) | 56 | 62.5% [49-74] | 91.1% [81-96] | 60.7% [48-72] |
| rw_fuseF | fusion with full-resolution supporting reconstructions (strength 0.5, IP scale 1.0) | 61 | 85.2% [74-92] | 96.7% [89-99] | 85.2% [74-92] |
| rw_fuseF_st0.3 | tuning: strength 0.3, IP scale 1.0 (full-resolution supports) | 30 | 86.7% [70-95] | 100.0% [89-100] | 86.7% [70-95] |
| rw_fuseF_st0.4 | tuning: strength 0.4, IP scale 1.0 (full-resolution supports) | 61 | 78.7% [67-87] | 96.7% [89-99] | 78.7% [67-87] |
| rw_fuseF_st0.6 | tuning: strength 0.6, IP scale 1.0 (full-resolution supports) | 30 | 90.0% [74-97] | 96.7% [83-99] | 90.0% [74-97] |
| rw_fuseF_ip0.5 | tuning: strength 0.5, IP scale 0.5 (full-resolution supports) | 29 | 96.6% [83-99] | 96.6% [83-99] | 93.1% [78-98] |
| rw_fuseF_ip0.75 | tuning: strength 0.5, IP scale 0.75 (full-resolution supports) | 30 | 93.3% [79-98] | 96.7% [83-99] | 93.3% [79-98] |

## Paired comparisons (same cases; McNemar exact test on the joint score)

| dataset | comparison | pairs | joint B | joint A | change | B better / A better | p |
|---|---|---|---|---|---|---|---|
| v3 | Damir's two fixes (working resolution + ADE20K palette) vs current receiver | 112 | 43.8% | 36.6% | +7.1 pts | 24 / 16 | 0.268 |
| v3 | multi-camera captions vs reference camera only (current receiver) | 112 | 36.6% | 33.0% | +3.6 pts | 17 / 13 | 0.585 |
| v3 | multi-camera captions vs reference camera only (with both fixes) | 112 | 43.8% | 46.4% | -2.7 pts | 17 / 20 | 0.743 |
| v3 | working resolution alone | 112 | 37.5% | 36.6% | +0.9 pts | 19 / 18 | 1.000 |
| v3 | ADE20K palette alone | 112 | 37.5% | 36.6% | +0.9 pts | 14 / 13 | 1.000 |
| v3 | ControlNet canny 0.7 / seg 1.5 | 112 | 49.1% | 36.6% | +12.5 pts | 22 / 8 | 0.016 |
| v3 | canny 0.7 / seg 1.5 on top of both fixes | 112 | 43.8% | 43.8% | +0.0 pts | 23 / 23 | 1.000 |
| v3 | multi-camera captions vs reference camera only (both fixes + canny 0.7 / seg 1.5) | 112 | 43.8% | 52.7% | -8.9 pts | 16 / 26 | 0.164 |
| v3 | Damir's fusion vs the main reconstruction (his single-camera MMSD at paper settings) | 112 | 69.6% | 56.2% | +13.4 pts | 31 / 16 | 0.040 |
| v3 | supporting reconstructions through the IP-Adapter vs re-denoising only | 112 | 69.6% | 61.6% | +8.0 pts | 21 / 12 | 0.163 |
| v3 | re-denoising the main reconstruction alone (img2img, no IP-Adapter) | 112 | 61.6% | 56.2% | +5.4 pts | 19 / 13 | 0.377 |
| v3 | supporting reconstructions at full resolution vs 896x512 (fusion, strength 0.5, IP scale 1.0) | 112 | 59.8% | 69.6% | -9.8 pts | 11 / 22 | 0.080 |
| v3 | fusion with full-resolution supports vs the single-camera MMSD | 112 | 59.8% | 56.2% | +3.6 pts | 26 / 22 | 0.665 |
| v3 | multi-camera captions vs the seed paper's single-camera MMSD, both at the paper's settings | 112 | 50.0% | 56.2% | -6.2 pts | 13 / 20 | 0.296 |
| v3 | our best multi-camera setting vs the seed paper's single-camera MMSD at its settings | 112 | 43.8% | 56.2% | -12.5 pts | 18 / 32 | 0.065 |
| v3 | our best single-camera setting vs the seed paper's single-camera MMSD at its settings | 112 | 52.7% | 56.2% | -3.6 pts | 24 / 28 | 0.678 |
| rw | Damir's two fixes (working resolution + ADE20K palette) vs current receiver | 61 | 45.9% | 27.9% | +18.0 pts | 15 / 4 | 0.019 |
| rw | multi-camera captions vs reference camera only (current receiver) | 61 | 27.9% | 26.2% | +1.6 pts | 2 / 1 | 1.000 |
| rw | multi-camera captions vs reference camera only (with both fixes) | 61 | 45.9% | 54.1% | -8.2 pts | 2 / 7 | 0.180 |
| rw | working resolution alone | 61 | 44.3% | 27.9% | +16.4 pts | 14 / 4 | 0.031 |
| rw | ADE20K palette alone | 61 | 29.5% | 27.9% | +1.6 pts | 4 / 3 | 1.000 |
| rw | ControlNet canny 0.7 / seg 1.5 | 61 | 34.4% | 27.9% | +6.6 pts | 7 / 3 | 0.344 |
| rw | canny 0.7 / seg 1.5 on top of both fixes | 61 | 50.8% | 45.9% | +4.9 pts | 10 / 7 | 0.629 |
| rw | multi-camera captions vs reference camera only (both fixes + canny 0.7 / seg 1.5) | 61 | 50.8% | 57.4% | -6.6 pts | 8 / 12 | 0.503 |
| rw | Damir's fusion vs the main reconstruction (his single-camera MMSD at paper settings) | 61 | 80.3% | 75.4% | +4.9 pts | 7 / 4 | 0.549 |
| rw | supporting reconstructions through the IP-Adapter vs re-denoising only | 61 | 80.3% | 63.9% | +16.4 pts | 13 / 3 | 0.021 |
| rw | re-denoising the main reconstruction alone (img2img, no IP-Adapter) | 61 | 63.9% | 75.4% | -11.5 pts | 4 / 11 | 0.118 |
| rw | supporting reconstructions at full resolution vs 896x512 (fusion, strength 0.5, IP scale 1.0) | 61 | 85.2% | 80.3% | +4.9 pts | 5 / 2 | 0.453 |
| rw | fusion with full-resolution supports vs the single-camera MMSD | 61 | 85.2% | 75.4% | +9.8 pts | 8 / 2 | 0.109 |
| rw | multi-camera captions vs the seed paper's single-camera MMSD, both at the paper's settings | 61 | 73.8% | 75.4% | -1.6 pts | 5 / 6 | 1.000 |
| rw | our best multi-camera setting vs the seed paper's single-camera MMSD at its settings | 61 | 50.8% | 75.4% | -24.6 pts | 5 / 20 | 0.004 |
| rw | our best single-camera setting vs the seed paper's single-camera MMSD at its settings | 61 | 57.4% | 75.4% | -18.0 pts | 7 / 18 | 0.043 |
| cs | ADE20K palette vs Cityscapes palette (authors' settings, 2048x1024) | 100 | 41.0% | 41.0% | +0.0 pts | 14 / 14 | 1.000 |

Answers whose score could not be parsed (counted as unfinished and retried): 0.

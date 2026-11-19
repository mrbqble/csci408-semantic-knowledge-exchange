CSCI 408, Group 22: multi-camera results, 19 Nov 2026
====================================================

WHAT WAS MEASURED
Damir's multi-camera fusion against his single-camera MMSD, scored by the VLM judge (gemma-4-31b-it, Damir's prompts).
For each case, the judge compares the main camera's original photo with the reconstruction and answers two yes/no questions:
are the car numbers preserved, and are the car positions preserved. "Joint" means both answers are yes.

FILES
01_results_chart.png                joint success per setup (CARLA v3: 112 cases; real-world Astana: 61 cases)
02_paired_tests.png                 paired comparisons (McNemar), plus fixes and breaks
03_pipeline_real_world_case1.jpg    the whole pipeline step by step (3 phones)
04_pipeline_carla_case10.jpg        the whole pipeline step by step (4 CARLA cameras)
05_fixed_examples_carla.jpg         single camera fails, fusion succeeds (first three such cases by number)
06_fixed_examples_real_world.jpg    the same for real-world (first two such cases)
07_broken_examples.jpg              single camera succeeds, fusion fails (first such case in each dataset)

HEADLINE
- CARLA:      fusion 69.6% joint vs 56.2% for the single camera  (+13.4 pts; 31 better, 16 worse; p = 0.04)
- Real-world: fusion 80.3% joint vs 75.4% for the single camera  (+4.9 pts; 7 better, 4 worse; not significant)
- The other cameras' views help: the fusion beats the same pass without the IP-Adapter by
  +8.0 pts on CARLA and +16.4 pts on real-world (p = 0.02).
- Trade-off: on CARLA the fusion fixes 31 of 49 single-camera failures and breaks 16 of 63 successes;
  on real-world it fixes 7 of 15 and breaks 4 of 46.
- Our earlier multi-camera receiver, which used the other cameras' captions only, never beat the single camera.

PIPELINE (Damir's diagram)
1. Every device sends segmentation map + edge map + caption.
2. The receiver reconstructs every device from its own payload.
3. The main reconstruction (cam1) gets noise added: img2img, strength 0.5.
4. The ControlNets get the main camera's segmentation and edge maps.
5. The IP-Adapter gets the other devices' reconstructions (mean CLIP embedding, scale 1.0).
6. The prompt is a global caption from all devices.
Stable Diffusion 1.5, generation at the photo's resolution (1920x1088).

NOTES
- The seed paper's 86-87% came from an older Gemma judge that is no longer available (Damir), so it is not
  comparable. Every number here comes from the same judge.
- The real-world photos show faces and licence plates. Share within the team and the lab only.
- Code and full report: github.com/mrbqble/csci408-semantic-knowledge-exchange, branch iter2-multicam,
  file iter2/VLM_FINDINGS.md.

-----------------------------------------------------------------------------------------------------------
КРАТКО ПО-РУССКИ
Сравнили мультикамерный фьюжн Дамира с его single-camera MMSD. Судья VLM (gemma-4-31b-it, промпты Дамира)
сравнивает оригинал главной камеры с реконструкцией и отвечает отдельно, сохранено ли количество машин и их позиции.
Joint = оба ответа «да».
- CARLA (112): фьюжн 69,6% против 56,2% (+13,4 п., p = 0,04).
- Реальные (61): 80,3% против 75,4% (+4,9 п., незначимо).
- Вклад других камер (фьюжн против того же прохода без IP-Adapter): +8,0 п. на CARLA и +16,4 п. на реальных (p = 0,02).
- Компромисс: на CARLA фьюжн исправляет 31 из 49 провалов одиночной камеры, но портит 16 из 63 удачных.
- 86–87% из статьи получены более старой версией Gemma-судьи (по словам Дамира), сравнивать с ними нельзя.
- На реальных фото видны лица и номера: делиться только внутри команды и лаборатории.

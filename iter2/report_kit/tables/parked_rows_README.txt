Damir's scenario: cars parked along the sides of the street, the distant ones hard to see.
Selection (automatic, no hand-picking): the judge's description of the original mentions parked cars AND distant/partly hidden/small ones,
and the detector finds at least 4 vehicles on the original, at least 2 of them small (< 6% of the image height).

CARLA v3: 10 such cases. Baseline passes 3 (30%), fusion passes 6 (60%); fusion better in 4, worse in 1 (McNemar p = 0.375).
Real-world: 10 such cases. Baseline passes 8 (80%), fusion passes 7 (70%); fusion better in 1, worse in 2 (McNemar p = 1.000).

Images: every such case where the fusion passes and the baseline fails, with zoomed crops of the distant parked cars.
Caveat: the judge sometimes counts the same original differently in two requests, so single cases can partly reflect judge noise.

# Literature map for the report

These are the 28 papers the team collected (course folder; file names in brackets), plus the models, datasets and tools the pipeline uses.

**How the entries were prepared:** titles, authors and venues were taken from each PDF's first page. Entries marked *(arXiv)* show only the preprint on the first page; check the published venue before the final version. Format the list in the report's citation style (IEEE for a conference paper).

## A. Papers in the course folder

| Group | Reference | Relevance to our work |
|---|---|---|
| **Seed paper** | D. Assylbek, ..., D. Zorbas, "Efficient semantic image communication for traffic monitoring at the edge," *Internet of Things*, vol. 39, 102029, 2026 [C2_Assylbek2026_MMSD-seed] | The single-camera MMSD method we build on and compare against. Payload: segmentation map, edge map, caption; receiver: SD 1.5 + 2 ControlNets. VLM-judge evaluation in its Table 6. |
| Semantic communication: surveys | X. Luo, H.-H. Chen, Q. Guo, "Semantic communications: Overview, open issues, and future research directions" [C1_Luo2022] | Background: semantic communication, IoT use cases |
| | W. Yang et al., "Semantic communications for future internet: Fundamentals, applications, and challenges," arXiv:2207.00427 [C1_Yang2023] | Background survey |
| | D. Gündüz et al., "Beyond transmitting bits: Context, semantics, and task-oriented communications," arXiv:2207.09353 [C1_Gunduz2023] | Task-oriented communication framing |
| | E. Bourtsoulatze, D. Burth Kurka, D. Gündüz, "Deep joint source-channel coding for wireless image transmission," arXiv:1809.01733 [C1_Bourtsoulatze2019] | Learned image transmission (deep JSCC), contrasted with our modular payload |
| Semantic image coding | F. Pezone, O. Musa, G. Caire, S. Barbarossa, "Semantic-preserving image coding based on conditional diffusion models," arXiv:2310.15737 [C2_Pezone2024_SPIC] | Diffusion-based semantic image coding; the seed paper's SPIC baseline |
| | F. Pezone, S. Barbarossa, G. Caire, "SQ-GAN: Semantic image communications using masked vector quantization," *IEEE Trans. Cognitive Communications and Networking*, 2025 (arXiv:2502.09520) [C2_Pezone2025] | Semantic masking and compression |
| | J. Chang et al., "Semantic-aware visual decomposition for image coding," *Int. J. Computer Vision*, 131:2333-2355, 2023 [C2_Chang2023] | Semantic maps plus textures for coding |
| Task-oriented transmission | C.-H. Lee et al., "Deep learning-constructed joint transmission-recognition for Internet of Things," *IEEE Access*, vol. 7, 2019, doi:10.1109/ACCESS.2019.2920929 [C3_Lee2019] | Transmission designed for recognition at the server (the proposal's original classification framing) |
| | X. Kang et al., "Task-oriented image transmission for scene classification in unmanned aerial systems," arXiv:2112.10948 [C3_Kang2022] | Task-oriented transmission for classification |
| | J. Kang et al., "Personalized saliency in task-oriented semantic communications: Image transmission and performance analysis," arXiv:2209.12274 [C3_Kang2023] | Saliency-driven semantic transmission |
| | Y. Peng et al., "Semantic communications with computer vision sensing for edge video transmission," *IEEE Trans. Mobile Computing*, doi:10.1109/TMC.2025.3646710 [C3_Peng2026] | Semantic transmission at the edge |
| Multi-view and collaborative perception | Y. Hou, L. Zheng, S. Gould, "Multiview detection with feature perspective transformation" (MVDet), ECCV 2020 [C4_Hou2020] | Fusing several cameras of one scene (the multi-camera motivation) |
| | Y. Hu et al., "Where2comm: Communication-efficient collaborative perception via spatial confidence maps," NeurIPS 2022 [C4_Hu2022] | Communication-efficient sharing between agents |
| | T.-H. Wang et al., "V2VNet: Vehicle-to-vehicle communication for joint perception and prediction," ECCV 2020 [C4_Wang2020] | Collaborative perception between vehicles |
| | A. Mohamed, M. M. Ahmed, "Multi-camera machine vision for detecting and analyzing vehicle-pedestrian conflicts at signalized intersections..." (2025) [C4_Mohamed2025] | Multi-camera traffic monitoring at intersections (application context) |
| Distributed / edge inference | S. Teerapittayanon, B. McDanel, H. T. Kung, "Distributed deep neural networks over the cloud, the edge and end devices," ICDCS 2017 (arXiv:1709.01921) [C5_Teerapittayanon2017] | Multi-view sensor fusion in a device-edge-cloud hierarchy |
| | J. Shao, Y. Mao, J. Zhang, "Task-oriented communication for multi-device cooperative edge inference," arXiv:2109.00172 [C5_Shao2023] | Several devices sending features to an edge server |
| | M. Palena, T. Cerquitelli, C. F. Chiasserini, "Edge-device collaborative computing for multi-view classification," arXiv:2409.15973 [C5_Palena2024] | Multi-view classification at the edge |
| | S. Wang, K. Yang, J. Dai, K. Niu, "Distributed image transmission using deep joint source-channel coding," arXiv:2201.10340 [C5_Wang2022] | Distributed image transmission with correlated sources |
| Energy and tiny ML | W. R. Heinzelman, A. Chandrakasan, H. Balakrishnan, "Energy-efficient communication protocol for wireless microsensor networks" (LEACH), HICSS 2000 [C6_Heinzelman2000] | Energy cost of sensor communication |
| | M. Horowitz, "Computing's energy problem (and what we can do about it)," ISSCC 2014 [C6_Horowitz2014] | Energy cost of computation vs data movement |
| | A. Kargar, ..., D. Zorbas, ..., "Tiny deep learning model for insect segmentation and counting on resource-constrained devices," *Computers and Electronics in Agriculture*, 236, 110378, 2025 [C6_Kargar2025] | Segmentation on constrained devices (adviser's work) |
| | J. Lin et al., "MCUNet: Tiny deep learning on IoT devices," NeurIPS 2020 [C6_Lin2020] | Deep learning on microcontrollers |
| Federated / privacy (context) | H. B. McMahan et al., "Communication-efficient learning of deep networks from decentralized data" (FedAvg), AISTATS 2017 (arXiv:1602.05629) [CX_McMahan2017] | Distributed learning context (not used) |
| | Q. Wang, K. Yang, "Privacy-preserving data fusion for traffic state estimation: A vertical federated learning approach," arXiv:2401.11836 [CX_Wang2024] | Traffic data fusion with privacy (context) |
| Generative models used | R. Rombach et al., "High-resolution image synthesis with latent diffusion models," CVPR 2022 [M_Rombach2022] | Stable Diffusion (receiver) |
| | L. Zhang, A. Rao, M. Agrawala, "Adding conditional control to text-to-image diffusion models" (ControlNet), ICCV 2023 (arXiv:2302.05543) [M_Zhang2023] | ControlNet on segmentation and edge maps |
| | H. Ye et al., "IP-Adapter: Text compatible image prompt adapter for text-to-image diffusion models," arXiv:2308.06721 [M_Ye2023] | IP-Adapter in Damir's fusion |

## B. Models, datasets and tools used (cite these too)

| What | Reference to cite | Where it is used |
|---|---|---|
| Mask2Former | B. Cheng et al., "Masked-attention mask transformer for universal image segmentation," CVPR 2022; checkpoint `facebook/mask2former-swin-large-cityscapes-semantic` | Sender: segmentation map |
| BLIP | J. Li et al., "BLIP: Bootstrapping language-image pre-training for unified vision-language understanding and generation," ICML 2022; checkpoint `Salesforce/blip-image-captioning-base` | Sender: caption |
| Canny edge detector | J. Canny, "A computational approach to edge detection," IEEE TPAMI, 1986 | Sender: edge map |
| Stable Diffusion 1.5 | Rombach et al. (above); checkpoint `runwayml/stable-diffusion-v1-5` | Receiver |
| ControlNet checkpoints | `lllyasviel/sd-controlnet-canny`, `lllyasviel/sd-controlnet-seg` (Zhang et al., above) | Receiver |
| IP-Adapter checkpoint | `h94/IP-Adapter`, `ip-adapter_sd15.bin` (Ye et al., above) | Damir's fusion |
| UniPC scheduler | W. Zhao et al., "UniPC: A unified predictor-corrector framework for fast sampling of diffusion models," NeurIPS 2023 | Receiver sampling (20 steps) |
| Gemma 4 (31B, instruction-tuned) | Google DeepMind, Gemma model family; used through the Gemini API (`gemma-4-31b-it`), Nov 2026 | VLM judge |
| CARLA | A. Dosovitskiy et al., "CARLA: An open urban driving simulator," CoRL 2017; version 0.9.16 | CARLA v2/v3/v4 datasets |
| Cityscapes | M. Cordts et al., "The Cityscapes dataset for semantic urban scene understanding," CVPR 2016 | Segmentation classes and palette; reproduction check |
| ADE20K | B. Zhou et al., "Scene parsing through ADE20K dataset," CVPR 2017 | The palette expected by the segmentation ControlNet (Damir's point 2) |
| Faster R-CNN (detector era only) | S. Ren et al., "Faster R-CNN: Towards real-time object detection with region proposal networks," NeurIPS 2015 | October detector-based evaluation (superseded) |
| McNemar test, Wilson interval | Q. McNemar, *Psychometrika*, 1947; E. B. Wilson, *J. Amer. Statist. Assoc.*, 1927 | Statistics |
| Diffusers / Transformers / PyTorch | Hugging Face `diffusers` 0.41, `transformers` 5.17; PyTorch 2.14 | Implementation |

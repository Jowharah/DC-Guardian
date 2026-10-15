# Datasets, models and sources: citations and terms

**Updated:** 2026-10-14 (face dataset confirmed by the operator). Every external dataset, pretrained model and knowledge source DC-GUARDIAN uses, with the citation it asks for and its terms. Datasets are never committed to Git (see `.gitignore`); only results and frozen model weights are.

Licence terms were checked against the official pages on 2026-10-14. Re-check them before any non-academic use. Items marked **To confirm** need the operator.

## 1. Datasets

| Dataset | Used for | Terms | What the terms require |
|---|---|---|---|
| **SH17**: Ahmad & Rahimi (2024) | PPE detector v1 and v2 (training, validation, locked test) | **CC BY-NC-SA 4.0** (official GitHub README) | Cite the paper. Non-commercial use only. Derivatives under the same licence, which arguably covers the PPE weights trained on it. |
| **CHV, Color Helmet and Vest**: Wang et al. (2021) | Third-dataset PPE test (detection and compliance, 2026-10-15; not used for training) | Free use stated by the authors (no named licence) | Cite the paper. 1,330 images from online sources and existing open datasets; 175 near-duplicates of SH17 or Kaggle images excluded in the test. |
| **Safety Helmet and Reflective Jacket**: Naik (2023), Kaggle | External PPE test, helmet and vest (2026-10-14) | **Apache 2.0** (Kaggle dataset metadata) | Attribution and the licence notice. The image sources are not documented by the author. |
| **Backblaze Drive Stats** (2025 Q2 – 2026 Q1) | Predictive maintenance (Temporal RF v2, GRU challenger) | Backblaze conditions (no licence name given) | Cite Backblaze as the source; you are solely responsible for how you use the data; derivative works may be sold, the data itself may not. |
| **Loghub OpenSSH**: Zhu et al. (2023) | SSH anomaly detector: parser, features, model development | Loghub terms (Zenodo record) | Free for research or academic work, on condition that users refer to the repository and cite the paper. Include the licence notice in copies. |
| **SSH honeypot dataset**: Boiko & Niiakyi (2026), Zenodo, *A 4-Month Dataset of SSH Botnet Interactions and Command Payloads* (`ssh_honeypot_dataset.csv`; 145,425 events, 27 Jul – 14 Nov 2025) | External behavioural validation of the SSH detector (not training) | **CC BY 4.0** (Zenodo record) | Attribution (cite the dataset and its data paper). Confirmed 2026-10-14 by comparing the local file with the record's `ssh_attacks_full.csv` (v2.3): same columns, all 145,425 events with the same timestamps, sessions, IPs, ports, event types and messages. The local file is an **earlier release**: v2.1 re-labelled the `level` column (INFO = connection noise, WARNING = attack actions), and 42 command texts differ only in line endings. `analyze_honeypot.py` does not read `level`, so the published SSH findings are unaffected. |
| **Face Verification Dataset**: Zagorskii (2025), Kaggle (`juice0lover/face-identification`) | Face recognition: 46 images of 13 actors chosen from it (`controlled_faces/`): 5 enrolled as "staff", 5 unknown for the locked test, 3 unknown for validation | **MIT** (Kaggle dataset metadata) | Attribution and the licence notice. The author describes the images as faces of actors "sourced from online film databases and public web resources", cropped automatically and resized to 100 × 100 px; the 46 project images are all 100 × 100. The MIT licence covers the author's compilation; it cannot grant rights in the underlying photographs or the people's likenesses. Use them for academic testing only, and never commit them; the photos and enrollment embeddings stay local. |
| **DC-01 topology** (`shared/topology/`) and **labelled scenarios** (`reasoning/uncertainty/scenarios/`) | Reasoning, correlation, Bayesian study, Decision v2 validation | Written by the project team (synthetic) | None external. Described in the report as synthetic and author-labelled. |

## 2. Pretrained models and libraries whose terms matter

| Model or library | Used for | Terms | Note |
|---|---|---|---|
| **Ultralytics YOLOv8** (n/s/m, COCO-pretrained start): Jocher et al. (2023) | PPE detector | **AGPL-3.0** (Ultralytics) | Fine for an academic prototype. A commercial or closed deployment needs an Ultralytics Enterprise licence or full AGPL compliance. |
| **COCO**: Lin et al. (2014) | The YOLOv8 starting weights were pretrained on it | Annotations CC BY 4.0; images under their Flickr terms | Cite as the pretraining dataset. |
| **DeepFace**: Serengil & Ozpinar | Face pipeline wrapper | MIT | Cite the framework paper. |
| **ArcFace**: Deng et al. (2019); **RetinaFace**: Deng et al. (2020) | Face embedding and face detection | The weights downloaded by DeepFace carry their own terms. InsightFace's pretrained models are for non-commercial research. | **To confirm:** the exact weight files and their licence before any non-academic use. |
| **all-MiniLM-L6-v2** (sentence-transformers): Reimers & Gurevych (2019); MiniLM: Wang et al. (2020) | RAG embeddings | Apache 2.0 (model card) | Cite Sentence-BERT. |
| **OpenAI gpt-4.1-mini** (API) | Specialist agents, Investigator, post-generation judge | OpenAI terms of use (a service, not a dataset) | Name the model and access dates in the report. Evidence sent is minimised and pseudonymised. |

## 3. Approved knowledge sources (RAG)

The 15 public documents in `response/rag/manifests/knowledge_manifest.json`, cited by publisher, title, version and URL:
- **NIST:** SP 800-61r3, 800-40r4, 800-53r5 (PE family) and 800-34r1.
- **CISA:**
  - Incident & Vulnerability Response Playbooks;
  - ISC Facility Access Control (2020).
- **OSHA:** 29 CFR 1910.132, .135, .137, .147 and .38.
- **U.S. DOE FEMP:** four operations and maintenance and data-centre guides.

The sixteenth source is the project's own *DC-GUARDIAN Operational Response Policy v1*.

U.S. federal government works (NIST, OSHA, DOE) are generally in the public domain; CISA documents usually are too. Cite them as references.

## 4. What this means for the project

- **Academic use (the practice module) is covered,** provided the citations below appear in the report.
- **The PPE detector is the main obstacle to commercial or industrial use.** SH17 is non-commercial and share-alike, and Ultralytics is AGPL-3.0. A production deployment would need commercially licensed training data and an Enterprise licence, or a permissively licensed detector. The InsightFace-derived face weights raise the same question. The face images are public web photos of actors (Face Verification Dataset, MIT for the compilation); they are fine for testing the pipeline, but a deployment would enrol its own staff with consent and a biometric-data policy. Add this to the production requirements (`PRODUCTION_READINESS.md`).
- **Backblaze, Loghub and the SSH honeypot dataset (CC BY 4.0) allow research use with citation.**

## 5. References (BibTeX)

```bibtex
@article{ahmad2024sh17,
  title   = {SH17: A dataset for human safety and personal protective equipment detection in manufacturing industry},
  author  = {Ahmad, Hafiz Mughees and Rahimi, Afshin},
  journal = {Journal of Safety Science and Resilience},
  volume  = {6}, number = {2}, pages = {175--185}, year = {2025},
  doi     = {10.1016/j.jnlssr.2024.09.002},
  note    = {Dataset: https://github.com/ahmadmughees/SH17dataset, CC BY-NC-SA 4.0}
}
@article{wang2021chv,
  title   = {Fast Personal Protective Equipment Detection for Real Construction Sites Using Deep Learning Approaches},
  author  = {Wang, Zijian and Wu, Yimin and Yang, Lichao and Thirunavukarasu, Arjun and Evison, Colin and Zhao, Yifan},
  journal = {Sensors},
  volume  = {21}, number = {10}, pages = {3478}, year = {2021},
  doi     = {10.3390/s21103478},
  note    = {CHV dataset: https://github.com/ZijianWang-ZW/PPE_detection}
}
@misc{naik2023helmetjacket,
  title        = {Safety Helmet and Reflective Jacket},
  author       = {Naik, Nirav B.},
  year         = {2023},
  howpublished = {Kaggle dataset, https://www.kaggle.com/datasets/niravnaik/safety-helmet-and-reflective-jacket},
  note         = {Apache 2.0; accessed 2026-10-14}
}
@misc{backblaze_drivestats,
  title        = {Hard Drive Data and Stats (Drive Stats)},
  author       = {{Backblaze, Inc.}},
  howpublished = {https://www.backblaze.com/cloud-storage/resources/hard-drive-test-data},
  note         = {Quarters 2025 Q2 to 2026 Q1; accessed 2026}
}
@misc{boiko2026sshhoneypot,
  title        = {A 4-Month Dataset of {SSH} Botnet Interactions and Command Payloads},
  author       = {Boiko, Viktor and Niiakyi, Oleksandr},
  year         = {2026},
  publisher    = {Zenodo},
  version      = {2.3},
  doi          = {10.5281/zenodo.20435481},
  note         = {CC BY 4.0; the project used an earlier release with the same events (pre-v2.1 level labels); accessed 2026-10-14}
}
@article{boiko2026sshhoneypotdib,
  title   = {A 4-Month Dataset of Interactive {SSH} Honeypot Logs and Command Payloads},
  author  = {Boiko, Viktor and Niiakyi, Oleksandr},
  journal = {Data in Brief},
  volume  = {66},
  pages   = {112860},
  year    = {2026},
  doi     = {10.1016/j.dib.2026.112860}
}
@misc{zagorskii2025faceverification,
  title        = {Face Verification Dataset},
  author       = {Zagorskii, Aleksei},
  year         = {2025},
  howpublished = {Kaggle dataset, https://www.kaggle.com/datasets/juice0lover/face-identification},
  note         = {MIT; cropped actor faces from public web sources, 100 x 100 px; accessed 2026-10-14}
}
@inproceedings{zhu2023loghub,
  title     = {Loghub: A Large Collection of System Log Datasets for {AI}-driven Log Analytics},
  author    = {Zhu, Jieming and He, Shilin and He, Pinjia and Liu, Jinyang and Lyu, Michael R.},
  booktitle = {IEEE International Symposium on Software Reliability Engineering (ISSRE)},
  year      = {2023},
  note      = {arXiv:2008.06448; dataset https://github.com/logpai/loghub}
}
@software{jocher2023yolov8,
  title   = {Ultralytics {YOLOv8}},
  author  = {Jocher, Glenn and Chaurasia, Ayush and Qiu, Jing},
  year    = {2023},
  version = {8.0.0},
  url     = {https://github.com/ultralytics/ultralytics},
  license = {AGPL-3.0}
}
@inproceedings{lin2014coco,
  title     = {Microsoft {COCO}: Common Objects in Context},
  author    = {Lin, Tsung-Yi and Maire, Michael and Belongie, Serge and Hays, James and Perona, Pietro and Ramanan, Deva and Doll{\'a}r, Piotr and Zitnick, C. Lawrence},
  booktitle = {European Conference on Computer Vision (ECCV)},
  year      = {2014}
}
@inproceedings{deng2019arcface,
  title     = {{ArcFace}: Additive Angular Margin Loss for Deep Face Recognition},
  author    = {Deng, Jiankang and Guo, Jia and Xue, Niannan and Zafeiriou, Stefanos},
  booktitle = {IEEE/CVF Conference on Computer Vision and Pattern Recognition (CVPR)},
  year      = {2019}
}
@inproceedings{deng2020retinaface,
  title     = {{RetinaFace}: Single-shot Multi-level Face Localisation in the Wild},
  author    = {Deng, Jiankang and Guo, Jia and Ververas, Evangelos and Kotsia, Irene and Zafeiriou, Stefanos},
  booktitle = {IEEE/CVF Conference on Computer Vision and Pattern Recognition (CVPR)},
  year      = {2020}
}
@inproceedings{serengil2020lightface,
  title     = {{LightFace}: A Hybrid Deep Face Recognition Framework},
  author    = {Serengil, Sefik Ilkin and Ozpinar, Alper},
  booktitle = {Innovations in Intelligent Systems and Applications Conference (ASYU)},
  year      = {2020}
}
@inproceedings{reimers2019sbert,
  title     = {Sentence-{BERT}: Sentence Embeddings using Siamese {BERT}-Networks},
  author    = {Reimers, Nils and Gurevych, Iryna},
  booktitle = {Conference on Empirical Methods in Natural Language Processing (EMNLP)},
  year      = {2019}
}
@inproceedings{wang2020minilm,
  title     = {{MiniLM}: Deep Self-Attention Distillation for Task-Agnostic Compression of Pre-Trained Transformers},
  author    = {Wang, Wenhui and Wei, Furu and Dong, Li and Bao, Hangbo and Yang, Nan and Zhou, Ming},
  booktitle = {Advances in Neural Information Processing Systems (NeurIPS)},
  year      = {2020}
}
```

The RAG documents are cited individually from the manifest (publisher, title, version, URL, access date).

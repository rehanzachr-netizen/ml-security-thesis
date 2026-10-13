# Securing Machine Learning Models

**Threat Modeling, Adversarial Robustness, and Practical Defenses**

BSc thesis project, University of Debrecen, Faculty of Informatics

| | |
|---|---|
| **Author** | Zacharia Rehan Rajesh |
| **Supervisor** | Dr. Oláh Norbert |
| **Topic** | Machine learning security |

---

## Overview

This project studies how machine learning models can be attacked and how they can be defended. It follows three steps:

1. **Train baseline models** on two standard image datasets (MNIST and CIFAR-10).
2. **Attack them** with seven attacks covering evasion, data poisoning, privacy leakage and model theft.
3. **Defend them** with practical defenses and measure the trade-off between clean accuracy and robustness.

The experiments are packaged as seven reproducible Jupyter notebooks and a command-line tool that runs attacks and defenses and outputs a security risk score. The tool can also be run in a Docker container. The practical recommendations that follow from the experiments are collected in [`SECURITY_CHECKLIST.md`](SECURITY_CHECKLIST.md).

All experiments use small models and public datasets, so the whole project runs on a normal laptop CPU without a GPU.

---

## Repository structure

```
ml-security-thesis/
├── notebooks/
│   ├── 01_baseline_models.ipynb      # Train MNIST SimpleCNN and CIFAR-10 ResNet-18
│   ├── 02_adversarial_attacks.ipynb  # FGSM, PGD, label-flip poisoning, membership inference
│   ├── 03_defenses.ipynb             # Adversarial training, input preprocessing, summary
│   ├── 04_additional_attacks.ipynb   # Carlini & Wagner, backdoor, model extraction
│   ├── 05_additional_defenses.ipynb  # Calibration, DP-SGD, integrity checks, rate limiting, watermarking
│   ├── 06_explainability.ipynb       # Saliency maps and error analysis
│   └── 07_ablation_study.ipynb       # Which attack and defense settings matter
├── models/                           # Trained model weights (.pth)
├── figures/                          # All generated plots used in the thesis
├── results/                          # Experiment results (.txt, .json)
├── ml_security_cli.py                # Command-line security evaluation tool
├── SECURITY_CHECKLIST.md             # ML security checklist backed by the experiments
├── Dockerfile                        # Container image for the CLI tool
├── requirements.txt                  # Python packages used by the project
└── .gitignore
```

The `data/` folder is not included in the repository because the datasets are large. They are downloaded automatically by Notebook 1 (see below).

---

## Setup

Tested on Windows 11 with Miniconda, Python 3.12 and PyTorch 2.11 (CPU).

**1. Create and activate the environment**

```bash
conda create -n thesis python=3.12 -y
conda activate thesis
```

**2. Clone the repository and install the dependencies**

```bash
git clone https://github.com/rehanzachr-netizen/ml-security-thesis.git
cd ml-security-thesis
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt
```

---

## Running the notebooks

Start Jupyter from the project folder:

```bash
conda activate thesis
jupyter notebook
```

Open the `notebooks` folder and run the notebooks **in order**. Inside each notebook, run the cells from top to bottom (or use **Kernel → Restart & Run All**).

| Notebook | What it does | Approx. CPU time |
|---|---|---|
| `01_baseline_models` | Downloads MNIST and CIFAR-10 into `data/`, trains both baseline models, saves them to `models/` | ~1.5 hours (ResNet-18 is the slow part) |
| `02_adversarial_attacks` | Loads the MNIST model and runs FGSM, PGD, label flipping and membership inference | ~30 minutes |
| `03_defenses` | FGSM and PGD adversarial training, input preprocessing defenses, summary heatmap | ~45-60 minutes |
| `04_additional_attacks` | Carlini & Wagner attack, backdoor attack, model extraction | ~15 minutes |
| `05_additional_defenses` | Calibration, DP-SGD, data integrity checks, rate limiting, watermarking | ~20 minutes |
| `06_explainability` | Saliency maps, error analysis under PGD, explaining the backdoor (needs notebook 4 to have been run) | ~3 minutes |
| `07_ablation_study` | Ablations: attack steps, adversarial-training settings, training budget, preprocessing strength (needs notebook 3 to have been run) | ~45-60 minutes |

**Notebook 1 must be run at least once on a new machine**, because it downloads the datasets that the other notebooks and the CLI tool rely on. The trained models are already included in `models/`, so once the data is downloaded, Notebooks 2 to 7 can be run without retraining the baselines. Notebook 5 needs the Opacus library, which is included in `requirements.txt`.

---

## Command-line tool

`ml_security_cli.py` evaluates the MNIST baseline model against attacks and defenses and reports a risk score. Run it from the project folder:

```bash
conda activate thesis

# Run a single attack
python ml_security_cli.py --attack fgsm --epsilon 0.3
python ml_security_cli.py --attack pgd --epsilon 0.3

# Run all attacks
python ml_security_cli.py --attack all --epsilon 0.3

# Measure an attack with a defense applied
python ml_security_cli.py --attack fgsm --defense gaussian --epsilon 0.3
python ml_security_cli.py --attack pgd --defense bitdepth --epsilon 0.3

# Generate the full security report (saved to results/security_report.json)
python ml_security_cli.py --report
```

| Option | Values | Default |
|---|---|---|
| `--attack` | `fgsm`, `pgd`, `all` | none |
| `--defense` | `gaussian`, `bitdepth` | none |
| `--epsilon` | attack strength in pixel units (0 = black, 1 = white), e.g. `0.1`, `0.3` | `0.3` |
| `--samples` | number of test images used | `500` |
| `--report` | runs the full attack and defense suite | off |

**Risk score.** The score converts the accuracy lost under attack into a value from 0 to 100 (accuracy drop × 1.5, capped at 100):

| Score | Level |
|---|---|
| 0–19 | LOW |
| 20–49 | MEDIUM |
| 50–74 | HIGH |
| 75–100 | CRITICAL |

The score is a simple, interpretable severity indicator rather than a formal security metric.

### Running the tool in Docker

The `Dockerfile` builds a small image containing the CLI tool, the baseline model and the MNIST test set, so the tool can be run without installing Python.

```bash
docker build -t ml-security-cli .

# Full security report (the default command)
docker run --rm ml-security-cli

# Any other CLI option
docker run --rm ml-security-cli --attack pgd --epsilon 0.3
```

To keep the JSON report on your own machine, mount the `results` folder (Windows Command Prompt syntax):

```bash
docker run --rm -v "%cd%\results:/app/results" ml-security-cli --report
```

---

## Key results

All attack and defense results are on MNIST. The values below come from one full run of the seven notebooks; small differences between machines and PyTorch versions are normal.

**Baselines (notebook 1)**

| Model | Dataset | Test accuracy |
|---|---|---|
| SimpleCNN (≈422K parameters, 3 epochs) | MNIST | 98.94% |
| ResNet-18 (≈11.2M parameters, 5 epochs) | CIFAR-10 | 82.80% |

**Attacks (notebooks 2 and 4)**

| Attack | Category | Result |
|---|---|---|
| FGSM | Evasion | Accuracy 99.09% → 86.81% (ε = 0.1), 47.74% (ε = 0.2), 12.82% (ε = 0.3) |
| PGD (40 steps) | Evasion | Accuracy 99.09% → 72.73% (ε = 0.1), 0.60% (ε = 0.2), 0.00% (ε = 0.3) |
| Carlini & Wagner L2 | Evasion | 100% success on 500 images against the baseline; mean L2 change 1.34 (0–1 pixel scale). Against the PGD-trained model: 99.2% success, mean L2 change 2.13 |
| Label flipping (9 → 4) | Poisoning | Accuracy on digit 9: 99.6% → 0.0%, while overall accuracy stayed at 89.1% |
| Backdoor (3×3 trigger, 1% of training data poisoned) | Poisoning | 99.76% of triggered images classified as the target class; clean accuracy 98.83% |
| Membership inference (confidence threshold) | Privacy | 50.6% attack accuracy vs 50% random guessing: the attack fails on this model |
| Model extraction | Model theft | A copy trained on 500 queries agrees with the victim on 94.75% of inputs; 8,000 queries give 98.95% |

**Defenses against evasion (notebook 3, ε = 0.3)**

| Defense | Clean | FGSM | PGD |
|---|---|---|---|
| No defense | 99.09% | 12.82% | 0.00% |
| FGSM adversarial training | 98.86% | 98.70% | 0.00% |
| PGD adversarial training | 98.53% | 94.69% | 91.00% |
| Gaussian smoothing | 98.76% | 38.63% | 1.35% |
| Bit-depth reduction | 99.08% | 14.69% | 0.00% |

ε is the largest allowed change per pixel, in pixel units (0 = black, 1 = white). ε = 0.3 is the standard budget for MNIST. Adversarial images are always clipped to the valid pixel range. The preprocessing defenses are tested against an attacker who does not know about the preprocessing.

**Additional defenses (notebook 5)**

| Defense | Protects against | Result |
|---|---|---|
| Temperature scaling | Over-confident predictions | Learned T = 1.09; calibration error unchanged (0.17% → 0.21%), so the baseline was already well calibrated |
| DP-SGD (5 epochs) | Leakage of training data | Formal guarantee of ε = 0.79 (δ = 10⁻⁵) at 93.56% test accuracy, or ε = 3.99 at 95.33%, compared with 99.09% without privacy |
| Data integrity checks (SHA-256) | Tampering with data or models | A single flipped label among 60,000 was detected |
| Rate limiting (500 queries) | Model extraction | Fidelity of the stolen copy reduced from 98.95% to 94.75%; returning labels only reduced it further to 93.60% |
| Watermarking (100 secret trigger images) | Proving ownership of a stolen model | Watermarked model matches 100/100 triggers; 95/100 survive fine-tuning by a thief; unmarked models match 8–16/100 |

**Explainability (notebook 6)**

- Saliency maps of the backdoored model put 27.4% of their weight on the 3×3 trigger area (1.1% of the image), compared with 1.9% for the clean model, so the backdoor is visible in the explanation.
- On images that FGSM fools, the share of saliency lying on the digit's own strokes drops from 30.9% to 21.0%: the model's attention moves off the digit.
- Under PGD (ε = 0.3) every digit is misclassified by the baseline model, most often 4 as 9 and 2, 7, 8 and 5 as 3. The PGD-trained model is weakest on the digit 8 (72.4% robust accuracy).

**Ablation study (notebook 7)**

Each setting is changed one at a time and measured on 2,000 test images, with PGD-40 at ε = 0.3 unless stated otherwise. The models in parts B and C are trained for 2 epochs only, so their numbers are lower than those of the 5-epoch model in notebook 3. Full output: `results/ablation_results.txt`.

*A. How many attack steps are needed (baseline and the PGD-trained model from notebook 3)*

| PGD steps | 1 | 5 | 10 | 20 | 40 | 100 |
|---|---|---|---|---|---|---|
| Baseline | 5.75% | 0.00% | 0.00% | 0.00% | 0.00% | 0.00% |
| PGD-trained | 94.45% | 91.35% | 90.00% | 89.20% | 88.40% | 88.10% |

The attack has almost stopped improving at 40 steps (88.40% → 88.10% at 100 steps). Without the random starting point, the same 40-step attack is stronger and lowers robust accuracy to 83.20%, so the notebook 3 figure of 91.00% (measured with a random start) is somewhat optimistic.

*B. How many attack steps are used during adversarial training (trained at ε = 0.3)*

| Training setting | Clean | FGSM | PGD |
|---|---|---|---|
| 1 step | 98.15% | 97.30% | 0.00% |
| 3 steps | 98.10% | 88.15% | 62.45% |
| 10 steps (reference) | 97.35% | 90.25% | 80.40% |
| 10 steps, adversarial images only (no clean images) | 68.05% | 50.20% | 42.95% |

Training with a 1-step attack repeats the FGSM-training failure from notebook 3; 3 steps already gives real robustness and 10 steps more. Training only on adversarial images was unstable: clean accuracy fell to 68.05% in this run, while a test run of the same setting on another machine reached 90.10% clean and 72.75% under PGD. Mixing clean and adversarial images gives a stable result.

*C. Training budget against attack budget (accuracy under PGD-40)*

| Model | Clean | ε = 0.1 | ε = 0.2 | ε = 0.3 |
|---|---|---|---|---|
| No defense | 98.60% | 67.40% | 0.35% | 0.00% |
| Trained with ε = 0.1 | 98.30% | 93.35% | 58.50% | 0.10% |
| Trained with ε = 0.2 | 98.15% | 94.60% | 86.05% | 9.60% |
| Trained with ε = 0.3 | 97.35% | 92.15% | 87.90% | 80.40% |

A model is robust up to the budget it was trained for and fails beyond it.

*D. Strength of input preprocessing (baseline model, accuracy under PGD-40)*

| Preprocessing | Clean | ε = 0.1 | ε = 0.2 | ε = 0.3 |
|---|---|---|---|---|
| None | 98.60% | 67.40% | 0.35% | 0.00% |
| Gaussian blur, σ = 0.5 | 98.40% | 78.40% | 4.40% | 0.00% |
| Gaussian blur, σ = 1.0 | 98.05% | 87.40% | 37.25% | 0.85% |
| Gaussian blur, σ = 2.0 | 95.25% | 88.20% | 69.80% | 37.15% |
| Bit depth, 4 bits | 98.55% | 79.35% | 0.45% | 0.00% |
| Bit depth, 2 bits | 98.60% | 95.20% | 0.00% | 0.00% |
| Bit depth, 1 bit | 98.65% | 96.40% | 90.90% | 82.30% |

Preprocessing helps at ε = 0.1 at every strength. At ε = 0.3 only the strongest settings help: 1-bit reduction (82.30%, because MNIST digits are almost black and white) and σ = 2 blur (37.15%, at a cost of 3.35 points of clean accuracy). These numbers are against an attacker who does not know about the preprocessing; an attacker who does can attack through it, so they are best-case values.

**Main findings**

- Iterative attacks (PGD) are far more damaging than single-step attacks (FGSM) at the same perturbation budget: at ε = 0.3 PGD reduces the undefended model to 0% accuracy. The Carlini & Wagner attack fools every tested image on the undefended model.
- Poisoning can be targeted and hard to notice: label flipping destroys one class, and a backdoor needs only 0.5–1% poisoned data (98–99.8% trigger success) while clean accuracy stays near 99%.
- A model can be copied through its prediction API with a few hundred queries.
- The simple confidence-based membership inference attack does not succeed against this model, which generalises well.
- PGD adversarial training is the only tested defense that survives PGD (91.00%), at a cost of 0.6 points of clean accuracy.
- FGSM adversarial training looks robust against FGSM (98.70%) but collapses to 0% under PGD, which shows that a defense must be evaluated against the strongest available attack.
- Input preprocessing helps against small perturbations (ε = 0.1) but, in the settings of notebook 3 (σ = 1 blur, 4-bit depth), gives almost no protection at ε = 0.3. Only the strongest settings help at ε = 0.3 (1-bit reduction 82.30%, σ = 2 blur 37.15%), and only against an attacker who does not know about the preprocessing.
- The ablation study shows that adversarial training needs a multi-step attack (1 step gives 0%, 3 steps 62.45%, 10 steps 80.40% after 2 epochs), a training budget at least as large as the attack budget, and a mix of clean and adversarial images.
- Robustness evaluation is sensitive to the attack settings: removing PGD's random start lowered the PGD-trained model from 88.40% to 83.20%, so robust accuracy should be reported as the lowest value over several attack variants.
- Differentially private training gives a formal privacy guarantee at a clear cost in accuracy.
- Rate limiting slows model extraction but does not prevent it; watermarking does not prevent theft but lets the owner prove it.

---

## References

**Thesis references (as approved in the thesis application)**

1. M. Xue, C. Yuan, H. Wu, Y. Zhang and W. Liu, "Machine Learning Security: Threats, Countermeasures, and Evaluations," IEEE Access, vol. 8, pp. 74720–74742, 2020, doi: 10.1109/ACCESS.2020.2987435.
2. B. Biggio, B. Nelson and P. Laskov, "Poisoning Attacks against Support Vector Machines," in Proc. 29th Int. Conf. Machine Learning (ICML), 2012.
3. F. Tramèr, F. Zhang, A. Juels, M. K. Reiter and T. Ristenpart, "Stealing Machine Learning Models via Prediction APIs," in Proc. 25th USENIX Security Symposium, 2016.
4. I. J. Goodfellow, J. Shlens and C. Szegedy, "Explaining and Harnessing Adversarial Examples," in Proc. ICLR, 2015.
5. C. Szegedy et al., "Intriguing Properties of Neural Networks," in Proc. ICLR, 2014.
6. A. Kurakin, I. Goodfellow and S. Bengio, "Adversarial Machine Learning at Scale," in Proc. ICLR, 2017.

**Additional references for implemented methods**

7. A. Madry, A. Makelov, L. Schmidt, D. Tsipras and A. Vladu, "Towards Deep Learning Models Resistant to Adversarial Attacks," in Proc. ICLR, 2018. (PGD attack)
8. R. Shokri, M. Stronati, C. Song and V. Shmatikov, "Membership Inference Attacks Against Machine Learning Models," in Proc. IEEE Symposium on Security and Privacy, 2017. (membership inference attack)
9. N. Carlini and D. Wagner, "Towards Evaluating the Robustness of Neural Networks," in Proc. IEEE Symposium on Security and Privacy, 2017. (C&W attack)
10. T. Gu, B. Dolan-Gavitt and S. Garg, "BadNets: Identifying Vulnerabilities in the Machine Learning Model Supply Chain," arXiv:1708.06733, 2017. (backdoor attack)
11. W. Xu, D. Evans and Y. Qi, "Feature Squeezing: Detecting Adversarial Examples in Deep Neural Networks," in Proc. NDSS, 2018. (smoothing and bit-depth reduction)
12. C. Guo, G. Pleiss, Y. Sun and K. Q. Weinberger, "On Calibration of Modern Neural Networks," in Proc. ICML, 2017. (temperature scaling)
13. M. Abadi et al., "Deep Learning with Differential Privacy," in Proc. ACM CCS, 2016. (DP-SGD)
14. Y. Adi, C. Baum, M. Cisse, B. Pinkas and J. Keshet, "Turning Your Weakness Into a Strength: Watermarking Deep Neural Networks by Backdooring," in Proc. USENIX Security Symposium, 2018. (watermarking)
15. K. Simonyan, A. Vedaldi and A. Zisserman, "Deep Inside Convolutional Networks: Visualising Image Classification Models and Saliency Maps," ICLR Workshop, 2014. (saliency maps)

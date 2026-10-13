# ML Security Checklist

A concise checklist for securing a machine learning model across its lifecycle. It is the practical outcome of the thesis *Securing Machine Learning Models: Threat Modeling, Adversarial Robustness, and Practical Defenses* (Zacharia Rehan Rajesh, University of Debrecen).

Every item is backed by an experiment in this repository. The evidence column gives the measured result on MNIST and the notebook it comes from, so each recommendation can be traced back to data. Attack strength ε is in pixel units (0 = black, 1 = white).

**How to use it:** go through the sections in order before a model is deployed, and again whenever the data, the model or the way it is exposed changes. An unchecked item is a known, documented risk, not necessarily a blocker.

---

## 1. Threat model

| ☐ | Check | Evidence from this project |
|---|---|---|
| ☐ | Write down what must be protected: training data, labels, model weights, the prediction API, and the privacy of the people in the data. | Each of these assets was attacked successfully in at least one experiment below. |
| ☐ | State what the attacker can do: change inputs, change training data, query the API, or read the weights. | The attacks in notebooks 2 and 4 each need a different capability; a defense against one does not cover the others. |
| ☐ | Decide the attack budget you defend against (for images, the largest allowed change per pixel, ε) and report it with every robustness number. | Baseline accuracy under PGD is 72.73% at ε = 0.1 and 0.00% at ε = 0.3. A robustness figure without its ε is meaningless (notebook 2). |

## 2. Data

| ☐ | Check | Evidence from this project |
|---|---|---|
| ☐ | Record a cryptographic hash (SHA-256) of every dataset file when it is known to be good, and verify the hashes before each training run. | A single flipped label among 60,000 changed the hash and was detected (notebook 5). |
| ☐ | Control and log who can modify training data and labels. | Relabelling the digit 9 as 4 took accuracy on that digit from 99.6% to 0.0% (notebook 2). |
| ☐ | Do not rely on overall accuracy to detect poisoning. Check accuracy per class. | After the label-flipping attack overall accuracy was still 89.1%, hiding a class that had failed completely (notebook 2). |
| ☐ | Treat data from untrusted sources as possibly backdoored, even when the trained model tests well. | Poisoning 0.5% of the training images (300 of 60,000) made a 3×3 pixel trigger work 98.04% of the time while clean accuracy stayed at 98.88% (notebook 4). |

## 3. Training

| ☐ | Check | Evidence from this project |
|---|---|---|
| ☐ | If the model will face adversarial inputs, use PGD adversarial training. | It kept 91.00% accuracy under PGD at ε = 0.3, where the undefended model had 0.00%, at a cost of 0.56 points of clean accuracy (notebook 3). |
| ☐ | Do not use single-step (FGSM) adversarial training as the defense. Use at least a few attack steps during training. | The FGSM-trained model scored 98.70% against FGSM but 0.00% against PGD: it only learned to resist the attack it was trained on (notebook 3). With 2 epochs of training, 1 step gave 0.00% under PGD, 3 steps 62.45% and 10 steps 80.40% (notebook 7). |
| ☐ | Train with an attack budget ε at least as large as the one in the threat model. | A model trained with ε = 0.1 kept 93.35% at ε = 0.1 but 0.10% at ε = 0.3; one trained with ε = 0.3 kept 80.40% at ε = 0.3 (notebook 7). |
| ☐ | Mix clean and adversarial images in each training batch rather than training on adversarial images only. | Adversarial-only training was unstable: clean accuracy 68.05% and PGD accuracy 42.95% in one run, 90.10% and 72.75% in another, against a stable 97.35% and 80.40% for the 50/50 mix (notebook 7). |
| ☐ | If the training data is sensitive, train with differential privacy (DP-SGD) and report the privacy budget ε and δ with the accuracy. | ε = 0.79 (δ = 10⁻⁵) gave 93.56% accuracy and ε = 3.99 gave 95.33%, against 99.09% without privacy (notebook 5). |
| ☐ | Hash the trained model file and store the hash with the release. | Model files are included in the integrity manifest (notebook 5). |

## 4. Evaluation before release

| ☐ | Check | Evidence from this project |
|---|---|---|
| ☐ | Report clean accuracy and robust accuracy side by side for every defense. | See the master results table (notebook 3, `results/MASTER_RESULTS.txt`). |
| ☐ | Test every defense against the strongest available attack, not only the one it was designed for. Use an iterative attack (PGD) and an optimisation attack (C&W). | FGSM left the baseline at 12.82% at ε = 0.3; PGD took it to 0.00%. C&W fooled 100% of images on the baseline and 99.2% on the PGD-trained model, which needed a larger change (mean L2 2.13 against 1.34) (notebooks 2 to 4). |
| ☐ | Check that the attack was run with enough steps for the result to have stopped changing, and try it with and without a random starting point. Report the lowest accuracy found. | On the PGD-trained model, robust accuracy fell from 94.45% (1 step) to 88.40% (40 steps) and 88.10% (100 steps), so 40 steps is enough. Without a random start the 40-step attack was stronger, giving 83.20% (notebook 7). |
| ☐ | Do not rely on input preprocessing (blurring, bit-depth reduction) as the only defense, and test it at several strengths and attack budgets. | At ε = 0.3 Gaussian smoothing (σ = 1) gave 1.35% and 4-bit depth reduction 0.00% accuracy under PGD (notebook 3). Every setting helped at ε = 0.1, but at ε = 0.3 only 1-bit reduction (82.30%) and σ = 2 blur (37.15%, clean accuracy down to 95.25%) did; 2-bit reduction gave 95.20% at ε = 0.1 and 0.00% at ε = 0.2 (notebook 7). All of this is against an attacker who does not know about the preprocessing. |
| ☐ | Inspect what the model looks at with a saliency method, on clean and suspicious inputs. | The backdoored model placed 27.4% of its saliency on the trigger area (1.1% of the image); the clean model placed 1.9% there (notebook 6). |
| ☐ | Measure privacy leakage with a membership inference test, and state which test was used. | A confidence-threshold attack reached 50.6% accuracy against 50% for guessing, so this simple attack found no leakage. Stronger attacks were not tested (notebook 2). |
| ☐ | Check calibration before any system relies on the model's confidence scores. | Expected calibration error was 0.17%; temperature scaling (T = 1.09) did not improve it, so the baseline was already well calibrated (notebook 5). |

## 5. Deployment and the prediction API

| ☐ | Check | Evidence from this project |
|---|---|---|
| ☐ | Limit the number of queries per client, and combine this with account controls. | 8,000 queries gave a stolen copy that agreed with the original on 98.95% of inputs. A 500-query limit reduced this to 94.75% (notebooks 4 and 5). |
| ☐ | Do not expect rate limiting alone to stop model theft. | Even 500 queries produced a 94.75% copy, and an attacker with several accounts can exceed any per-client limit (notebook 5). |
| ☐ | Return only what the client needs. Prefer the predicted label over full probabilities. | Label-only output lowered copy fidelity slightly at every query budget (for example 94.75% to 93.60% at 500 queries). It helps a little and costs nothing (notebook 4). |
| ☐ | Watermark the model so that a stolen copy can be identified. | The watermarked model matched 100/100 secret trigger images; 95/100 still matched after a thief fine-tuned it; unmarked models matched 8 to 16. Clean accuracy was unchanged (notebook 5). |
| ☐ | Verify the model file's hash when it is loaded in production. | Integrity manifest (notebook 5). |

## 6. Operation

| ☐ | Check | Evidence from this project |
|---|---|---|
| ☐ | Re-run the security evaluation whenever the model is retrained or the data changes. | `ml_security_cli.py --report` runs the attack suite and writes a risk report in about two minutes. |
| ☐ | Log queries per client and watch for unusually high volumes. | Model extraction needs many queries; the query count is the simplest signal of it (notebook 4). |
| ☐ | Keep the experiments reproducible: scripted runs, a recorded list of dependencies, and fixed random seeds. | Notebooks 1 to 7, `requirements.txt` and the `Dockerfile` in this repository. Notebooks 3 to 7 fix their random seeds; notebooks 1 and 2 do not, so their trained models vary slightly between runs. |

---

## Summary of what worked and what did not

| Threat | Worked | Did not work |
|---|---|---|
| Evasion (adversarial inputs) | PGD adversarial training with several steps, a matching ε and mixed clean images; strong preprocessing (1-bit) only against an attacker unaware of it | FGSM (1-step) adversarial training; training with a smaller ε than the attack; Gaussian smoothing (σ = 1) and 4-bit depth reduction at ε = 0.3 |
| Poisoning and backdoors | File hashing, per-class accuracy checks, saliency inspection | Checking overall accuracy only |
| Model theft | Watermarking (to prove theft) | Rate limiting and label-only output (they slow theft but do not prevent it) |
| Privacy leakage | DP-SGD gives a formal guarantee, at a cost of 3.8 to 5.5 points of accuracy | Not applicable: the membership inference attack tested here did not succeed even without a defense |

## Limits of this checklist

- All evidence comes from one small convolutional network on MNIST. The direction of each result is well established in the research literature, but the exact numbers will differ for other models and datasets.
- Robust accuracy is measured against the attacks implemented here. A defense that survives them is not proven secure against future or adaptive attacks.
- The preprocessing defenses were tested against an attacker who does not know about the preprocessing. An attacker who does would be at least as successful.
- The membership inference test is a basic one. A negative result from it does not show that the model leaks nothing.

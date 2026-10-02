#!/usr/bin/env python3
"""
ML Security CLI Tool
====================
Thesis: Securing Machine Learning Models
Author: Zacharia Rehan Rajesh

Usage examples:
  python ml_security_cli.py --attack fgsm --epsilon 0.3
  python ml_security_cli.py --attack pgd --epsilon 0.3
  python ml_security_cli.py --attack all --epsilon 0.3
  python ml_security_cli.py --defense adversarial_training
  python ml_security_cli.py --attack fgsm --defense gaussian --epsilon 0.2
  python ml_security_cli.py --report
"""

import argparse
import torch
import torch.nn as nn
import torchvision
import torchvision.transforms as transforms
import torch.nn.functional as F
import numpy as np
import os
import json
from datetime import datetime

# ── Model definition ────────────────────────────────────────────
class SimpleCNN(nn.Module):
    def __init__(self):
        super().__init__()
        self.conv1   = nn.Conv2d(1, 32, kernel_size=3, padding=1)
        self.conv2   = nn.Conv2d(32, 64, kernel_size=3, padding=1)
        self.pool    = nn.MaxPool2d(2, 2)
        self.relu    = nn.ReLU()
        self.fc1     = nn.Linear(64 * 7 * 7, 128)
        self.fc2     = nn.Linear(128, 10)
        self.dropout = nn.Dropout(0.25)

    def forward(self, x):
        x = self.pool(self.relu(self.conv1(x)))
        x = self.pool(self.relu(self.conv2(x)))
        x = x.view(-1, 64 * 7 * 7)
        x = self.relu(self.fc1(x))
        x = self.dropout(x)
        return self.fc2(x)

# ── Attack functions ─────────────────────────────────────────────
def fgsm_attack(model, images, labels, epsilon):
    images.requires_grad = True
    loss = nn.CrossEntropyLoss()(model(images), labels)
    model.zero_grad()
    loss.backward()
    return torch.clamp(
        images + epsilon * images.grad.data.sign(), -1, 1
    ).detach()

def pgd_attack(model, images, labels, epsilon=0.3, alpha=0.01, steps=40):
    adv = torch.clamp(
        images + torch.empty_like(images).uniform_(-epsilon, epsilon),
        -1, 1
    ).detach()
    for _ in range(steps):
        adv.requires_grad = True
        loss = nn.CrossEntropyLoss()(model(adv), labels)
        model.zero_grad()
        loss.backward()
        adv = torch.clamp(
            images + torch.clamp(
                adv + alpha * adv.grad.sign() - images,
                -epsilon, epsilon
            ), -1, 1
        ).detach()
    return adv

# ── Defense functions ────────────────────────────────────────────
def gaussian_smoothing(images):
    sigma, ks = 1.0, 3
    x = torch.arange(ks).float() - ks // 2
    gauss = torch.exp(-x**2 / (2 * sigma**2))
    gauss = gauss / gauss.sum()
    kernel = (gauss.unsqueeze(0) * gauss.unsqueeze(1)).view(1, 1, ks, ks)
    kernel = kernel.expand(images.shape[1], 1, ks, ks)
    return F.conv2d(images, kernel, padding=ks//2,
                    groups=images.shape[1]).detach()

def bit_depth_reduction(images, bits=4):
    imgs = (images + 1) / 2
    levels = 2 ** bits
    imgs = torch.round(imgs * levels) / levels
    return (imgs * 2 - 1).detach()

# ── Evaluation ───────────────────────────────────────────────────
def evaluate(model, loader, attack_fn=None, epsilon=0.3,
             preprocess_fn=None):
    model.eval()
    correct, total = 0, 0
    for images, labels in loader:
        if attack_fn:
            with torch.enable_grad():
                images = attack_fn(model, images, labels, epsilon)
        if preprocess_fn:
            images = preprocess_fn(images)
        with torch.no_grad():
            _, predicted = model(images).max(1)
        correct += predicted.eq(labels).sum().item()
        total   += labels.size(0)
    return 100. * correct / total

# ── Risk score ───────────────────────────────────────────────────
def compute_risk_score(clean_acc, attacked_acc):
    """
    Risk score 0–100:
      0  = no risk   (attack had no effect)
      100 = critical  (model completely broken)
    """
    drop = clean_acc - attacked_acc
    score = min(100, max(0, drop * 1.5))
    if score < 20:   level = "LOW"
    elif score < 50: level = "MEDIUM"
    elif score < 75: level = "HIGH"
    else:            level = "CRITICAL"
    return round(score, 1), level

def print_risk_bar(score):
    filled = int(score / 5)
    bar    = "█" * filled + "░" * (20 - filled)
    return f"[{bar}] {score}/100"

# ── Load model and data ──────────────────────────────────────────
def load_model_and_data(model_path, data_path, num_samples=500):
    model = SimpleCNN()
    if not os.path.exists(model_path):
        print(f"ERROR: Model not found at {model_path}")
        print("Please run notebook 01_baseline_models first.")
        exit(1)
    model.load_state_dict(
        torch.load(model_path, weights_only=True)
    )
    model.eval()

    transform = transforms.Compose([
        transforms.ToTensor(),
        transforms.Normalize((0.1307,), (0.3081,))
    ])
    dataset = torchvision.datasets.MNIST(
        root=data_path, train=False, download=False, transform=transform
    )
    # Use subset for speed
    subset = torch.utils.data.Subset(dataset, range(num_samples))
    loader = torch.utils.data.DataLoader(
        subset, batch_size=64, shuffle=False
    )
    return model, loader

# ── CLI commands ─────────────────────────────────────────────────
def cmd_attack(args, model, loader):
    print(f"\n{'='*55}")
    print(f"  ATTACK EVALUATION")
    print(f"  Model  : MNIST SimpleCNN baseline")
    print(f"  Epsilon: {args.epsilon}")
    print(f"{'='*55}")

    clean_acc = evaluate(model, loader)
    print(f"\n  Clean accuracy  : {clean_acc:.2f}%")

    results = {}
    attacks = ['fgsm', 'pgd'] if args.attack == 'all' else [args.attack]

    for atk in attacks:
        fn = fgsm_attack if atk == 'fgsm' else pgd_attack
        label = atk.upper()
        print(f"\n  Running {label} attack...", end="", flush=True)
        acc = evaluate(model, loader, fn, args.epsilon)
        score, level = compute_risk_score(clean_acc, acc)
        print(f"\r  {label} accuracy   : {acc:.2f}%")
        print(f"  Risk score      : {print_risk_bar(score)}")
        print(f"  Risk level      : {level}")
        results[atk] = {
            "accuracy": acc,
            "risk_score": score,
            "risk_level": level
        }

    return clean_acc, results

def cmd_defense(args, model, loader):
    print(f"\n{'='*55}")
    print(f"  DEFENSE EVALUATION")
    print(f"  Defense: {args.defense}")
    print(f"  Epsilon: {args.epsilon}")
    print(f"{'='*55}")

    preprocess_fn = None
    if args.defense == "gaussian":
        preprocess_fn = gaussian_smoothing
        defense_name = "Gaussian smoothing"
    elif args.defense == "bitdepth":
        preprocess_fn = bit_depth_reduction
        defense_name = "Bit-depth reduction"
    else:
        print(f"Unknown defense: {args.defense}")
        return

    clean_acc    = evaluate(model, loader)
    clean_def    = evaluate(model, loader, preprocess_fn=preprocess_fn)
    fgsm_no_def  = evaluate(model, loader, fgsm_attack, args.epsilon)
    fgsm_def     = evaluate(model, loader, fgsm_attack, args.epsilon,
                            preprocess_fn)
    pgd_no_def   = evaluate(model, loader, pgd_attack,  args.epsilon)
    pgd_def      = evaluate(model, loader, pgd_attack,  args.epsilon,
                            preprocess_fn)

    print(f"\n  Defense applied : {defense_name}")
    print(f"\n  {'Condition':<28} {'No defense':>12} {'With defense':>12}")
    print(f"  {'-'*54}")
    print(f"  {'Clean accuracy':<28} {clean_acc:>11.2f}% {clean_def:>11.2f}%")
    print(f"  {'Under FGSM':<28} {fgsm_no_def:>11.2f}% {fgsm_def:>11.2f}%")
    print(f"  {'Under PGD':<28} {pgd_no_def:>11.2f}% {pgd_def:>11.2f}%")

    fgsm_score, fgsm_level = compute_risk_score(clean_acc, fgsm_def)
    pgd_score,  pgd_level  = compute_risk_score(clean_acc, pgd_def)
    print(f"\n  FGSM risk after defense: {print_risk_bar(fgsm_score)} ({fgsm_level})")
    print(f"  PGD  risk after defense: {print_risk_bar(pgd_score)}  ({pgd_level})")

def cmd_report(args, model, loader):
    print(f"\n{'='*55}")
    print(f"  FULL SECURITY REPORT")
    print(f"  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*55}")

    clean_acc = evaluate(model, loader)
    print(f"\n  Baseline clean accuracy: {clean_acc:.2f}%\n")

    report = {
        "generated": datetime.now().isoformat(),
        "clean_accuracy": clean_acc,
        "attacks": {},
        "defenses": {}
    }

    # Test all attacks
    print(f"  {'Attack':<20} {'Accuracy':>10} {'Risk Score':>12} {'Level':>10}")
    print(f"  {'-'*55}")
    for name, fn, eps in [
        ("FGSM e=0.1", fgsm_attack, 0.1),
        ("FGSM e=0.3", fgsm_attack, 0.3),
        ("PGD  e=0.1", pgd_attack,  0.1),
        ("PGD  e=0.3", pgd_attack,  0.3),
    ]:
        acc = evaluate(model, loader, fn, eps)
        score, level = compute_risk_score(clean_acc, acc)
        print(f"  {name:<20} {acc:>9.2f}% {score:>11.1f}  {level:>10}")
        report["attacks"][name] = {
            "accuracy": acc, "risk_score": score, "risk_level": level
        }

    # Test defenses
    print(f"\n  {'Defense vs FGSM 0.3':<28} {'Accuracy':>10} {'Risk':>8}")
    print(f"  {'-'*48}")
    for def_name, def_fn in [
        ("Gaussian smoothing", gaussian_smoothing),
        ("Bit-depth reduction", bit_depth_reduction),
    ]:
        acc = evaluate(model, loader, fgsm_attack, 0.3, def_fn)
        score, level = compute_risk_score(clean_acc, acc)
        print(f"  {def_name:<28} {acc:>9.2f}% {score:>7.1f} ({level})")
        report["defenses"][def_name] = {
            "accuracy": acc, "risk_score": score, "risk_level": level
        }

    # Save JSON report
    report_path = "results/security_report.json"
    os.makedirs("results", exist_ok=True)
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)
    print(f"\n  Full report saved to: {report_path}")

    # Overall risk verdict
    pgd_score, _ = compute_risk_score(
        clean_acc, report["attacks"]["PGD  e=0.3"]["accuracy"]
    )
    print(f"\n{'='*55}")
    if pgd_score >= 75:
        print("  VERDICT: Model is CRITICALLY vulnerable without defenses.")
        print("  RECOMMENDATION: Deploy adversarial training immediately.")
    elif pgd_score >= 50:
        print("  VERDICT: Model is HIGHLY vulnerable without defenses.")
        print("  RECOMMENDATION: Apply adversarial training or smoothing.")
    else:
        print("  VERDICT: Model shows MODERATE vulnerability.")
        print("  RECOMMENDATION: Monitor and apply preprocessing defenses.")
    print(f"{'='*55}\n")

# ── Main entry point ─────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="ML Security CLI — Thesis tool by Zacharia Rehan Rajesh",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("--attack",  choices=["fgsm","pgd","all"],
                        help="Attack to run")
    parser.add_argument("--defense", choices=["gaussian","bitdepth",
                                               "adversarial_training"],
                        help="Defense to evaluate")
    parser.add_argument("--epsilon", type=float, default=0.3,
                        help="Attack strength (default: 0.3)")
    parser.add_argument("--report",  action="store_true",
                        help="Generate full security report")
    parser.add_argument("--samples", type=int, default=500,
                        help="Number of test samples (default: 500)")

    args = parser.parse_args()

    # Paths
    model_path = "models/mnist_cnn_baseline.pth"
    data_path  = "data"

    print("\n  ML Security CLI Tool")
    print("  Thesis: Securing Machine Learning Models")
    print("  Author: Zacharia Rehan Rajesh")

    model, loader = load_model_and_data(
        model_path, data_path, args.samples
    )
    print(f"  Model loaded. Testing on {args.samples} samples.\n")

    if args.report:
        cmd_report(args, model, loader)
    elif args.attack:
        cmd_attack(args, model, loader)
        if args.defense:
            cmd_defense(args, model, loader)
    elif args.defense:
        cmd_defense(args, model, loader)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
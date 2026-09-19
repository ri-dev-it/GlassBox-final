"""Print a small synthetic A/B routing run without requiring model assets.

Run from the repository root with: python backend/scripts/demo_ab_test.py
"""
import argparse
import random
from collections import Counter


def run(requests: int, treatment_percentage: float, seed: int) -> Counter:
    random_generator = random.Random(seed)
    assignments = Counter()
    for _ in range(requests):
        variant = "treatment" if random_generator.random() * 100 < treatment_percentage else "control"
        # Synthetic outcomes stand in for two independently served model versions.
        approved = random_generator.random() < (0.72 if variant == "treatment" else 0.64)
        assignments[(variant, "APPROVE" if approved else "DECLINE")] += 1
    return assignments


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Demonstrate synthetic A/B prediction routing.")
    parser.add_argument("--requests", type=int, default=1000)
    parser.add_argument("--treatment-percentage", type=float, default=50)
    parser.add_argument("--seed", type=int, default=42)
    arguments = parser.parse_args()
    if arguments.requests < 1 or not 0 <= arguments.treatment_percentage <= 100:
        parser.error("requests must be positive and treatment-percentage must be between 0 and 100")
    for key, count in sorted(run(arguments.requests, arguments.treatment_percentage, arguments.seed).items()):
        print(f"{key[0]:9} {key[1]:7} {count}")
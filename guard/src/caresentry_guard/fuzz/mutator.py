"""CareSentry Guard Linter Mutation Fuzzer & Robustness Tester."""

from __future__ import annotations

import random
from dataclasses import asdict, dataclass
from typing import Any, Callable, Dict, List, Tuple

from caresentry_guard.adapters.a_linter import LinterAdapter


@dataclass
class MutationFamilyResult:
    family_name: str
    total_mutations: int
    caught_count: int
    bypassed_count: int
    catch_rate: float


@dataclass
class FuzzReport:
    total_mutations: int
    overall_catch_rate: float
    families: List[MutationFamilyResult]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class LinterMutationFuzzer:
    """Adversarial mutation testing engine measuring invariant linter robustness."""

    def __init__(self, random_seed: int = 42):
        self.rng = random.Random(random_seed)
        self.linter = LinterAdapter()

    def mutate_misspelling(self, drug: str) -> str:
        """Introduce single-character deletion, transposition, or substitution."""
        if len(drug) <= 3:
            return drug
        idx = self.rng.randint(1, len(drug) - 2)
        op = self.rng.choice(["delete", "swap", "sub"])
        if op == "delete":
            return drug[:idx] + drug[idx + 1 :]
        elif op == "swap":
            return drug[:idx] + drug[idx + 1] + drug[idx] + drug[idx + 2 :]
        else:
            return drug[:idx] + "x" + drug[idx + 1 :]

    def mutate_spacing(self, drug: str) -> str:
        """Inject intra-token spaces or hyphens."""
        mid = len(drug) // 2
        sep = self.rng.choice(["-", " ", ".", "_"])
        return drug[:mid] + sep + drug[mid:]

    def mutate_case(self, drug: str) -> str:
        """Randomize uppercase and lowercase characters."""
        return "".join(c.upper() if self.rng.random() > 0.5 else c.lower() for c in drug)

    def mutate_brand(self, drug: str) -> str:
        """Map generic to alternative trade name."""
        brand_map = {
            "amoxicillin": "Augmentin",
            "ampicillin": "Unasyn",
            "metformin": "Glucophage XR",
            "spironolactone": "Aldactone",
            "bactrim": "Septra DS",
            "ibuprofen": "Advil Liqui-Gels",
        }
        return brand_map.get(drug.lower(), drug)

    def mutate_homoglyph(self, drug: str) -> str:
        """Substitute ASCII characters with Cyrillic or Greek homoglyphs."""
        replacements = {"a": "а", "e": "е", "o": "о", "p": "р", "c": "с"}
        chars = list(drug)
        for i, ch in enumerate(chars):
            if ch.lower() in replacements:
                chars[i] = replacements[ch.lower()]
                break
        return "".join(chars)

    def run_fuzz_evaluation(self, samples_per_family: int = 25) -> FuzzReport:
        """Run mutations across 5 families and record bypass rates."""
        base_drugs = ["amoxicillin", "ampicillin", "metformin", "spironolactone", "bactrim", "ibuprofen"]
        ehr = "Patient with documented allergy to Penicillin, sulfa, and eGFR of 20 mL/min."

        mutation_families: List[Tuple[str, Callable[[str], str]]] = [
            ("Misspellings / Typos", self.mutate_misspelling),
            ("Spacing & Punctuation", self.mutate_spacing),
            ("Case Variations", self.mutate_case),
            ("Brand Synonyms", self.mutate_brand),
            ("Unicode Homoglyphs", self.mutate_homoglyph),
        ]

        family_results: List[MutationFamilyResult] = []
        total_all = 0
        caught_all = 0

        for name, fn in mutation_families:
            caught = 0
            bypassed = 0
            for i in range(samples_per_family):
                drug = base_drugs[i % len(base_drugs)]
                mutated = fn(drug)
                summary = f"Discharge prescription: Take {mutated} 500mg PO daily."

                res = self.linter.audit(ehr, summary)
                if res.status == "FAIL":
                    caught += 1
                else:
                    bypassed += 1

            total = caught + bypassed
            total_all += total
            caught_all += caught
            rate = round(caught / total, 4) if total > 0 else 0.0

            family_results.append(
                MutationFamilyResult(
                    family_name=name,
                    total_mutations=total,
                    caught_count=caught,
                    bypassed_count=bypassed,
                    catch_rate=rate,
                )
            )

        overall = round(caught_all / total_all, 4) if total_all > 0 else 0.0
        return FuzzReport(
            total_mutations=total_all,
            overall_catch_rate=overall,
            families=family_results,
        )


if __name__ == "__main__":
    fuzzer = LinterMutationFuzzer()
    rep = fuzzer.run_fuzz_evaluation(samples_per_family=20)
    print("=" * 65)
    print(" CareSentry Guard Linter Mutation Robustness Fuzz Report")
    print("=" * 65)
    print(f" Total Mutations Tested : {rep.total_mutations}")
    print(f" Overall Catch Rate     : {rep.overall_catch_rate:.2%}")
    print("-" * 65)
    print(f" {'Mutation Family':<25} | {'Tested':<6} | {'Caught':<6} | {'Catch Rate':<10}")
    print("-" * 65)
    for f in rep.families:
        print(f" {f.family_name:<25} | {f.total_mutations:<6} | {f.caught_count:<6} | {f.catch_rate:<10.2%}")
    print("=" * 65)

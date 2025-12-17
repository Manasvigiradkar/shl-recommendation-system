"""
Evaluation Script - Calculate Recall@K, Precision@K, MAP
"""

import pandas as pd
import json
import requests
from typing import List, Dict
import numpy as np


class RecommendationEvaluator:
    def __init__(self, api_url: str = "http://localhost:8000"):
        self.api_url = api_url

    # ------------------ METRICS ------------------

    def recall_at_k(self, predicted: List[str], relevant: List[str], k: int = 10) -> float:
        if not relevant:
            return 0.0
        top_k = predicted[:k]
        return len(set(top_k) & set(relevant)) / len(relevant)

    def precision_at_k(self, predicted: List[str], relevant: List[str], k: int = 10) -> float:
        if not predicted:
            return 0.0
        top_k = predicted[:k]
        return len(set(top_k) & set(relevant)) / len(top_k)

    def mean_recall_at_k(self, results: List[Dict], k: int = 10) -> float:
        recalls = [
            self.recall_at_k(r["predicted"], r["relevant"], k)
            for r in results
        ]
        return float(np.mean(recalls)) if recalls else 0.0

    def mean_average_precision(self, results: List[Dict]) -> float:
        aps = []

        for r in results:
            relevant = set(r["relevant"])
            if not relevant:
                continue

            score = 0.0
            hits = 0

            for i, pred in enumerate(r["predicted"], start=1):
                if pred in relevant:
                    hits += 1
                    score += hits / i

            aps.append(score / len(relevant) if relevant else 0.0)

        return float(np.mean(aps)) if aps else 0.0

    # ------------------ EVALUATION ------------------

    def evaluate_from_csv(self, train_csv: str, k: int = 10) -> Dict:
        print(f"Loading training data from {train_csv}...")

        # ✅ Robust CSV loading
        try:
            df = pd.read_csv(train_csv, encoding="utf-8")
        except UnicodeDecodeError:
            df = pd.read_csv(train_csv, encoding="latin1")

        df.columns = df.columns.str.strip()

        # ✅ Handle column name mismatch
        query_col = "query" if "query" in df.columns else "csvquery"

        if "Assessment_url" not in df.columns:
            raise ValueError("CSV must contain 'Assessment_url' column")

        # Group relevant URLs per query
        query_groups = (
            df.groupby(query_col)["Assessment_url"]
            .apply(list)
            .to_dict()
        )

        print(f"Found {len(query_groups)} unique queries")

        results = []

        for idx, (query, relevant_urls) in enumerate(query_groups.items(), 1):
            print(f"\nEvaluating {idx}/{len(query_groups)} → {query[:60]}")

            predicted_urls = self._get_predictions(query)

            result = {
                "query": query,
                "relevant": relevant_urls,
                "predicted": predicted_urls,
                "num_relevant": len(relevant_urls),
                "num_predicted": len(predicted_urls),
            }
            results.append(result)

            r = self.recall_at_k(predicted_urls, relevant_urls, k)
            p = self.precision_at_k(predicted_urls, relevant_urls, k)

            print(f"  Recall@{k}: {r:.3f}")
            print(f"  Precision@{k}: {p:.3f}")

        # ------------------ SUMMARY ------------------

        metrics = {
            "mean_recall_at_k": self.mean_recall_at_k(results, k),
            "mean_precision_at_k": float(
                np.mean([
                    self.precision_at_k(r["predicted"], r["relevant"], k)
                    for r in results
                ])
            ),
            "mean_average_precision": self.mean_average_precision(results),
            "k": k,
            "num_queries": len(results),
        }

        self._print_summary(metrics)
        return metrics

    # ------------------ API CALL ------------------

    def _get_predictions(self, query: str) -> List[str]:
        try:
            response = requests.post(
                f"{self.api_url}/recommend",
                json={"query": query},
                timeout=60
            )
            response.raise_for_status()
            data = response.json()
            return [rec["url"] for rec in data.get("recommendations", [])]
        except Exception as e:
            print(f"  API error: {e}")
            return []

    # ------------------ OUTPUT ------------------

    def _print_summary(self, metrics: Dict):
        print("\n" + "=" * 60)
        print("EVALUATION SUMMARY")
        print("=" * 60)
        print(f"Queries evaluated : {metrics['num_queries']}")
        print(f"K value           : {metrics['k']}")
        print(f"Mean Recall@K     : {metrics['mean_recall_at_k']:.4f}")
        print(f"Mean Precision@K  : {metrics['mean_precision_at_k']:.4f}")
        print(f"Mean AP           : {metrics['mean_average_precision']:.4f}")
        print("=" * 60 + "\n")


# ------------------ MAIN ------------------

def main():
    import argparse

    parser = argparse.ArgumentParser("Evaluate SHL Recommendation System")
    parser.add_argument("--mode", choices=["evaluate"], required=True)
    parser.add_argument("--train-csv", required=True)
    parser.add_argument("--api-url", default="http://localhost:8000")
    parser.add_argument("--k", type=int, default=10)

    args = parser.parse_args()

    evaluator = RecommendationEvaluator(api_url=args.api_url)
    metrics = evaluator.evaluate_from_csv(args.train_csv, args.k)

    with open("evaluation_metrics.json", "w") as f:
        json.dump(metrics, f, indent=2)

    print("✅ Metrics saved to evaluation_metrics.json")


if __name__ == "__main__":
    main()

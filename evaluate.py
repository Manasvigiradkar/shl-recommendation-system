"""
SHL Recommendation System
Evaluation & Submission Script (FINAL)

✔ Constraint-based evaluation
✔ Prediction CSV generation
✔ Robust CSV encoding handling
✔ Automatic query column detection
✔ No ground-truth dependency
"""

import pandas as pd
import requests
import time
import numpy as np
from typing import List


# ================== UTILITY ==================

def read_csv_safe(path: str) -> pd.DataFrame:
    """Read CSV with encoding fallback."""
    try:
        return pd.read_csv(path, encoding="utf-8")
    except UnicodeDecodeError:
        try:
            return pd.read_csv(path, encoding="latin1")
        except UnicodeDecodeError:
            return pd.read_csv(path, encoding="ISO-8859-1")


def detect_query_column(df: pd.DataFrame) -> str:
    """
    Detect query column name automatically.
    Supports: query, csvquery, Query
    """
    normalized_cols = {c.lower().strip(): c for c in df.columns}

    for candidate in ["query", "csvquery", "question"]:
        if candidate in normalized_cols:
            return normalized_cols[candidate]

    raise ValueError(
        f"Query column not found. Available columns: {list(df.columns)}"
    )


# ================== EVALUATOR ==================

class RecommendationEvaluator:
    def __init__(self, api_url: str = "http://localhost:8000"):
        self.api_url = api_url

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
            print(f"API error for query: {query[:50]} → {e}")
            return []

    # ------------------ CONSTRAINT EVALUATION ------------------

    def evaluate_constraints(self, test_csv: str, k: int = 10):
        print(f"Loading test data from {test_csv}...")

        df = read_csv_safe(test_csv)
        df.columns = df.columns.str.strip()

        query_col = detect_query_column(df)

        total_queries = len(df)
        valid_queries = 0
        response_times = []

        print(f"Detected query column: '{query_col}'")
        print(f"Found {total_queries} queries\n")

        for idx, query in enumerate(df[query_col], 1):
            query = str(query)

            print(f"Evaluating {idx}/{total_queries} → {query[:60]}")

            start = time.time()
            predictions = self._get_predictions(query)
            latency = time.time() - start
            response_times.append(latency)

            predictions = predictions[:k]
            unique_predictions = set(predictions)

            is_valid = (
                5 <= len(predictions) <= 10
                and len(predictions) == len(unique_predictions)
            )

            if is_valid:
                valid_queries += 1

            print(f"  Recommendations : {len(predictions)}")
            print(f"  Unique URLs     : {len(unique_predictions)}")
            print(f"  Latency (sec)   : {latency:.2f}")

        # ------------------ SUMMARY ------------------

        print("\n" + "=" * 60)
        print("CONSTRAINT EVALUATION SUMMARY")
        print("=" * 60)
        print(f"Total Queries        : {total_queries}")
        print(f"Valid Responses      : {valid_queries}/{total_queries}")
        print(f"Success Rate         : {(valid_queries / total_queries) * 100:.2f}%")
        print(f"Average Latency (s)  : {np.mean(response_times):.2f}")
        print(f"Max Latency (s)      : {np.max(response_times):.2f}")
        print("=" * 60 + "\n")

    # ------------------ PREDICTION (PHASE 7) ------------------

    def generate_predictions(self, test_csv: str, output_csv: str, k: int = 10):
        print(f"Generating predictions from {test_csv}...")

        df = read_csv_safe(test_csv)
        df.columns = df.columns.str.strip()

        query_col = detect_query_column(df)

        rows = []

        for idx, query in enumerate(df[query_col], 1):
            query = str(query)

            print(f"Predicting {idx}/{len(df)} → {query[:60]}")

            predictions = self._get_predictions(query)[:k]

            for url in predictions:
                rows.append({
                    "query": query,
                    "Assessment_url": url
                })

        out_df = pd.DataFrame(rows)
        out_df.to_csv(output_csv, index=False)

        print(f"✅ Predictions saved to {output_csv}")


# ================== MAIN ==================

def main():
    import argparse

    parser = argparse.ArgumentParser("SHL Recommendation System")

    parser.add_argument(
        "--mode",
        choices=["evaluate", "predict"],
        required=True
    )

    parser.add_argument(
        "--test-csv",
        required=True,
        help="CSV file containing job queries"
    )

    parser.add_argument(
        "--output-csv",
        default="predictions.csv",
        help="Output CSV file for predictions"
    )

    parser.add_argument(
        "--api-url",
        default="http://localhost:8000"
    )

    parser.add_argument(
        "--k",
        type=int,
        default=10
    )

    args = parser.parse_args()

    evaluator = RecommendationEvaluator(api_url=args.api_url)

    if args.mode == "evaluate":
        evaluator.evaluate_constraints(
            test_csv=args.test_csv,
            k=args.k
        )

    elif args.mode == "predict":
        evaluator.generate_predictions(
            test_csv=args.test_csv,
            output_csv=args.output_csv,
            k=args.k
        )


if __name__ == "__main__":
    main()

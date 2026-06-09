import argparse
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path


def read_jsonl(path):
    rows = []
    with open(path, "r", encoding="utf-8") as file:
        for line in file:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def extract_model_name(path):
    name = Path(path).stem

    if "__" in name:
        return name.split("__")[-1]

    return name


def extract_score(review_row, score_key):
    try:
        return float(review_row["sample_score"]["score"]["value"][score_key])
    except Exception:
        return None


def load_review_scores(reviews_dir, score_key):
    """
    Reads all review jsonl files in a benchmark folder.

    Expected examples:
    live_code_bench_v5__gpt-oss-120b.jsonl
    aa_lcr__kimi-k2.5.jsonl
    """
    reviews_dir = Path(reviews_dir)
    files = sorted(reviews_dir.glob("*.jsonl"))

    if not files:
        raise FileNotFoundError(f"No .jsonl files found in {reviews_dir}")

    sample_scores = defaultdict(dict)
    model_scores = defaultdict(list)

    for file_path in files:
        model = extract_model_name(file_path)

        for row in read_jsonl(file_path):
            index = row.get("index")
            score = extract_score(row, score_key)

            if index is None or score is None:
                continue

            sample_scores[index][model] = score
            model_scores[model].append(score)

    return sample_scores, model_scores


def build_sample_features(sample_scores):
    """
    For each sample:
    - difficulty = average score across models
      Lower value means harder sample.
    - disagreement = score standard deviation across models
      Higher value means the sample separates models better.
    """
    features = []

    for index, scores_by_model in sample_scores.items():
        scores = list(scores_by_model.values())

        if not scores:
            continue

        difficulty = sum(scores) / len(scores)

        if len(scores) > 1:
            disagreement = statistics.pstdev(scores)
        else:
            disagreement = 0.0

        features.append(
            {
                "index": index,
                "difficulty": difficulty,
                "disagreement": disagreement,
                "model_count": len(scores),
                "scores": scores_by_model,
            }
        )

    return features


def difficulty_bucket(difficulty):
    if difficulty < 0.34:
        return "hard"
    if difficulty < 0.67:
        return "medium"
    return "easy"


def select_from_bucket(items, count):
    """
    Deterministic selection.
    Prefer high-disagreement samples because they separate models.
    Then spread by index to avoid taking only adjacent samples.
    """
    if count <= 0 or not items:
        return []

    ranked = sorted(
        items,
        key=lambda item: (
            -item["disagreement"],
            abs(item["difficulty"] - 0.5),
            item["index"],
        ),
    )

    return ranked[: min(count, len(ranked))]


def prune_samples(features, target_size):
    """
    Minimum defensible pruner:
    - keep hard, medium, and easy samples
    - oversample high-disagreement examples
    - deterministic, not random
    """
    if target_size >= len(features):
        return sorted(features, key=lambda item: item["index"])

    buckets = {
        "hard": [],
        "medium": [],
        "easy": [],
    }

    for item in features:
        buckets[difficulty_bucket(item["difficulty"])].append(item)

    # Reserve 20% for highest-disagreement samples globally.
    disagreement_budget = max(1, math.floor(target_size * 0.20))
    stratified_budget = target_size - disagreement_budget

    selected_by_index = {}

    # Stratified allocation across difficulty buckets.
    non_empty_buckets = [name for name, items in buckets.items() if items]
    per_bucket = max(1, stratified_budget // max(1, len(non_empty_buckets)))

    for bucket_name in non_empty_buckets:
        selected = select_from_bucket(buckets[bucket_name], per_bucket)
        for item in selected:
            selected_by_index[item["index"]] = item

    # Fill remaining slots with highest-disagreement samples.
    remaining = target_size - len(selected_by_index)

    global_ranked = sorted(
        features,
        key=lambda item: (-item["disagreement"], abs(item["difficulty"] - 0.5), item["index"]),
    )

    for item in global_ranked:
        if remaining <= 0:
            break

        if item["index"] not in selected_by_index:
            selected_by_index[item["index"]] = item
            remaining -= 1

    # If still short, fill deterministically by index.
    if len(selected_by_index) < target_size:
        for item in sorted(features, key=lambda item: item["index"]):
            if len(selected_by_index) >= target_size:
                break
            selected_by_index[item["index"]] = item

    return sorted(selected_by_index.values(), key=lambda item: item["index"])


def average_score(scores):
    if not scores:
        return None
    return sum(scores) / len(scores)


def compare_full_vs_pruned(sample_scores, selected_indexes):
    selected_indexes = set(selected_indexes)

    full_by_model = defaultdict(list)
    pruned_by_model = defaultdict(list)

    for index, scores_by_model in sample_scores.items():
        for model, score in scores_by_model.items():
            full_by_model[model].append(score)

            if index in selected_indexes:
                pruned_by_model[model].append(score)

    comparison = []

    for model in sorted(full_by_model):
        full_score = average_score(full_by_model[model])
        pruned_score = average_score(pruned_by_model[model])
        delta = None

        if full_score is not None and pruned_score is not None:
            delta = pruned_score - full_score

        comparison.append(
            {
                "model": model,
                "full_score": full_score,
                "pruned_score": pruned_score,
                "delta": delta,
                "full_count": len(full_by_model[model]),
                "pruned_count": len(pruned_by_model[model]),
            }
        )

    return comparison


def write_output(path, benchmark_name, score_key, selected, comparison):
    output = {
        "benchmark": benchmark_name,
        "score_key": score_key,
        "selected_count": len(selected),
        "selected_indexes": [item["index"] for item in selected],
        "selected_samples": [
            {
                "index": item["index"],
                "difficulty": item["difficulty"],
                "disagreement": item["disagreement"],
                "bucket": difficulty_bucket(item["difficulty"]),
            }
            for item in selected
        ],
        "score_comparison": comparison,
    }

    with open(path, "w", encoding="utf-8") as file:
        json.dump(output, file, indent=2)

    return output


def print_summary(output, total_count):
    print()
    print(f"Benchmark: {output['benchmark']}")
    print(f"Score key: {output['score_key']}")
    print(f"Full samples: {total_count}")
    print(f"Selected samples: {output['selected_count']}")
    print()
    print("Model score comparison:")
    print("-" * 72)

    for row in output["score_comparison"]:
        full_score = row["full_score"]
        pruned_score = row["pruned_score"]
        delta = row["delta"]

        print(
            f"{row['model']:<24} "
            f"full={full_score:.4f} "
            f"pruned={pruned_score:.4f} "
            f"delta={delta:+.4f} "
            f"n={row['pruned_count']}"
        )

    print("-" * 72)
    print(f"Selected indexes written to output file.")


def main():
    parser = argparse.ArgumentParser(
        description="Prune benchmark samples using difficulty and disagreement stratification."
    )

    parser.add_argument("--reviews-dir", required=True, help="Directory containing review jsonl files.")
    parser.add_argument("--benchmark-name", required=True, help="Name to store in the output report.")
    parser.add_argument("--score-key", required=True, help="Score key, for example pass or acc.")
    parser.add_argument("--target-size", type=int, required=True, help="Number of samples to keep.")
    parser.add_argument("--output", required=True, help="Output JSON file path.")

    args = parser.parse_args()

    sample_scores, _ = load_review_scores(args.reviews_dir, args.score_key)
    features = build_sample_features(sample_scores)

    selected = prune_samples(features, args.target_size)
    selected_indexes = [item["index"] for item in selected]

    comparison = compare_full_vs_pruned(sample_scores, selected_indexes)

    output = write_output(
        args.output,
        args.benchmark_name,
        args.score_key,
        selected,
        comparison,
    )

    print_summary(output, total_count=len(features))


if __name__ == "__main__":
    main()
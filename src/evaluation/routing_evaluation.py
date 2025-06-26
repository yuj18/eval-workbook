def ordered_match(
    output: list[str],
    reference_output: list[str],
) -> int:
    """
    Check if the output is a strict ordered match of the reference output.
    Returns 1 if match, 0 otherwise.
    """
    return int(output == reference_output)


def unordered_match(
    output: list[str],
    reference_output: list[str],
) -> int:
    """
    Check if the output is an unordered match of the reference output.
    Returns 1 if match, 0 otherwise.
    """
    return int(sorted(output) == sorted(reference_output))


def superset_match(
    output: list[str],
    reference_output: list[str],
) -> int:
    """
    Check if the output is a superset of the reference output. Each element in output
    can only be matched once to an element in reference_output.
    Returns 1 if match, 0 otherwise.
    """
    matched_output_indices = set()
    for ref_item in reference_output:
        found_match = False
        for idx, out_item in enumerate(output):
            if idx in matched_output_indices:
                continue
            if out_item == ref_item:
                matched_output_indices.add(idx)
                found_match = True
                break
        if not found_match:
            return 0
    return 1


def subset_match(
    output: list[str],
    reference_output: list[str],
) -> int:
    """
    Check if the output is a subset of the reference output. Each element in output
    can only be matched once to an element in reference_output.
    Returns 1 if match, 0 otherwise.
    """
    return superset_match(reference_output, output)


def precision(
    output: list[str],
    reference_output: list[str],
) -> float:
    """
    Calculate the precision of the output against the reference output.
    Each element in reference_output can only be matched once.
    """
    if not output:
        return 0.0
    matched_ref_indices = set()
    matches = 0
    for out_item in output:
        for idx, ref_item in enumerate(reference_output):
            if idx in matched_ref_indices:
                continue
            if out_item == ref_item:
                matched_ref_indices.add(idx)
                matches += 1
                break
    return round(matches / len(output), 2)


def recall(
    output: list[str],
    reference_output: list[str],
) -> float:
    """
    Calculate the recall of the output against the reference output.
    Each element in output can only be matched once.
    """
    if not reference_output:
        return 0.0
    matched_out_indices = set()
    matches = 0
    for ref_item in reference_output:
        for idx, out_item in enumerate(output):
            if idx in matched_out_indices:
                continue
            if out_item == ref_item:
                matched_out_indices.add(idx)
                matches += 1
                break
    return round(matches / len(reference_output), 2)


def evaluate_routing(
    output: list[str],
    reference_output: list[str],
) -> dict:
    """
    Evaluate the routing of the output against the reference output.

    Args:
        output (list[str]): The actual output sequence.
        reference_output (list[str]): The reference output sequence to match against.

    Returns:
        dict: A dictionary containing evaluation metrics.
    """
    return {
        "ordered_match": ordered_match(output, reference_output),
        "unordered_match": unordered_match(output, reference_output),
        "superset_match": superset_match(output, reference_output),
        "subset_match": subset_match(output, reference_output),
        "precision": precision(output, reference_output),
        "recall": recall(output, reference_output),
    }


if __name__ == "__main__":

    # Read eval data in the JSON format (list of dictionaries)
    import json

    eval_data = []
    eval_file = "eval_data.json"
    with open(eval_file, "r") as file:
        eval_data = json.load(file)

    # Initialize aggregates
    ordered_total = 0
    unordered_total = 0
    superset_total = 0
    subset_total = 0
    precision_total = 0.0
    recall_total = 0.0
    n = len(eval_data)

    for data in eval_data:
        output = data["output"]
        reference_output = data["reference_output"]
        results = evaluate_routing(output, reference_output)
        ordered_total += results["ordered_match"]
        unordered_total += results["unordered_match"]
        superset_total += results["superset_match"]
        subset_total += results["subset_match"]
        precision_total += results["precision"]
        recall_total += results["recall"]
        print(f"Query: {data.get('query', 'N/A')}")
        print(f"Output: {output}")
        print(f"Reference Output: {reference_output}")
        print("Evaluation Results:")
        for metric, score in results.items():
            print(f"  {metric}: {score}")
        print()
        print("-" * 40)

    # Calculate per-label precision and recall
    from collections import defaultdict

    label_stats = defaultdict(lambda: {"tp": 0, "fp": 0, "fn": 0})
    all_labels = set()
    for data in eval_data:
        output = data["output"]
        reference_output = data["reference_output"]
        output_set = set(output)
        reference_set = set(reference_output)
        all_labels.update(output_set)
        all_labels.update(reference_set)
        for label in output_set:
            if label in reference_set:
                label_stats[label]["tp"] += 1
            else:
                label_stats[label]["fp"] += 1
        for label in reference_set:
            if label not in output_set:
                label_stats[label]["fn"] += 1

    if n > 0:
        print("Aggregate Results:")
        print(f"  Total queries evaluated: {n}")
        print(f"  ordered_match rate: {ordered_total / n * 100:.1f}%")
        print(f"  unordered_match rate: {unordered_total / n * 100:.1f}%")
        print(f"  superset_match rate: {superset_total / n * 100:.1f}%")
        print(f"  subset_match rate: {subset_total / n * 100:.1f}%")
        print(f"  mean precision: {precision_total / n:.2f}")
        print(f"  mean recall: {recall_total / n:.2f}")
        print("\nPer-label precision and recall:")
        for label in sorted(all_labels):
            tp = label_stats[label]["tp"]
            fp = label_stats[label]["fp"]
            fn = label_stats[label]["fn"]
            label_precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
            label_recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
            print(
                f"  {label}: precision={label_precision:.2f}, "
                f"recall={label_recall:.2f}"
            )

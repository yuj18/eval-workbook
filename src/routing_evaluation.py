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

    eval_data = [
        # ordered match
        {
            "output": ["banking_agent"],
            "reference_output": ["banking_agent"],
        },
        # unordered match
        {
            "output": ["banking_agent", "credit_card_agent"],
            "reference_output": ["credit_card_agent", "banking_agent"],
        },
        # high precision, low recall
        {
            "output": ["banking_agent"],
            "reference_output": ["banking_agent", "credit_card_agent"],
        },
        # low precision, high recall
        {
            "output": ["banking_agent", "credit_card_agent", "insurance_agent"],
            "reference_output": ["insurance_agent", "banking_agent"],
        },
        # repeat elements in reference output
        {
            "output": ["banking_agent", "credit_card_agent"],
            "reference_output": ["banking_agent", "credit_card_agent", "banking_agent"],
        },
        # repeat elements in output
        {
            "output": ["banking_agent", "credit_card_agent", "banking_agent"],
            "reference_output": ["banking_agent", "credit_card_agent"],
        },
    ]

    for data in eval_data:
        output = data["output"]
        reference_output = data["reference_output"]
        results = evaluate_routing(output, reference_output)
        print(f"Output: {output}")
        print(f"Reference Output: {reference_output}")
        print("Evaluation Results:")
        for metric, score in results.items():
            print(f"  {metric}: {score}")
        print()
        print("-" * 40)

import logging
from typing import List, Set, TypedDict

logger = logging.getLogger(__name__)

EVALUATOR_NAME = "RoutingAccuracyEvaluator"
EVALUATOR_DESCRIPTION = (
    "Evaluate the routing accuracy of a given route against a reference route."
)


class RoutingAccuracyResult(TypedDict):
    ordered_match: int
    unordered_match: int
    superset_match: int
    subset_match: int
    precision: float
    recall: float
    unordered_match_dedup: int
    superset_match_dedup: int
    subset_match_dedup: int
    precision_dedup: float
    recall_dedup: float
    step_stats: dict
    route_evaluated: List[str]
    reference_route_evaluated: List[str]


class RoutingAccuracyEvaluator:
    """
    A class to evaluate the routing accuracy of a given route against a reference route.
    This class provides methods to evaluate various metrics such as ordered match,
    unordered match, superset match, subset match, precision, recall, and step stats.
    """

    def __init__(self, step_types_to_evaluate: list = ["agent"]):
        """
        Initialize the evaluator with optional step types to evaluate.
        If step_types_to_evaluate is provided, only those steps will be evaluated.
        """
        self._step_types_to_evaluate = step_types_to_evaluate

    def _ordered_match(self, route: List[str], reference_route: List[str]) -> int:
        """
        Check if the route is a strict ordered match of the reference route.
        Returns 1 if match, 0 otherwise.
        """
        return int(route == reference_route)

    def _unordered_match(self, route: List[str], reference_route: List[str]) -> int:
        """
        Check if the route is an unordered match of the reference route.
        Returns 1 if match, 0 otherwise.
        """
        return int(sorted(route) == sorted(reference_route))

    def _unordered_match_dedup(
        self, route: List[str], reference_route: List[str]
    ) -> int:
        """
        Check if the deduplicated route is an unordered match of the
        deduplicated reference route. Returns 1 if match, 0 otherwise.
        Deduplication is done using set().
        """
        return int(set(route) == set(reference_route))

    def _superset_match(self, route: List[str], reference_route: List[str]) -> int:
        """
        Check if the route is a superset of the reference route. Each element in
        route can only be matched once to an element in reference_route.
        Returns 1 if match, 0 otherwise.
        """
        matched_route_indices: Set[int] = set()
        for ref_item in reference_route:
            found_match = False
            for idx, out_item in enumerate(route):
                if idx in matched_route_indices:
                    continue
                if out_item == ref_item:
                    matched_route_indices.add(idx)
                    found_match = True
                    break
            if not found_match:
                return 0
        return 1

    def _superset_match_dedup(
        self, route: List[str], reference_route: List[str]
    ) -> int:
        """
        Check if the deduplicated route is a superset of the deduplicated
        reference route. Returns 1 if match, 0 otherwise.
        """
        route_set = set(route)
        reference_set = set(reference_route)
        return int(reference_set.issubset(route_set))

    def _subset_match(self, route: List[str], reference_route: List[str]) -> int:
        """
        Check if the route is a subset of the reference route. Each element in route
        can only be matched once to an element in reference_route.
        Returns 1 if match, 0 otherwise.
        """
        return self._superset_match(reference_route, route)

    def _subset_match_dedup(self, route: List[str], reference_route: List[str]) -> int:
        """
        Check if the deduplicated route is a subset of the deduplicated
        reference route. Returns 1 if match, 0 otherwise.
        """
        route_set = set(route)
        reference_set = set(reference_route)
        return int(route_set.issubset(reference_set))

    def _precision(self, route: List[str], reference_route: List[str]) -> float:
        """
        Calculate the precision of the route against the reference route.
        Each element in reference_route can only be matched once.
        """
        if not route:
            return 0.0
        matched_ref_indices: Set[int] = set()
        matches = 0
        for out_item in route:
            for idx, ref_item in enumerate(reference_route):
                if idx in matched_ref_indices:
                    continue
                if out_item == ref_item:
                    matched_ref_indices.add(idx)
                    matches += 1
                    break
        return round(matches / len(route), 2)

    def _precision_dedup(self, route: List[str], reference_route: List[str]) -> float:
        """
        Calculate the precision of the deduplicated route against the
        deduplicated reference route. Precision = |intersection| / |route_set|.
        Returns 1.0 if both sets are empty, 0.0 if only route_set is empty.
        """
        route_set = set(route)
        reference_set = set(reference_route)
        if not route_set:
            if not reference_set:
                return 1.0
            return 0.0
        matches = len(route_set & reference_set)
        return round(matches / len(route_set), 2)

    def _recall(self, route: List[str], reference_route: List[str]) -> float:
        """
        Calculate the recall of the route against the reference route.
        Each element in route can only be matched once.
        If both route and reference_route are empty, recall is 1.0.
        """
        if not reference_route:
            if not route:
                return 1.0
            return 0.0
        matched_out_indices: Set[int] = set()
        matches = 0
        for ref_item in reference_route:
            for idx, out_item in enumerate(route):
                if idx in matched_out_indices:
                    continue
                if out_item == ref_item:
                    matched_out_indices.add(idx)
                    matches += 1
                    break
        return round(matches / len(reference_route), 2)

    def _recall_dedup(self, route: List[str], reference_route: List[str]) -> float:
        """
        Calculate the recall of the deduplicated route against the
        deduplicated reference route. Recall = |intersection| / |reference_set|.
        Returns 1.0 if both sets are empty, 0.0 if only reference_set is empty.
        """
        route_set = set(route)
        reference_set = set(reference_route)
        if not reference_set:
            if not route_set:
                return 1.0
            return 0.0
        matches = len(route_set & reference_set)
        return round(matches / len(reference_set), 2)

    def _step_stats(self, route: List[str], reference_route: List[str]) -> dict:
        """
        Calculate true positives (tp), false positives (fp), and false negatives (fn)
        for each step. Returns a dict: {step: {"tp": int, "fp": int, "fn": int}}
        """
        stats = {}
        route_set = set(route)
        reference_set = set(reference_route)
        all_steps = route_set | reference_set
        for step in all_steps:
            if step in route_set and step in reference_set:
                stats[step] = {"tp": 1, "fp": 0, "fn": 0}
            elif step in route_set and step not in reference_set:
                stats[step] = {"tp": 0, "fp": 1, "fn": 0}
            elif step in reference_set and step not in route_set:
                stats[step] = {"tp": 0, "fp": 0, "fn": 1}
        return stats

    def _evaluate(
        self,
        route: List[str],
        reference_route: List[str],
    ) -> RoutingAccuracyResult:
        """
        Evaluate the chosen route against the reference route.
        Returns a dictionary of all metrics.
        """
        return {
            "ordered_match": self._ordered_match(route, reference_route),
            "unordered_match": self._unordered_match(route, reference_route),
            "superset_match": self._superset_match(route, reference_route),
            "subset_match": self._subset_match(route, reference_route),
            "precision": self._precision(route, reference_route),
            "recall": self._recall(route, reference_route),
            "unordered_match_dedup": self._unordered_match_dedup(
                route, reference_route
            ),
            "superset_match_dedup": self._superset_match_dedup(route, reference_route),
            "subset_match_dedup": self._subset_match_dedup(route, reference_route),
            "precision_dedup": self._precision_dedup(route, reference_route),
            "recall_dedup": self._recall_dedup(route, reference_route),
            "step_stats": self._step_stats(route, reference_route),
            "route_evaluated": route,
            "reference_route_evaluated": reference_route,
        }

    def __call__(self, *, route: list, reference_route: list):
        """
        Evaluate the routing accuracy of the given route against the reference route.
        Args:
            route (List[dict]): The route to evaluate.
            reference_route (List[dict]): The expected route to match against.
        Returns:
            RoutingAccuracyResult: A dictionary containing evaluation metrics.
        """

        route_to_evaluate = [
            step["name"]
            for step in route
            if step["type"] in self._step_types_to_evaluate
        ]
        reference_route_to_evaluate = [
            step["name"]
            for step in reference_route
            if step["type"] in self._step_types_to_evaluate
        ]

        result = self._evaluate(
            route=route_to_evaluate,
            reference_route=reference_route_to_evaluate,
        )
        return result

    def __aggregate__(self, results: List):
        """
        Aggregate precision, recall, and support for each agent from a list of
        result dicts. Each dict should have the key
        'outputs.RoutingAccuracyEvaluator.step_stats'.
        Returns a flat dict: {agent}_precision, {agent}_recall, {agent}_tp, etc.
        Support is defined as tp + fn (number of reference positives).
        """
        agent_stats = {}
        for idx, record in enumerate(results):
            step_stats = record["step_stats"]
            for agent, stats in step_stats.items():
                if agent not in agent_stats:
                    agent_stats[agent] = {"tp": 0, "fp": 0, "fn": 0}
                agent_stats[agent]["tp"] += stats.get("tp", 0)
                agent_stats[agent]["fp"] += stats.get("fp", 0)
                agent_stats[agent]["fn"] += stats.get("fn", 0)
        agent_matrics = {}
        for agent, stats in agent_stats.items():
            tp = stats["tp"]
            fp = stats["fp"]
            fn = stats["fn"]
            support = tp + fn
            if (tp + fp) > 0:
                precision = tp / (tp + fp)
            elif (tp + fp + fn) == 0:
                precision = 1.0
            else:
                precision = 0.0
            if (tp + fn) > 0:
                recall = tp / (tp + fn)
            elif (tp + fp + fn) == 0:
                recall = 1.0
            else:
                recall = 0.0
            agent_matrics[f"{agent}_precision"] = round(precision, 2)
            agent_matrics[f"{agent}_recall"] = round(recall, 2)
            agent_matrics[f"{agent}_tp"] = tp
            agent_matrics[f"{agent}_fp"] = fp
            agent_matrics[f"{agent}_fn"] = fn
            agent_matrics[f"{agent}_support"] = support
            logger.info(
                f"Agent stats: name={agent}, "
                f"precision={precision}, recall={recall}, "
                f"tp={tp}, fp={fp}, fn={fn}, support={support}"
            )

        return agent_matrics


# Usage example:

if __name__ == "__main__":
    import json

    evaluator = RoutingAccuracyEvaluator()
    route = [
        {"name": "A", "type": "agent"},
        {"name": "B", "type": "agent"},
        {"name": "E", "type": "topic"},
        {"name": "A", "type": "agent"},
    ]
    reference_route = [
        {"name": "A", "type": "agent"},
        {"name": "B", "type": "agent"},
        {"name": "C", "type": "agent"},
        {"name": "D", "type": "agent"},
    ]
    evaluation_result = evaluator(route=route, reference_route=reference_route)
    print(json.dumps(evaluation_result, indent=4))

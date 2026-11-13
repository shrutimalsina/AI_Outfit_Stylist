"""Metrics for a single relevant hidden item per case."""

from statistics import mean


def summarize(ranks):
    if not ranks:
        return {"recall_at_1": None, "recall_at_3": None, "mrr_at_3": None}
    return {
        "recall_at_1": mean(rank == 1 for rank in ranks),
        "recall_at_3": mean(rank is not None for rank in ranks),
        "mrr_at_3": mean(1 / rank if rank else 0 for rank in ranks),
    }


def hidden_rank(matches, hidden_id):
    return next((match.position for match in matches if match.item_id == hidden_id), None)

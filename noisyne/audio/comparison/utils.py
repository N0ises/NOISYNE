from __future__ import annotations


def percentage_difference(

    reference: float,

    current: float,

) -> float:

    if abs(reference) < 1e-9:

        return 0.0

    return abs(

        (current - reference)

        / reference

    ) * 100.0
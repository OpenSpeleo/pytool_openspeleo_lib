"""Independent exact horizontal least-squares ground truth.

Mirrors buildGraph/solveRustGraph in cave-closure's ariane_solver.java:
STARTs are fixed, CLOSUREs substitute stations, and measured vectors form a
weighted graph Laplacian. These fixtures deliberately use five-metre edges,
so Java's min(10, 1 / magnitude) is exactly 1/5 for every observation.
OpenSpeleo's uniform Cartesian model matches it with sigma_m=sqrt(5).
No production parser, geometry helper, or solver generates expected values.

Regenerate the public synthetic fixture from the package root with:
uv run python -m tests.loop_closure_reference /path/to/ground_truth.json
"""

import json
import sys
from fractions import Fraction
from pathlib import Path

CASES = {
    "open_branch": {
        "edges": [[1, 2, 3, 4], [2, 3, -4, 3], [2, 4, 0, -5]],
        "closures": [],
    },
    "misclosed_ring": {
        "edges": [[1, 2, 5, 0], [2, 3, 0, 5], [3, 4, -3, -4]],
        "closures": [[4, 1]],
    },
    "coupled_loops_and_branch": {
        "edges": [
            [1, 2, 5, 0],
            [2, 3, 0, 5],
            [3, 4, -3, -4],
            [2, 5, 3, 4],
            [5, 6, -5, 0],
            [5, 7, 4, -3],
        ],
        "closures": [[4, 1], [6, 3]],
    },
}


def reference(case):
    """Solve the substituted normal equations using exact rational elimination."""
    stations = sorted({i for a, b, _, _ in case["edges"] for i in (a, b)})
    aliases = {i: i for i in stations}

    def root(i):
        while aliases[i] != i:
            i = aliases[i]
        return i

    for a, b in case["closures"]:
        aliases[root(a)] = root(b)
    fixed = root(1)
    free = sorted({root(i) for i in stations} - {fixed})
    matrix = [[Fraction(0) for _ in free] for _ in free]
    rhs = [[Fraction(0), Fraction(0)] for _ in free]
    weight = Fraction(1, 5)
    for a, b, dx, dy in case["edges"]:
        row = [Fraction((root(b) == i) - (root(a) == i)) for i in free]
        for j in range(len(free)):
            for k in range(len(free)):
                matrix[j][k] += weight * row[j] * row[k]
            for axis, delta in enumerate((dx, dy)):
                rhs[j][axis] += weight * row[j] * delta
    augmented = [a + b for a, b in zip(matrix, rhs, strict=True)]
    for j in range(len(free)):
        pivot = augmented[j][j]
        assert pivot > 0
        augmented[j] = [v / pivot for v in augmented[j]]
        for k in range(len(free)):
            if k != j:
                scale = augmented[k][j]
                augmented[k] = [
                    a - scale * b
                    for a, b in zip(augmented[k], augmented[j], strict=True)
                ]
    points = {fixed: [Fraction(0), Fraction(0)]}
    points.update({i: augmented[j][-2:] for j, i in enumerate(free)})
    objective = sum(
        weight * (points[root(b)][axis] - points[root(a)][axis] - delta) ** 2
        for a, b, dx, dy in case["edges"]
        for axis, delta in enumerate((dx, dy))
    )
    return {
        **case,
        "coordinates": {str(i): [float(v) for v in points[root(i)]] for i in stations},
        "objective": float(objective),
    }


def generate():
    return (
        json.dumps(
            {name: reference(case) for name, case in CASES.items()},
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )


if __name__ == "__main__":
    Path(sys.argv[1]).write_text(generate())

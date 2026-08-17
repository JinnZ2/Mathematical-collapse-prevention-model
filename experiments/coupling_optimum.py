"""
Experiment: is 1/phi^2 an approximation of the coupling optimum, or a
different quantity wearing its name?

`audit_bridge.phi_coupling_optimum` supplies a coupling target C* with
off-diagonal 1/phi^2, labelled a placeholder in its own docstring.
`coupling_physics` derives the optimum from the Master Stability Function
with no free parameter. Both claim to answer "where does f(C) peak?"

This runs both on the same networks and reports the disagreement. It is a
measurement of the framework by the framework, and it is not kind to the
placeholder.

THE BRIDGE BETWEEN THE TWO REPRESENTATIONS
------------------------------------------
`audit_bridge.coupling_matrix(n, c)` is diagonal 1/phi, off-diagonal c.
As a network that is the complete graph K_n with uniform edge weight c,
so the coupling strength sigma is exactly c. K_n has Laplacian
eigenvalues 0 and n (multiplicity n-1), giving lambda_2 = lambda_N = n.
That makes the two forms directly comparable rather than merely
analogous.

Run from the repository root:

    python -m experiments.coupling_optimum

Findings are recorded in docs/FALSIFICATION_LOG.md (F-2, F-9, F-10).
Every number printed here is reproducible from this file; the random
graphs use a fixed seed.
"""

import numpy as np

from src.core.coherence_metric import PHI, CoherenceMetric
from src.measurement.audit_bridge import coupling_matrix, phi_coupling_optimum
from src.measurement.coupling_physics import (
    MSFWindow,
    coupling_coherence,
    optimal_coupling,
    spectrum,
    synchronizable,
)

PHI_OPT = 1.0 / PHI**2  # 0.381966..., the placeholder's off-diagonal target

# An illustrative Class III window. Every conclusion below that depends on
# the window says so; the topology-blindness result does not depend on it.
WINDOW = MSFWindow(
    nu_lower=0.2,
    nu_upper=4.0,
    source="illustrative; measure the MSF for your own node dynamics",
    system="Class III node dynamics",
)

SCALES = np.geomspace(1e-3, 1e2, 4000)
RULE = "=" * 84


# --------------------------------------------------------------------------
# Test networks
# --------------------------------------------------------------------------


def complete(n):
    return np.ones((n, n)) - np.eye(n)


def ring(n):
    A = np.zeros((n, n))
    for i in range(n):
        A[i, (i + 1) % n] = A[(i + 1) % n, i] = 1.0
    return A


def path(n):
    A = np.zeros((n, n))
    for i in range(n - 1):
        A[i, i + 1] = A[i + 1, i] = 1.0
    return A


def star(n):
    A = np.zeros((n, n))
    A[0, 1:] = A[1:, 0] = 1.0
    return A


def barbell(bridged=True):
    """Two triangles joined by a single edge. Cutting it splits the network."""
    A = np.zeros((6, 6))
    edges = [(0, 1), (1, 2), (0, 2), (3, 4), (4, 5), (3, 5)]
    if bridged:
        edges.append((2, 3))
    for i, j in edges:
        A[i, j] = A[j, i] = 1.0
    return A


# --------------------------------------------------------------------------
# The two measures, each given its own best coupling scale on the same graph
# --------------------------------------------------------------------------


def frobenius_peak(A):
    """Peak of the Gaussian f(C) over global coupling scale s.

    Returns (argmax s, peak f). The argmax is analytically exactly
    1/phi^2 for any unweighted graph: absent edges contribute a constant
    (1/phi^2)^2 to the squared deviation regardless of s, so only the
    present edges' (s - 1/phi^2)^2 terms move. The sweep confirms the
    algebra rather than discovering it.
    """
    n = A.shape[0]
    metric = CoherenceMetric(coupling_optimum=phi_coupling_optimum(n))
    best_f, best_s = -1.0, None
    for s in SCALES:
        C = s * A
        np.fill_diagonal(C, 1.0 / PHI)
        f = metric.coupling_function(C)
        if f > best_f:
            best_f, best_s = f, float(s)
    return best_s, best_f


def physics_peak(A):
    """Peak of the MSF-derived f(C) over global coupling scale s."""
    spec = spectrum(A)
    if not synchronizable(spec, WINDOW):
        return None, 0.0
    s = optimal_coupling(spec, WINDOW)
    return s, coupling_coherence(s, A, WINDOW).coherence


# --------------------------------------------------------------------------
# Sections
# --------------------------------------------------------------------------


def section_default_has_no_interior_optimum():
    print(RULE)
    print("1. Does the DEFAULT C* = I/phi have an interior optimum?")
    print(RULE)
    print("   The framework's stated design is 'too weak = fragmented, too")
    print("   strong = rigid'. That requires a peak at intermediate coupling.")
    print()
    for n in (2, 3, 5):
        metric = CoherenceMetric()  # default C* = I/phi
        cs = np.linspace(0.0, 1.5, 1501)
        fs = np.array([metric.coupling_function(coupling_matrix(n, float(c)))
                       for c in cs])
        i = int(np.argmax(fs))
        monotone = bool(np.all(np.diff(fs) <= 1e-15))
        print(f"   n={n}: argmax at c={cs[i]:.4f}, f={fs[i]:.4f}, "
              f"monotone decreasing: {monotone}")
    print()
    print("   The peak is at ZERO coupling. C* = I/phi has an off-diagonal")
    print("   target of zero, so any coupling at all only moves C away from")
    print("   C*. There is no interior optimum, and 'too weak = fragmented'")
    print("   is not merely mis-located — it is inexpressible.")


def section_scale_with_n():
    print()
    print(RULE)
    print("2. Physics optimum vs the placeholder, on K_n")
    print(RULE)
    print(f"   window nu = ({WINDOW.nu_lower}, {WINDOW.nu_upper}), "
          f"width ratio {WINDOW.width_ratio:.1f}")
    print(f"   sigma* = sqrt(nu1*nu2 / (lambda_2*lambda_N)) "
          f"= sqrt(nu1*nu2)/n for K_n")
    print()
    print(f"   {'n':>4} {'sigma* physics':>15} {'1/phi^2':>9} {'ratio':>7} "
          f"{'stable window':>22} {'regime at 1/phi^2':>20}")
    for n in (2, 3, 5, 10, 11, 20, 50):
        A = complete(n)
        spec = spectrum(A)
        s_opt = optimal_coupling(spec, WINDOW)
        r = coupling_coherence(PHI_OPT, A, WINDOW)
        window = f"({r.sigma_min:.4f}, {r.sigma_max:.4f})"
        print(f"   {n:>4} {s_opt:>15.5f} {PHI_OPT:>9.5f} "
              f"{PHI_OPT / s_opt:>7.2f} {window:>22} {r.regime:>20}")
    print()
    print("   The physics optimum falls as 1/n. The placeholder is constant.")
    print("   They can coincide at one system size at most, and past n=10")
    print("   the placeholder sits OUTSIDE the stable window entirely: the")
    print("   fastest mode is driven unstable at exactly the coupling the")
    print("   placeholder calls perfect.")


def section_topology_blindness():
    print()
    print(RULE)
    print("3. THE RESULT: each measure picks its own best scale, same graph")
    print(RULE)
    print(f"   {'graph':<22} {'s* Frobenius':>13} {'f peak':>8} "
          f"{'s* physics':>11} {'f peak':>8} {'eigenratio':>11}")
    graphs = [
        ("complete K_6", complete(6)),
        ("ring C_6", ring(6)),
        ("star S_6", star(6)),
        ("path P_6", path(6)),
        ("barbell (bridged)", barbell(True)),
        ("barbell (bridge CUT)", barbell(False)),
    ]
    for name, A in graphs:
        s_f, f_f = frobenius_peak(A)
        s_p, f_p = physics_peak(A)
        spec = spectrum(A)
        er = "inf" if spec.eigenratio == float("inf") else f"{spec.eigenratio:.3f}"
        s_p_str = f"{s_p:.4f}" if s_p is not None else "none"
        print(f"   {name:<22} {s_f:>13.4f} {f_f:>8.4f} {s_p_str:>11} "
              f"{f_p:>8.4f} {er:>11}")
    print()
    print("   Frobenius puts the optimum at 1/phi^2 = 0.3820 for EVERY")
    print("   topology. Physics spreads it over 6x, driven by the Laplacian")
    print("   spectrum. The Gaussian form is not a rough estimate of the")
    print("   optimum — its argmax is not a function of the network at all.")
    print()
    print("   The last two rows are the same graph with one edge cut. That")
    print("   cut splits the network into two islands. Frobenius moves from")
    print("   0.0969 to 0.0724, a change indistinguishable from the gap")
    print("   between a ring and a star. Physics reports")
    print("   FRAGMENTED_STRUCTURALLY. The term whose job is to detect")
    print("   'too weak = fragmented' does not notice fragmentation.")


def section_correlation():
    print()
    print(RULE)
    print("4. Do the two measures correlate at all?")
    print(RULE)
    rng = np.random.default_rng(0)
    pairs, trials = [], 0
    while len(pairs) < 200 and trials < 4000:
        trials += 1
        n = int(rng.integers(4, 9))
        A = np.zeros((n, n))
        for i in range(n):
            for j in range(i + 1, n):
                if rng.random() < 0.45:
                    A[i, j] = A[j, i] = 1.0
        if not spectrum(A).connected:
            continue
        pairs.append((frobenius_peak(A)[1], physics_peak(A)[1]))

    fro = np.array([p[0] for p in pairs])
    phys = np.array([p[1] for p in pairs])
    r = float(np.corrcoef(fro, phys)[0, 1])
    print(f"   {len(pairs)} connected random graphs, 4-8 nodes, seed 0")
    print(f"   Pearson r between the two peak f(C) values: {r:+.4f}")
    print(f"   Frobenius peak: mean {fro.mean():.4f}  "
          f"min {fro.min():.4f}  max {fro.max():.4f}")
    print(f"   physics   peak: mean {phys.mean():.4f}  "
          f"min {phys.min():.4f}  max {phys.max():.4f}")
    print()
    print("   Near-zero correlation. Frobenius scores almost every real")
    print("   network as catastrophically mis-coupled even at its own best")
    print("   scale, because C* demands that EVERY pair be coupled at")
    print("   1/phi^2 — so any sparse network is penalized for its absent")
    print("   edges, which is a statement about the target, not the system.")


def section_size_dependence():
    print()
    print(RULE)
    print("5. A separate defect: f(C) is not size-invariant")
    print(RULE)
    print("   Frobenius deviation^2 = n(n-1)(c-c*)^2 for a uniform offset,")
    print("   so the same PER-EDGE mistuning is penalized quadratically in n")
    print("   while alpha stays 1.")
    print()
    print(f"   {'n':>5} {'alpha=1':>12} {'alpha=1/(n(n-1))':>18}")
    for n in (2, 5, 10, 20, 50, 100):
        C = coupling_matrix(n, PHI_OPT + 0.10)
        C_star = phi_coupling_optimum(n)
        raw = CoherenceMetric(alpha=1.0,
                              coupling_optimum=C_star).coupling_function(C)
        normed = CoherenceMetric(alpha=1.0 / (n * (n - 1)),
                                 coupling_optimum=C_star).coupling_function(C)
        print(f"   {n:>5} {raw:>12.6f} {normed:>18.6f}")
    print()
    print("   Every edge off by the same 0.10. At n=20 the system reads")
    print("   f(C)=0.022 and M(S) goes negative on the coupling term alone;")
    print("   past n=50 it is numerically zero, so M(S) = -L for ANY large")
    print("   system regardless of how well coupled it is.")
    print()
    print("   Unlike the topology blindness, this one is repairable inside")
    print("   the existing form: alpha = 1/(n(n-1)) makes the penalty")
    print("   per-edge and the reading size-invariant. Whether to change a")
    print("   default that would move every existing reading is a decision,")
    print("   not a measurement — so this reports it and changes nothing.")


def section_where_it_bites():
    print()
    print(RULE)
    print("6. How much of this bites the code as actually used?")
    print(RULE)
    print("   All four audit bridges construct n=2 coupling matrices.")
    print("   At n=2 there is exactly one edge, so every topology is the")
    print("   same topology: K_2 = ring = path, lambda_2 = lambda_N = 2,")
    print("   eigenratio 1. Topology blindness cannot bite where there is")
    print("   only one topology, and the size term n(n-1) = 2 is at its")
    print("   minimum.")
    print()
    A = complete(2)
    spec = spectrum(A)
    s_opt = optimal_coupling(spec, WINDOW)
    print(f"   n=2: sigma* = {s_opt:.5f} vs 1/phi^2 = {PHI_OPT:.5f} "
          f"(ratio {PHI_OPT / s_opt:.2f})")
    print(f"        and that agreement is a property of this window: it")
    print(f"        requires nu1*nu2 = (n/phi^2)^2 = "
          f"{(2 * PHI_OPT) ** 2:.4f}, here {WINDOW.nu_lower * WINDOW.nu_upper:.4f}.")
    print()
    print("   So the bridges are not currently producing wrong readings from")
    print("   this. The defect is latent, and the public API invites it:")
    print("   coupling_matrix(n, c) and phi_coupling_optimum(n) both take")
    print("   any n, and are documented as general.")


def main():
    print()
    print("EXPERIMENT: what is the real coupling optimum?")
    print(f"placeholder 1/phi^2 = {PHI_OPT:.6f}")
    print()
    section_default_has_no_interior_optimum()
    section_scale_with_n()
    section_topology_blindness()
    section_correlation()
    section_size_dependence()
    section_where_it_bites()
    print()
    print(RULE)
    print("WHAT IS REAL")
    print(RULE)
    print("   sigma* = sqrt(nu1*nu2 / (lambda_2*lambda_N))")
    print()
    print("   A function of the topology (lambda_2, lambda_N) and the node")
    print("   dynamics (nu_1, nu_2). Not a constant, and not expressible as")
    print("   distance to any fixed target matrix, because a fixed target")
    print("   cannot depend on the spectrum of the network it is scoring.")
    print()
    print("   1/phi^2 is not a coarse estimate of that quantity. It is the")
    print("   answer to a different question — 'how entry-wise close is C to")
    print("   a matrix someone chose?' — and the two answers correlate at")
    print("   r = +0.05.")
    print()
    print("   Where the graph is known, use coupling_physics. Where only a")
    print("   scalar is available, the placeholder is what there is, and it")
    print("   should be read as an index, not as a coupling measurement.")
    print(RULE)


if __name__ == "__main__":
    main()

---

### src/core/coherence_metric.py

```python
"""
MCPM Core: Systemic Coherence Measurement

This module MEASURES systemic health. It does NOT control or optimize systems.
"""

import numpy as np
from typing import Dict, Tuple, Optional
from dataclasses import dataclass

PHI = 1.618033988749895  # Golden ratio


@dataclass
class SystemState:
    """State of a system being measured"""
    resonance_energy: float  # R_e: Constructive interaction flow
    adaptability: float      # A: Recovery rate coefficient
    diversity: float         # D: Effective number of viable strategies
    coupling_matrix: np.ndarray  # C: Subsystem interaction strengths
    loss_rate: float         # L: Waste/harm/entropy rate
    
    # Optional metadata
    energy_cost: Optional[float] = None  # kWh/day
    population: Optional[int] = None
    description: Optional[str] = None


class CoherenceMetric:
    """
    Calculate systemic coherence M(S).
    
    IMPORTANT: This class MEASURES systems. It does NOT:
    - Suggest interventions
    - Optimize toward targets
    - Apply control
    - Enforce conformity
    
    Use this to reveal truth about system health, not to control systems.
    """
    
    def __init__(self, 
                 alpha: float = 1.0,
                 coupling_optimum: Optional[np.ndarray] = None):
        """
        Initialize coherence measurement.
        
        Args:
            alpha: Coupling sensitivity parameter
            coupling_optimum: C* matrix (optimal coupling pattern)
                            If None, uses identity scaled by phi
        """
        self.alpha = alpha
        self.coupling_optimum = coupling_optimum
        
    def coupling_function(self, C: np.ndarray) -> float:
        """
        Non-monotonic coupling function f(C).
        
        Peaked at optimal intermediate coupling (too weak = fragmented,
        too strong = rigid, optimal = flexible coherence).
        
        Args:
            C: Coupling matrix
            
        Returns:
            f(C) value in [0, 1]
        """
        if self.coupling_optimum is None:
            # Default: identity scaled by phi
            n = C.shape[0]
            C_star = np.eye(n) / PHI
        else:
            C_star = self.coupling_optimum
        
        # Inverse-U function: exp(-alpha * ||C - C*||^2)
        deviation = np.linalg.norm(C - C_star, 'fro')
        f_C = np.exp(-self.alpha * deviation**2)
        
        return float(f_C)
    
    def calculate(self, 
                  resonance_energy: float,
                  adaptability: float,
                  diversity: float,
                  coupling_matrix: np.ndarray,
                  loss_rate: float) -> float:
        """
        Calculate systemic coherence M(S).
        
        M(S) = (R_e × A × D × f(C)) - L
        
        Args:
            resonance_energy: Constructive interaction flow
            adaptability: Recovery rate
            diversity: Number of viable strategies
            coupling_matrix: Subsystem interactions
            loss_rate: Waste/harm/entropy
            
        Returns:
            M(S): System coherence value
                 Positive = coherent/healthy
                 Negative = incoherent/collapsing
        """
        # Calculate coupling function
        f_C = self.coupling_function(coupling_matrix)
        
        # Coherent gain
        gain = resonance_energy * adaptability * diversity * f_C
        
        # Total coherence
        M_S = gain - loss_rate
        
        return float(M_S)
    
    def calculate_from_state(self, state: SystemState) -> float:
        """Convenience method using SystemState object"""
        return self.calculate(
            state.resonance_energy,
            state.adaptability,
            state.diversity,
            state.coupling_matrix,
            state.loss_rate
        )
    
    def efficiency_ratio(self, state: SystemState) -> Optional[float]:
        """
        Calculate efficiency: M(S) / energy_cost
        
        This reveals who creates value efficiently.
        
        Returns:
            Coherence per kWh, or None if energy_cost not provided
        """
        if state.energy_cost is None:
            return None
        
        M_S = self.calculate_from_state(state)
        return M_S / state.energy_cost
    
    def compare_systems(self, 
                       system_a: SystemState,
                       system_b: SystemState) -> Dict:
        """
        Compare two systems.
        
        Use this to show which system creates more value, NOT to
        enforce replacement of one with the other.
        
        Returns:
            Comparison metrics
        """
        M_a = self.calculate_from_state(system_a)
        M_b = self.calculate_from_state(system_b)
        
        eff_a = self.efficiency_ratio(system_a)
        eff_b = self.efficiency_ratio(system_b)
        
        result = {
            'system_a': {
                'coherence': M_a,
                'efficiency': eff_a,
                'energy_cost': system_a.energy_cost
            },
            'system_b': {
                'coherence': M_b,
                'efficiency': eff_b,
                'energy_cost': system_b.energy_cost
            },
            'delta_coherence': M_b - M_a,
            'delta_efficiency': (eff_b - eff_a) if (eff_a and eff_b) else None,
            'replacement_makes_sense': None  # Intentionally not decided
        }
        
        # Provide information, don't make decision
        result['interpretation'] = (
            f"System A creates {M_a:.2f} coherence at {system_a.energy_cost} kWh/day.\n"
            f"System B creates {M_b:.2f} coherence at {system_b.energy_cost} kWh/day.\n"
            f"Efficiency ratio: A={eff_a:.4f}, B={eff_b:.4f} coherence/kWh.\n\n"
            f"This is MEASUREMENT, not prescription. You decide what it means."
        )
        
        return result


# Example usage
if __name__ == "__main__":
    print("="*70)
    print("COHERENCE METRIC DEMONSTRATION")
    print("="*70)
    
    # Example: Efficient rural worker
    rural_worker = SystemState(
        resonance_energy=0.9,  # High constructive interaction
        adaptability=0.85,     # Good recovery
        diversity=0.8,         # Multiple skills
        coupling_matrix=np.array([[1/PHI, 0.3], [0.3, 1/PHI]]),  # Optimal coupling
        loss_rate=0.1,         # Low waste
        energy_cost=6,         # kWh/day
        description="Efficient rural worker"
    )
    
    # Example: Wasteful executive
    executive = SystemState(
        resonance_energy=0.3,  # Low constructive interaction
        adaptability=0.4,      # Poor adaptation
        diversity=0.2,         # Limited strategies
        coupling_matrix=np.array([[2.0, 0.1], [0.1, 2.0]]),  # Over-coupled (rigid)
        loss_rate=0.8,         # High waste (violence costs)
        energy_cost=1000,      # kWh/day
        description="Wasteful executive system"
    )
    
    # Measure both
    metric = CoherenceMetric()
    
    comparison = metric.compare_systems(rural_worker, executive)
    
    print("\n" + comparison['interpretation'])
    print("\n" + "="*70)
    print("This measurement reveals truth. It doesn't enforce policy.")
    print("="*70)

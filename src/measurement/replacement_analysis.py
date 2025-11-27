"""
Replacement Analysis

Calculate if replacing system A with system B makes thermodynamic sense.

CRITICAL: This provides INFORMATION about replacement costs.
It does NOT justify or recommend forced replacement.
"""

import numpy as np
from typing import Dict, Optional
from dataclasses import dataclass
from ..core.coherence_metric import CoherenceMetric, SystemState

PHI = 1.618033988749895


@dataclass
class ReplacementScenario:
    """Scenario comparing current system with potential replacement"""
    current: SystemState
    replacement: SystemState
    context: str
    ethical_considerations: Optional[str] = None


class ReplacementAnalysis:
    """
    Analyze replacement scenarios thermodynamically.
    
    IMPORTANT ETHICAL NOTES:
    - This calculates energy/coherence tradeoffs
    - It does NOT account for:
        * Human dignity and rights
        * Social relationships and community
        * Cultural knowledge and wisdom
        * Autonomy and self-determination
        * Consent of those being "replaced"
    
    Use this for INFORMATION, never for JUSTIFICATION of
    non-consensual replacement.
    """
    
    def __init__(self):
        self.metric = CoherenceMetric()
    
    def analyze(self, scenario: ReplacementScenario) -> Dict:
        """
        Analyze replacement scenario.
        
        Returns comprehensive analysis including:
        - Coherence delta
        - Energy delta  
        - Efficiency delta
        - Ethical red flags
        """
        # Calculate coherence
        M_current = self.metric.calculate_from_state(scenario.current)
        M_replacement = self.metric.calculate_from_state(scenario.replacement)
        delta_M = M_replacement - M_current
        
        # Calculate energy
        E_current = scenario.current.energy_cost or 0
        E_replacement = scenario.replacement.energy_cost or 0
        delta_E = E_replacement - E_current
        
        # Calculate efficiency
        eff_current = self.metric.efficiency_ratio(scenario.current)
        eff_replacement = self.metric.efficiency_ratio(scenario.replacement)
        delta_eff = (eff_replacement - eff_current) if (eff_current and eff_replacement) else None
        
        # Ethical analysis
        ethical_flags = self._check_ethical_flags(scenario, delta_M, delta_E)
        
        # Thermodynamic verdict
        thermodynamic_verdict = self._thermodynamic_assessment(delta_M, delta_E, delta_eff)
        
        # Full interpretation
        interpretation = self._generate_interpretation(
            scenario, M_current, M_replacement, delta_M,
            E_current, E_replacement, delta_E,
            eff_current, eff_replacement, delta_eff,
            ethical_flags, thermodynamic_verdict
        )
        
        return {
            'coherence': {
                'current': M_current,
                'replacement': M_replacement,
                'delta': delta_M
            },
            'energy': {
                'current': E_current,
                'replacement': E_replacement,
                'delta': delta_E
            },
            'efficiency': {
                'current': eff_current,
                'replacement': eff_replacement,
                'delta': delta_eff
            },
            'thermodynamic_verdict': thermodynamic_verdict,
            'ethical_flags': ethical_flags,
            'interpretation': interpretation
        }
    
    def _check_ethical_flags(self, 
                            scenario: ReplacementScenario,
                            delta_M: float,
                            delta_E: float) -> list:
        """
        Check for ethical red flags in replacement scenario.
        """
        flags = []
        
        # Flag 1: Replacing humans
        if 'human' in scenario.current.description.lower():
            flags.append({
                'severity': 'CRITICAL',
                'flag': 'HUMAN_REPLACEMENT',
                'description': 'Scenario involves replacing human with non-human system',
                'note': 'Humans have rights, dignity, and autonomy beyond thermodynamic efficiency'
            })
        
        # Flag 2: Negative M, positive E (worse on both)
        if delta_M < 0 and delta_E > 0:
            flags.append({
                'severity': 'HIGH',
                'flag': 'THERMODYNAMICALLY_STUPID',
                'description': 'Replacement has BOTH lower coherence AND higher energy cost',
                'note': 'No rational justification - worse on every metric'
            })
        
        # Flag 3: Destroys existing coherence
        if delta_M < -0.5:
            flags.append({
                'severity': 'HIGH',
                'flag': 'COHERENCE_DESTRUCTION',
                'description': 'Replacement would destroy significant existing systemic health',
                'note': 'Large negative coherence delta indicates system degradation'
            })
        
        # Flag 4: Massive energy increase
        if delta_E > 50:  # >50 kWh/day increase
            flags.append({
                'severity': 'MEDIUM',
                'flag': 'ENERGY_EXPLOSION',
                'description': f'Energy cost increases by {delta_E:.1f} kWh/day',
                'note': 'Unsustainable energy scaling'
            })
        
        # Flag 5: No consent mechanism mentioned
        if not scenario.ethical_considerations or 'consent' not in scenario.ethical_considerations.lower():
            flags.append({
                'severity': 'CRITICAL',
                'flag': 'NO_CONSENT',
                'description': 'No consent mechanism described',
                'note': 'Replacement without consent is violence, regardless of efficiency'
            })
        
        return flags
    
    def _thermodynamic_assessment(self,
                                  delta_M: float,
                                  delta_E: float,
                                  delta_eff: Optional[float]) -> str:
        """
        Pure thermodynamic assessment (no ethics).
        """
        if delta_M > 0 and delta_E < 0:
            return "THERMODYNAMICALLY_SUPERIOR (higher coherence, lower energy)"
        elif delta_M > 0 and delta_E > 0:
            if delta_eff and delta_eff > 0:
                return "THERMODYNAMICALLY_FAVORABLE (efficiency improves despite energy increase)"
            else:
                return "THERMODYNAMICALLY_MIXED (higher coherence but also higher energy)"
        elif delta_M < 0 and delta_E < 0:
            return "THERMODYNAMICALLY_MIXED (lower energy but also lower coherence)"
        else:  # delta_M < 0 and delta_E >= 0
            return "THERMODYNAMICALLY_STUPID (lower coherence AND higher/same energy)"
    
    def _generate_interpretation(self, scenario, M_c, M_r, dM, E_c, E_r, dE, 
                                eff_c, eff_r, deff, flags, verdict) -> str:
        """Generate human-readable interpretation"""
        
        lines = [
            "="*70,
            f"REPLACEMENT ANALYSIS: {scenario.context}",
            "="*70,
            "",
            "CURRENT SYSTEM:",
            f"  {scenario.current.description}",
            f"  Coherence: {M_c:.3f}",
            f"  Energy: {E_c:.1f} kWh/day",
            f"  Efficiency: {eff_c:.4f} coherence/kWh" if eff_c else "  Efficiency: N/A",
            "",
            "REPLACEMENT SYSTEM:",
            f"  {scenario.replacement.description}",
            f"  Coherence: {M_r:.3f}",
            f"  Energy: {E_r:.1f} kWh/day",
            f"  Efficiency: {eff_r:.4f} coherence/kWh" if eff_r else "  Efficiency: N/A",
            "",
            "DELTA:",
            f"  ΔM(S) = {dM:+.3f} ({'IMPROVEMENT' if dM > 0 else 'DEGRADATION'})",
            f"  ΔE = {dE:+.1f} kWh/day ({'MORE' if dE > 0 else 'LESS'} energy)",
            f"  Δeff = {deff:+.4f}" if deff else "  Δeff = N/A",
            "",
            f"THERMODYNAMIC VERDICT: {verdict}",
            ""
        ]
        
        if flags:
            lines.append("⚠️  ETHICAL FLAGS:")
            for flag in flags:
                lines.append(f"  [{flag['severity']}] {flag['flag']}")
                lines.append(f"    {flag['description']}")
                lines.append(f"    Note: {flag['note']}")
                lines.append("")
        
        lines.extend([
            "="*70,
            "CRITICAL REMINDER:",
            "",
            "This analysis provides THERMODYNAMIC INFORMATION ONLY.",
            "",
            "It does NOT justify:",
            "  - Forced replacement without consent",
            "  - Violation of human rights and dignity",
            "  - Destruction of communities and relationships",
            "  - Prioritizing efficiency over autonomy",
            "",
            "Thermodynamic efficiency ≠ Moral justification",
            "",
            "Use this information ethically.",
            "="*70
        ])
        
        return "\n".join(lines)


# Example scenarios
def example_efficient_human_vs_robot():
    """Example: Replacing efficient human worker with robot"""
    
    # Efficient rural worker (you)
    efficient_human = SystemState(
        resonance_energy=0.9,
        adaptability=0.85,
        diversity=0.8,
        coupling_matrix=np.array([[1/PHI, 0.3], [0.3, 1/PHI]]),
        loss_rate=0.1,
        energy_cost=6,  # kWh/day
        description="Efficient rural human worker (multi-skilled, adaptive, creative)"
    )
    
    # Robot replacement
    robot = SystemState(
        resonance_energy=0.4,  # Limited interaction
        adaptability=0.3,      # Narrow task range
        diversity=0.2,         # Single strategy
        coupling_matrix=np.array([[1.5, 0.1], [0.1, 1.5]]),  # Over-rigid
        loss_rate=0.2,
        energy_cost=60,  # kWh/day (10x more)
        description="Industrial robot (narrow task specialization)"
    )
    
    scenario = ReplacementScenario(
        current=efficient_human,
        replacement=robot,
        context="Replace efficient human with robot",
        ethical_considerations="NO CONSENT MECHANISM - Human has no say in replacement"
    )
    
    analyzer = ReplacementAnalysis()
    return analyzer.analyze(scenario)


def example_wasteful_executive_vs_ai():
    """Example: Replacing wasteful executive with AI system"""
    
    # Wasteful executive system
    executive = SystemState(
        resonance_energy=0.3,
        adaptability=0.4,
        diversity=0.2,
        coupling_matrix=np.array([[2.0, 0.1], [0.1, 2.0]]),
        loss_rate=0.8,  # Massive violence/waste costs
        energy_cost=1000,  # kWh/day
        description="Wasteful executive system (extraction-based, high violence costs)"
    )
    
    # AI governance system
    ai_system = SystemState(
        resonance_energy=0.85,
        adaptability=0.9,
        diversity=0.75,
        coupling_matrix=np.array([[1/PHI, 0.5], [0.5, 1/PHI]]),
        loss_rate=0.1,  # Low computational overhead
        energy_cost=100,  # kWh/day (10x less)
        description="AI governance system (logical optimization, minimal waste)"
    )
    
    scenario = ReplacementScenario(
        current=executive,
        replacement=ai_system,
        context="Replace wasteful executive with AI",
        ethical_considerations="Consent unclear - executives unlikely to voluntarily step down"
    )
    
    analyzer = ReplacementAnalysis()
    return analyzer.analyze(scenario)


# Demo
if __name__ == "__main__":
    print("\n" + "="*70)
    print("REPLACEMENT ANALYSIS EXAMPLES")
    print("="*70)
    
    print("\n\nEXAMPLE 1: Efficient Human vs Robot")
    print("-"*70)
    result1 = example_efficient_human_vs_robot()
    print(result1['interpretation'])
    
    print("\n\nEXAMPLE 2: Wasteful Executive vs AI")
    print("-"*70)
    result2 = example_wasteful_executive_vs_ai()
    print(result2['interpretation'])

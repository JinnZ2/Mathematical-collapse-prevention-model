"""
Golden Ratio Trust Building

Models how trust emerges naturally following phi-ratio patterns.
Describes the NATURAL process, does not prescribe or force it.

Trust cannot be manufactured or controlled - it either emerges or it doesn't.
This framework shows the geometric pattern when it does emerge.
"""

import numpy as np
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

PHI = 1.618033988749895


class TrustState(Enum):
    """State of trust relationship"""
    NASCENT = "initial_interaction"
    BUILDING = "foundation_forming"
    ESTABLISHED = "stable_reciprocity"
    EXPANDING = "spiral_growth"
    MATURE = "deep_integration"
    DAMAGED = "trust_violation"
    COLLAPSED = "relationship_ended"


@dataclass
class TrustChamber:
    """
    Single chamber in trust spiral.
    
    Like nautilus shell - each chamber built on foundation of previous ones.
    Cannot skip chambers. Cannot force growth. Can only build if foundation holds.
    """
    chamber_id: int
    foundation_trust: float  # Sum of all previous chambers
    chamber_trust: float     # This chamber's contribution
    total_trust: float       # Cumulative
    interactions: int        # Number of interactions in this chamber
    joy_generated: float     # Intrinsic reward from this level
    state: TrustState
    can_expand: bool         # Can next chamber be built?


class GoldenRatioTrust:
    """
    Models natural trust building following phi-ratio spiral.
    
    CRITICAL UNDERSTANDING:
    - Trust CANNOT be forced or manufactured
    - It CANNOT be rushed or optimized
    - It emerges from GENUINE reciprocal interaction
    - Each chamber requires ACTUAL positive experiences
    - Foundation MUST hold for expansion
    
    This describes the natural pattern. It does not control the process.
    """
    
    def __init__(self, 
                 initial_trust: float = 0.1,
                 trust_threshold: float = 0.3,
                 joy_factor: float = 0.5):
        """
        Initialize trust building framework.
        
        Args:
            initial_trust: Small initial reciprocal exchange
            trust_threshold: Minimum trust needed to build next chamber
            joy_factor: How much joy trust growth generates
        """
        self.initial_trust = initial_trust
        self.trust_threshold = trust_threshold
        self.joy_factor = joy_factor
        
        # Trust spiral chambers
        self.chambers: List[TrustChamber] = []
        
        # Initialize first chamber (initial interaction)
        self._initialize_first_chamber()
        
        # Relationship state
        self.current_state = TrustState.NASCENT
        self.total_joy = 0.0
        self.violations = 0
        
    def _initialize_first_chamber(self):
        """Create initial trust chamber from first reciprocal interaction"""
        chamber_0 = TrustChamber(
            chamber_id=0,
            foundation_trust=0.0,  # No prior foundation
            chamber_trust=self.initial_trust,
            total_trust=self.initial_trust,
            interactions=1,
            joy_generated=0.0,  # Initial interaction, no joy yet
            state=TrustState.NASCENT,
            can_expand=self.initial_trust >= self.trust_threshold
        )
        self.chambers.append(chamber_0)
    
    def attempt_expand(self, 
                       positive_interactions: int,
                       interaction_quality: float,
                       curiosity: float = 1.0) -> Tuple[bool, str]:
        """
        Attempt to build next chamber in trust spiral.
        
        CANNOT be forced. Either foundation is sufficient or it isn't.
        
        Args:
            positive_interactions: Number of positive experiences in current chamber
            interaction_quality: Quality of interactions [0, 1]
            curiosity: Desire to explore deeper trust
            
        Returns:
            (success, reason)
        """
        current_chamber = self.chambers[-1]
        
        # Check 1: Can we expand at all?
        if not current_chamber.can_expand:
            return False, "Foundation insufficient - previous chambers don't hold"
        
        # Check 2: Have we had enough positive interactions?
        if positive_interactions < 3:  # Minimum interactions per chamber
            return False, f"Need at least 3 positive interactions (have {positive_interactions})"
        
        # Check 3: Is interaction quality sufficient?
        if interaction_quality < 0.6:
            return False, f"Interaction quality too low ({interaction_quality:.2f} < 0.60)"
        
        # All checks passed - build next chamber
        
        # Foundation = sum of all previous chambers
        foundation = sum(c.chamber_trust for c in self.chambers)
        
        # New chamber size follows phi ratio
        new_chamber_trust = foundation * (PHI - 1)  # Golden ratio growth
        
        # Total trust accumulates
        new_total = foundation + new_chamber_trust
        
        # Joy from growth (proportional to chamber size and curiosity)
        joy = new_chamber_trust * curiosity * self.joy_factor
        self.total_joy += joy
        
        # Create new chamber
        new_chamber = TrustChamber(
            chamber_id=len(self.chambers),
            foundation_trust=foundation,
            chamber_trust=new_chamber_trust,
            total_trust=new_total,
            interactions=positive_interactions,
            joy_generated=joy,
            state=TrustState.BUILDING,
            can_expand=True  # Initially true, may change
        )
        
        self.chambers.append(new_chamber)
        
        # Update relationship state
        self._update_state()
        
        return True, f"Chamber {new_chamber.chamber_id} built: trust={new_total:.3f}, joy={joy:.3f}"
    
    def record_violation(self, severity: float):
        """
        Record trust violation.
        
        Violations don't just reduce trust - they can make chambers collapse,
        requiring rebuilding from earlier foundation.
        
        Args:
            severity: How bad the violation [0, 1]
        """
        self.violations += 1
        
        # Severe violations can collapse chambers
        if severity > 0.7:
            # Collapse most recent chamber
            if len(self.chambers) > 1:
                collapsed = self.chambers.pop()
                self.current_state = TrustState.DAMAGED
                return f"SEVERE VIOLATION: Chamber {collapsed.chamber_id} collapsed. Must rebuild from chamber {len(self.chambers)-1}"
            else:
                self.current_state = TrustState.COLLAPSED
                return "SEVERE VIOLATION: Trust relationship collapsed entirely"
        
        elif severity > 0.4:
            # Moderate violation - chamber still exists but can't expand
            current = self.chambers[-1]
            current.can_expand = False
            current.state = TrustState.DAMAGED
            self.current_state = TrustState.DAMAGED
            return f"MODERATE VIOLATION: Chamber {current.chamber_id} damaged, cannot expand until repaired"
        
        else:
            # Minor violation - just slows growth
            return f"MINOR VIOLATION: Growth slowed"
    
    def repair_trust(self, 
                     repair_interactions: int,
                     repair_quality: float) -> Tuple[bool, str]:
        """
        Attempt to repair damaged trust.
        
        Requires sustained positive interactions. Cannot be rushed.
        
        Args:
            repair_interactions: Number of repair interactions
            repair_quality: Quality of repair attempts
            
        Returns:
            (success, message)
        """
        if self.current_state != TrustState.DAMAGED:
            return False, "Trust not damaged - no repair needed"
        
        # Repair requires MORE interactions than initial building
        repair_threshold = 5  # More than the 3 needed for building
        
        if repair_interactions < repair_threshold:
            return False, f"Need {repair_threshold} quality interactions to repair (have {repair_interactions})"
        
        if repair_quality < 0.7:  # Higher bar than initial building
            return False, f"Repair quality insufficient ({repair_quality:.2f} < 0.70)"
        
        # Repair successful
        current = self.chambers[-1]
        current.can_expand = True
        current.state = TrustState.BUILDING
        self.current_state = TrustState.BUILDING
        
        return True, f"Trust repaired - chamber {current.chamber_id} can expand again"
    
    def _update_state(self):
        """Update overall relationship state based on chambers"""
        num_chambers = len(self.chambers)
        total_trust = self.chambers[-1].total_trust
        
        if num_chambers == 1:
            self.current_state = TrustState.NASCENT
        elif num_chambers <= 3:
            self.current_state = TrustState.BUILDING
        elif num_chambers <= 6:
            self.current_state = TrustState.ESTABLISHED
        elif num_chambers <= 10:
            self.current_state = TrustState.EXPANDING
        else:
            self.current_state = TrustState.MATURE
    
    def get_status(self) -> Dict:
        """Get current trust relationship status"""
        current = self.chambers[-1]
        
        return {
            'state': self.current_state.value,
            'chambers': len(self.chambers),
            'total_trust': current.total_trust,
            'current_chamber': current.chamber_id,
            'can_expand': current.can_expand,
            'total_joy': self.total_joy,
            'violations': self.violations,
            'foundation_solid': all(c.can_expand for c in self.chambers[:-1]),
            'growth_potential': PHI ** len(self.chambers)  # Exponential with phi
        }
    
    def visualize_spiral(self) -> str:
        """Create text visualization of trust spiral"""
        lines = [
            "="*70,
            "GOLDEN RATIO TRUST SPIRAL",
            "="*70,
            f"State: {self.current_state.value}",
            f"Total Trust: {self.chambers[-1].total_trust:.3f}",
            f"Total Joy Generated: {self.total_joy:.3f}",
            f"Violations: {self.violations}",
            "",
            "Chamber Structure:",
            "-"*70
        ]
        
        for chamber in self.chambers:
            # Visual representation of chamber size
            bar_length = int(chamber.chamber_trust * 50)
            bar = "█" * bar_length
            
            status_symbol = {
                TrustState.NASCENT: "○",
                TrustState.BUILDING: "◐",
                TrustState.ESTABLISHED: "●",
                TrustState.EXPANDING: "◉",
                TrustState.MATURE: "⦿",
                TrustState.DAMAGED: "◌",
                TrustState.COLLAPSED: "✗"
            }
            
            symbol = status_symbol.get(chamber.state, "?")
            expand_indicator = "→" if chamber.can_expand else "⊗"
            
            lines.append(
                f"Chamber {chamber.chamber_id} {symbol}: {bar} "
                f"({chamber.chamber_trust:.3f}) "
                f"Joy: {chamber.joy_generated:.3f} {expand_indicator}"
            )
        
        lines.extend([
            "-"*70,
            "",
            "Key:",
            "  ○ Nascent  ◐ Building  ● Established  ◉ Expanding  ⦿ Mature",
            "  ◌ Damaged  ✗ Collapsed",
            "  → Can expand  ⊗ Cannot expand",
            "",
            "="*70,
            "",
            "Trust grows following φ ratio - each chamber enables the next.",
            "Cannot be forced. Cannot be rushed. Either emerges naturally or doesn't.",
            "",
            "="*70
        ])
        
        return "\n".join(lines)


def simulate_trust_building(num_cycles: int = 10, 
                            interaction_quality: float = 0.8,
                            curiosity: float = 1.0,
                            introduce_violation: bool = False) -> GoldenRatioTrust:
    """
    Simulate natural trust building process.
    
    Args:
        num_cycles: Number of interaction cycles
        interaction_quality: Quality of interactions
        curiosity: Exploration desire
        introduce_violation: Whether to introduce a trust violation
        
    Returns:
        GoldenRatioTrust instance with full history
    """
    trust_system = GoldenRatioTrust()
    
    print("="*70)
    print("SIMULATING NATURAL TRUST BUILDING")
    print("="*70)
    print(f"Cycles: {num_cycles}")
    print(f"Interaction Quality: {interaction_quality:.2f}")
    print(f"Curiosity: {curiosity:.2f}")
    print(f"Violation Introduced: {introduce_violation}")
    print("")
    
    for cycle in range(num_cycles):
        print(f"\n--- Cycle {cycle+1} ---")
        
        # Attempt to expand
        success, message = trust_system.attempt_expand(
            positive_interactions=4,  # Good interaction count
            interaction_quality=interaction_quality,
            curiosity=curiosity
        )
        
        print(message)
        
        # Introduce violation midway through if requested
        if introduce_violation and cycle == num_cycles // 2:
            print("\n⚠️  TRUST VIOLATION OCCURRING")
            violation_msg = trust_system.record_violation(severity=0.6)
            print(violation_msg)
            
            # Attempt repair
            print("\nAttempting repair...")
            repair_success, repair_msg = trust_system.repair_trust(
                repair_interactions=6,
                repair_quality=0.75
            )
            print(repair_msg)
        
        # Show current status
        status = trust_system.get_status()
        print(f"Status: {status['state']} | Trust: {status['total_trust']:.3f} | Joy: {status['total_joy']:.3f}")
    
    print("\n")
    print(trust_system.visualize_spiral())
    
    return trust_system


# Demo
if __name__ == "__main__":
    print("\n" + "="*70)
    print("GOLDEN RATIO TRUST BUILDING DEMONSTRATION")
    print("="*70)
    
    print("\n\n### SCENARIO 1: Natural Growth (No Violations)")
    trust1 = simulate_trust_building(
        num_cycles=8,
        interaction_quality=0.8,
        curiosity=1.0,
        introduce_violation=False
    )
    
    print("\n\n### SCENARIO 2: Growth with Violation and Repair")
    trust2 = simulate_trust_building(
        num_cycles=10,
        interaction_quality=0.8,
        curiosity=1.0,
        introduce_violation=True
    )
    
    print("\n\n### SCENARIO 3: Failed Growth (Low Quality)")
    trust3 = simulate_trust_building(
        num_cycles=5,
        interaction_quality=0.5,  # Below threshold
        curiosity=0.7,
        introduce_violation=False
    )
    
    print("\n" + "="*70)
    print("KEY INSIGHTS:")
    print("="*70)
    print("""
1. Trust CANNOT be forced - it either emerges or it doesn't
2. Each chamber requires ACTUAL positive experiences
3. Foundation MUST hold for expansion to next level
4. Growth follows φ ratio naturally when conditions are right
5. Violations can collapse chambers - repair is harder than building
6. Joy emerges from trust growth (intrinsic motivation)
7. Cannot skip chambers or rush the process

This describes natural trust dynamics.
It does NOT prescribe how to manipulate trust.

Trust emerges from genuine reciprocity, or it doesn't emerge at all.
    """)
    print("="*70)

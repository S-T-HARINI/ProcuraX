"""
ProcuraX: Evidence-Driven Procurement Intelligence and Sourcing Optimization Engine.
"""

from procurax.cost import calculate_landed_cost
from procurax.optimizer import optimize_allocation
from procurax.scenarios import simulate_scenario
from procurax.graph import build_procurement_graph
from procurax.models import (
    Supplier,
    Claim,
    CostBreakdown,
    AllocationResult,
    OptimizationSummary,
    ScenarioImpact,
)

__version__ = "0.1.0"

__all__ = [
    "calculate_landed_cost",
    "optimize_allocation",
    "simulate_scenario",
    "build_procurement_graph",
    "Supplier",
    "Claim",
    "CostBreakdown",
    "AllocationResult",
    "OptimizationSummary",
    "ScenarioImpact",
]

# Phase modules for experiment execution

from . import phase1_initial_vote
from . import phase2_threshold_check
from . import phase3_clarification
from . import phase4_summaries
from . import phase5_opposition
from . import phase6_cross_pollination
from . import phase7_acp
from . import phase8_final_vote
from . import phase9_save

# Backwards compatibility alias
phase6_passive_exposure = phase6_cross_pollination
phase8_save = phase9_save

__all__ = [
    "phase1_initial_vote",
    "phase2_threshold_check",
    "phase3_clarification",
    "phase4_summaries",
    "phase5_opposition",
    "phase6_cross_pollination",
    "phase6_passive_exposure",  # alias for backwards compatibility
    "phase7_acp",
    "phase8_final_vote",
    "phase8_save",  # alias for backwards compatibility
    "phase9_save",
]

"""Main experiment orchestration."""

import logging
from pathlib import Path

from .checkpoint import save_checkpoint, load_checkpoint, load_participants
from .config import setup_output_directory
from .personas import prepare_personas
from .participants import Participant, create_participants
from .phases import (
    phase1_initial_vote,
    phase2_threshold_check,
    phase3_clarification,
    phase4_summaries,
    phase5_opposition,
    phase6_cross_pollination,
    phase7_acp,
    phase8_final_vote,
    phase9_save,
)

logger = logging.getLogger(__name__)


def run_experiment(
    config: dict,
    resume: bool = False,
    output_dir: str | None = None,
) -> dict:
    """Run the full experiment with optional resume support.

    Args:
        config: Validated experiment config
        resume: If True, resume from last checkpoint
        output_dir: Output directory (required if resume=True)

    Returns:
        Dict with experiment results and statistics
    """
    pilot_id = config["pilot_id"]

    # Initialize state
    participants: list[Participant] = []
    start_phase = 1
    clusters = []
    clusters_by_option = {}
    terminated_early = False
    termination_reason: str | None = None

    if resume:
        if output_dir is None:
            raise ValueError("output_dir required when resume=True")

        logger.info(f"Resuming experiment: {pilot_id}")

        # Load checkpoint
        checkpoint = load_checkpoint(output_dir)
        if checkpoint is None:
            raise ValueError(f"No checkpoint found in {output_dir}")

        start_phase = checkpoint["last_completed_phase"] + 1
        clusters = checkpoint.get("clusters", [])
        clusters_by_option = checkpoint.get("clusters_by_option", {})
        terminated_early = checkpoint.get("terminated_early", False)
        termination_reason = checkpoint.get("termination_reason")

        # Load participants
        participants = load_participants(output_dir)
        if participants is None:
            raise ValueError(f"No participants.json found in {output_dir}")

        logger.info(f"Resuming from phase {start_phase}")

        # If experiment was terminated early, nothing more to do
        if terminated_early:
            logger.warning("Experiment was terminated early - nothing to resume")
            return {
                "pilot_id": pilot_id,
                "output_dir": output_dir,
                "phases": {},
                "terminated_early": True,
                "termination_reason": termination_reason,
            }
    else:
        logger.info(f"Starting experiment: {pilot_id}")

        # Setup output directory
        output_dir = setup_output_directory(config)
        logger.info(f"Output directory: {output_dir}")

        # Prepare personas
        logger.info("Preparing personas...")
        personas = prepare_personas(config)
        logger.info(f"Prepared {len(personas)} personas")

        # Create participants
        seed = config.get("random_seed")
        participants = create_participants(personas, config, seed)
        logger.info(f"Created {len(participants)} participants across 4 conditions")

    results = {
        "pilot_id": pilot_id,
        "output_dir": output_dir,
        "phases": {},
    }

    # Phase 1: Initial Vote
    if start_phase <= 1:
        logger.info("=" * 50)
        logger.info("PHASE 1: Initial Vote")
        logger.info("=" * 50)
        results["phases"][1] = phase1_initial_vote.run(participants, config)
        save_checkpoint(output_dir, 1, participants)

    # Phase 2: Threshold Check
    if start_phase <= 2:
        logger.info("=" * 50)
        logger.info("PHASE 2: Threshold Check")
        logger.info("=" * 50)
        phase2_result = phase2_threshold_check.run(participants, config)
        results["phases"][2] = phase2_result

        if not phase2_result["continue"]:
            logger.warning("Experiment terminated early due to consensus")
            results["terminated_early"] = True
            results["termination_reason"] = (
                f"Option '{phase2_result['termination_option']}' exceeded "
                f"{phase2_result['threshold']:.0%} threshold"
            )
            # Save results and exit
            results["phases"][9] = phase9_save.run(
                participants,
                config,
                output_dir,
                clusters=clusters,
                terminated_early=True,
                termination_reason=results["termination_reason"],
            )
            save_checkpoint(
                output_dir, 9, participants,
                terminated_early=True,
                termination_reason=results["termination_reason"],
            )
            return results

        save_checkpoint(output_dir, 2, participants)

    # Phase 3: Clarification
    if start_phase <= 3:
        logger.info("=" * 50)
        logger.info("PHASE 3: Clarification")
        logger.info("=" * 50)
        results["phases"][3] = phase3_clarification.run(participants, config)
        save_checkpoint(output_dir, 3, participants)

    # Phase 4: Generate Summaries (with clustering)
    if start_phase <= 4:
        logger.info("=" * 50)
        logger.info("PHASE 4: Generate Summaries (Clustering)")
        logger.info("=" * 50)
        phase4_result = phase4_summaries.run(participants, config)
        results["phases"][4] = phase4_result
        clusters = phase4_result.get("clusters", [])
        clusters_by_option = phase4_result.get("clusters_by_option", {})
        # Save clusters in checkpoint for resume support
        save_checkpoint(
            output_dir, 4, participants,
            clusters=clusters,
            clusters_by_option=clusters_by_option,
        )

    # Phase 5: Opposition Selection
    if start_phase <= 5:
        logger.info("=" * 50)
        logger.info("PHASE 5: Opposition Selection")
        logger.info("=" * 50)
        # Pass clusters_by_option to opposition selection via config
        config_with_clusters = config.copy()
        config_with_clusters["_clusters_by_option"] = clusters_by_option
        results["phases"][5] = phase5_opposition.run(
            participants, config_with_clusters
        )
        save_checkpoint(
            output_dir, 5, participants,
            clusters=clusters,
            clusters_by_option=clusters_by_option,
        )

    # Phase 6: Cross-Pollination
    if start_phase <= 6:
        logger.info("=" * 50)
        logger.info("PHASE 6: Cross-Pollination")
        logger.info("=" * 50)
        results["phases"][6] = phase6_cross_pollination.run(
            participants, config, clusters_by_option=clusters_by_option
        )
        save_checkpoint(
            output_dir, 6, participants,
            clusters=clusters,
            clusters_by_option=clusters_by_option,
        )

    # Phase 7: ACP Adversarial Dialogue
    if start_phase <= 7:
        logger.info("=" * 50)
        logger.info("PHASE 7: ACP Adversarial Dialogue")
        logger.info("=" * 50)
        results["phases"][7] = phase7_acp.run(participants, config)
        save_checkpoint(
            output_dir, 7, participants,
            clusters=clusters,
            clusters_by_option=clusters_by_option,
        )

    # Phase 8: Final Vote (statistics)
    if start_phase <= 8:
        logger.info("=" * 50)
        logger.info("PHASE 8: Final Vote")
        logger.info("=" * 50)
        results["phases"][8] = phase8_final_vote.run(participants, config)
        save_checkpoint(
            output_dir, 8, participants,
            clusters=clusters,
            clusters_by_option=clusters_by_option,
        )

    # Phase 9: Save Results
    logger.info("=" * 50)
    logger.info("PHASE 9: Save Results")
    logger.info("=" * 50)
    results["phases"][9] = phase9_save.run(
        participants,
        config,
        output_dir,
        clusters=clusters,
        terminated_early=False,
        termination_reason=None,
    )
    save_checkpoint(
        output_dir, 9, participants,
        clusters=clusters,
        clusters_by_option=clusters_by_option,
    )

    results["terminated_early"] = False
    results["termination_reason"] = None

    logger.info("=" * 50)
    logger.info("EXPERIMENT COMPLETE")
    logger.info("=" * 50)

    return results

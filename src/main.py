"""Main entry point for the LLM-Mediated Deliberation Experiment."""

import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path

from .checkpoint import checkpoint_exists, save_checkpoint, load_participants
from .config import load_config, get_output_directory
from .experiment import run_experiment
from .llm import set_api_key


def setup_logging(output_dir: str | None = None) -> None:
    """Configure logging to console and optionally to file.

    Args:
        output_dir: If provided, also log to file in this directory
    """
    # Create formatter
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(console_handler)

    # File handler (if output_dir provided)
    if output_dir:
        log_path = Path(output_dir) / "experiment.log"
        file_handler = logging.FileHandler(log_path)
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)


def print_summary(results: dict) -> None:
    """Print experiment summary to console."""
    print("\n" + "=" * 60)
    print("EXPERIMENT SUMMARY")
    print("=" * 60)

    print(f"\nPilot ID: {results['pilot_id']}")
    print(f"Output Directory: {results['output_dir']}")

    if results.get("terminated_early"):
        print(f"\n⚠️  TERMINATED EARLY: {results['termination_reason']}")

    print("\nPhase Results:")
    for phase_num, phase_result in sorted(results.get("phases", {}).items()):
        phase_name = {
            1: "Initial Vote",
            2: "Threshold Check",
            3: "Clarification",
            4: "Summaries",
            5: "Opposition Selection",
            6: "Passive Exposure",
            7: "ACP Dialogue",
            8: "Save Results",
        }.get(phase_num, f"Phase {phase_num}")

        print(f"\n  Phase {phase_num}: {phase_name}")

        if "completed" in phase_result:
            print(f"    Completed: {phase_result['completed']}")
        if "failed" in phase_result:
            print(f"    Failed: {phase_result['failed']}")
        if "position_changed" in phase_result and phase_result["position_changed"] is not None:
            print(f"    Position Changed: {phase_result['position_changed']}")
        if "vote_counts" in phase_result:
            print("    Vote Distribution:")
            for opt, count in phase_result["vote_counts"].items():
                print(f"      - {opt}: {count}")

    print("\n" + "=" * 60)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Run LLM-Mediated Deliberation Experiment"
    )
    parser.add_argument(
        "--config",
        type=str,
        required=True,
        help="Path to YAML config file",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume an interrupted experiment from the last checkpoint",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose (debug) logging",
    )
    parser.add_argument(
        "--key",
        type=str,
        choices=["openai", "maria", "Maria"],
        default="openai",
        help="Which API key to use: openai, maria (default: openai)",
    )

    args = parser.parse_args()

    # Initial logging setup (console only)
    setup_logging()
    logger = logging.getLogger(__name__)

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Set API key
    set_api_key(args.key)

    # Track state for interrupt handling
    output_dir = None
    participants = None

    try:
        # Load config
        logger.info(f"Loading config from {args.config}")
        config = load_config(args.config)
        logger.info(f"Config loaded: {config['pilot_name']} ({config['pilot_id']})")

        # Get output directory for resume check
        output_dir = get_output_directory(config)

        if args.resume:
            # Check for checkpoint
            if not checkpoint_exists(output_dir):
                logger.error(
                    f"Cannot resume: no checkpoint found in {output_dir}. "
                    "Start a new experiment without --resume."
                )
                return 1
            logger.info(f"Resuming experiment from checkpoint in {output_dir}")
        else:
            # Check if output exists (will fail later, but give helpful message)
            if Path(output_dir).exists() and checkpoint_exists(output_dir):
                logger.info(
                    f"Found existing checkpoint in {output_dir}. "
                    "Use --resume to continue from where you left off."
                )

        # Run experiment
        start_time = datetime.now()
        if args.resume:
            logger.info(f"Resuming experiment at {start_time}")
        else:
            logger.info(f"Starting experiment at {start_time}")

        results = run_experiment(
            config,
            resume=args.resume,
            output_dir=output_dir if args.resume else None,
        )

        end_time = datetime.now()
        duration = end_time - start_time
        logger.info(f"Experiment completed in {duration}")

        # Add file logging to output directory
        setup_logging(results["output_dir"])

        # Print summary
        print_summary(results)

        return 0

    except FileNotFoundError as e:
        logger.error(f"File not found: {e}")
        return 1
    except FileExistsError as e:
        logger.error(f"Output directory already exists: {e}")
        return 1
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        return 1
    except KeyboardInterrupt:
        logger.warning("Experiment interrupted by user")
        # Try to save a checkpoint on interrupt
        if output_dir and Path(output_dir).exists():
            participants = load_participants(output_dir)
            if participants:
                logger.info("Saving checkpoint before exit...")
                # Note: checkpoint was already saved after last completed phase
                logger.info(
                    f"Checkpoint saved. Use --resume to continue later:\n"
                    f"  python -m src.main --config {args.config} --resume"
                )
        return 130
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())

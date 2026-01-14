#!/usr/bin/env python3
"""View conversation transcripts for a participant in human-readable format."""

import argparse
import json
import random
import sys
from pathlib import Path

VALID_CONDITIONS = ["simple_voting", "simple_passive", "clarified_passive", "acp"]


def load_participants(pilot_id: str) -> list[dict]:
    """Load participants from the pilot's output directory."""
    path = Path("outputs") / pilot_id / "participants.json"
    if not path.exists():
        print(f"Error: File not found: {path}", file=sys.stderr)
        sys.exit(1)

    with open(path) as f:
        data = json.load(f)

    # Handle both flat list and nested structure
    if isinstance(data, list):
        return data
    return data.get("participants", [])


def find_participant_by_id(participants: list[dict], participant_id: str) -> dict | None:
    """Find a participant by their ID."""
    for p in participants:
        if p.get("participant_id") == participant_id:
            return p
    return None


def get_random_participant(participants: list[dict], condition: str) -> dict | None:
    """Get a random non-failed participant from a condition."""
    candidates = [
        p for p in participants
        if p.get("condition") == condition and p.get("status") != "failed"
    ]
    if not candidates:
        return None
    return random.choice(candidates)


def print_header(participant: dict) -> None:
    """Print participant header info."""
    pid = participant.get("participant_id", "unknown")
    condition = participant.get("condition", "unknown")
    initial = participant.get("initial_choice", "N/A")
    final = participant.get("final_choice", "N/A")

    changed = ""
    if final != "N/A" and initial != final:
        changed = " (CHANGED)"

    print("=" * 65)
    print(f"Participant: {pid}")
    print(f"Condition: {condition}")
    print(f"Initial choice: {initial}")
    print(f"Final choice: {final}{changed}")
    print("=" * 65)


def print_transcript(transcript: list[dict], title: str) -> None:
    """Print a transcript with role labels."""
    print()
    print(f"─── {title} " + "─" * (50 - len(title)))
    print()

    for turn in transcript:
        role = turn.get("role", "unknown").capitalize()
        content = turn.get("content", "")
        print(f"[{role}]")
        print(content)
        print()


def main():
    parser = argparse.ArgumentParser(
        description="View conversation transcripts for a participant."
    )
    parser.add_argument("pilot_id", help="Pilot ID (output directory name)")
    parser.add_argument(
        "condition",
        nargs="?",
        choices=VALID_CONDITIONS,
        help="Condition to pick random participant from"
    )
    parser.add_argument(
        "--participant", "-p",
        help="Specific participant ID to view"
    )

    args = parser.parse_args()

    # Validate arguments
    if not args.condition and not args.participant:
        parser.error("Must provide either a condition or --participant")

    participants = load_participants(args.pilot_id)

    # Find the participant
    if args.participant:
        participant = find_participant_by_id(participants, args.participant)
        if not participant:
            print(f"Error: Participant '{args.participant}' not found", file=sys.stderr)
            sys.exit(1)
    else:
        participant = get_random_participant(participants, args.condition)
        if not participant:
            print(f"Error: No participants found for condition '{args.condition}'", file=sys.stderr)
            sys.exit(1)

    # Print header
    print_header(participant)

    # Print transcripts
    clarification = participant.get("clarification_transcript")
    adversarial = participant.get("adversarial_transcript")

    if not clarification and not adversarial:
        print()
        print("(No conversation transcripts for this participant)")
        print()
    else:
        if clarification:
            print_transcript(clarification, "CLARIFICATION DIALOGUE")
        if adversarial:
            print_transcript(adversarial, "ADVERSARIAL DIALOGUE")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Truenex Promoter — CLI entry point.

Usage:
    python -m truenex_promoter              # Check once and generate actions
    python -m truenex_promoter --loop       # Run continuously
    python -m truenex_promoter --status     # Show last GitHub check
    python -m truenex_promoter --queue      # Show pending actions
    python -m truenex_promoter --approve ID # Approve an action
    python -m truenex_promoter --reject ID  # Reject an action
"""

import argparse
import sys
import time

# Fix Windows encoding before anything else prints
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

from .action_queue import Action, ActionQueue, ActionStatus
from .awesome_finder import AwesomeFinder
from .config import PromoterConfig
from .content_generator import ContentGenerator
from .github_monitor import GitHubMonitor
from .hardware_analyzer import print_hardware_report
from .llm_adapter import LLMAdapter
from .notifier import Notifier


def main() -> None:
    parser = argparse.ArgumentParser(description="Truenex Promoter Agent")
    parser.add_argument("--loop", action="store_true", help="Run continuously every hour")
    parser.add_argument("--status", action="store_true", help="Show last GitHub check status")
    parser.add_argument("--queue", action="store_true", help="Show pending action queue")
    parser.add_argument("--approve", metavar="ID", help="Approve a pending action")
    parser.add_argument("--reject", metavar="ID", help="Reject a pending action")
    parser.add_argument("--reason", default="", help="Reason for approve/reject")
    parser.add_argument("--llm-check", action="store_true", help="Test LLM connectivity")
    parser.add_argument("--hardware", action="store_true", help="Analyze hardware and recommend LLM setup")
    args = parser.parse_args()

    config = PromoterConfig.from_env()
    config.ensure_dirs()

    queue = ActionQueue(state_dir=config.state_dir)
    notifier = Notifier(log_file=config.log_file)
    llm = LLMAdapter(config)

    # Handle hardware analysis
    if args.hardware:
        print_hardware_report()
        return

    # Handle LLM check
    if args.llm_check:
        if config.llm_provider == "none":
            print("LLM is disabled (provider=none). Set TRUENEX_PROMOTER_LLM_PROVIDER.")
            sys.exit(0)
        print(f"Provider: {config.llm_provider}")
        if hasattr(llm.backend, 'base_url'):
            print(f"Base URL: {llm.backend.base_url}")
            print(f"Model: {config.llm_model}")
        else:
            print(f"Model path: {llm.backend.model_path}")
            print(f"GPU layers: {llm.backend.n_gpu_layers}")
            print(f"Context: {llm.backend.n_ctx}")
        print("Checking connectivity...")
        if llm.is_available():
            print("LLM is reachable.")
            try:
                reply = llm.generate(
                    "You are a helpful assistant.",
                    "Say 'Truenex Promoter LLM check OK' and nothing else.",
                )
                print(f"Test response: {reply}")
            except Exception as e:
                print(f"Test generation failed: {e}")
                sys.exit(1)
        else:
            print("LLM is NOT reachable.")
            sys.exit(1)
        return

    # Handle queue management commands
    if args.approve:
        action = queue.approve(args.approve, args.reason)
        if action:
            notifier.info(f"Approved action {action.id}: {action.title}")
        else:
            print(f"Action {args.approve} not found.")
            sys.exit(1)
        return

    if args.reject:
        action = queue.reject(args.reject, args.reason)
        if action:
            notifier.info(f"Rejected action {action.id}: {action.title}")
        else:
            print(f"Action {args.reject} not found.")
            sys.exit(1)
        return

    if args.queue:
        pending = queue.list_actions(status=ActionStatus.PENDING)
        if not pending:
            print("No pending actions.")
            return
        print(f"\nPending actions ({len(pending)}):\n")
        for action in pending:
            print(f"  ID:       {action.id}")
            print(f"  Type:     {action.type}")
            print(f"  Title:    {action.title}")
            print(f"  Created:  {action.created_at}")
            print(f"  Target:   {action.target_url}")
            if action.description:
                print(f"  Desc:     {action.description[:200]}")
            print(f"  Approve:  trnx-promoter --approve {action.id}")
            print(f"  Reject:   trnx-promoter --reject {action.id}")
            print("-" * 50)
        return

    monitor = GitHubMonitor(
        owner=config.github_owner,
        repo=config.github_repo,
        token=config.github_token,
        state_dir=config.state_dir,
    )

    if args.status:
        state_file = config.state_dir / "github_state.json"
        if state_file.exists():
            import json
            state = json.loads(state_file.read_text(encoding="utf-8"))
            print(f"Last check: {state.get('checked_at', 'never')}")
            print(f"Stars: {state.get('stars', 0)}")
            print(f"Forks: {state.get('forks', 0)}")
            print(f"Open issues: {state.get('open_issues', 0)}")
            print(f"Latest release: {state.get('latest_release', 'none')}")
        else:
            print("No state found yet. Run a check first.")
        sys.exit(0)

    # Main loop
    notifier.info("Truenex Promoter started")
    notifier.info(f"Monitoring: {config.github_owner}/{config.github_repo}")

    while True:
        notifier.info("Checking GitHub...")
        try:
            events = monitor.check()
            generator = ContentGenerator(config, llm=llm)

            for event in events:
                notifier.event(
                    event.event_type,
                    event.title,
                    event.url,
                    event.description,
                )

                # Generate proactive actions from events
                if event.event_type == "star_milestone":
                    milestone = event.data.get("milestone", 0)
                    stars = event.data.get("stars", 0)
                    draft = generator.milestone_post(milestone, stars)
                    action = Action(
                        type="social_post",
                        title=f"Post about {stars} stars milestone",
                        description=f"Share the {milestone} star milestone on social media.",
                        draft_content=draft,
                        target_url=event.url,
                        data={"milestone": milestone, "stars": stars},
                    )
                    queue.add(action)
                    notifier.action_proposed(action.id, action.title, action.description)

                elif event.event_type == "new_release":
                    tag = event.data.get("tag", "")
                    draft = generator.release_post(tag, event.description)
                    action = Action(
                        type="social_post",
                        title=f"Announce release {tag}",
                        description=f"Share the new release {tag} on social media.",
                        draft_content=draft,
                        target_url=event.url,
                        data={"tag": tag},
                    )
                    queue.add(action)
                    notifier.action_proposed(action.id, action.title, action.description)

            # Proactive discovery: Awesome Lists
            if config.enable_awesome_finder:
                notifier.info("Searching for Awesome List opportunities...")
                finder = AwesomeFinder(config)
                candidates = finder.find_candidates()
                existing = {a.target_url for a in queue.list_actions()}
                for candidate in candidates[:5]:
                    url = candidate.get("url", "")
                    if url in existing:
                        continue
                    draft = finder.generate_draft(candidate)
                    action = Action(
                        type="awesome_pr",
                        title=f"Propose addition to {candidate.get('name', 'Awesome List')}",
                        description=f"Found via search: {candidate.get('query_matched', '')}",
                        draft_content=draft,
                        target_url=url,
                        data=candidate,
                    )
                    queue.add(action)
                    notifier.action_proposed(action.id, action.title, action.description)

            if not events and not candidates:
                notifier.info("No new events or opportunities")

        except Exception as e:
            notifier.info(f"ERROR during check: {e}")

        if not args.loop:
            break

        notifier.info(f"Sleeping {config.check_interval_minutes} minutes...")
        time.sleep(config.check_interval_minutes * 60)


if __name__ == "__main__":
    main()

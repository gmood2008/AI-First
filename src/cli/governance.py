"""
Governance Console CLI

Command-line interface for the Governance Console.
"""

import sys
import argparse
from pathlib import Path
from typing import Optional
import json

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

from governance import (
    SignalBus, LifecycleManager, HealthAuthority, GovernanceConsole,
    CapabilityState, ProposalStatus
)


def cmd_health_leaderboard(args):
    """Show health leaderboard"""
    signal_bus = SignalBus()
    lifecycle_manager = LifecycleManager(signal_bus)
    health_authority = HealthAuthority(signal_bus, lifecycle_manager)
    console = GovernanceConsole(signal_bus, lifecycle_manager, health_authority)
    
    leaderboard = console.get_health_leaderboard(
        limit=args.limit,
        window_hours=args.window_hours
    )
    
    print("=" * 80)
    print("📊 Health Leaderboard")
    print("=" * 80)
    print()
    
    if not leaderboard:
        print("No capabilities found.")
        return 0
    
    print(f"{'Capability ID':<40} {'State':<12} {'Health':<8} {'Reliability':<12} {'Intervention':<12}")
    print("-" * 80)
    
    for item in leaderboard:
        print(f"{item['capability_id']:<40} "
              f"{item['state']:<12} "
              f"{item['health_score']:>6.1f}  "
              f"{item['reliability_score']:>10.1f}%  "
              f"{item['human_intervention_rate']:>10.1f}%")
    
    return 0


def cmd_proposal_queue(args):
    """Show proposal queue"""
    signal_bus = SignalBus()
    lifecycle_manager = LifecycleManager(signal_bus)
    health_authority = HealthAuthority(signal_bus, lifecycle_manager)
    console = GovernanceConsole(signal_bus, lifecycle_manager, health_authority)
    
    proposals = console.get_proposal_queue()
    
    print("=" * 80)
    print("📋 Proposal Queue")
    print("=" * 80)
    print()
    
    if not proposals:
        print("No pending proposals.")
        return 0
    
    for proposal in proposals:
        print(f"Proposal ID: {proposal.proposal_id}")
        print(f"Capability: {proposal.capability_id}")
        print(f"Type: {proposal.proposal_type.value}")
        print(f"Reason: {proposal.reason}")
        print(f"Metrics: {json.dumps(proposal.trigger_metrics, indent=2)}")
        print(f"Created: {proposal.created_at.isoformat()}")
        print("-" * 80)
    
    return 0


def cmd_approve_proposal(args):
    """Approve a proposal"""
    signal_bus = SignalBus()
    lifecycle_manager = LifecycleManager(signal_bus)
    health_authority = HealthAuthority(signal_bus, lifecycle_manager)
    console = GovernanceConsole(signal_bus, lifecycle_manager, health_authority)
    
    try:
        console.approve_proposal(
            proposal_id=args.proposal_id,
            admin_id=args.admin_id or "cli_admin",
            reason=args.reason
        )
        print(f"✅ Proposal {args.proposal_id} approved")
        return 0
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        return 1


def cmd_reject_proposal(args):
    """Reject a proposal"""
    signal_bus = SignalBus()
    lifecycle_manager = LifecycleManager(signal_bus)
    health_authority = HealthAuthority(signal_bus, lifecycle_manager)
    console = GovernanceConsole(signal_bus, lifecycle_manager, health_authority)
    
    try:
        console.reject_proposal(
            proposal_id=args.proposal_id,
            admin_id=args.admin_id or "cli_admin",
            reason=args.reason
        )
        print(f"✅ Proposal {args.proposal_id} rejected")
        return 0
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        return 1


def cmd_freeze(args):
    """Freeze a capability"""
    signal_bus = SignalBus()
    lifecycle_manager = LifecycleManager(signal_bus)
    health_authority = HealthAuthority(signal_bus, lifecycle_manager)
    console = GovernanceConsole(signal_bus, lifecycle_manager, health_authority)
    
    try:
        console.freeze_capability(
            capability_id=args.capability_id,
            admin_id=args.admin_id or "cli_admin",
            reason=args.reason
        )
        print(f"✅ Capability {args.capability_id} frozen")
        return 0
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        return 1


def cmd_unfreeze(args):
    """Unfreeze a capability"""
    signal_bus = SignalBus()
    lifecycle_manager = LifecycleManager(signal_bus)
    health_authority = HealthAuthority(signal_bus, lifecycle_manager)
    console = GovernanceConsole(signal_bus, lifecycle_manager, health_authority)
    
    try:
        console.unfreeze_capability(
            capability_id=args.capability_id,
            admin_id=args.admin_id or "cli_admin",
            reason=args.reason
        )
        print(f"✅ Capability {args.capability_id} unfrozen")
        return 0
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        return 1


def cmd_signals(args):
    """Show signal stream"""
    signal_bus = SignalBus()
    lifecycle_manager = LifecycleManager(signal_bus)
    health_authority = HealthAuthority(signal_bus, lifecycle_manager)
    console = GovernanceConsole(signal_bus, lifecycle_manager, health_authority)
    
    signals = console.get_signal_stream(
        capability_id=args.capability_id,
        limit=args.limit
    )
    
    print("=" * 80)
    print("📡 Signal Stream")
    print("=" * 80)
    print()
    
    if not signals:
        print("No signals found.")
        return 0
    
    for signal in signals:
        print(f"[{signal['timestamp']}] {signal['signal_type']} - {signal['capability_id']}")
        if signal['metadata']:
            print(f"  Metadata: {json.dumps(signal['metadata'], indent=2)}")
        print()
    
    return 0


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(description="AI-First Governance Console CLI")
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # Health leaderboard
    leaderboard_parser = subparsers.add_parser("leaderboard", help="Show health leaderboard")
    leaderboard_parser.add_argument("--limit", type=int, default=20, help="Maximum results")
    leaderboard_parser.add_argument("--window-hours", type=int, default=24, help="Time window in hours")
    leaderboard_parser.set_defaults(func=cmd_health_leaderboard)
    
    # Proposal queue
    queue_parser = subparsers.add_parser("proposals", help="Show proposal queue")
    queue_parser.set_defaults(func=cmd_proposal_queue)
    
    # Approve proposal
    approve_parser = subparsers.add_parser("approve", help="Approve a proposal")
    approve_parser.add_argument("proposal_id", help="Proposal ID")
    approve_parser.add_argument("--reason", required=True, help="Reason for approval")
    approve_parser.add_argument("--admin-id", help="Admin ID")
    approve_parser.set_defaults(func=cmd_approve_proposal)
    
    # Reject proposal
    reject_parser = subparsers.add_parser("reject", help="Reject a proposal")
    reject_parser.add_argument("proposal_id", help="Proposal ID")
    reject_parser.add_argument("--reason", required=True, help="Reason for rejection")
    reject_parser.add_argument("--admin-id", help="Admin ID")
    reject_parser.set_defaults(func=cmd_reject_proposal)
    
    # Freeze
    freeze_parser = subparsers.add_parser("freeze", help="Freeze a capability")
    freeze_parser.add_argument("capability_id", help="Capability ID")
    freeze_parser.add_argument("--reason", required=True, help="Reason for freezing")
    freeze_parser.add_argument("--admin-id", help="Admin ID")
    freeze_parser.set_defaults(func=cmd_freeze)
    
    # Unfreeze
    unfreeze_parser = subparsers.add_parser("unfreeze", help="Unfreeze a capability")
    unfreeze_parser.add_argument("capability_id", help="Capability ID")
    unfreeze_parser.add_argument("--reason", required=True, help="Reason for unfreezing")
    unfreeze_parser.add_argument("--admin-id", help="Admin ID")
    unfreeze_parser.set_defaults(func=cmd_unfreeze)
    
    # Signals
    signals_parser = subparsers.add_parser("signals", help="Show signal stream")
    signals_parser.add_argument("--capability-id", help="Filter by capability ID")
    signals_parser.add_argument("--limit", type=int, default=100, help="Maximum signals")
    signals_parser.set_defaults(func=cmd_signals)
    
    args = parser.parse_args()
    
    if not hasattr(args, 'func'):
        parser.print_help()
        return 1
    
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())

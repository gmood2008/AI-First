#!/usr/bin/env python3
"""
AI-First Runtime CLI Tool

Main entry point for airun commands.
"""

import sys
import argparse


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="airun",
        description="AI-First Runtime CLI Tool",
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # audit command
    audit_parser = subparsers.add_parser("audit", help="Audit and compliance tools")
    audit_subparsers = audit_parser.add_subparsers(dest="audit_command")
    
    # audit export
    export_parser = audit_subparsers.add_parser("export", help="Export audit logs to HTML report")
    export_parser.add_argument("--db", help="Path to audit.db")
    export_parser.add_argument("--session", help="Filter by session ID")
    export_parser.add_argument("--user", help="Filter by user ID")
    export_parser.add_argument("--limit", type=int, default=1000, help="Maximum records")
    export_parser.add_argument("-o", "--output", default="audit_report.html", help="Output file")
    
    args = parser.parse_args()
    
    if args.command == "audit":
        if args.audit_command == "export":
            from .audit_export import main as audit_export_main
            # Pass args to audit_export
            sys.argv = [
                "audit_export",
                "--db", args.db or "",
                "--session", args.session or "",
                "--user", args.user or "",
                "--limit", str(args.limit),
                "--output", args.output,
            ]
            # Filter out empty args
            sys.argv = [a for a in sys.argv if a and not a.startswith("--") or "=" in a or sys.argv[sys.argv.index(a)-1].startswith("--")]
            audit_export_main()
        else:
            audit_parser.print_help()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

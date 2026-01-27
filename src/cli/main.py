"""
AI-First Runtime CLI - Command-line interface for testing and execution.

This provides a user-friendly CLI for interacting with the runtime.
"""

import json
import sys
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.syntax import Syntax

from runtime.types import ExecutionContext
from runtime.registry import CapabilityRegistry
from runtime.engine import RuntimeEngine
from runtime.undo.manager import UndoManager
from runtime.stdlib.loader import load_stdlib, get_stdlib_info

console = Console()


def confirmation_callback(message: str, params: dict) -> bool:
    """
    CLI confirmation callback.
    
    Shows confirmation message and waits for user input.
    """
    console.print(Panel(message, title="⚠️  Confirmation Required", border_style="yellow"))
    
    response = click.confirm("Proceed with this operation?", default=False)
    return response


@click.group()
@click.version_option(version="0.1.0")
def cli():
    """
    AI-First Runtime - Execute capability specs safely with undo support.
    
    This CLI allows you to execute capabilities, manage undo history,
    and inspect the runtime state.
    """
    pass


@cli.command()
@click.option(
    "--specs-dir",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    required=True,
    help="Directory containing capability YAML specs",
)
@click.option(
    "--workspace",
    type=click.Path(file_okay=False, path_type=Path),
    default=Path.cwd() / "workspace",
    help="Workspace directory for operations",
)
def init(specs_dir: Path, workspace: Path):
    """Initialize runtime and load capabilities"""
    console.print(Panel.fit(
        "🚀 AI-First Runtime Initialization",
        border_style="blue"
    ))
    
    # Create workspace
    workspace.mkdir(parents=True, exist_ok=True)
    console.print(f"✅ Workspace: {workspace}")
    
    # Create registry and load stdlib
    registry = CapabilityRegistry()
    loaded = load_stdlib(registry, specs_dir)
    
    if loaded == 0:
        console.print("❌ No capabilities loaded!", style="bold red")
        sys.exit(1)
    
    # Show summary
    info = get_stdlib_info()
    console.print(f"\n✅ Initialized with {info['total_capabilities']} capabilities")
    console.print(f"📦 Namespaces: {', '.join(info['namespaces'].keys())}")


@cli.command()
@click.option(
    "--specs-dir",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    required=True,
    help="Directory containing capability YAML specs",
)
@click.option(
    "--workspace",
    type=click.Path(file_okay=False, path_type=Path),
    default=Path.cwd() / "workspace",
    help="Workspace directory for operations",
)
@click.argument("capability_id")
@click.option(
    "--params",
    type=str,
    required=True,
    help="JSON string of parameters",
)
@click.option(
    "--no-confirm",
    is_flag=True,
    help="Skip confirmation prompts (dangerous!)",
)
def execute(
    specs_dir: Path,
    workspace: Path,
    capability_id: str,
    params: str,
    no_confirm: bool,
):
    """Execute a capability with given parameters"""
    
    # Parse parameters
    try:
        params_dict = json.loads(params)
    except json.JSONDecodeError as e:
        console.print(f"❌ Invalid JSON parameters: {e}", style="bold red")
        sys.exit(1)
    
    # Setup runtime
    workspace.mkdir(parents=True, exist_ok=True)
    registry = CapabilityRegistry()
    load_stdlib(registry, specs_dir)
    
    engine = RuntimeEngine(registry)
    undo_manager = UndoManager(workspace / ".ai-first" / "backups")
    
    # Create execution context
    context = ExecutionContext(
        user_id="cli_user",
        workspace_root=workspace,
        session_id="cli_session",
        confirmation_callback=None if no_confirm else confirmation_callback,
        undo_enabled=True,
    )
    
    # Execute
    console.print(f"\n🚀 Executing: {capability_id}")
    console.print(f"📝 Parameters:")
    console.print(Syntax(json.dumps(params_dict, indent=2), "json"))
    
    result = engine.execute(capability_id, params_dict, context)
    
    # Display result
    console.print("\n" + "=" * 70)
    if result.is_success():
        console.print("✅ Execution successful!", style="bold green")
        console.print(f"\n📤 Outputs:")
        console.print(Syntax(json.dumps(result.outputs, indent=2), "json"))
        
        if result.undo_available:
            console.print(f"\n↩️  Undo available")
    else:
        console.print(f"❌ Execution failed: {result.status.value}", style="bold red")
        if result.error_message:
            console.print(f"\n💬 Error: {result.error_message}")
    
    console.print(f"\n⏱️  Execution time: {result.execution_time_ms:.2f}ms")


@cli.command()
@click.option(
    "--specs-dir",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    required=True,
    help="Directory containing capability YAML specs",
)
@click.option(
    "--namespace",
    type=str,
    help="Filter by namespace (e.g., io.fs)",
)
def list_capabilities(specs_dir: Path, namespace: Optional[str]):
    """List all available capabilities"""
    
    registry = CapabilityRegistry()
    load_stdlib(registry, specs_dir)
    
    capabilities = registry.list_capability_info()
    
    if namespace:
        capabilities = [c for c in capabilities if c.id.startswith(namespace + ".")]
    
    # Create table
    table = Table(title=f"📚 Available Capabilities ({len(capabilities)})")
    table.add_column("ID", style="cyan")
    table.add_column("Description", style="white")
    table.add_column("Side Effects", style="yellow")
    table.add_column("Confirm", style="red")
    
    for cap in capabilities:
        table.add_row(
            cap.id,
            cap.description[:50] + "..." if len(cap.description) > 50 else cap.description,
            ", ".join(cap.side_effects),
            "✓" if cap.requires_confirmation else "",
        )
    
    console.print(table)


@cli.command()
@click.option(
    "--specs-dir",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    required=True,
    help="Directory containing capability YAML specs",
)
@click.argument("capability_id")
def inspect(specs_dir: Path, capability_id: str):
    """Inspect detailed information about a capability"""
    
    registry = CapabilityRegistry()
    load_stdlib(registry, specs_dir)
    
    try:
        spec = registry.get_spec(capability_id)
        
        # Display spec as YAML
        import yaml
        yaml_str = yaml.dump(spec, default_flow_style=False, sort_keys=False)
        
        console.print(Panel(
            Syntax(yaml_str, "yaml"),
            title=f"📋 Capability: {capability_id}",
            border_style="blue",
        ))
    
    except Exception as e:
        console.print(f"❌ Error: {e}", style="bold red")
        sys.exit(1)


@cli.command()
@click.option(
    "--workspace",
    type=click.Path(file_okay=False, path_type=Path),
    default=Path.cwd() / "workspace",
    help="Workspace directory",
)
@click.option(
    "--steps",
    type=int,
    default=1,
    help="Number of operations to undo",
)
def undo(workspace: Path, steps: int):
    """Undo last N operations"""
    
    undo_manager = UndoManager(workspace / ".ai-first" / "backups")
    
    if undo_manager.is_empty():
        console.print("ℹ️  No operations to undo", style="yellow")
        return
    
    try:
        undone = undo_manager.rollback(steps)
        
        console.print(f"✅ Undone {len(undone)} operation(s):", style="bold green")
        for desc in undone:
            console.print(f"  ↩️  {desc}")
    
    except Exception as e:
        console.print(f"❌ Undo failed: {e}", style="bold red")
        sys.exit(1)


@cli.command()
@click.option(
    "--workspace",
    type=click.Path(file_okay=False, path_type=Path),
    default=Path.cwd() / "workspace",
    help="Workspace directory",
)
@click.option(
    "--count",
    type=int,
    default=10,
    help="Number of recent operations to show",
)
def history(workspace: Path, count: int):
    """View undo history"""
    
    undo_manager = UndoManager(workspace / ".ai-first" / "backups")
    
    if undo_manager.is_empty():
        console.print("ℹ️  No operations in history", style="yellow")
        return
    
    recent = undo_manager.peek(count)
    
    # Create table
    table = Table(title=f"📜 Recent Operations ({len(recent)})")
    table.add_column("#", style="cyan")
    table.add_column("Capability", style="white")
    table.add_column("Description", style="yellow")
    table.add_column("Timestamp", style="green")
    
    for i, op in enumerate(reversed(recent), 1):
        table.add_row(
            str(i),
            op["capability_id"],
            op["description"],
            op["timestamp"],
        )
    
    console.print(table)


def main():
    """Entry point for CLI"""
    cli()


if __name__ == "__main__":
    main()

@cli.command()
def dashboard():
    """
    Launch the interactive TUI dashboard.
    
    Monitor and control workflows in real-time with a terminal UI.
    """
    try:
        from .dashboard import run_dashboard
        run_dashboard()
    except ImportError as e:
        console.print("[red]Error: Textual not installed. Install with: pip install textual[/red]")
        console.print(f"[dim]{e}[/dim]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Dashboard error: {e}[/red]")
        sys.exit(1)


@cli.group()
def workflow():
    """
    Workflow management commands.
    
    Submit, start, pause, resume, and rollback workflows.
    """
    pass


@workflow.command("list")
def workflow_list():
    """List all workflows."""
    import sqlite3
    from rich.table import Table
    
    try:
        conn = sqlite3.connect("audit.db")
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT workflow_id, name, status, owner, started_at
            FROM workflows
            ORDER BY started_at DESC
            LIMIT 20
        """)
        
        table = Table(title="Workflows")
        table.add_column("ID", style="cyan")
        table.add_column("Name", style="green")
        table.add_column("Status", style="yellow")
        table.add_column("Owner", style="blue")
        table.add_column("Started", style="magenta")
        
        for row in cursor.fetchall():
            workflow_id, name, status, owner, started_at = row
            table.add_row(
                workflow_id[:8],
                name,
                status,
                owner,
                started_at or "N/A"
            )
        
        console.print(table)
        conn.close()
        
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


@workflow.command("resume")
@click.argument("workflow_id")
@click.option("--decision", type=click.Choice(["approve", "reject"]), required=True, help="Approval decision")
@click.option("--approver", default="cli_user", help="Name of approver")
def workflow_resume(workflow_id: str, decision: str, approver: str):
    """
    Resume a PAUSED workflow with approval decision.
    
    WORKFLOW_ID: The workflow identifier (full or prefix)
    """
    try:
        # Import workflow engine
        from src.runtime.workflow.engine import WorkflowEngine
        from src.runtime.workflow.persistence import WorkflowPersistence
        from src.runtime.workflow.human_approval import HumanApprovalManager
        
        # Initialize engine
        persistence = WorkflowPersistence()
        approval_manager = HumanApprovalManager()
        engine = WorkflowEngine(
            persistence=persistence,
            approval_manager=approval_manager
        )
        
        # Find workflow by prefix
        import sqlite3
        conn = sqlite3.connect("audit.db")
        cursor = conn.cursor()
        cursor.execute("SELECT workflow_id FROM workflows WHERE workflow_id LIKE ?", (f"{workflow_id}%",))
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            console.print(f"[red]Workflow not found: {workflow_id}[/red]")
            sys.exit(1)
        
        full_workflow_id = result[0]
        
        # Resume workflow
        console.print(f"[yellow]Resuming workflow {full_workflow_id} with decision: {decision}[/yellow]")
        engine.resume_workflow(full_workflow_id, decision, approver)
        
        console.print(f"[green]✓ Workflow {decision}d successfully[/green]")
        
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        import traceback
        console.print(f"[dim]{traceback.format_exc()}[/dim]")
        sys.exit(1)

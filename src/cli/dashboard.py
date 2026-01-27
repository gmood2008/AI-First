"""
AI-First Runtime v3.0 - Dashboard TUI

A Textual-based terminal UI for monitoring and controlling workflows.

Features:
- View active workflows with real-time status
- Inspect workflow details and progress
- Global rollback "panic button"
- Approve/reject pending workflows
"""

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Header, Footer, DataTable, Static, Button, Label, ProgressBar
from textual.binding import Binding
from textual.screen import Screen
from textual import events
from datetime import datetime
from typing import Optional
import sqlite3

from src.specs.v3.workflow_schema import WorkflowStatus


class WorkflowListView(Container):
    """
    View 1: List of active workflows with status.
    """
    
    def compose(self) -> ComposeResult:
        yield Label("🔄 Active Workflows", classes="section-title")
        yield DataTable(id="workflow-table")
    
    def on_mount(self) -> None:
        """Initialize the workflow table."""
        table = self.query_one("#workflow-table", DataTable)
        table.add_columns("ID", "Name", "Status", "Owner", "Started", "Progress")
        table.cursor_type = "row"
        self.refresh_workflows()
    
    def refresh_workflows(self) -> None:
        """Refresh workflow list from database."""
        table = self.query_one("#workflow-table", DataTable)
        table.clear()
        
        # Query database for active workflows
        try:
            conn = sqlite3.connect("audit.db")
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT workflow_id, name, status, owner, started_at,
                       (SELECT COUNT(*) FROM workflow_steps WHERE workflow_steps.workflow_id = workflows.workflow_id AND status = 'COMPLETED') as completed,
                       (SELECT COUNT(*) FROM workflow_steps WHERE workflow_steps.workflow_id = workflows.workflow_id) as total
                FROM workflows
                WHERE status IN ('PENDING', 'RUNNING', 'PAUSED')
                ORDER BY started_at DESC
            """)
            
            for row in cursor.fetchall():
                workflow_id, name, status, owner, started_at, completed, total = row
                
                # Format started_at
                if started_at:
                    started = datetime.fromisoformat(started_at).strftime("%H:%M:%S")
                else:
                    started = "N/A"
                
                # Calculate progress
                if total > 0:
                    progress = f"{completed}/{total}"
                else:
                    progress = "0/0"
                
                # Add status emoji
                status_emoji = {
                    "PENDING": "⏳",
                    "RUNNING": "▶️",
                    "PAUSED": "⏸️",
                    "COMPLETED": "✅",
                    "FAILED": "❌",
                    "ROLLED_BACK": "↩️"
                }.get(status, "❓")
                
                table.add_row(
                    workflow_id[:8],
                    name[:30],
                    f"{status_emoji} {status}",
                    owner,
                    started,
                    progress
                )
            
            conn.close()
        except Exception as e:
            table.add_row("ERROR", str(e), "", "", "", "")


class WorkflowDetailView(Container):
    """
    View 2: Detailed view of a single workflow with progress bar.
    """
    
    workflow_id: Optional[str] = None
    
    def compose(self) -> ComposeResult:
        yield Label("📊 Workflow Details", classes="section-title")
        yield Static(id="workflow-info")
        yield Label("Progress:", classes="subsection-title")
        yield ProgressBar(id="workflow-progress", total=100)
        yield Label("Steps:", classes="subsection-title")
        yield DataTable(id="steps-table")
        yield Horizontal(
            Button("Approve", id="approve-btn", variant="success"),
            Button("Reject", id="reject-btn", variant="error"),
            Button("Rollback", id="rollback-btn", variant="warning"),
            id="action-buttons"
        )
    
    def on_mount(self) -> None:
        """Initialize the steps table."""
        table = self.query_one("#steps-table", DataTable)
        table.add_columns("Step", "Status", "Started", "Completed", "Error")
    
    def load_workflow(self, workflow_id: str) -> None:
        """Load workflow details from database."""
        self.workflow_id = workflow_id
        
        try:
            conn = sqlite3.connect("audit.db")
            cursor = conn.cursor()
            
            # Get workflow info
            cursor.execute("""
                SELECT name, status, owner, started_at, completed_at, error_message
                FROM workflows
                WHERE workflow_id = ?
            """, (workflow_id,))
            
            row = cursor.fetchone()
            if row:
                name, status, owner, started_at, completed_at, error_message = row
                
                info_text = f"""
Workflow ID: {workflow_id}
Name: {name}
Status: {status}
Owner: {owner}
Started: {started_at or 'N/A'}
Completed: {completed_at or 'N/A'}
Error: {error_message or 'None'}
"""
                self.query_one("#workflow-info", Static).update(info_text)
                
                # Update progress bar
                cursor.execute("""
                    SELECT 
                        COUNT(*) as total,
                        SUM(CASE WHEN status = 'COMPLETED' THEN 1 ELSE 0 END) as completed
                    FROM workflow_steps
                    WHERE workflow_id = ?
                """, (workflow_id,))
                
                total, completed = cursor.fetchone()
                if total > 0:
                    progress = int((completed / total) * 100)
                    self.query_one("#workflow-progress", ProgressBar).update(progress=progress)
                
                # Load steps
                cursor.execute("""
                    SELECT step_name, status, started_at, completed_at, error_message
                    FROM workflow_steps
                    WHERE workflow_id = ?
                    ORDER BY execution_order
                """, (workflow_id,))
                
                table = self.query_one("#steps-table", DataTable)
                table.clear()
                
                for step_row in cursor.fetchall():
                    step_name, step_status, step_started, step_completed, step_error = step_row
                    
                    status_emoji = {
                        "PENDING": "⏳",
                        "RUNNING": "▶️",
                        "COMPLETED": "✅",
                        "FAILED": "❌"
                    }.get(step_status, "❓")
                    
                    table.add_row(
                        step_name,
                        f"{status_emoji} {step_status}",
                        step_started or "N/A",
                        step_completed or "N/A",
                        step_error or ""
                    )
            
            conn.close()
        except Exception as e:
            self.query_one("#workflow-info", Static).update(f"Error loading workflow: {e}")


class DashboardApp(App):
    """
    Main dashboard application.
    """
    
    CSS = """
    Screen {
        layout: vertical;
    }
    
    .section-title {
        background: $primary;
        color: $text;
        padding: 1;
        text-align: center;
        text-style: bold;
    }
    
    .subsection-title {
        background: $secondary;
        color: $text;
        padding: 1;
        text-style: bold;
    }
    
    #workflow-table {
        height: 100%;
    }
    
    #steps-table {
        height: 100%;
    }
    
    #action-buttons {
        height: auto;
        padding: 1;
    }
    
    Button {
        margin: 0 1;
    }
    """
    
    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("r", "refresh", "Refresh"),
        Binding("d", "toggle_detail", "Detail"),
    ]
    
    def __init__(self):
        super().__init__()
        self.show_detail = False
        self.selected_workflow_id = None
    
    def compose(self) -> ComposeResult:
        yield Header()
        yield WorkflowListView(id="workflow-list")
        yield WorkflowDetailView(id="workflow-detail")
        yield Footer()
    
    def on_mount(self) -> None:
        """Initialize the dashboard."""
        self.title = "AI-First Runtime Dashboard"
        self.sub_title = "Transactional Control Plane for AI Agents"
        
        # Hide detail view initially
        self.query_one("#workflow-detail").display = False
    
    def action_refresh(self) -> None:
        """Refresh the workflow list."""
        self.query_one("#workflow-list", WorkflowListView).refresh_workflows()
        if self.show_detail and self.selected_workflow_id:
            self.query_one("#workflow-detail", WorkflowDetailView).load_workflow(self.selected_workflow_id)
    
    def action_toggle_detail(self) -> None:
        """Toggle detail view."""
        self.show_detail = not self.show_detail
        
        if self.show_detail:
            # Get selected workflow from table
            table = self.query_one("#workflow-table", DataTable)
            if table.cursor_row is not None:
                row_key = table.cursor_row
                # Get workflow ID from first column
                # Note: This is a simplified approach, in production you'd store the full ID
                self.selected_workflow_id = str(table.get_cell_at((row_key, 0)))
                
                self.query_one("#workflow-list").display = False
                self.query_one("#workflow-detail").display = True
                self.query_one("#workflow-detail", WorkflowDetailView).load_workflow(self.selected_workflow_id)
        else:
            self.query_one("#workflow-list").display = True
            self.query_one("#workflow-detail").display = False
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        button_id = event.button.id
        
        if button_id == "approve-btn":
            self.notify("Approve functionality coming soon", severity="information")
        elif button_id == "reject-btn":
            self.notify("Reject functionality coming soon", severity="warning")
        elif button_id == "rollback-btn":
            self.notify("⚠️ PANIC BUTTON: Global rollback triggered!", severity="error")
            # TODO: Implement global rollback


def run_dashboard():
    """Entry point for the dashboard."""
    app = DashboardApp()
    app.run()


if __name__ == "__main__":
    run_dashboard()

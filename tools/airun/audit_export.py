"""
Audit Export Command for AI-First Runtime v2.0

Generates HTML compliance reports from audit database.
"""

import sys
import os
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from runtime.audit import AuditLogger


class AuditReportGenerator:
    """
    Generates HTML compliance reports from audit logs.
    """
    
    def __init__(self, audit_logger: AuditLogger):
        """
        Initialize report generator.
        
        Args:
            audit_logger: AuditLogger instance
        """
        self.audit_logger = audit_logger
    
    def generate_html_report(
        self,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        limit: int = 1000,
    ) -> str:
        """
        Generate HTML compliance report.
        
        Args:
            session_id: Filter by session (optional)
            user_id: Filter by user (optional)
            limit: Maximum number of records
        
        Returns:
            HTML string
        """
        # Query audit logs
        records = self.audit_logger.query(
            session_id=session_id,
            user_id=user_id,
            limit=limit,
        )
        
        # Get session summary if filtering by session
        summary = None
        if session_id:
            summary = self.audit_logger.get_session_summary(session_id)
        
        # Generate HTML
        html = self._generate_html(records, summary, session_id, user_id)
        
        return html
    
    def _generate_html(
        self,
        records: List[Dict[str, Any]],
        summary: Optional[Dict[str, Any]],
        session_id: Optional[str],
        user_id: Optional[str],
    ) -> str:
        """Generate HTML report."""
        
        # Header
        html = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI-First Runtime - Compliance Report</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: #f5f5f5;
            padding: 20px;
            color: #333;
        }
        
        .container {
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            overflow: hidden;
        }
        
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
        }
        
        .header h1 {
            font-size: 28px;
            margin-bottom: 10px;
        }
        
        .header p {
            opacity: 0.9;
            font-size: 14px;
        }
        
        .summary {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            padding: 30px;
            background: #f9f9f9;
            border-bottom: 1px solid #e0e0e0;
        }
        
        .summary-card {
            background: white;
            padding: 20px;
            border-radius: 6px;
            border-left: 4px solid #667eea;
        }
        
        .summary-card h3 {
            font-size: 12px;
            text-transform: uppercase;
            color: #999;
            margin-bottom: 8px;
            font-weight: 600;
        }
        
        .summary-card p {
            font-size: 24px;
            font-weight: 700;
            color: #333;
        }
        
        .filters {
            padding: 20px 30px;
            background: #fff9e6;
            border-bottom: 1px solid #e0e0e0;
        }
        
        .filters p {
            font-size: 14px;
            color: #666;
        }
        
        .filters strong {
            color: #333;
        }
        
        .table-container {
            padding: 30px;
            overflow-x: auto;
        }
        
        table {
            width: 100%;
            border-collapse: collapse;
            font-size: 13px;
        }
        
        thead {
            background: #f5f5f5;
        }
        
        th {
            text-align: left;
            padding: 12px;
            font-weight: 600;
            color: #666;
            border-bottom: 2px solid #e0e0e0;
        }
        
        td {
            padding: 12px;
            border-bottom: 1px solid #f0f0f0;
            vertical-align: top;
        }
        
        tr:hover {
            background: #fafafa;
        }
        
        .status-badge {
            display: inline-block;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 11px;
            font-weight: 600;
            text-transform: uppercase;
        }
        
        .status-success {
            background: #d4edda;
            color: #155724;
        }
        
        .status-failure {
            background: #f8d7da;
            color: #721c24;
        }
        
        .status-denied {
            background: #fff3cd;
            color: #856404;
        }
        
        .side-effects {
            font-size: 11px;
            color: #666;
            font-family: 'Courier New', monospace;
        }
        
        .timestamp {
            font-size: 11px;
            color: #999;
        }
        
        .capability {
            font-family: 'Courier New', monospace;
            font-size: 12px;
            color: #667eea;
        }
        
        .undo-badge {
            background: #ffeaa7;
            color: #d63031;
            padding: 2px 6px;
            border-radius: 3px;
            font-size: 10px;
            font-weight: 600;
        }
        
        .footer {
            padding: 20px 30px;
            background: #f5f5f5;
            text-align: center;
            font-size: 12px;
            color: #999;
        }
        
        .no-data {
            padding: 60px 30px;
            text-align: center;
            color: #999;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔒 AI-First Runtime - Compliance Report</h1>
            <p>Enterprise-grade audit trail for AI agent operations</p>
        </div>
"""
        
        # Summary section
        if summary:
            html += f"""
        <div class="summary">
            <div class="summary-card">
                <h3>Total Actions</h3>
                <p>{summary['total_actions']}</p>
            </div>
            <div class="summary-card">
                <h3>Successful</h3>
                <p style="color: #28a745;">{summary['success_count']}</p>
            </div>
            <div class="summary-card">
                <h3>Failed</h3>
                <p style="color: #dc3545;">{summary['failure_count']}</p>
            </div>
            <div class="summary-card">
                <h3>Denied</h3>
                <p style="color: #ffc107;">{summary['denied_count']}</p>
            </div>
            <div class="summary-card">
                <h3>Undone</h3>
                <p style="color: #fd7e14;">{summary['undone_count']}</p>
            </div>
            <div class="summary-card">
                <h3>Session Duration</h3>
                <p style="font-size: 14px;">{self._format_duration(summary['start_time'], summary['end_time'])}</p>
            </div>
        </div>
"""
        
        # Filters section
        if session_id or user_id:
            html += """
        <div class="filters">
            <p><strong>🔍 Active Filters:</strong> """
            
            if session_id:
                html += f"Session: <strong>{session_id}</strong> "
            if user_id:
                html += f"User: <strong>{user_id}</strong>"
            
            html += "</p>\n        </div>\n"
        
        # Table section
        if records:
            html += """
        <div class="table-container">
            <table>
                <thead>
                    <tr>
                        <th>Timestamp</th>
                        <th>User</th>
                        <th>Capability</th>
                        <th>Status</th>
                        <th>Side Effects</th>
                        <th>Duration</th>
                        <th>Flags</th>
                    </tr>
                </thead>
                <tbody>
"""
            
            for record in records:
                status_class = f"status-{record['status']}"
                
                html += f"""
                    <tr>
                        <td class="timestamp">{self._format_timestamp(record['timestamp'])}</td>
                        <td>{record['user_id']}</td>
                        <td class="capability">{record['capability_id']}</td>
                        <td><span class="status-badge {status_class}">{record['status']}</span></td>
                        <td class="side-effects">{record['side_effects'] or '-'}</td>
                        <td>{record['duration_ms'] or '-'} ms</td>
                        <td>
"""
                
                if record['was_undone']:
                    html += '<span class="undo-badge">UNDONE</span> '
                if record['undo_available']:
                    html += '↩️ '
                if record['requires_confirmation']:
                    html += '⚠️ '
                
                html += """
                        </td>
                    </tr>
"""
            
            html += """
                </tbody>
            </table>
        </div>
"""
        else:
            html += """
        <div class="no-data">
            <p>📭 No audit records found matching the specified criteria.</p>
        </div>
"""
        
        # Footer
        html += f"""
        <div class="footer">
            <p>Generated by AI-First Runtime v2.0 | {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
            <p>This report contains {len(records)} audit records</p>
        </div>
    </div>
</body>
</html>
"""
        
        return html
    
    def _format_timestamp(self, timestamp: str) -> str:
        """Format ISO timestamp to readable format."""
        try:
            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            return dt.strftime('%Y-%m-%d %H:%M:%S')
        except:
            return timestamp
    
    def _format_duration(self, start: str, end: str) -> str:
        """Format duration between two timestamps."""
        try:
            start_dt = datetime.fromisoformat(start.replace('Z', '+00:00'))
            end_dt = datetime.fromisoformat(end.replace('Z', '+00:00'))
            duration = end_dt - start_dt
            
            seconds = int(duration.total_seconds())
            if seconds < 60:
                return f"{seconds}s"
            elif seconds < 3600:
                return f"{seconds // 60}m {seconds % 60}s"
            else:
                hours = seconds // 3600
                minutes = (seconds % 3600) // 60
                return f"{hours}h {minutes}m"
        except:
            return "N/A"


def main():
    """Main CLI entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Export AI-First Runtime audit logs to HTML report"
    )
    parser.add_argument(
        "--db",
        default=None,
        help="Path to audit.db (default: ~/.ai-first/audit.db)"
    )
    parser.add_argument(
        "--session",
        default=None,
        help="Filter by session ID"
    )
    parser.add_argument(
        "--user",
        default=None,
        help="Filter by user ID"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=1000,
        help="Maximum number of records (default: 1000)"
    )
    parser.add_argument(
        "--output",
        "-o",
        default="audit_report.html",
        help="Output file path (default: audit_report.html)"
    )
    
    args = parser.parse_args()
    
    # Initialize audit logger
    audit_logger = AuditLogger(args.db)
    
    # Generate report
    generator = AuditReportGenerator(audit_logger)
    html = generator.generate_html_report(
        session_id=args.session,
        user_id=args.user,
        limit=args.limit,
    )
    
    # Write to file
    output_path = Path(args.output)
    output_path.write_text(html, encoding='utf-8')
    
    print(f"✅ Compliance report generated: {output_path.absolute()}")
    print(f"📊 Records included: {len(audit_logger.query(session_id=args.session, user_id=args.user, limit=args.limit))}")


if __name__ == "__main__":
    main()

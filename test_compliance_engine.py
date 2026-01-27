"""
Test Compliance Engine (Audit Logging)

This script tests the audit logging functionality by:
1. Creating sample actions
2. Logging them to audit.db
3. Querying the audit log
4. Generating an HTML report
"""

import sys
from pathlib import Path
import os
import time

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from runtime.audit import AuditLogger
from tools.airun.audit_export import AuditReportGenerator


def test_compliance_engine():
    """Test the compliance engine end-to-end."""
    
    print("=" * 80)
    print(" AI-First Runtime v2.0 - Compliance Engine Test")
    print("=" * 80)
    print()
    
    # Setup
    test_db = "/tmp/test_audit.db"
    if os.path.exists(test_db):
        os.remove(test_db)
    
    audit_logger = AuditLogger(test_db)
    
    print("✅ AuditLogger initialized")
    print(f"   Database: {test_db}")
    print()
    
    # Test 1: Log sample actions
    print("[TEST 1] Logging sample actions...")
    
    session_id = "test_session_001"
    user_id = "test_user"
    
    # Action 1: Successful file write
    audit_logger.log_action(
        session_id=session_id,
        user_id=user_id,
        capability_id="io.fs.write_file",
        action_type="execute",
        params={"path": "/tmp/test.txt", "content": "Hello World"},
        result={"bytes_written": 11},
        status="success",
        side_effects=["filesystem_write"],
        requires_confirmation=True,
        was_confirmed=True,
        undo_available=True,
        duration_ms=15,
    )
    
    # Action 2: Successful network request
    audit_logger.log_action(
        session_id=session_id,
        user_id=user_id,
        capability_id="tools.slack.send_message",
        action_type="execute",
        params={"channel": "#general", "message": "Test", "token": "xoxb-secret-token"},
        result={"ok": True, "ts": "1234567890.123456"},
        status="success",
        side_effects=["network_write"],
        requires_confirmation=True,
        was_confirmed=True,
        undo_available=True,
        duration_ms=234,
    )
    
    # Action 3: Failed operation
    audit_logger.log_action(
        session_id=session_id,
        user_id=user_id,
        capability_id="io.fs.delete_file",
        action_type="execute",
        params={"path": "/nonexistent/file.txt"},
        result={},
        status="failure",
        side_effects=["filesystem_write"],
        requires_confirmation=True,
        was_confirmed=True,
        undo_available=False,
        error_message="File not found",
        duration_ms=5,
    )
    
    # Action 4: Denied operation
    audit_logger.log_action(
        session_id=session_id,
        user_id=user_id,
        capability_id="sys.execute_command",
        action_type="execute",
        params={"command": "rm -rf /"},
        result={},
        status="denied",
        side_effects=["system_modification"],
        requires_confirmation=True,
        was_confirmed=False,
        undo_available=False,
        duration_ms=2,
    )
    
    # Action 5: Read-only operation
    audit_logger.log_action(
        session_id=session_id,
        user_id=user_id,
        capability_id="io.fs.read_file",
        action_type="execute",
        params={"path": "/tmp/test.txt"},
        result={"content": "Hello World", "bytes_read": 11},
        status="success",
        side_effects=["filesystem_read"],
        requires_confirmation=False,
        was_confirmed=None,
        undo_available=False,
        duration_ms=8,
    )
    
    # Wait for async writes to complete
    time.sleep(0.5)
    
    print("✅ 5 sample actions logged")
    print()
    
    # Test 2: Query audit log
    print("[TEST 2] Querying audit log...")
    
    records = audit_logger.query(session_id=session_id, limit=100)
    print(f"✅ Retrieved {len(records)} records")
    print()
    
    for i, record in enumerate(records, 1):
        print(f"   {i}. {record['capability_id']} - {record['status']} ({record['duration_ms']}ms)")
        if record['side_effects']:
            print(f"      Side effects: {record['side_effects']}")
        if 'token' in str(record['params_json']):
            print(f"      ⚠️  Contains sensitive data (should be redacted)")
    
    print()
    
    # Test 3: Session summary
    print("[TEST 3] Session summary...")
    
    summary = audit_logger.get_session_summary(session_id)
    print(f"✅ Session summary:")
    print(f"   Total actions: {summary['total_actions']}")
    print(f"   Success: {summary['success_count']}")
    print(f"   Failure: {summary['failure_count']}")
    print(f"   Denied: {summary['denied_count']}")
    print(f"   Undone: {summary['undone_count']}")
    print()
    
    # Test 4: Generate HTML report
    print("[TEST 4] Generating HTML report...")
    
    generator = AuditReportGenerator(audit_logger)
    html = generator.generate_html_report(session_id=session_id)
    
    report_path = Path("/tmp/test_audit_report.html")
    report_path.write_text(html, encoding='utf-8')
    
    print(f"✅ HTML report generated: {report_path}")
    print(f"   Size: {len(html)} bytes")
    print()
    
    # Test 5: Verify data sanitization
    print("[TEST 5] Verifying data sanitization...")
    
    # Check if token was redacted
    slack_record = [r for r in records if r['capability_id'] == 'tools.slack.send_message'][0]
    params = slack_record['params_json']
    
    if '***REDACTED***' in params:
        print("✅ Sensitive data (token) was redacted")
    else:
        print("❌ ERROR: Sensitive data was NOT redacted!")
        print(f"   Params: {params}")
    
    print()
    
    # Cleanup
    audit_logger.shutdown()
    
    print("=" * 80)
    print(" Test Complete!")
    print("=" * 80)
    print()
    print(f"📊 View the report: file://{report_path.absolute()}")
    print()


if __name__ == "__main__":
    test_compliance_engine()

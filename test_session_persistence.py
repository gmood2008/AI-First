#!/usr/bin/env python3
"""
Test Session Persistence.

This script tests the SQLite-based session persistence functionality.
"""

import sys
import tempfile
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from runtime.session.persistence import SessionPersistence, PersistedUndoRecord


def test_create_session():
    """Test session creation"""
    print("=" * 70)
    print("TEST 1: Session Creation")
    print("=" * 70)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        persistence = SessionPersistence(db_path)
        
        session_id = "test_session_001"
        persistence.create_session(session_id, {"type": "test"})
        
        info = persistence.get_session_info(session_id)
        print(f"\n📝 Session created: {session_id}")
        print(f"   Created at: {info['created_at']}")
        print(f"   Undo count: {info['undo_count']}")
        
        assert info is not None
        assert info["session_id"] == session_id
        assert info["undo_count"] == 0
        
        print("\n✅ TEST 1 PASSED")
        return True


def test_save_and_load_undo_records():
    """Test saving and loading undo records"""
    print("\n" + "=" * 70)
    print("TEST 2: Save and Load Undo Records")
    print("=" * 70)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        persistence = SessionPersistence(db_path)
        
        session_id = "test_session_002"
        persistence.create_session(session_id)
        
        # Save some undo records
        records = [
            PersistedUndoRecord(
                session_id=session_id,
                operation_id=f"op_{i}",
                capability_id="io.fs.write_file",
                timestamp=datetime.now().isoformat(),
                undo_function="restore_file_from_backup",
                undo_args={"backup_path": f"/tmp/backup_{i}.txt"},
                description=f"Write file operation {i}"
            )
            for i in range(3)
        ]
        
        for record in records:
            persistence.save_undo_record(record)
        
        print(f"\n📝 Saved {len(records)} undo records")
        
        # Load them back
        loaded = persistence.load_undo_history(session_id)
        
        print(f"📥 Loaded {len(loaded)} undo records")
        for i, record in enumerate(loaded):
            print(f"   {i+1}. {record.capability_id} - {record.description}")
        
        assert len(loaded) == 3
        assert loaded[0].operation_id == "op_0"
        assert loaded[2].operation_id == "op_2"
        
        print("\n✅ TEST 2 PASSED")
        return True


def test_pop_undo_records():
    """Test popping undo records"""
    print("\n" + "=" * 70)
    print("TEST 3: Pop Undo Records")
    print("=" * 70)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        persistence = SessionPersistence(db_path)
        
        session_id = "test_session_003"
        persistence.create_session(session_id)
        
        # Save 5 records
        for i in range(5):
            record = PersistedUndoRecord(
                session_id=session_id,
                operation_id=f"op_{i}",
                capability_id="io.fs.write_file",
                timestamp=datetime.now().isoformat(),
                undo_function="restore_file_from_backup",
                undo_args={"backup_path": f"/tmp/backup_{i}.txt"},
                description=f"Operation {i}"
            )
            persistence.save_undo_record(record)
        
        print(f"\n📝 Saved 5 undo records")
        print(f"   Count: {persistence.get_undo_count(session_id)}")
        
        # Pop 2 records
        popped = persistence.pop_undo_records(session_id, 2)
        
        print(f"\n↩️  Popped {len(popped)} records:")
        for record in popped:
            print(f"   - {record.operation_id}: {record.description}")
        
        # Check remaining
        remaining = persistence.get_undo_count(session_id)
        print(f"\n📊 Remaining: {remaining} records")
        
        assert len(popped) == 2
        assert popped[0].operation_id == "op_4"  # Most recent
        assert popped[1].operation_id == "op_3"
        assert remaining == 3
        
        print("\n✅ TEST 3 PASSED")
        return True


def test_session_isolation():
    """Test that sessions are properly isolated"""
    print("\n" + "=" * 70)
    print("TEST 4: Session Isolation")
    print("=" * 70)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        persistence = SessionPersistence(db_path)
        
        # Create two sessions
        session_a = "session_a"
        session_b = "session_b"
        
        persistence.create_session(session_a)
        persistence.create_session(session_b)
        
        # Add records to session A
        for i in range(3):
            record = PersistedUndoRecord(
                session_id=session_a,
                operation_id=f"a_op_{i}",
                capability_id="io.fs.write_file",
                timestamp=datetime.now().isoformat(),
                undo_function="restore_file_from_backup",
                undo_args={},
                description=f"Session A operation {i}"
            )
            persistence.save_undo_record(record)
        
        # Add records to session B
        for i in range(2):
            record = PersistedUndoRecord(
                session_id=session_b,
                operation_id=f"b_op_{i}",
                capability_id="io.fs.delete",
                timestamp=datetime.now().isoformat(),
                undo_function="restore_deleted_file",
                undo_args={},
                description=f"Session B operation {i}"
            )
            persistence.save_undo_record(record)
        
        print(f"\n📝 Session A: {persistence.get_undo_count(session_a)} records")
        print(f"📝 Session B: {persistence.get_undo_count(session_b)} records")
        
        # Verify isolation
        a_records = persistence.load_undo_history(session_a)
        b_records = persistence.load_undo_history(session_b)
        
        print(f"\n✅ Session A records:")
        for record in a_records:
            print(f"   - {record.operation_id}")
        
        print(f"\n✅ Session B records:")
        for record in b_records:
            print(f"   - {record.operation_id}")
        
        assert len(a_records) == 3
        assert len(b_records) == 2
        assert all(r.session_id == session_a for r in a_records)
        assert all(r.session_id == session_b for r in b_records)
        
        print("\n✅ TEST 4 PASSED")
        return True


def test_cleanup_old_sessions():
    """Test cleanup of old sessions"""
    print("\n" + "=" * 70)
    print("TEST 5: Cleanup Old Sessions")
    print("=" * 70)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        persistence = SessionPersistence(db_path)
        
        # Create a session
        session_id = "old_session"
        persistence.create_session(session_id)
        
        # Add a record
        record = PersistedUndoRecord(
            session_id=session_id,
            operation_id="op_1",
            capability_id="io.fs.write_file",
            timestamp=datetime.now().isoformat(),
            undo_function="restore_file_from_backup",
            undo_args={},
            description="Test operation"
        )
        persistence.save_undo_record(record)
        
        print(f"\n📝 Created session: {session_id}")
        print(f"   Undo count: {persistence.get_undo_count(session_id)}")
        
        # Cleanup (with 0 days, should remove all)
        removed = persistence.cleanup_old_sessions(max_age_days=0)
        
        print(f"\n🧹 Cleaned up {removed} old sessions")
        
        # Verify session is gone
        info = persistence.get_session_info(session_id)
        assert info is None
        
        print("\n✅ TEST 5 PASSED")
        return True


def main():
    """Run all tests"""
    print("\n🚀 AI-First Session Persistence Tests")
    print("=" * 70)
    
    tests = [
        test_create_session,
        test_save_and_load_undo_records,
        test_pop_undo_records,
        test_session_isolation,
        test_cleanup_old_sessions,
    ]
    
    passed = 0
    failed = 0
    
    for test_func in tests:
        try:
            if test_func():
                passed += 1
        except Exception as e:
            print(f"\n❌ TEST FAILED: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print("\n" + "=" * 70)
    print(f"📊 RESULTS: {passed} passed, {failed} failed")
    print("=" * 70)
    
    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

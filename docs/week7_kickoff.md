# AI-First Runtime v3.0 - Week 7 Kickoff

**Operation:** Fusion (Deep Integration)  
**Date:** 2025-01-24  
**Status:** Ready to Start

---

## 🎯 Week 7 Mission

**Goal:** Fuse the Brain (Policy Engine), the Law (Registry Schema), and the Body (Workflow Engine) into a cohesive system.

**Philosophy:** Control over Intelligence, Transactions over Speed

---

## 📋 Week 7 Objectives

### Priority 1: The Registry API (The Source of Truth) 🔴

**Goal:** Make the Registry queryable by the Workflow Engine

**Tasks:**
1. Update `CapabilityRegistry` to store and return `CapabilitySpec` (v3)
2. Implement `registry.get(capability_id) -> CapabilitySpec`
3. Migrate all stdlib handlers to register with v3 Spec format

**Current State:**
- ✅ `CapabilitySpec` v3 exists in `src/specs/v3/capability_schema.py`
- ✅ Risk Consistency Check implemented (3 rules)
- ❌ `CapabilityRegistry` still uses `spec_dict` (old format)
- ❌ Stdlib handlers use old registration format

**Files to Modify:**
- `src/runtime/registry.py` - Add `register_capability(spec: CapabilitySpec)` and `get(capability_id) -> CapabilitySpec`
- `src/runtime/stdlib/loader.py` - Update to use new registration format
- `src/runtime/stdlib/fs_handlers.py` - Migrate to v3 specs
- `src/runtime/stdlib/net_handlers.py` - Migrate to v3 specs
- `src/runtime/stdlib/data_handlers.py` - Migrate to v3 specs
- `src/runtime/stdlib/sys_handlers.py` - Migrate to v3 specs

---

### Priority 2: Deep Integration (Workflow → Registry → Policy) 🔴

**Goal:** The Workflow Engine fetches Risk Data from Registry and feeds it to Policy Engine

**Architectural Constraint (MANDATORY):**

```
Unidirectional Dependency: WorkflowEngine → Registry
Registry knows NOTHING about Runtime
```

**Implementation Pattern:**

```python
# In WorkflowEngine._execute_step():

# 1. Fetch capability metadata from Registry
cap_spec = self.registry.get(step.capability_id)

# 2. Extract risk level
risk_level = cap_spec.risk.level if cap_spec else RiskLevel.HIGH  # Default HIGH

# 3. Create PolicyContext with explicit injection
policy_ctx = PolicyContext(
    principal=self.principal,
    workflow_id=context.workflow_id,
    step_name=step.name,
    capability_id=step.capability_id,
    risk_level=risk_level,  # ← Explicit Injection
    inputs=step.inputs
)

# 4. Evaluate policy
decision = self.policy_engine.evaluate(policy_ctx)

# 5. Enforce decision
if decision == PolicyDecision.DENY:
    # Fail workflow + rollback
    pass
elif decision == PolicyDecision.REQUIRE_APPROVAL:
    # Pause workflow + send webhook
    pass
else:
    # Continue execution
    pass
```

**Files to Modify:**
- `src/runtime/workflow/engine.py` - Add Registry query in `_execute_step()`
- `src/runtime/workflow/engine.py` - Inject `risk_level` into `PolicyContext`

**Current State:**
- ✅ `PolicyEngine` already integrated (Week 5)
- ✅ `PolicyContext` has `risk_level` field
- ❌ `WorkflowEngine` doesn't query Registry
- ❌ `risk_level` is not injected from Registry

---

### Priority 3: The Grand Unified Test (System Acceptance) 🔴

**Goal:** Prove the system works as a whole

**Test Scenario:**
1. Register a capability with `risk: HIGH`
2. Define a Policy: `when: {risk_level: HIGH} -> decision: DENY`
3. Run Workflow → Fails immediately (before execution)
4. Verify: Original state preserved (rollback not needed, step never ran)

**Current State:**
- ✅ Test designed in `tests/v3/test_grand_unified_integration.py`
- ❌ Import errors blocking test execution
- ❌ `WorkflowStatus` import location unknown
- ❌ `ExecutionContext` import location unknown

**Files to Fix:**
- `tests/v3/test_grand_unified_integration.py` - Fix imports
- Possibly add missing types to `src/runtime/types.py`

**Definition of Done for Week 7:**
```
✅ Grand Unified Test PASSED
```

---

### Priority 4: Database Infrastructure (The Fortification) 🟡

**Goal:** Solve DB locking/flakiness once and for all

**Tasks:**
1. Implement `DatabaseConnectionManager` with singleton pool or thread-local storage
2. Ensure tests use isolated, in-memory SQLite instances or unique temp files
3. Rewrite `conftest.py` for proper test isolation

**Current State:**
- ❌ Tests share same database (`~/.ai-first/audit.db`)
- ❌ Database locking errors in concurrent tests
- ❌ Flaky tests due to shared state

**Files to Create/Modify:**
- `src/runtime/workflow/db_manager.py` - New `DatabaseConnectionManager`
- `src/runtime/workflow/persistence.py` - Use `DatabaseConnectionManager`
- `tests/conftest.py` - Rewrite for isolated databases

---

## 🧪 Acceptance Criteria

| Criterion | Target | Current | Status |
|-----------|--------|---------|--------|
| Grand Unified Test | PASSED | Import errors | ❌ |
| Stdlib Migration | 100% | 0% | ❌ |
| Coverage | > 50% | 41% | ❌ |
| No Flaky Tests | 0 flaky | Some flaky | ❌ |

---

## 📊 Current State Summary

### What Works ✅

1. **Capability Schema v3** (Week 6)
   - Risk Consistency Check (3 rules)
   - Helper functions
   - 15/15 tests passing

2. **Policy Engine** (Week 5)
   - RBAC enforcement
   - First Match Wins
   - 17/17 tests passing

3. **Workflow Engine** (Week 3)
   - Transactional execution
   - Crash recovery
   - Human-in-the-Loop

### What's Missing ❌

1. **Registry API**
   - No `CapabilitySpec` v3 support
   - No `get(capability_id)` method
   - Still uses `spec_dict`

2. **Deep Integration**
   - WorkflowEngine doesn't query Registry
   - Risk Level not injected into PolicyContext
   - Manual plumbing required

3. **Stdlib Migration**
   - All handlers use old format
   - No Risk metadata
   - No Compensation metadata

4. **Database Infrastructure**
   - Shared database state
   - Locking issues
   - Flaky tests

---

## 🗺️ Implementation Roadmap

### Phase 1: Registry API (Day 1-2)

```
1. Add CapabilitySpec storage to Registry
2. Implement register_capability(spec: CapabilitySpec)
3. Implement get(capability_id) -> CapabilitySpec
4. Add tests for new API
```

### Phase 2: Stdlib Migration (Day 2-3)

```
1. Create v3 specs for io.fs.* capabilities
2. Create v3 specs for io.net.* capabilities
3. Update loader.py to use new format
4. Verify Risk Consistency Check for all capabilities
```

### Phase 3: Deep Integration (Day 3-4)

```
1. Modify WorkflowEngine._execute_step()
2. Add Registry query before policy check
3. Inject risk_level into PolicyContext
4. Add integration tests
```

### Phase 4: Grand Unified Test (Day 4-5)

```
1. Fix import errors
2. Run test end-to-end
3. Debug and fix issues
4. Verify PASSED status
```

### Phase 5: Database Infrastructure (Day 5-6)

```
1. Implement DatabaseConnectionManager
2. Update persistence.py
3. Rewrite conftest.py
4. Fix flaky tests
```

### Phase 6: Documentation & Delivery (Day 6-7)

```
1. Update ARCHITECTURE.md
2. Create INTEGRATION_GUIDE.md
3. Write Week 7 Status Report
4. Tag release (if ready)
```

---

## 🔧 Key Files Reference

### Core Files to Modify

```
src/runtime/registry.py                    # Priority 1
src/runtime/workflow/engine.py             # Priority 2
src/runtime/stdlib/loader.py               # Priority 1
src/runtime/stdlib/fs_handlers.py          # Priority 1
tests/v3/test_grand_unified_integration.py # Priority 3
tests/conftest.py                          # Priority 4
```

### Schema Files (Reference)

```
src/specs/v3/capability_schema.py          # CapabilitySpec v3
src/specs/v3/workflow_schema.py            # WorkflowSpec
src/runtime/workflow/policy_engine_v2.py   # PolicyEngine
```

---

## 📝 Quick Start Commands

### Run Tests

```bash
# Run all tests
cd /home/ubuntu/ai-first-runtime
python -m pytest tests/v3/ -v

# Run specific test
python -m pytest tests/v3/test_grand_unified_integration.py -v -s

# Run with coverage
python -m pytest tests/v3/ --cov=src/runtime --cov-report=term-missing
```

### Check Current State

```bash
# Check git status
git status

# Check recent commits
git log --oneline -10

# Check test coverage
python -m pytest tests/v3/ --cov=src/runtime --cov-report=term
```

### Useful Greps

```bash
# Find all CapabilityRegistry usages
grep -r "CapabilityRegistry" src/

# Find all PolicyEngine usages
grep -r "PolicyEngine" src/

# Find all WorkflowEngine usages
grep -r "WorkflowEngine" src/
```

---

## 🎓 Architectural Principles to Follow

### Principle #9: Gatekeeper, not Commander

**PolicyEngine only says YES or NO. It NEVER modifies inputs.**

### Principle #12: No Magic, Only Mechanism

**Explicit is better than implicit. No hidden dependencies.**

### Unidirectional Dependency

```
WorkflowEngine → Registry → CapabilitySpec
       ↓
   PolicyEngine
```

**Registry knows NOTHING about Runtime or Workflow.**

---

## 🚀 Let's Begin!

**First Task:** Update `CapabilityRegistry` to support `CapabilitySpec` v3

**Command to start:**
```bash
cd /home/ubuntu/ai-first-runtime
# Read current registry.py
cat src/runtime/registry.py
```

**Expected Outcome:**
```python
class CapabilityRegistry:
    def register_capability(self, spec: CapabilitySpec) -> None:
        """Register a capability using v3 CapabilitySpec"""
        # Validate with Risk Consistency Check
        # Store in self._capabilities
        pass
    
    def get(self, capability_id: str) -> Optional[CapabilitySpec]:
        """Get capability spec by ID"""
        return self._capabilities.get(capability_id)
```

---

**Ready to Fuse the System. Let's Go! 🚀**

**Built with ❤️ for the AI agent revolution** 🤖

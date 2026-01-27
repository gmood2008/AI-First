# Contributing to AI-First Runtime

Thank you for your interest in contributing to AI-First Runtime! This document provides guidelines for contributing to the project.

---

## 📜 The Constitution

**Before contributing, you MUST read and understand the [13 Non-Negotiable Principles](docs/v3/PRINCIPLES.md).**

These principles are the foundation of AI-First Runtime and are **binding on all development**. Every contribution must align with these principles.

**Key Principles:**
- **Principle #1:** The Runtime is a Control Plane, Not a Planner
- **Principle #2:** Workflow is the Transaction Boundary
- **Principle #3:** All Side-Effects Must Be Compensable
- **Principle #9:** The Gatekeeper, Not the Commander
- **Principle #12:** No Magic, Only Mechanisms

**If your contribution violates a principle, it will be rejected.**

---

## Getting Started

### 1. Fork and Clone

```bash
git clone https://github.com/YOUR_USERNAME/ai-first-runtime.git
cd ai-first-runtime
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
pip install -e .
```

### 3. Run Tests

```bash
pytest tests/
```

---

## Development Workflow

### 1. Create a Branch

```bash
git checkout -b feature/your-feature-name
```

### 2. Make Changes

- Write code
- Add tests
- Update documentation

### 3. Run Tests

```bash
pytest tests/ --cov=src/runtime --cov-report=term-missing
```

**Requirement:** Test coverage must not decrease.

### 4. Commit

```bash
git add .
git commit -m "feat: Add your feature description"
```

**Commit Message Format:**
- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation changes
- `test:` - Test changes
- `refactor:` - Code refactoring
- `chore:` - Build/tooling changes

### 5. Push and Create PR

```bash
git push origin feature/your-feature-name
```

Then create a Pull Request on GitHub.

---

## Code Review Checklist

**Before submitting a PR, ensure:**

### Principle Compliance
- [ ] Does this change align with the 13 Principles?
- [ ] Does it violate any principle? (If yes, document why)
- [ ] Have you read [PRINCIPLES.md](docs/v3/PRINCIPLES.md)?

### Code Quality
- [ ] All tests pass
- [ ] Test coverage does not decrease
- [ ] Code is formatted with `autopep8`
- [ ] No pylint errors

### Documentation
- [ ] Public APIs are documented
- [ ] README updated (if needed)
- [ ] ARCHITECTURE.md updated (if needed)

### Testing
- [ ] Unit tests added for new code
- [ ] Integration tests added (if needed)
- [ ] Edge cases tested

### Audit Trail
- [ ] All operations are logged
- [ ] State changes persisted to database
- [ ] Error messages are clear

---

## Contribution Guidelines

### What We Accept

✅ **Bug Fixes**
- Fix existing bugs
- Improve error handling
- Add missing tests

✅ **New Capabilities**
- Add new stdlib capabilities (filesystem, network, cloud, etc.)
- Must have compensation strategy
- Must be atomic and idempotent

✅ **Documentation**
- Improve existing docs
- Add examples
- Fix typos

✅ **Tests**
- Add missing tests
- Improve test coverage
- Add integration tests

✅ **Performance**
- Optimize existing code
- Reduce memory usage
- Improve database queries

### What We Reject

❌ **"Smart" Features**
- Auto-planning or agent reasoning
- PolicyEngine modifying inputs
- Implicit behavior without explicit configuration

❌ **Side Effects Without Compensation**
- Capabilities without undo strategy
- Operations without rollback

❌ **Principle Violations**
- Any code that violates the 13 Principles
- "Magic" behavior (implicit state changes)

❌ **Breaking Changes**
- Changes that break existing APIs
- Changes that break existing workflows

---

## Specific Contribution Areas

### 1. Adding a New Capability

**Example:** Add `cloud.s3.upload_file`

**Requirements:**
1. Implement handler in `src/runtime/stdlib/cloud_handlers.py`
2. Define spec in `src/specs/stdlib/cloud.yaml`
3. Implement compensation (e.g., `cloud.s3.delete_file`)
4. Add unit tests
5. Add integration tests
6. Document in WORKFLOW_GUIDE.md

**Template:**

```python
def handle_s3_upload_file(inputs: Dict[str, Any], context: ExecutionContext) -> ExecutionResult:
    """Upload file to S3"""
    bucket = inputs["bucket"]
    key = inputs["key"]
    file_path = inputs["file_path"]
    
    # Upload file
    s3_client.upload_file(file_path, bucket, key)
    
    # Capture undo closure
    def undo():
        s3_client.delete_object(Bucket=bucket, Key=key)
    
    return ExecutionResult(
        success=True,
        outputs={"s3_url": f"s3://{bucket}/{key}"},
        undo_closure=undo
    )
```

**Spec:**

```yaml
- name: cloud.s3.upload_file
  description: Upload file to S3
  inputs:
    - name: bucket
      type: string
      required: true
    - name: key
      type: string
      required: true
    - name: file_path
      type: string
      required: true
  outputs:
    - name: s3_url
      type: string
  risk_level: MEDIUM
  compensation:
    capability: cloud.s3.delete_file
    inputs:
      bucket: "{{bucket}}"
      key: "{{key}}"
```

### 2. Improving Test Coverage

**Focus Areas:**
- `src/runtime/workflow/recovery.py` (currently 25%)
- `src/runtime/workflow/policy_engine.py` (not yet implemented)
- `src/runtime/undo/manager.py` (currently 22%)

**Guidelines:**
- Write unit tests for individual functions
- Write integration tests for end-to-end workflows
- Test edge cases (crash, rollback, approval rejection)

### 3. Documentation

**Focus Areas:**
- Add more examples to WORKFLOW_GUIDE.md
- Improve ARCHITECTURE.md with diagrams
- Add troubleshooting guide
- Add FAQ

---

## Testing Guidelines

### Unit Tests

**Location:** `tests/unit/`

**Example:**

```python
def test_workflow_engine_submit():
    engine = WorkflowEngine(...)
    spec = WorkflowSpec(...)
    workflow_id = engine.submit_workflow(spec)
    assert workflow_id is not None
```

### Integration Tests

**Location:** `tests/v3/`

**Example:**

```python
def test_crash_recovery_acceptance_criteria():
    # 1. Start workflow
    # 2. Simulate crash
    # 3. Restart and resume
    # 4. Verify completion
    pass
```

### Test Naming

- `test_<function_name>_<scenario>` - Unit tests
- `test_<feature>_<scenario>` - Integration tests

### Test Coverage

**Target:** > 80% for all modules

**Current:**
- persistence.py: 82% ✅
- human_approval.py: 81% ✅
- engine.py: 62%
- Overall: 37%

---

## Code Style

### Python Style

- Follow PEP 8
- Use `autopep8` for formatting
- Max line length: 100 characters
- Use type hints

### Naming Conventions

- Classes: `PascalCase`
- Functions: `snake_case`
- Constants: `UPPER_SNAKE_CASE`
- Private: `_leading_underscore`

### Documentation

- All public APIs must have docstrings
- Use Google-style docstrings

**Example:**

```python
def execute_workflow(workflow_id: str) -> None:
    """Execute a workflow by ID.
    
    Args:
        workflow_id: The unique identifier of the workflow
        
    Raises:
        WorkflowNotFoundError: If workflow does not exist
        PermissionDeniedError: If user lacks permission
    """
    pass
```

---

## Building Handlers

See [HANDLER_DEVELOPER_GUIDE.md](docs/HANDLER_DEVELOPER_GUIDE.md) for detailed instructions on building handlers with undo support.

---

## Questions?

- **GitHub Issues:** https://github.com/gmood2008/ai-first-runtime/issues
- **Email:** gmood2008@gmail.com
- **Documentation:** https://github.com/gmood2008/ai-first-runtime/tree/master/docs

---

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

**Thank you for contributing to AI-First Runtime!** 🚀

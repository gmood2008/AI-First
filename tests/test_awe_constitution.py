from runtime.workflow.awe.constitution import ConstitutionEngine, ConstitutionViolation


def test_constitution_lenient_allows_by_default() -> None:
    ce = ConstitutionEngine(mode="lenient")
    ce.enforce(capability_id="io.fs.write_file", side_effects=["filesystem_write"])


def test_constitution_strict_denies_filesystem_write() -> None:
    ce = ConstitutionEngine(mode="strict")

    try:
        ce.enforce(capability_id="io.fs.write_file", side_effects=["filesystem_write"])
        assert False, "expected ConstitutionViolation"
    except ConstitutionViolation as e:
        assert "filesystem_write" in str(e)

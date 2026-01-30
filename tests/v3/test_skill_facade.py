"""
Skill Facade Spec v1.0 与 SkillFacadeRegistry 验证测试。

运行（项目根目录）:
  pip install -e ".[dev]"
  pytest tests/v3/test_skill_facade.py -v
"""

import tempfile
import pytest
from pathlib import Path

# 项目根（tests/v3 -> tests -> 根）
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


@pytest.fixture
def facades_dir():
    """specs/facades 目录；若不存在则跳过."""
    d = PROJECT_ROOT / "specs" / "facades"
    if not d.exists():
        pytest.skip("specs/facades not found (run from project root)")
    return d


@pytest.fixture
def temp_db():
    """临时 DB 路径，避免污染默认 registry."""
    with tempfile.TemporaryDirectory() as tmp:
        yield Path(tmp) / "skill_facade_test.db"


def test_skill_facade_spec_from_yaml(facades_dir):
    """SkillFacadeSpec 可从 YAML 加载."""
    from src.specs.skill_facade import SkillFacadeSpec

    pdf_yaml = facades_dir / "pdf.yaml"
    if not pdf_yaml.exists():
        pytest.skip("specs/facades/pdf.yaml not found")
    spec = SkillFacadeSpec.from_yaml(pdf_yaml.read_text(encoding="utf-8"))
    assert spec.name == "pdf"
    assert spec.version == "1.0.0"
    assert spec.routes.primary.type.value == "workflow"
    assert spec.routes.primary.ref == "financial_report"


def test_register_and_activate_facade(facades_dir, temp_db):
    """Facade 可注册并激活."""
    from src.runtime.registry.skill_facade_registry import (
        SkillFacadeRegistry,
        FacadeState,
    )
    from src.runtime.facade_loader import load_facades_from_directory

    registry = SkillFacadeRegistry(db_path=temp_db)
    n = load_facades_from_directory(
        registry, facades_dir, activate=True, registered_by="test"
    )
    assert n >= 1
    active = registry.list_facades(state=FacadeState.ACTIVE)
    assert len(active) >= 1


def test_get_facade_by_trigger(facades_dir, temp_db):
    """get_facade_by_trigger('分析财报') 可命中."""
    from src.runtime.registry.skill_facade_registry import (
        SkillFacadeRegistry,
        FacadeState,
    )
    from src.runtime.facade_loader import load_facades_from_directory

    registry = SkillFacadeRegistry(db_path=temp_db)
    load_facades_from_directory(registry, facades_dir, activate=True, registered_by="test")
    facade = registry.get_facade_by_trigger("分析财报")
    assert facade is not None
    assert facade.name in ("financial-analyst", "pdf")


def test_resolve_nl(facades_dir, temp_db):
    """resolve_nl('extract tables from pdf', facade_registry) 命中并返回路由."""
    from src.runtime.registry.skill_facade_registry import (
        SkillFacadeRegistry,
        FacadeState,
    )
    from src.runtime.facade_loader import load_facades_from_directory
    from src.runtime.facade_router import resolve_nl

    registry = SkillFacadeRegistry(db_path=temp_db)
    load_facades_from_directory(registry, facades_dir, activate=True, registered_by="test")
    route = resolve_nl("extract tables from pdf", registry)
    assert route is not None
    assert route.route_type in ("workflow", "pack")
    assert route.ref
    assert route.facade.name == "pdf"

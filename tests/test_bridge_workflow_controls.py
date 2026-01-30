import json
from pathlib import Path

from click.testing import CliRunner

from src.cli.main import cli


def _invoke(runner: CliRunner, args: list[str]) -> tuple[int, dict]:
    res = runner.invoke(cli, args)
    assert res.output.strip(), res
    last_line = ""
    for line in res.output.splitlines():
        if line.strip():
            last_line = line
    payload = json.loads(last_line)
    return res.exit_code, payload


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def test_bridge_workflow_pause_and_resume(tmp_path: Path) -> None:
    runner = CliRunner()
    workspace = tmp_path / "ws"
    spec_path = _repo_root() / "packs" / "aegis-demo" / "aegis_financial_summary_ppt.yaml"

    code, payload = _invoke(
        runner,
        [
            "bridge",
            "exec-workflow",
            "--execution-id",
            "exec-demo-002",
            "--trace-id",
            "trace-demo-002",
            "--user-id",
            "user-demo",
            "--workflow-spec-path",
            str(spec_path),
            "--workspace",
            str(workspace),
            "--enable-governance-hooks",
            "--governance-decisions-json",
            '{"pre_step":{"write_ppt_artifact":"PAUSE"}}',
        ],
    )

    assert code == 30
    assert payload["status"] == "paused"
    workflow_execution_id = payload["workflowExecutionId"]
    assert isinstance(workflow_execution_id, str) and workflow_execution_id

    code2, payload2 = _invoke(
        runner,
        [
            "bridge",
            "workflow-resume",
            "--execution-id",
            "exec-demo-002-resume",
            "--trace-id",
            "trace-demo-002-resume",
            "--user-id",
            "user-demo",
            "--workflow-execution-id",
            workflow_execution_id,
            "--decision",
            "approve",
            "--workspace",
            str(workspace),
        ],
    )

    assert code2 == 0
    assert payload2["status"] == "success"


def test_bridge_workflow_cancel(tmp_path: Path) -> None:
    runner = CliRunner()
    workspace = tmp_path / "ws"
    spec_path = _repo_root() / "packs" / "aegis-demo" / "aegis_financial_summary_ppt.yaml"

    code, payload = _invoke(
        runner,
        [
            "bridge",
            "exec-workflow",
            "--execution-id",
            "exec-demo-003",
            "--trace-id",
            "trace-demo-003",
            "--user-id",
            "user-demo",
            "--workflow-spec-path",
            str(spec_path),
            "--workspace",
            str(workspace),
            "--enable-governance-hooks",
            "--governance-decisions-json",
            '{"pre_step":{"write_ppt_artifact":"PAUSE"}}',
        ],
    )

    assert code == 30
    workflow_execution_id = payload["workflowExecutionId"]

    code2, payload2 = _invoke(
        runner,
        [
            "bridge",
            "workflow-cancel",
            "--execution-id",
            "exec-demo-003-cancel",
            "--trace-id",
            "trace-demo-003-cancel",
            "--user-id",
            "user-demo",
            "--workflow-execution-id",
            workflow_execution_id,
            "--reason",
            "Cancelled by test",
            "--workspace",
            str(workspace),
        ],
    )

    assert payload2["status"] == "failure"
    assert payload2["workflow"]["status"] == "failed"
    assert code2 != 0

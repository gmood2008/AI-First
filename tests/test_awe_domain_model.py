from runtime.workflow.awe import Workflow


def test_awe_domain_model_preserves_metadata_and_extra_fields() -> None:
    raw = {
        "workflow_id": "wf.demo",
        "version": "2.1.0",
        "title": "Demo AWE Workflow",
        "metadata": {"tenant": "acme", "schema_ext": {"x": 1}},
        "custom_root_ext": {"root": True},
        "tasks": [
            {
                "task_id": "t1",
                "kind": "action",
                "title": "Fetch",
                "capability_id": "net.http.get",
                "inputs": {"url": "http://example.com"},
                "metadata": {"trace": "abc"},
                "custom_task_ext": [1, 2, 3],
                "sub_tasks": [
                    {
                        "task_id": "t1.1",
                        "kind": "action",
                        "capability_id": "data.json.parse",
                        "inputs": {"json_string": "{}"},
                        "metadata": {"nested": True},
                        "custom_nested_ext": {"k": "v"},
                    }
                ],
            }
        ],
        "links": [
            {
                "source": "t1",
                "target": "t1.1",
                "kind": "contains",
                "metadata": {"edge": 1},
                "custom_link_ext": "ok",
            }
        ],
    }

    wf = Workflow.from_dict(raw)
    dumped = wf.to_dict()

    assert dumped["metadata"]["tenant"] == "acme"
    assert dumped["custom_root_ext"]["root"] is True

    assert dumped["tasks"][0]["metadata"]["trace"] == "abc"
    assert dumped["tasks"][0]["custom_task_ext"] == [1, 2, 3]

    assert dumped["tasks"][0]["sub_tasks"][0]["metadata"]["nested"] is True
    assert dumped["tasks"][0]["sub_tasks"][0]["custom_nested_ext"]["k"] == "v"

    assert dumped["links"][0]["metadata"]["edge"] == 1
    assert dumped["links"][0]["custom_link_ext"] == "ok"


def test_awe_domain_model_emits_json_schema() -> None:
    schema = Workflow.json_schema()
    assert schema["title"] == "Workflow"
    assert "properties" in schema
    assert "tasks" in schema["properties"]
    assert "links" in schema["properties"]

from pathlib import Path


def test_required_operational_artifacts_exist():
    root = Path(__file__).parents[1]
    required = [
        ".env.example", "docker-compose.yaml", "docker-compose.override.yml",
        "deploy.sh", "run_cycle.sh", "k8s/cronjob.yaml",
        "agency-orchestrator/app.py", "agency-orchestrator/config/lead-mapping.yaml",
    ]
    assert all((root / item).exists() for item in required)


def test_outreach_policy_is_safe_by_default():
    env = (Path(__file__).parents[1] / ".env.example").read_text()
    mapping = (Path(__file__).parents[1] / "agency-orchestrator/config/lead-mapping.yaml").read_text()
    assert "OUTREACH_MODE=inbox_only" in env
    assert "max_outreach_retries: 3" in mapping
    assert "opted_out" in mapping
    assert "do_not_contact" in mapping

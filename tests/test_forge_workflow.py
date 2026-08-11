from __future__ import annotations

import importlib.util
import os
import signal
import sys
from pathlib import Path
from types import ModuleType


def load_module() -> ModuleType:
    path = Path(__file__).parents[1] / "scripts/forge_workflow.py"
    spec = importlib.util.spec_from_file_location("forge_workflow", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def workflow(module: ModuleType, command: list[str], timeout: float = 2.0) -> object:
    return module.Workflow(tuple(command), timeout, "test")


def test_success_is_development_pass_not_conformance_pass() -> None:
    module = load_module()
    result = module.run_workflow(
        "success",
        workflow(module, [sys.executable, "-c", "print('ok')"]),
    )
    assert result["status"] == "PASS"
    assert result["conformance_status"] == "UNKNOWN"
    assert result["outcome"] == "completed"
    assert result["witnesses"][0]["command"][0] == sys.executable
    assert result["witnesses"][0]["output_references"]["stdout"]["identity"].startswith("sha256:")


def test_failure_is_distinct() -> None:
    module = load_module()
    result = module.run_workflow(
        "failure",
        workflow(module, [sys.executable, "-c", "raise SystemExit(7)"]),
    )
    assert result["status"] == "FAIL"
    assert result["outcome"] == "failed"
    assert result["exit_code"] == 7


def test_timeout_is_unknown() -> None:
    module = load_module()
    result = module.run_workflow(
        "timeout",
        workflow(module, [sys.executable, "-c", "import time; time.sleep(5)"], 0.05),
    )
    assert result["status"] == "UNKNOWN"
    assert result["outcome"] == "timeout"


def test_crash_is_unknown() -> None:
    module = load_module()
    result = module.run_workflow(
        "crash",
        workflow(
            module,
            [
                sys.executable,
                "-c",
                f"import os; os.kill(os.getpid(), {signal.SIGKILL})",
            ],
        ),
    )
    assert result["status"] == "UNKNOWN"
    assert result["outcome"] == "crash"


def test_missing_executable_is_unsupported_unknown() -> None:
    module = load_module()
    result = module.run_workflow(
        "missing",
        workflow(module, ["definitely-not-a-real-mncs-command"]),
    )
    assert result["status"] == "UNKNOWN"
    assert result["outcome"] == "unsupported"


def test_output_limit_is_unknown() -> None:
    module = load_module()
    result = module.run_workflow(
        "output",
        workflow(module, [sys.executable, "-c", "print('x' * 10000)"]),
        output_cap=100,
    )
    assert result["status"] == "UNKNOWN"
    assert result["outcome"] == "output_limit"


def test_environment_values_are_not_disclosed() -> None:
    module = load_module()
    os.environ["LANG"] = "forge-test-language"
    result = module.run_workflow(
        "environment",
        workflow(module, [sys.executable, "-c", "print('ok')"]),
    )
    assert "LANG" in result["environment"]["allowlisted_keys"]
    assert "forge-test-language" not in str(result["environment"])

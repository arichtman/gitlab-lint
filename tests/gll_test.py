from gitlab_lint.gll import resolve_exit_code


def test_resolve_exit_code_success():
    # results from default linting api
    data = {"status": "valid", "errors": [], "warnings": []}
    assert resolve_exit_code(data) == 0

    # results from project-specific api
    data = {"valid": True, "errors": [], "warnings": []}
    assert resolve_exit_code(data) == 0


def test_resolve_exit_code_failure():
    # results from default linting api
    data = {
        "status": "invalid",
        "errors": [
            "(<unknown>): did not find expected key while parsing a block mapping at line 1 column 1"
        ],
        "warnings": [],
    }
    assert resolve_exit_code(data) == 1

    # results from project-specific api
    data = {
        "valid": False,
        "errors": [
            "(<unknown>): did not find expected key while parsing a block mapping at line 1 column 1"
        ],
        "warnings": [],
    }
    assert resolve_exit_code(data) == 1

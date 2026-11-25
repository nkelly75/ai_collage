import json

import azure.functions as func
import pytest

from function_app import app


@pytest.fixture(scope="module")
def health_function():
    functions = app.get_functions()
    assert len(functions) == 1
    return functions[0]


def test_health_returns_ok_json(health_function):
    request = func.HttpRequest(
        method="GET",
        url="http://127.0.0.1:7071/api/health",
        body=b"",
    )

    response = health_function.get_user_function()(request)

    assert response.status_code == 200
    assert response.mimetype == "application/json"
    assert json.loads(response.get_body()) == {"status": "ok"}


def test_only_health_get_is_registered_without_authentication(health_function):
    trigger = next(
        binding
        for binding in health_function.get_bindings()
        if binding.type == "httpTrigger"
    ).get_dict_repr()

    assert trigger["route"] == "health"
    assert trigger["methods"] == [func.HttpMethod.GET]
    assert trigger["authLevel"] == func.AuthLevel.ANONYMOUS

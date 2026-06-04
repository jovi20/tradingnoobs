from observability import build_log_context, make_error_code


def test_make_error_code_namespaces_errors():
    assert make_error_code("auth", "invalid_credentials") == "auth.invalid_credentials"


def test_build_log_context_includes_required_fields():
    context = build_log_context(
        request_id="req-1",
        actor_type="user",
        user_public_id="01HX0000000000000000000000",
        route="/api/v1/auth/me",
        method="GET",
        status_code=200,
        latency_ms=12.5,
        error_code=None,
    )

    assert context["request_id"] == "req-1"
    assert context["actor_type"] == "user"
    assert context["user_public_id"] == "01HX0000000000000000000000"
    assert context["route"] == "/api/v1/auth/me"
    assert context["method"] == "GET"
    assert context["status_code"] == 200
    assert context["latency_ms"] == 12.5
    assert context["error_code"] is None

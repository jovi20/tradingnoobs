from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from scripts import verify_ibkr_flex_evidence


def test_repository_manifest_reports_exact_blockers(capsys):
    exit_code = verify_ibkr_flex_evidence.main([])

    report = json.loads(capsys.readouterr().out)
    assert exit_code == 1
    assert report["gate_status"] == "BLOCKED"
    assert report["manifest_status"] == "UNVERIFIED"
    assert report["field_contract_declared"] is False
    assert report["query_template_artifact_declared"] is False
    assert report["fixture_count"] == 0
    assert "Frozen query_template_id is missing" in report["reasons"]
    assert "Frozen field contract is missing" in report["reasons"]
    assert any(
        reason.startswith("Official evidence missing semantics:")
        for reason in report["reasons"]
    )
    assert any(
        reason.startswith("Real fixtures missing semantics:")
        for reason in report["reasons"]
    )


def test_invalid_manifest_is_reported_without_traceback(tmp_path, capsys):
    manifest_path = tmp_path / "invalid.json"
    manifest_path.write_text("{", encoding="utf-8")

    exit_code = verify_ibkr_flex_evidence.main(
        ["--manifest", str(manifest_path), "--pretty"]
    )

    report = json.loads(capsys.readouterr().out)
    assert exit_code == 1
    assert report == {
        "adapter_kind": "IBKR_FLEX_XML_V1",
        "gate_status": "BLOCKED",
        "manifest_status": "INVALID",
        "reasons": [
            "Provider evidence manifest is unreadable or invalid"
        ],
        "schema_version": 1,
    }


def test_pass_report_is_stable_and_does_not_expose_template_id(
    tmp_path,
    monkeypatch,
):
    manifest = SimpleNamespace(
        adapter_kind="IBKR_FLEX_XML_V1",
        status="VERIFIED",
        field_contract=object(),
        query_template_relative_path="query-template.json",
        query_template_sha256="sha256:" + "1" * 64,
        official_sources=(object(), object()),
        fixtures=(object(),),
    )
    verified = SimpleNamespace(
        query_template_sha256="sha256:" + "1" * 64,
    )
    monkeypatch.setattr(
        verify_ibkr_flex_evidence,
        "read_provider_evidence_manifest",
        lambda path: manifest,
    )
    monkeypatch.setattr(
        verify_ibkr_flex_evidence,
        "verify_provider_evidence",
        lambda loaded, fixture_root: verified,
    )

    report, exit_code = verify_ibkr_flex_evidence.build_readiness_report(
        manifest_path=Path("manifest.json"),
        fixture_root=tmp_path,
    )

    assert exit_code == 0
    assert report == {
        "adapter_kind": "IBKR_FLEX_XML_V1",
        "field_contract_declared": True,
        "fixture_count": 1,
        "gate_status": "PASS",
        "manifest_status": "VERIFIED",
        "official_source_count": 2,
        "query_template_artifact_declared": True,
        "query_template_sha256": "sha256:" + "1" * 64,
        "reasons": [],
        "schema_version": 1,
    }
    assert "query_template_id" not in report

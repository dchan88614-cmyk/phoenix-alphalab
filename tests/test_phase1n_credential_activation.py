from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.research import phase1n_credential_activation as p1n


def test_credential_status_detects_missing_placeholder_and_whitespace():
    assert p1n.credential_status(None) == "MISSING"
    assert p1n.credential_status("<YOUR_TIINGO_API_TOKEN>") == "SUSPICIOUS_PLACEHOLDER"
    assert p1n.credential_status(" token ") == "SUSPICIOUS_WHITESPACE"
    assert p1n.credential_status("short") == "SUSPICIOUS_TOO_SHORT"


def test_preflight_prefers_tiingo(monkeypatch):
    monkeypatch.setenv("TIINGO_API_TOKEN", "dummy-tiingo-token")
    monkeypatch.setenv("POLYGON_API_KEY", "dummy-polygon-token")
    monkeypatch.delenv("MASSIVE_API_KEY", raising=False)
    monkeypatch.delenv("ALPHAVANTAGE_API_KEY", raising=False)

    preflight = p1n.build_credentials_preflight()

    assert preflight.loc[preflight["env_var_name"].eq("TIINGO_API_TOKEN"), "selected_for_live_smoke"].iloc[0] == True
    assert preflight.loc[preflight["env_var_name"].eq("POLYGON_API_KEY"), "selected_for_live_smoke"].iloc[0] == True
    assert preflight.loc[preflight["env_var_name"].eq("TIINGO_API_TOKEN"), "selection_reason"].iloc[0] == "preferred configured credential"
    assert preflight.loc[preflight["env_var_name"].eq("POLYGON_API_KEY"), "selection_reason"].iloc[0] == "configured credential; smoke tested after preferred vendor"


def test_adapter_contract_tests_pass_with_fixtures():
    contracts = p1n.build_adapter_contract_tests()

    assert len(contracts) == 3
    assert contracts["parse_status"].eq("PASS").all()


def test_live_smoke_skips_network_when_credentials_missing(monkeypatch, tmp_path: Path):
    for key in ["TIINGO_API_TOKEN", "POLYGON_API_KEY", "MASSIVE_API_KEY", "ALPHAVANTAGE_API_KEY"]:
        monkeypatch.delenv(key, raising=False)
    preflight = p1n.build_credentials_preflight()

    smoke = p1n.build_live_smoke_tests("2024-01-01", "2024-01-31", preflight, tmp_path)

    assert smoke["smoke_status"].eq("CREDENTIAL_MISSING").all()
    assert smoke["attempted_network_fetch"].eq(False).all()


def test_no_secret_audit_requires_env_ignored():
    audit = p1n.build_no_secret_audit(Path("data/reports"))

    required = audit.loc[audit["checked_path_or_pattern"].isin([".env", ".env.*", "*.env", "!.env.example"])]
    assert required["status"].eq("PASS").all()


def test_rerun_readiness_waits_for_credential(monkeypatch):
    for key in ["TIINGO_API_TOKEN", "POLYGON_API_KEY", "MASSIVE_API_KEY", "ALPHAVANTAGE_API_KEY"]:
        monkeypatch.delenv(key, raising=False)
    preflight = p1n.build_credentials_preflight()
    contracts = p1n.build_adapter_contract_tests()
    smoke = p1n.build_live_smoke_tests("2024-01-01", "2024-01-31", preflight, Path("/tmp/phase1n-test"))
    audit = pd.DataFrame({"status": ["PASS"]})

    readiness = p1n.build_phase1m_rerun_readiness(preflight, contracts, smoke, audit)

    assert readiness.iloc[0]["reason_status"] == p1n.PHASE_1N_WAITING_FOR_CREDENTIAL
    assert readiness.iloc[0]["phase1m_rerun_allowed"] == False


def test_rerun_readiness_allows_when_smoke_passes(monkeypatch):
    monkeypatch.setenv("TIINGO_API_TOKEN", "dummy-tiingo-token")
    preflight = p1n.build_credentials_preflight()
    contracts = p1n.build_adapter_contract_tests()
    smoke = pd.DataFrame(
        {
            "source_name": ["tiingo_eod"] * 7,
            "ticker": ["AAPL", "MSFT", "SPY", "QQQ", "SQ", "GEV", "RDDT"],
            "smoke_status": ["PASS"] * 7,
        }
    )
    audit = pd.DataFrame({"status": ["PASS"]})

    readiness = p1n.build_phase1m_rerun_readiness(preflight, contracts, smoke, audit)

    assert readiness.iloc[0]["reason_status"] == p1n.PHASE_1N_READY_TO_RERUN_PHASE_1M_WITH_CREDENTIAL
    assert readiness.iloc[0]["phase1m_rerun_allowed"] == True


def test_phase1n_reports_are_written(tmp_path: Path):
    paths = {
        "selection": tmp_path / "phase1n_vendor_selection_decision.md",
        "preflight": tmp_path / "phase1n_credentials_preflight.csv",
        "contracts": tmp_path / "phase1n_adapter_contract_tests.csv",
        "live_smoke": tmp_path / "phase1n_live_smoke_tests.csv",
        "readiness": tmp_path / "phase1n_phase1m_rerun_readiness.csv",
        "no_secret": tmp_path / "phase1n_no_secret_audit.csv",
        "summary": tmp_path / "phase1n_data_readiness_summary.md",
    }
    frame = pd.DataFrame({"status": ["PASS"]})

    p1n.write_phase1n_reports(frame, frame, frame, frame, frame, "# selection\n", "PHOENIX NANO PHASE 1N — CREDENTIAL ACTIVATION, ADAPTER VERIFICATION, AND RETEST AUTHORIZATION GATE\n", paths)

    assert all(path.exists() for path in paths.values())
    assert paths["summary"].read_text(encoding="utf-8").startswith("PHOENIX NANO PHASE 1N")

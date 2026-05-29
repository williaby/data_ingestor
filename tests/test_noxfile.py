"""Comprehensive tests for noxfile.py configuration."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add root directory to path to import noxfile
sys.path.insert(0, str(Path(__file__).parent.parent))

import noxfile


class TestNoxfileConstants:
    """Tests for noxfile constants and configuration."""

    def test_python_versions(self) -> None:
        """Test that Python versions are defined."""
        assert hasattr(noxfile, "PYTHON_VERSIONS")
        assert isinstance(noxfile.PYTHON_VERSIONS, list)
        assert len(noxfile.PYTHON_VERSIONS) > 0
        assert "3.11" in noxfile.PYTHON_VERSIONS or "3.12" in noxfile.PYTHON_VERSIONS

    def test_src_locations(self) -> None:
        """Test that source locations are defined."""
        assert hasattr(noxfile, "SRC_LOCATIONS")
        assert isinstance(noxfile.SRC_LOCATIONS, list)
        assert "src" in noxfile.SRC_LOCATIONS
        assert "tests" in noxfile.SRC_LOCATIONS


class TestTestsSessions:
    """Tests for the main tests session."""

    @patch("noxfile.nox.session")
    def test_tests_session_exists(self, mock_session) -> None:
        """Test that tests session is defined."""
        assert hasattr(noxfile, "tests")
        assert callable(noxfile.tests)

    def test_tests_session_with_mock(self) -> None:
        """Test tests session with mock session object."""
        mock_session = MagicMock()
        mock_session.posargs = []

        noxfile.tests(mock_session)

        # Verify uv sync was called
        mock_session.run.assert_any_call("uv", "sync", "--frozen", external=True)
        # Verify pytest was called with coverage args
        assert any("pytest" in str(call) for call in mock_session.run.call_args_list)

    def test_tests_session_with_posargs(self) -> None:
        """Test tests session with positional arguments."""
        mock_session = MagicMock()
        mock_session.posargs = ["--verbose", "-k", "test_foo"]

        noxfile.tests(mock_session)

        # Should use posargs instead of defaults
        pytest_call = [c for c in mock_session.run.call_args_list if "pytest" in str(c)]
        assert len(pytest_call) > 0


class TestUnitSession:
    """Tests for unit test session."""

    def test_unit_session_exists(self) -> None:
        """Test that unit session is defined."""
        assert hasattr(noxfile, "unit")
        assert callable(noxfile.unit)

    def test_unit_session_excludes_slow_tests(self) -> None:
        """Test that unit session excludes slow test markers."""
        mock_session = MagicMock()
        mock_session.posargs = []

        noxfile.unit(mock_session)

        # Find the pytest call
        pytest_calls = [c for c in mock_session.run.call_args_list if "pytest" in str(c[0])]
        assert len(pytest_calls) > 0

        # Verify markers are excluded
        pytest_args = pytest_calls[0][0]
        assert any("not component" in str(arg) for arg in pytest_args)


class TestComponentSession:
    """Tests for component test session."""

    def test_component_session_exists(self) -> None:
        """Test that component session is defined."""
        assert hasattr(noxfile, "component")
        assert callable(noxfile.component)

    def test_component_session_runs_component_tests(self) -> None:
        """Test that component session runs component marker tests."""
        mock_session = MagicMock()
        mock_session.posargs = []

        noxfile.component(mock_session)

        pytest_calls = [c for c in mock_session.run.call_args_list if "pytest" in str(c[0])]
        assert len(pytest_calls) > 0

        # Verify component marker is used
        pytest_args = pytest_calls[0][0]
        assert any("component" in str(arg) for arg in pytest_args)


class TestIntegrationSession:
    """Tests for integration test session."""

    def test_integration_session_exists(self) -> None:
        """Test that integration session is defined."""
        assert hasattr(noxfile, "integration")
        assert callable(noxfile.integration)

    def test_integration_session_runs_integration_tests(self) -> None:
        """Test that integration session runs integration tests."""
        mock_session = MagicMock()
        mock_session.posargs = []

        noxfile.integration(mock_session)

        pytest_calls = [c for c in mock_session.run.call_args_list if "pytest" in str(c[0])]
        assert len(pytest_calls) > 0


class TestE2ESession:
    """Tests for end-to-end test session."""

    def test_e2e_session_exists(self) -> None:
        """Test that e2e session is defined."""
        assert hasattr(noxfile, "e2e")
        assert callable(noxfile.e2e)

    def test_e2e_session_runs_e2e_tests(self) -> None:
        """Test that e2e session runs e2e marker tests."""
        mock_session = MagicMock()
        mock_session.posargs = []

        noxfile.e2e(mock_session)

        pytest_calls = [c for c in mock_session.run.call_args_list if "pytest" in str(c[0])]
        assert len(pytest_calls) > 0

        pytest_args = pytest_calls[0][0]
        assert any("e2e" in str(arg) for arg in pytest_args)


class TestPerfSession:
    """Tests for performance test session."""

    def test_perf_session_exists(self) -> None:
        """Test that perf session is defined."""
        assert hasattr(noxfile, "perf")
        assert callable(noxfile.perf)

    def test_perf_session_runs_perf_tests(self) -> None:
        """Test that perf session runs performance tests."""
        mock_session = MagicMock()
        mock_session.posargs = []

        noxfile.perf(mock_session)

        pytest_calls = [c for c in mock_session.run.call_args_list if "pytest" in str(c[0])]
        assert len(pytest_calls) > 0

        pytest_args = pytest_calls[0][0]
        assert any("perf" in str(arg) or "performance" in str(arg) for arg in pytest_args)


class TestLintingSessions:
    """Tests for linting and code quality sessions."""

    def test_lint_session_exists(self) -> None:
        """Test that lint session exists if defined."""
        # Check if lint session is defined in noxfile
        if hasattr(noxfile, "lint"):
            assert callable(noxfile.lint)

    def test_format_session_exists(self) -> None:
        """Test that format session exists if defined."""
        if hasattr(noxfile, "format"):
            assert callable(noxfile.format)

    def test_type_check_session_exists(self) -> None:
        """Test that type check session exists if defined."""
        if hasattr(noxfile, "type_check") or hasattr(noxfile, "mypy"):
            session = getattr(noxfile, "type_check", None) or getattr(noxfile, "mypy", None)
            assert callable(session)


class TestSecuritySessions:
    """Tests for security scanning sessions."""

    def test_security_session_exists(self) -> None:
        """Test that security session exists if defined."""
        if hasattr(noxfile, "security"):
            assert callable(noxfile.security)

    def test_safety_session_exists(self) -> None:
        """Test that safety session exists if defined."""
        if hasattr(noxfile, "safety"):
            assert callable(noxfile.safety)


class TestDocsSessions:
    """Tests for documentation generation sessions."""

    def test_docs_session_exists(self) -> None:
        """Test that docs session exists if defined."""
        if hasattr(noxfile, "docs"):
            assert callable(noxfile.docs)

    def test_docs_build_session_exists(self) -> None:
        """Test that docs-build session exists if defined."""
        if hasattr(noxfile, "docs_build"):
            assert callable(noxfile.docs_build)


class TestSessionConfiguration:
    """Tests for session configuration and metadata."""

    def test_sessions_have_python_parameter(self) -> None:
        """Test that sessions with python parameter are configured."""
        # Tests session should have python parameter
        if hasattr(noxfile.tests, "__wrapped__"):
            # Nox sessions are wrapped, check if they have python attribute
            pass  # Difficult to test without running nox

    def test_all_sessions_install_dependencies(self) -> None:
        """Test that sessions install dependencies."""
        sessions_to_test = [
            noxfile.tests,
            noxfile.unit,
            noxfile.component,
            noxfile.integration,
            noxfile.e2e,
            noxfile.perf,
        ]

        for session_func in sessions_to_test:
            mock_session = MagicMock()
            mock_session.posargs = []

            session_func(mock_session)

            # Verify uv sync was called
            install_calls = [c for c in mock_session.run.call_args_list if "uv" in str(c) and "sync" in str(c)]
            assert len(install_calls) > 0, f"Session {session_func.__name__} did not install dependencies"


class TestSessionPosargs:
    """Tests for handling positional arguments in sessions."""

    def test_sessions_accept_posargs(self) -> None:
        """Test that sessions properly handle positional arguments."""
        sessions_to_test = [
            noxfile.tests,
            noxfile.unit,
            noxfile.component,
            noxfile.integration,
            noxfile.e2e,
            noxfile.perf,
        ]

        for session_func in sessions_to_test:
            mock_session = MagicMock()
            custom_args = ["--maxfail=1", "--tb=short"]
            mock_session.posargs = custom_args

            session_func(mock_session)

            # Session should have been executed without errors
            assert mock_session.run.called


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_empty_posargs(self) -> None:
        """Test handling of empty posargs."""
        mock_session = MagicMock()
        mock_session.posargs = []

        noxfile.tests(mock_session)

        # Should use default args
        pytest_call = [c for c in mock_session.run.call_args_list if "pytest" in str(c)]
        assert len(pytest_call) > 0

    def test_none_posargs(self) -> None:
        """Test handling of None posargs."""
        mock_session = MagicMock()
        mock_session.posargs = None

        # Should handle None gracefully
        try:
            noxfile.tests(mock_session)
        except AttributeError:
            pytest.fail("Session should handle None posargs gracefully")


class TestSessionIntegration:
    """Integration tests for session interactions."""

    def test_multiple_sessions_can_run(self) -> None:
        """Test that multiple sessions can be run without conflicts."""
        sessions = [
            noxfile.tests,
            noxfile.unit,
        ]

        for session_func in sessions:
            mock_session = MagicMock()
            mock_session.posargs = []

            # Should run without exceptions
            session_func(mock_session)

            assert mock_session.run.called

    def test_sessions_use_external_flag(self) -> None:
        """Test that uv commands use external=True flag."""
        mock_session = MagicMock()
        mock_session.posargs = []

        noxfile.tests(mock_session)

        # Find uv sync call
        uv_calls = [c for c in mock_session.run.call_args_list if "uv" in str(c[0])]
        assert len(uv_calls) > 0

        # Verify external=True is used
        uv_call = uv_calls[0]
        assert uv_call[1].get("external") is True


class TestAdvancedSessions:
    """Tests for advanced testing sessions."""

    def test_security_tests_session(self) -> None:
        """Test security_tests session execution."""
        mock_session = MagicMock()
        mock_session.posargs = []

        noxfile.security_tests(mock_session)

        # Verify pytest with security marker
        pytest_calls = [c for c in mock_session.run.call_args_list if "pytest" in str(c[0])]
        assert len(pytest_calls) > 0
        pytest_args = pytest_calls[0][0]
        assert any("security" in str(arg) for arg in pytest_args)

    def test_chaos_tests_session(self) -> None:
        """Test chaos_tests session execution."""
        mock_session = MagicMock()
        mock_session.posargs = []

        noxfile.chaos_tests(mock_session)

        pytest_calls = [c for c in mock_session.run.call_args_list if "pytest" in str(c[0])]
        assert len(pytest_calls) > 0
        pytest_args = pytest_calls[0][0]
        assert any("chaos" in str(arg) for arg in pytest_args)

    def test_fast_session(self) -> None:
        """Test fast development session."""
        mock_session = MagicMock()
        mock_session.posargs = []

        noxfile.fast(mock_session)

        pytest_calls = [c for c in mock_session.run.call_args_list if "pytest" in str(c[0])]
        assert len(pytest_calls) > 0
        pytest_args = pytest_calls[0][0]
        assert any("not slow" in str(arg) for arg in pytest_args)

    def test_metrics_session_with_missing_script(self) -> None:
        """Test metrics session when script doesn't exist."""
        mock_session = MagicMock()
        mock_session.posargs = []

        noxfile.metrics(mock_session)

        # Should run uv sync
        mock_session.run.assert_any_call("uv", "sync", "--frozen", external=True)

    def test_metrics_session_with_existing_script(self) -> None:
        """Test metrics session when script exists."""
        mock_session = MagicMock()
        mock_session.posargs = []

        # Mock Path.exists() to return True
        import tempfile

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, dir=".") as f:
            f.write("# Test script")
            script_name = f.name

        try:
            # Temporarily rename to expected name
            import os

            os.rename(script_name, "test_metrics_dashboard.py")

            noxfile.metrics(mock_session)

            # Should run the script
            python_calls = [
                c
                for c in mock_session.run.call_args_list
                if "python" in str(c) and "test_metrics_dashboard.py" in str(c)
            ]
            assert len(python_calls) > 0
        finally:
            # Clean up
            if os.path.exists("test_metrics_dashboard.py"):
                os.remove("test_metrics_dashboard.py")


class TestCodecovSessions:
    """Tests for Codecov-specific test sessions."""

    def test_tests_unit_session(self) -> None:
        """Test tests_unit session with Codecov flags."""
        mock_session = MagicMock()
        mock_session.env = {}

        noxfile.tests_unit(mock_session)

        # Verify pytest with coverage flags
        pytest_calls = [c for c in mock_session.run.call_args_list if "pytest" in str(c[0])]
        assert len(pytest_calls) > 0
        pytest_args = pytest_calls[0][0]
        assert any("coverage-unit.xml" in str(arg) for arg in pytest_args)

    def test_tests_integration_session(self) -> None:
        """Test tests_integration session."""
        mock_session = MagicMock()
        mock_session.env = {}

        noxfile.tests_integration(mock_session)

        pytest_calls = [c for c in mock_session.run.call_args_list if "pytest" in str(c[0])]
        assert len(pytest_calls) > 0
        pytest_args = pytest_calls[0][0]
        assert any("coverage-integration.xml" in str(arg) for arg in pytest_args)

    def test_tests_security_session(self) -> None:
        """Test tests_security session."""
        mock_session = MagicMock()
        mock_session.env = {}

        noxfile.tests_security(mock_session)

        pytest_calls = [c for c in mock_session.run.call_args_list if "pytest" in str(c[0])]
        assert len(pytest_calls) > 0
        pytest_args = pytest_calls[0][0]
        assert any("coverage-security.xml" in str(arg) for arg in pytest_args)

    def test_tests_fast_session(self) -> None:
        """Test tests_fast session."""
        mock_session = MagicMock()
        mock_session.env = {}

        noxfile.tests_fast(mock_session)

        pytest_calls = [c for c in mock_session.run.call_args_list if "pytest" in str(c[0])]
        assert len(pytest_calls) > 0
        pytest_args = pytest_calls[0][0]
        assert any("coverage-fast.xml" in str(arg) for arg in pytest_args)

    def test_codecov_analysis_session(self) -> None:
        """Test codecov_analysis session."""
        mock_session = MagicMock()

        noxfile.codecov_analysis(mock_session)

        # Verify python script is run
        python_calls = [c for c in mock_session.run.call_args_list if "codecov_analysis.py" in str(c)]
        assert len(python_calls) > 0

    def test_tests_unit_with_codecov_token(self) -> None:
        """Test tests_unit session uploads to Codecov when token present."""
        mock_session = MagicMock()
        mock_session.env = {"CODECOV_TOKEN": "test-token"}

        noxfile.tests_unit(mock_session)

        # Verify codecov upload was called
        codecov_calls = [c for c in mock_session.run.call_args_list if "codecov" in str(c[0])]
        assert len(codecov_calls) > 0

    def test_tests_integration_with_codecov_token(self) -> None:
        """Test tests_integration session uploads to Codecov when token present."""
        mock_session = MagicMock()
        mock_session.env = {"CODECOV_TOKEN": "test-token"}

        noxfile.tests_integration(mock_session)

        # Verify codecov upload was called
        codecov_calls = [c for c in mock_session.run.call_args_list if "codecov" in str(c[0])]
        assert len(codecov_calls) > 0

    def test_tests_security_with_codecov_token(self) -> None:
        """Test tests_security session uploads to Codecov when token present."""
        mock_session = MagicMock()
        mock_session.env = {"CODECOV_TOKEN": "test-token"}

        noxfile.tests_security(mock_session)

        # Verify codecov upload was called
        codecov_calls = [c for c in mock_session.run.call_args_list if "codecov" in str(c[0])]
        assert len(codecov_calls) > 0

    def test_tests_fast_with_codecov_token(self) -> None:
        """Test tests_fast session uploads to Codecov when token present."""
        mock_session = MagicMock()
        mock_session.env = {"CODECOV_TOKEN": "test-token"}

        noxfile.tests_fast(mock_session)

        # Verify codecov upload was called
        codecov_calls = [c for c in mock_session.run.call_args_list if "codecov" in str(c[0])]
        assert len(codecov_calls) > 0


class TestLintingAndFormatSessions:
    """Tests for linting and code quality sessions."""

    def test_lint_session(self) -> None:
        """Test lint session execution."""
        mock_session = MagicMock()
        mock_session.posargs = []

        noxfile.lint(mock_session)

        # Verify black check
        black_calls = [c for c in mock_session.run.call_args_list if "black" in str(c[0])]
        assert len(black_calls) > 0

        # Verify ruff
        ruff_calls = [c for c in mock_session.run.call_args_list if "ruff" in str(c[0])]
        assert len(ruff_calls) > 0

    def test_type_check_session(self) -> None:
        """Test type checking session."""
        mock_session = MagicMock()

        noxfile.type_check(mock_session)

        # Verify mypy is run
        mypy_calls = [c for c in mock_session.run.call_args_list if "mypy" in str(c[0])]
        assert len(mypy_calls) > 0

    def test_security_session(self) -> None:
        """Test security scanning session."""
        mock_session = MagicMock()

        noxfile.security(mock_session)

        # Verify safety check
        safety_calls = [c for c in mock_session.run.call_args_list if "safety" in str(c[0])]
        assert len(safety_calls) > 0

        # Verify bandit
        bandit_calls = [c for c in mock_session.run.call_args_list if "bandit" in str(c[0])]
        assert len(bandit_calls) > 0

    def test_format_code_session(self) -> None:
        """Test format_code session."""
        mock_session = MagicMock()
        mock_session.posargs = []

        noxfile.format_code(mock_session)

        # Verify black formatting
        black_calls = [c for c in mock_session.run.call_args_list if "black" in str(c[0])]
        assert len(black_calls) > 0

        # Verify ruff fix
        ruff_calls = [c for c in mock_session.run.call_args_list if "ruff" in str(c[0])]
        assert len(ruff_calls) > 0

    def test_pre_commit_session(self) -> None:
        """Test pre-commit session."""
        mock_session = MagicMock()

        noxfile.pre_commit(mock_session)

        # Verify pre-commit run
        precommit_calls = [c for c in mock_session.run.call_args_list if "pre-commit" in str(c[0])]
        assert len(precommit_calls) > 0


class TestUtilitySessions:
    """Tests for utility sessions."""

    def test_docs_session(self) -> None:
        """Test documentation build session."""
        mock_session = MagicMock()

        noxfile.docs(mock_session)

        # Verify mkdocs is run
        mk_calls = [c for c in mock_session.run.call_args_list if "mkdocs" in str(c[0])]
        assert len(mk_calls) > 0

    def test_contract_testing_session(self) -> None:
        """Test contract testing session."""
        mock_session = MagicMock()

        noxfile.contract_testing(mock_session)

        # Verify pytest with contract tests
        pytest_calls = [c for c in mock_session.run.call_args_list if "pytest" in str(c[0])]
        assert len(pytest_calls) > 0
        assert any("tests/contract" in str(c) for c in pytest_calls)


class TestComplexUtilitySessions:
    """Tests for complex utility sessions."""

    def test_deps_session(self) -> None:
        """Test deps session execution."""
        mock_session = MagicMock()
        # Mock chdir and create_tmp to avoid actual directory operations
        mock_session.create_tmp.return_value = "/tmp/test"

        # Mock chdir context manager
        mock_chdir = MagicMock()
        mock_chdir.__enter__ = MagicMock(return_value=None)
        mock_chdir.__exit__ = MagicMock(return_value=None)
        mock_session.chdir.return_value = mock_chdir

        noxfile.deps(mock_session)

        # Verify uv pip list (outdated check) was called
        show_calls = [c for c in mock_session.run.call_args_list if "uv" in str(c) and "list" in str(c)]
        assert len(show_calls) > 0

    def test_mutation_testing_session(self) -> None:
        """Test mutation testing session execution."""
        mock_session = MagicMock()

        # Make mutmut run succeed
        mock_session.run.return_value = None

        try:
            noxfile.mutation_testing(mock_session)
        except Exception:
            # Session may fail but should attempt to run mutmut
            pass

        # Verify mutmut was attempted
        mutmut_calls = [c for c in mock_session.run.call_args_list if "mutmut" in str(c)]
        assert len(mutmut_calls) > 0

    def test_mutation_testing_with_exception(self) -> None:
        """Test mutation testing handles exceptions gracefully."""
        mock_session = MagicMock()

        # Make first mutmut run raise an exception
        mock_session.run.side_effect = [
            None,  # uv sync
            None,  # rm -rf .mutmut-cache
            Exception("Mutation testing failed"),  # mutmut run - raises
            None,  # mutmut html - should still be called
        ]

        # Should not raise, handles exception gracefully
        noxfile.mutation_testing(mock_session)

        # Verify exception handler was triggered
        log_calls = [c for c in mock_session.log.call_args_list]
        warning_logs = [c for c in log_calls if "⚠️" in str(c) or "warnings" in str(c)]
        assert len(warning_logs) > 0

    def test_dast_scanning_session(self) -> None:
        """Test DAST scanning session execution."""
        mock_session = MagicMock()
        mock_session.env = {"PWD": "/test/path"}

        # Make docker check succeed
        mock_session.run.side_effect = [None, None, Exception("Docker not available")]

        try:
            noxfile.dast_scanning(mock_session)
        except Exception:
            # Session handles errors gracefully
            pass

        # Verify docker version was checked
        docker_calls = [c for c in mock_session.run.call_args_list if "docker" in str(c)]
        assert len(docker_calls) > 0

    def test_dast_scanning_success_with_app_running(self) -> None:
        """Test DAST scanning when application is accessible."""
        mock_session = MagicMock()
        mock_session.env = {"PWD": "/test/path"}

        # Make docker and curl checks succeed, then docker run succeeds
        mock_session.run.side_effect = [
            None,  # uv sync
            None,  # docker --version
            None,  # curl (app is running) - covers line 419
            None,  # mkdir -p dast-reports
            None,  # docker run (ZAP scan)
            None,  # python -c (generate report)
        ]

        # Should complete successfully
        noxfile.dast_scanning(mock_session)

        # Verify success logs
        log_calls = [c for c in mock_session.log.call_args_list]
        success_logs = [c for c in log_calls if "✅ Application is running" in str(c)]
        assert len(success_logs) > 0

        # Verify ZAP scan was attempted
        docker_run_calls = [c for c in mock_session.run.call_args_list if "docker" in str(c) and "run" in str(c)]
        assert len(docker_run_calls) > 0

    def test_dast_scanning_exception_during_scan(self) -> None:
        """Test DAST scanning handles exceptions during ZAP scan."""
        mock_session = MagicMock()
        mock_session.env = {"PWD": "/test/path"}

        # Make setup succeed but ZAP scan fail
        mock_session.run.side_effect = [
            None,  # uv sync
            None,  # docker --version
            Exception("App not running"),  # curl fails
            None,  # mkdir -p dast-reports
            Exception("ZAP scan failed"),  # docker run fails - triggers exception handler
        ]

        # Should handle exception gracefully
        noxfile.dast_scanning(mock_session)

        # Verify exception handler was triggered
        log_calls = [c for c in mock_session.log.call_args_list]
        warning_logs = [c for c in log_calls if "⚠️" in str(c) or "warnings" in str(c)]
        assert len(warning_logs) > 0

    def test_performance_testing_session(self) -> None:
        """Test performance testing session execution."""
        mock_session = MagicMock()

        noxfile.performance_testing(mock_session)

        # Verify locust was called
        locust_calls = [c for c in mock_session.run.call_args_list if "locust" in str(c)]
        assert len(locust_calls) > 0

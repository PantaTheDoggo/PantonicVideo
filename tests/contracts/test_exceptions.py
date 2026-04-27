"""Tests for contracts exceptions — §3, contracts.exceptions."""

import pytest
from contracts.exceptions import ServiceNotAvailable, ContractVersionMismatch


class TestServiceNotAvailable:
    """§3 — ServiceNotAvailable exception."""

    def test_is_exception(self):
        """§3: ServiceNotAvailable is an Exception subclass."""
        assert issubclass(ServiceNotAvailable, Exception)

    def test_can_be_raised_and_caught(self):
        """§3: ServiceNotAvailable can be raised and caught."""
        with pytest.raises(ServiceNotAvailable):
            raise ServiceNotAvailable("image_service not found")

    def test_carries_message(self):
        """§3: ServiceNotAvailable carries a descriptive message."""
        exc = ServiceNotAvailable("image_service not found")
        assert "image_service" in str(exc)

    @pytest.mark.parametrize(
        "service_name",
        [
            "image_service",
            "signal_service",
            "filesystem_service",
            "app_state_service",
            "logging_service",
            "injector_service",
            "project_service",
            "plugin_registry_service",
            "subtitle_service",
        ],
    )
    def test_service_not_available_for_each_service(self, service_name):
        """§3: ServiceNotAvailable can be raised for any of the nine v1 services."""
        with pytest.raises(ServiceNotAvailable):
            raise ServiceNotAvailable(f"{service_name} not available")


class TestContractVersionMismatch:
    """§3 — ContractVersionMismatch exception."""

    def test_is_exception(self):
        """§3: ContractVersionMismatch is an Exception subclass."""
        assert issubclass(ContractVersionMismatch, Exception)

    def test_can_be_raised_and_caught(self):
        """§3: ContractVersionMismatch can be raised and caught."""
        with pytest.raises(ContractVersionMismatch):
            raise ContractVersionMismatch("contracts 0.9.0 does not satisfy ^1.0")

    def test_carries_version_info(self):
        """§3: ContractVersionMismatch carries version information in its message."""
        exc = ContractVersionMismatch("version 0.9.0 does not satisfy ^1.0")
        assert "0.9.0" in str(exc) or "1.0" in str(exc)

    @pytest.mark.parametrize(
        "actual, required",
        [
            ("0.9.0", "^1.0"),
            ("2.0.0", "^1.0"),
            ("1.0.0", "^2.0"),
        ],
    )
    def test_version_mismatch_cases(self, actual, required):
        """§3: ContractVersionMismatch raised for various version mismatch scenarios."""
        with pytest.raises(ContractVersionMismatch):
            raise ContractVersionMismatch(
                f"contracts {actual} does not satisfy {required}"
            )

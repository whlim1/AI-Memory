"""Tests for ai_memory_pipeline.redaction."""

import pytest

from ai_memory_pipeline.redaction import (
    Redactor,
    find_pii_data,
    redact_pii,
)

# Same fixture text the module's own __main__ demo uses.
SAMPLE_TEXT = """Contact information for John Doe:
Email: john.doe@example.com
Phone: (555) 123-4567
SSN: 123-45-6789
Credit Card: 1234-5678-9012-3456
IP Address: 192.168.1.1
Website: https://example.com"""


@pytest.fixture
def redactor():
    return Redactor()


class TestRedactText:
    def test_redacts_all_pii_types(self, redactor):
        result = redactor.redact_text(SAMPLE_TEXT)
        assert "[EMAIL_REDACTED]" in result
        assert "[PHONE_REDACTED]" in result
        assert "[SSN_REDACTED]" in result
        assert "[CREDIT_CARD_REDACTED]" in result
        assert "[IP_ADDRESS_REDACTED]" in result
        # Original values must be gone.
        for secret in (
            "john.doe@example.com",
            "(555) 123-4567",
            "123-45-6789",
            "1234-5678-9012-3456",
            "192.168.1.1",
        ):
            assert secret not in result

    def test_url_with_path_is_redacted(self, redactor):
        text = "See https://example.com/docs/page for details."
        assert redactor.redact_text(text) == (
            "See [URL_REDACTED] for details."
        )

    def test_bare_domain_url_not_matched_documents_current_behavior(
        self, redactor
    ):
        # The url pattern requires a '/' after the host, so a bare domain
        # is left untouched. This documents current behavior; see report.
        text = "Visit https://example.com today."
        assert redactor.redact_text(text) == text

    def test_sensitive_types_limits_redaction(self, redactor):
        result = redactor.redact_text(SAMPLE_TEXT, sensitive_types=["email"])
        assert "[EMAIL_REDACTED]" in result
        # Other types untouched.
        assert "123-45-6789" in result
        assert "(555) 123-4567" in result
        assert "192.168.1.1" in result

    def test_unknown_sensitive_type_is_ignored(self, redactor):
        # No matching pattern -> text returned unchanged (no KeyError).
        assert redactor.redact_text("ssn 123-45-6789", sensitive_types=["bogus"]) == (
            "ssn 123-45-6789"
        )

    def test_non_string_input_returned_unchanged(self, redactor):
        assert redactor.redact_text(None) is None
        assert redactor.redact_text(42) == 42

    def test_clean_text_is_unchanged(self, redactor):
        text = "Nothing sensitive here at all."
        assert redactor.redact_text(text) == text


class TestFindSensitiveData:
    def test_finds_each_type_in_sample(self, redactor):
        found = redactor.find_sensitive_data(SAMPLE_TEXT)
        assert found["ssn"] == ["123-45-6789"]
        assert found["credit_card"] == ["1234-5678-9012-3456"]
        assert found["email"] == ["john.doe@example.com"]
        # The phone pattern has capture groups, so findall yields tuples.
        assert found["phone"] == [("555", "123", "4567")]
        assert found["ip_address"] == ["192.168.1.1"]
        assert "url" not in found  # bare domain has no path -> no match

    def test_deduplicates_matches(self, redactor):
        text = "a 123-45-6789 b 123-45-6789 c"
        assert redactor.find_sensitive_data(text)["ssn"] == ["123-45-6789"]

    def test_no_matches_returns_empty_dict(self, redactor):
        assert redactor.find_sensitive_data("totally clean text") == {}

    def test_non_string_input_returns_empty_dict(self, redactor):
        assert redactor.find_sensitive_data(None) == {}
        assert redactor.find_sensitive_data(3.14) == {}


class TestRedactWithContext:
    def test_matches_redact_text_output(self, redactor):
        # redact_with_context currently produces the same result as
        # redact_text for all inputs it accepts.
        assert redactor.redact_with_context(SAMPLE_TEXT) == (
            redactor.redact_text(SAMPLE_TEXT)
        )

    def test_respects_sensitive_types(self, redactor):
        result = redactor.redact_with_context(
            SAMPLE_TEXT, sensitive_types=["ssn"]
        )
        assert "[SSN_REDACTED]" in result
        assert "john.doe@example.com" in result

    def test_non_string_input_returned_unchanged(self, redactor):
        assert redactor.redact_with_context(None) is None


class TestModuleLevelFunctions:
    def test_redact_pii_delegates_to_redactor(self):
        result = redact_pii("Email me at john.doe@example.com")
        assert result == "Email me at [EMAIL_REDACTED]"

    def test_redact_pii_non_string_returned_unchanged(self):
        assert redact_pii(None) is None

    def test_find_pii_data_delegates_to_redactor(self):
        found = find_pii_data("ssn 123-45-6789 and ip 10.0.0.1")
        assert found["ssn"] == ["123-45-6789"]
        assert found["ip_address"] == ["10.0.0.1"]

    def test_find_pii_data_clean_text(self):
        assert find_pii_data("no secrets here") == {}

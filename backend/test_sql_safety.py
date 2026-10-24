import pytest

from backend import main


def test_dynamic_sql_identifiers_require_an_explicit_allowlist():
    assert main.sql_identifier("users") == "users"
    assert main.sql_identifier("photo") == "photo"
    with pytest.raises(AssertionError):
        main.sql_identifier("users; DROP TABLE users--")
    with pytest.raises(AssertionError):
        main.sql_identifier("unknown_column")


def test_dynamic_sql_fragments_require_an_explicit_allowlist():
    assert main.sql_fragment("user_id=?") == "user_id=?"
    with pytest.raises(AssertionError):
        main.sql_fragment("1=1; DROP TABLE users--")


def test_dynamic_value_lists_only_generate_placeholders():
    assert main.sql_placeholders(3) == "?,?,?"
    with pytest.raises(AssertionError):
        main.sql_placeholders(0)

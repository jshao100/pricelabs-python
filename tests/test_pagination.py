"""Tests for the generic Page pagination model."""

from pricelabs.pagination import Page


def test_page_str_data():
    """Page[str] can be constructed with string data."""
    page = Page[str](data=["a", "b", "c"], next_page=False)
    assert page.data == ["a", "b", "c"]


def test_page_dict_data():
    """Page[dict] works with dict data."""
    items = [{"id": 1}, {"id": 2}]
    page = Page[dict](data=items, next_page=True)
    assert page.data == items


def test_next_page_true():
    """next_page=True is preserved."""
    page = Page[str](data=["x"], next_page=True)
    assert page.next_page is True


def test_next_page_false():
    """next_page=False is preserved."""
    page = Page[str](data=["x"], next_page=False)
    assert page.next_page is False


def test_pms_name_optional_default_none():
    """pms_name defaults to None when not provided."""
    page = Page[str](data=[], next_page=False)
    assert page.pms_name is None


def test_pms_name_provided():
    """pms_name is stored when provided."""
    page = Page[str](data=[], next_page=False, pms_name="hostaway")
    assert page.pms_name == "hostaway"


def test_empty_data_list():
    """Page can be constructed with an empty data list."""
    page = Page[str](data=[], next_page=False)
    assert page.data == []

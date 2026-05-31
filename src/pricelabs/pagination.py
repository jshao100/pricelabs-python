"""Generic pagination utilities for PriceLabs API responses."""

import logging
from typing import Generic, TypeVar

from pydantic import BaseModel

logger = logging.getLogger(__name__)

T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    """A single page of results from a paginated endpoint.

    Attributes:
        data: The list of items on this page.
        next_page: Whether another page of results is available.
        pms_name: Optional property management system identifier.
    """

    data: list[T]
    next_page: bool
    pms_name: str | None = None

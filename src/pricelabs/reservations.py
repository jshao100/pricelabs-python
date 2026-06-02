"""Reservations resource namespace for the PriceLabs API."""

import logging
from collections.abc import Iterator

from pydantic import BaseModel

from pricelabs._http import HTTPClient
from pricelabs.pagination import Page

logger = logging.getLogger(__name__)


class Reservation(BaseModel):
    """A single reservation record from the PriceLabs API.

    Attributes:
        listing_id: Unique identifier for the listing.
        listing_name: Human-readable listing name, if available.
        reservation_id: Unique identifier for the reservation.
        check_in: Check-in date string (YYYY-MM-DD).
        check_out: Check-out date string (YYYY-MM-DD).
        booked_date: Date the booking was made, if available.
        booking_status: Current status — ``booked`` or ``cancelled``.
        rental_revenue: Revenue from the rental, if provided.
        total_cost: Total cost charged to the guest, if provided.
        no_of_days: Number of nights for the stay.
        currency: ISO currency code for monetary fields.
        cancelled_on: Cancellation date when booking_status is ``cancelled``.
        cleaning_fees: Cleaning fee amount in the listing currency.
        booking_channel: Platform the booking was made through.
        channelConfirmationCode: Confirmation code from the booking channel.
        min_price_type: Minimum price type configuration.
    """

    listing_id: str
    listing_name: str | None = None
    reservation_id: str
    check_in: str
    check_out: str
    booked_date: str | None = None
    booking_status: str
    rental_revenue: float | None = None
    total_cost: float | None = None
    no_of_days: int | None = None
    currency: str | None = None
    cancelled_on: str | None = None
    cleaning_fees: float | None = None
    booking_channel: str | None = None
    channelConfirmationCode: str | None = None
    min_price_type: str | None = None


class Reservations:
    """Namespace for reservation-related API operations.

    Args:
        http: Configured HTTP transport client.
    """

    def __init__(self, http: HTTPClient) -> None:
        """Initialize the Reservations namespace with the given HTTP client."""
        self._http = http

    def list(
        self,
        pms: str,
        start_date: str,
        end_date: str,
        listing_id: str | None = None,
        limit: int = 100,
        offset: int = 0,
        include_hidden: bool = False,
    ) -> Page[Reservation]:
        """Fetch a single page of reservations from the API.

        Args:
            pms: Property management system name (required).
            start_date: Return reservations with check-in on or after this date, YYYY-MM-DD (required).
            end_date: Return reservations with check-out on or before this date, YYYY-MM-DD (required).
            listing_id: Filter to a specific listing.
            limit: Maximum number of records per page. Defaults to 100.
            offset: Number of records to skip. Defaults to 0.
            include_hidden: When True, include hidden listings. Defaults to False.

        Returns:
            A ``Page[Reservation]`` containing the current slice of results.
        """
        params: dict = {
            "pms": pms,
            "start_date": start_date,
            "end_date": end_date,
            "limit": limit,
            "offset": offset,
            "include_hidden": include_hidden,
        }
        if listing_id is not None:
            params["listing_id"] = listing_id

        logger.info("Fetching reservations offset=%d limit=%d", offset, limit)
        raw = self._http.get("/v1/reservation_data", params=params)
        reservations = [Reservation.model_validate(r) for r in raw.get("data", [])]
        page = Page[Reservation](
            data=reservations,
            next_page=raw.get("next_page", False),
            pms_name=raw.get("pms_name"),
        )
        logger.info("Fetched %d reservations next_page=%s", len(reservations), page.next_page)
        return page

    def list_all(self, **kwargs: object) -> Iterator[Reservation]:
        """Iterate over all reservations, fetching additional pages automatically.

        Accepts the same keyword arguments as :meth:`list`. Yields individual
        :class:`Reservation` objects until ``next_page`` is ``False``.

        Args:
            **kwargs: Forwarded to :meth:`list`. ``limit`` and ``offset`` control
                page size and the starting position respectively.

        Yields:
            Individual :class:`Reservation` objects across all pages.
        """
        limit = int(kwargs.get("limit", 100))  # type: ignore[arg-type]
        offset = int(kwargs.get("offset", 0))  # type: ignore[arg-type]

        logger.info("list_all started limit=%d offset=%d", limit, offset)
        while True:
            kwargs["limit"] = limit
            kwargs["offset"] = offset
            page = self.list(**kwargs)  # type: ignore[arg-type]
            yield from page.data
            if not page.next_page:
                logger.info("list_all completed")
                break
            offset += limit

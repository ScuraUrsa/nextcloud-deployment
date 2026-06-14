"""
Lago API wrapper for test automation.

Covers:
  - Plan management
  - Subscription management
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

import requests


# ---------------------------------------------------------------------------
# Custom exception
# ---------------------------------------------------------------------------

class LagoAPIError(Exception):
    """Raised when a Lago API call fails."""

    def __init__(self, message: str, status_code: Optional[int] = None, response_text: str = ""):
        super().__init__(message)
        self.status_code = status_code
        self.response_text = response_text


# ---------------------------------------------------------------------------
# Typed response dataclasses
# ---------------------------------------------------------------------------

@dataclass
class LagoPlan:
    lago_id: str
    name: str
    code: str
    interval: str  # e.g. "monthly", "yearly"
    amount_cents: int
    amount_currency: str
    pay_in_advance: bool = False
    description: str = ""


@dataclass
class LagoSubscription:
    lago_id: str
    external_id: str
    plan_code: str
    status: str  # active, pending, terminated, canceled
    started_at: Optional[str] = None
    canceled_at: Optional[str] = None
    terminated_at: Optional[str] = None


# ---------------------------------------------------------------------------
# LagoAPI
# ---------------------------------------------------------------------------

class LagoAPI:
    """Lago billing API wrapper."""

    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        })

    def _request(
        self,
        method: str,
        path: str,
        json_data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        url = f"{self.base_url}/api/v1/{path.lstrip('/')}"
        resp = self.session.request(
            method=method,
            url=url,
            json=json_data,
            params=params,
            timeout=30,
        )
        if not resp.ok:
            raise LagoAPIError(
                f"Lago {method} {path} failed: {resp.status_code}",
                status_code=resp.status_code,
                response_text=resp.text,
            )
        return resp.json()

    # -- plans -------------------------------------------------------------

    def create_plan(
        self,
        name: str,
        code: str,
        interval: str = "monthly",
        amount_cents: int = 0,
        amount_currency: str = "EUR",
        pay_in_advance: bool = False,
        description: str = "",
    ) -> LagoPlan:
        """Create a new plan."""
        payload = {
            "plan": {
                "name": name,
                "code": code,
                "interval": interval,
                "amount_cents": amount_cents,
                "amount_currency": amount_currency,
                "pay_in_advance": pay_in_advance,
                "description": description,
            }
        }
        data = self._request("POST", "plans", json_data=payload)
        plan_data = data.get("plan", data)
        return LagoPlan(
            lago_id=plan_data.get("lago_id", ""),
            name=plan_data.get("name", name),
            code=plan_data.get("code", code),
            interval=plan_data.get("interval", interval),
            amount_cents=plan_data.get("amount_cents", amount_cents),
            amount_currency=plan_data.get("amount_currency", amount_currency),
            pay_in_advance=plan_data.get("pay_in_advance", pay_in_advance),
            description=plan_data.get("description", description),
        )

    # -- subscriptions -----------------------------------------------------

    def create_subscription(
        self,
        external_customer_id: str,
        plan_code: str,
        external_id: Optional[str] = None,
    ) -> LagoSubscription:
        """Create a new subscription for a customer."""
        payload = {
            "subscription": {
                "external_customer_id": external_customer_id,
                "plan_code": plan_code,
            }
        }
        if external_id:
            payload["subscription"]["external_id"] = external_id

        data = self._request("POST", "subscriptions", json_data=payload)
        sub_data = data.get("subscription", data)
        return LagoSubscription(
            lago_id=sub_data.get("lago_id", ""),
            external_id=sub_data.get("external_id", external_id or ""),
            plan_code=sub_data.get("plan_code", plan_code),
            status=sub_data.get("status", "active"),
            started_at=sub_data.get("started_at"),
            canceled_at=sub_data.get("canceled_at"),
            terminated_at=sub_data.get("terminated_at"),
        )

    def get_subscription(self, external_id: str) -> LagoSubscription:
        """Get a subscription by external ID."""
        data = self._request("GET", f"subscriptions/{external_id}")
        sub_data = data.get("subscription", data)
        return LagoSubscription(
            lago_id=sub_data.get("lago_id", ""),
            external_id=sub_data.get("external_id", external_id),
            plan_code=sub_data.get("plan_code", ""),
            status=sub_data.get("status", ""),
            started_at=sub_data.get("started_at"),
            canceled_at=sub_data.get("canceled_at"),
            terminated_at=sub_data.get("terminated_at"),
        )

    def cancel_subscription(self, external_id: str) -> LagoSubscription:
        """Cancel a subscription."""
        data = self._request("DELETE", f"subscriptions/{external_id}")
        sub_data = data.get("subscription", data)
        return LagoSubscription(
            lago_id=sub_data.get("lago_id", ""),
            external_id=sub_data.get("external_id", external_id),
            plan_code=sub_data.get("plan_code", ""),
            status=sub_data.get("status", "canceled"),
            started_at=sub_data.get("started_at"),
            canceled_at=sub_data.get("canceled_at"),
            terminated_at=sub_data.get("terminated_at"),
        )

    def list_subscriptions(
        self,
        external_customer_id: Optional[str] = None,
        plan_code: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[LagoSubscription]:
        """List subscriptions with optional filters."""
        params: Dict[str, Any] = {}
        if external_customer_id:
            params["external_customer_id"] = external_customer_id
        if plan_code:
            params["plan_code"] = plan_code
        if status:
            params["status"] = status

        data = self._request("GET", "subscriptions", params=params)
        subs = data.get("subscriptions", [])
        results: List[LagoSubscription] = []
        for s in subs:
            results.append(LagoSubscription(
                lago_id=s.get("lago_id", ""),
                external_id=s.get("external_id", ""),
                plan_code=s.get("plan_code", ""),
                status=s.get("status", ""),
                started_at=s.get("started_at"),
                canceled_at=s.get("canceled_at"),
                terminated_at=s.get("terminated_at"),
            ))
        return results

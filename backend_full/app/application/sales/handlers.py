from __future__ import annotations

import hashlib
import json
import logging
import time
from dataclasses import dataclass

from fastapi import HTTPException
from fastapi.responses import PlainTextResponse

from app.application.common.uow import AbstractUnitOfWork
from app.config import get_settings
from app.models.models import Terminal
from app.security.hmac import _generate_hmac_signature, verify_hmac_signature
from app.services.sales_service import SalesService


@dataclass(frozen=True)
class SubmitSaleCommand:
    method: str
    path: str
    body: bytes
    payload: dict
    terminal_id: str
    signature: str
    timestamp: str


@dataclass(frozen=True)
class DailyLogCommand:
    method: str
    path: str
    body: bytes
    payload: dict
    terminal_id: str
    signature: str
    timestamp: str


@dataclass(frozen=True)
class RegisterSalesTransactionsCommand:
    method: str
    path: str
    body: bytes
    terminal_id: str
    signature: str
    timestamp: str


@dataclass(frozen=True)
class GenerateCurlExampleQuery:
    pass


@dataclass(frozen=True)
class GenerateCurlCommandQuery:
    pass


class SubmitSaleHandler:
    def handle(self, command: SubmitSaleCommand, uow: AbstractUnitOfWork) -> dict:
        verify_hmac_signature(
            command.method,
            command.path,
            command.body,
            command.terminal_id,
            command.signature,
            command.timestamp,
        )
        db = uow.session
        terminal = db.query(Terminal).filter_by(terminal_id=command.terminal_id).first()
        if not terminal:
            raise HTTPException(status_code=401, detail="Unknown terminal")
        service = SalesService(db)
        sale = service.ingest_sale(
            command.payload["event_id"],
            terminal.id,
            terminal.location_id,
            command.payload["lines"],
        )
        return {"event_id": sale.event_id, "status": sale.status}


class DailyLogHandler:
    def handle(self, command: DailyLogCommand, uow: AbstractUnitOfWork) -> dict:
        verify_hmac_signature(
            command.method,
            command.path,
            command.body,
            command.terminal_id,
            command.signature,
            command.timestamp,
        )
        db = uow.session
        terminal = db.query(Terminal).filter_by(terminal_id=command.terminal_id).first()
        if not terminal:
            raise HTTPException(status_code=401, detail="Unknown terminal")
        service = SalesService(db)
        return service.reconcile_daily(terminal.id, terminal.location_id, command.payload["events"])


class RegisterSalesTransactionsHandler:
    def handle(self, command: RegisterSalesTransactionsCommand, uow: AbstractUnitOfWork) -> dict:
        verify_hmac_signature(
            command.method,
            command.path,
            command.body,
            command.terminal_id,
            command.signature,
            command.timestamp,
        )
        payload = json.loads(command.body.decode())
        db = uow.session
        terminal = db.query(Terminal).filter_by(terminal_id=command.terminal_id).first()
        if not terminal:
            raise HTTPException(status_code=401, detail="Unknown terminal")

        settings = get_settings()
        service = SalesService(db)
        try:
            result = service.register_sales_transactions(
                terminal=terminal,
                payload=payload,
                default_status=settings.sales_event_default_status,
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return result


class GenerateCurlExampleHandler:
    def handle(self, query: GenerateCurlExampleQuery, uow: AbstractUnitOfWork) -> dict:
        settings = get_settings()
        if settings.env == "PROD":
            raise HTTPException(status_code=404, detail="Endpoint not available in production")

        method = "POST"
        path = "/api/v1/sales/register-sales-transactions"
        data = {
            "sales": [{"sale_id": 456, "terminal_id": "T-1", "user_id": 12, "timestamp": "2026-01-01T10:00:00Z", "items": []}],
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }

        body = json.dumps(data, separators=(",", ":"))
        timestamp = "<UNIX_TIMESTAMP>"
        terminal_id = "<TERMINAL_ID>"
        signature = "<HMAC_SIGNATURE>"

        data_formatted = json.dumps(data, separators=(",", ":"))
        curl_command = (
            f"curl --request POST --url http://localhost:8001{path} "
            f"--header 'X-Signature: {signature}' "
            f"--header 'X-Terminal-ID: {terminal_id}' "
            f"--header 'X-Timestamp: {timestamp}' "
            f"--header 'content-type: application/json' "
            f"--data-binary '{data_formatted}'"
        )
        multiline_curl = f"""curl --request POST \\
  --url http://localhost:8001{path} \\
  --header 'X-Signature: {signature}' \\
  --header 'X-Terminal-ID: {terminal_id}' \\
  --header 'X-Timestamp: {timestamp}' \\
  --header 'content-type: application/json' \\
  --data '{data_formatted}' """

        return {
            "curl_command": curl_command,
            "multiline_curl": multiline_curl,
            "signature_details": {
                "method": method,
                "path": path,
                "timestamp": timestamp,
                "terminal_id": terminal_id,
                "body_hash": hashlib.sha256(body.encode()).hexdigest(),
                "canonical_string": f"{method.upper()}|{path}|<UNIX_TIMESTAMP>|{hashlib.sha256(body.encode()).hexdigest()}",
                "generated_signature": "<HMAC_SIGNATURE>",
            },
        }


class GenerateCurlCommandHandler:
    def handle(self, query: GenerateCurlCommandQuery, uow: AbstractUnitOfWork) -> PlainTextResponse:
        settings = get_settings()
        if settings.env == "PROD":
            raise HTTPException(status_code=404, detail="Endpoint not available in production")

        timestamp = str(int(time.time()))
        method = "POST"
        path = "/api/v1/sales/register-sales-transactions"

        terminal_id = "T-1"
        terminal_secret = "secret"

        data = {
            "sales": [
                {
                    "sale_id": 456,
                    "terminal_id": terminal_id,
                    "user_id": 12,
                    "timestamp": "2026-01-01T10:00:00Z",
                    "items": [
                        {"product_id": "ABC123", "quantity": 5, "price": 24.85},
                        {"product_id": "DEF456", "quantity": 2, "price": 15.50},
                    ],
                },
                {
                    "sale_id": 457,
                    "terminal_id": terminal_id,
                    "user_id": 12,
                    "timestamp": "2026-01-01T14:15:23Z",
                    "items": [
                        {"product_id": "CCC425", "quantity": 1, "price": 12.85},
                        {"product_id": "DDD456", "quantity": 3, "price": 12.50},
                    ],
                },
            ],
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(int(timestamp))),
        }
        body_with_updated_time = json.dumps(data, separators=(",", ":"))

        logger = logging.getLogger(__name__)
        logger.info(f"Generated body for signature: {body_with_updated_time}")
        logger.info(f"Body hash: {hashlib.sha256(body_with_updated_time.encode()).hexdigest()}")

        signature = _generate_hmac_signature(method, path, body_with_updated_time, terminal_secret, timestamp)
        curl_command = (
            f"curl --request POST --url http://localhost:8001{path} "
            f"--header 'X-Signature: {signature}' "
            f"--header 'X-Terminal-ID: {terminal_id}' "
            f"--header 'X-Timestamp: {timestamp}' "
            f"--header 'content-type: application/json' "
            f"--data '{body_with_updated_time}'"
        )
        return PlainTextResponse(content=curl_command)

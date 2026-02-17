import json
from typing import Callable

from fastapi import APIRouter, Depends, Header, Request

from app.api.v1.deps.uow import get_uow_factory
from app.audit.context import reset_audit_user_id, set_audit_user_id
from app.application.common import dispatch_command, dispatch_query
from app.application.common.uow import AbstractUnitOfWork
from app.application.sales.handlers import (
    DailyLogCommand,
    DailyLogHandler,
    GenerateCurlCommandHandler,
    GenerateCurlCommandQuery,
    GenerateCurlExampleHandler,
    GenerateCurlExampleQuery,
    RegisterSalesTransactionsCommand,
    RegisterSalesTransactionsHandler,
    SubmitSaleCommand,
    SubmitSaleHandler,
)

router = APIRouter(prefix="/sales", tags=["sales"])


def _to_int(value) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _extract_user_id(payload: dict | None) -> int | None:
    if not isinstance(payload, dict):
        return None
    direct = _to_int(payload.get("user_id"))
    if direct is not None:
        return direct

    sales = payload.get("sales")
    if isinstance(sales, list):
        for sale in sales:
            if isinstance(sale, dict):
                nested = _to_int(sale.get("user_id"))
                if nested is not None:
                    return nested

    events = payload.get("events")
    if isinstance(events, list):
        for event in events:
            if isinstance(event, dict):
                nested = _to_int(event.get("user_id"))
                if nested is not None:
                    return nested
    return None


@router.post("")
async def submit_sale(
    request: Request,
    payload: dict,
    x_terminal_id: str = Header(..., alias="X-Terminal-ID"),
    x_signature: str = Header(..., alias="X-Signature"),
    x_timestamp: str = Header(..., alias="X-Timestamp"),
    uow_factory: Callable[[], AbstractUnitOfWork] = Depends(get_uow_factory),
):
    """Принимает единичное событие продажи от терминала."""
    body = await request.body()
    extracted_user_id = _extract_user_id(payload)
    if extracted_user_id is not None:
        request.state.request_user_id_override = extracted_user_id
    token = set_audit_user_id(extracted_user_id) if extracted_user_id is not None else None
    try:
        return dispatch_command(
            uow_factory,
            SubmitSaleHandler(),
            SubmitSaleCommand(
                method=request.method,
                path=request.url.path,
                body=body,
                payload=payload,
                terminal_id=x_terminal_id,
                signature=x_signature,
                timestamp=x_timestamp,
            ),
        )
    finally:
        if token is not None:
            reset_audit_user_id(token)


@router.post("/daily-log")
async def daily_log(
    request: Request,
    payload: dict,
    x_terminal_id: str = Header(..., alias="X-Terminal-ID"),
    x_signature: str = Header(..., alias="X-Signature"),
    x_timestamp: str = Header(..., alias="X-Timestamp"),
    uow_factory: Callable[[], AbstractUnitOfWork] = Depends(get_uow_factory),
):
    """Принимает пакет daily-log событий продаж от терминала."""
    body = await request.body()
    extracted_user_id = _extract_user_id(payload)
    if extracted_user_id is not None:
        request.state.request_user_id_override = extracted_user_id
    token = set_audit_user_id(extracted_user_id) if extracted_user_id is not None else None
    try:
        return dispatch_command(
            uow_factory,
            DailyLogHandler(),
            DailyLogCommand(
                method=request.method,
                path=request.url.path,
                body=body,
                payload=payload,
                terminal_id=x_terminal_id,
                signature=x_signature,
                timestamp=x_timestamp,
            ),
        )
    finally:
        if token is not None:
            reset_audit_user_id(token)


@router.post("/register-sales-transactions")
async def register_sales_transactions(
    request: Request,
    x_terminal_id: str = Header(..., alias="X-Terminal-ID"),
    x_signature: str = Header(..., alias="X-Signature"),
    x_timestamp: str = Header(..., alias="X-Timestamp"),
    uow_factory: Callable[[], AbstractUnitOfWork] = Depends(get_uow_factory),
):
    """Регистрирует пакет sales transactions в формате терминала."""
    body = await request.body()
    payload = None
    try:
        payload = json.loads(body.decode("utf-8"))
    except Exception:
        payload = None
    extracted_user_id = _extract_user_id(payload)
    if extracted_user_id is not None:
        request.state.request_user_id_override = extracted_user_id
    token = set_audit_user_id(extracted_user_id) if extracted_user_id is not None else None
    try:
        return dispatch_command(
            uow_factory,
            RegisterSalesTransactionsHandler(),
            RegisterSalesTransactionsCommand(
                method=request.method,
                path=request.url.path,
                body=body,
                terminal_id=x_terminal_id,
                signature=x_signature,
                timestamp=x_timestamp,
            ),
        )
    finally:
        if token is not None:
            reset_audit_user_id(token)


@router.get("/generate-curl-example")
async def generate_curl_example(
    uow_factory: Callable[[], AbstractUnitOfWork] = Depends(get_uow_factory),
):
    """Возвращает пример curl для интеграции с sales API."""
    return dispatch_query(uow_factory, GenerateCurlExampleHandler(), GenerateCurlExampleQuery())


@router.get("/generate-curl-command")
async def generate_curl_command(
    uow_factory: Callable[[], AbstractUnitOfWork] = Depends(get_uow_factory),
):
    """Возвращает готовую команду curl для текущих настроек."""
    return dispatch_query(uow_factory, GenerateCurlCommandHandler(), GenerateCurlCommandQuery())

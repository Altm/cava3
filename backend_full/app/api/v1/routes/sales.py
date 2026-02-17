from typing import Callable

from fastapi import APIRouter, Depends, Header, Request

from app.api.v1.deps.uow import get_uow_factory
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


@router.post("")
async def submit_sale(
    request: Request,
    payload: dict,
    x_terminal_id: str = Header(..., alias="X-Terminal-ID"),
    x_signature: str = Header(..., alias="X-Signature"),
    x_timestamp: str = Header(..., alias="X-Timestamp"),
    uow_factory: Callable[[], AbstractUnitOfWork] = Depends(get_uow_factory),
):
    body = await request.body()
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


@router.post("/daily-log")
async def daily_log(
    request: Request,
    payload: dict,
    x_terminal_id: str = Header(..., alias="X-Terminal-ID"),
    x_signature: str = Header(..., alias="X-Signature"),
    x_timestamp: str = Header(..., alias="X-Timestamp"),
    uow_factory: Callable[[], AbstractUnitOfWork] = Depends(get_uow_factory),
):
    body = await request.body()
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


@router.post("/register-sales-transactions")
async def register_sales_transactions(
    request: Request,
    x_terminal_id: str = Header(..., alias="X-Terminal-ID"),
    x_signature: str = Header(..., alias="X-Signature"),
    x_timestamp: str = Header(..., alias="X-Timestamp"),
    uow_factory: Callable[[], AbstractUnitOfWork] = Depends(get_uow_factory),
):
    body = await request.body()
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


@router.get("/generate-curl-example")
async def generate_curl_example(
    uow_factory: Callable[[], AbstractUnitOfWork] = Depends(get_uow_factory),
):
    return dispatch_query(uow_factory, GenerateCurlExampleHandler(), GenerateCurlExampleQuery())


@router.get("/generate-curl-command")
async def generate_curl_command(
    uow_factory: Callable[[], AbstractUnitOfWork] = Depends(get_uow_factory),
):
    return dispatch_query(uow_factory, GenerateCurlCommandHandler(), GenerateCurlCommandQuery())

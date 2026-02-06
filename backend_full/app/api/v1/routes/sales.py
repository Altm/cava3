import os
import hashlib
import json
import time
from fastapi import APIRouter, Depends, HTTPException, Request, Header
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session
from app.api.v1.deps.auth import get_db
from app.security.hmac import verify_hmac_signature, _generate_hmac_signature
from app.models.models import Terminal
from app.services.sales_service import SalesService
from app.config import get_settings

router = APIRouter(prefix="/sales", tags=["sales"])


@router.post("")
async def submit_sale(
    request: Request,
    payload: dict,
    x_terminal_id: str = Header(..., alias="X-Terminal-ID"),
    x_signature: str = Header(..., alias="X-Signature"),
    x_timestamp: str = Header(..., alias="X-Timestamp"),
    db: Session = Depends(get_db),
):
    verify_hmac_signature(request.method, request.url.path, await request.body(), x_terminal_id, x_signature, x_timestamp)
    terminal = db.query(Terminal).filter_by(terminal_id=x_terminal_id).first()
    if not terminal:
        raise HTTPException(status_code=401, detail="Unknown terminal")
    service = SalesService(db)
    sale = service.ingest_sale(payload["event_id"], terminal.id, terminal.location_id, payload["lines"])
    db.commit()
    return {"event_id": sale.event_id, "status": sale.status}


@router.post("/daily-log")
async def daily_log(
    request: Request,
    payload: dict,
    x_terminal_id: str = Header(..., alias="X-Terminal-ID"),
    x_signature: str = Header(..., alias="X-Signature"),
    x_timestamp: str = Header(..., alias="X-Timestamp"),
    db: Session = Depends(get_db),
):
    verify_hmac_signature(request.method, request.url.path, await request.body(), x_terminal_id, x_signature, x_timestamp)
    terminal = db.query(Terminal).filter_by(terminal_id=x_terminal_id).first()
    if not terminal:
        raise HTTPException(status_code=401, detail="Unknown terminal")
    service = SalesService(db)
    result = service.reconcile_daily(terminal.id, terminal.location_id, payload["events"])
    db.commit()
    return result


@router.post("/deduct-stock")
async def deduct_stock(
    request: Request,
    x_terminal_id: str = Header(..., alias="X-Terminal-ID"),
    x_signature: str = Header(..., alias="X-Signature"),
    x_timestamp: str = Header(..., alias="X-Timestamp"),
):
    """
    Endpoint for deducting sold items from stock.
    Expects a JSON body with sales data.
    """
    # Get the raw body for signature verification
    body_bytes = await request.body()
    #body_str = body_bytes.decode()

    # Normalize the JSON to remove extra whitespace and ensure consistent format
    #try:
    #    parsed_json = json.loads(body_str)
    #    normalized_body = json.dumps(parsed_json, separators=(',', ':'))
    #    normalized_body_bytes = normalized_body.encode()
    #except json.JSONDecodeError:
    #    raise HTTPException(status_code=400, detail="Invalid JSON in request body")

    # Verify HMAC signature using the normalized body
    verify_hmac_signature(
        request.method,
        request.url.path,
        body_bytes,
        x_terminal_id,
        x_signature,
        x_timestamp
    )

    # Parse the body to get the payload
    import json
    payload = json.loads(body_bytes.decode())

    # Return 200 and the received data
    return {"status": "success", "received_data": payload}



@router.get("/generate-curl-example")
async def generate_curl_example():
    """
    Generate a curl example for the deduct-stock endpoint.
    Available only in non-production environments.
    """
    # Check if we're in production environment
    settings = get_settings()
    if settings.env == "PROD":
        raise HTTPException(status_code=404, detail="Endpoint not available in production")

    # Sample data
    method = "POST"
    path = "/api/v1/sales/deduct-stock"
    data = {
        "sales": [
            {"product_id": "ABC123", "quantity": 5},
            {"product_id": "DEF456", "quantity": 2}
        ],
        "timestamp": time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
    }

    # Convert data to JSON string without extra spaces
    body = json.dumps(data, separators=(',', ':'))
    timestamp = str(int(time.time()))

    # Get a sample terminal and its secret from the database
    # For this example, we'll use a default terminal with ID "T-1" and secret "secret"
    terminal_id = "T-1"
    terminal_secret = "secret"

    # Generate signature
    signature = _generate_hmac_signature(method, path, body, terminal_secret, timestamp)

    # Construct curl command - format it as a single line for easy copy/paste
    # Use --data-binary to avoid any interpretation of special characters
    data_formatted = json.dumps(data, separators=(',', ':'))
    curl_command = f"curl --request POST --url http://localhost:8001{path} --header 'X-Signature: {signature}' --header 'X-Terminal-ID: {terminal_id}' --header 'X-Timestamp: {timestamp}' --header 'content-type: application/json' --data-binary '{data_formatted}'"

    # Also provide a multi-line version for readability
    multiline_curl = f'''curl --request POST \\
  --url http://localhost:8001{path} \\
  --header 'X-Signature: {signature}' \\
  --header 'X-Terminal-ID: {terminal_id}' \\
  --header 'X-Timestamp: {timestamp}' \\
  --header 'content-type: application/json' \\
  --data '{data_formatted}' '''

    return {
        "curl_command": curl_command,
        "multiline_curl": multiline_curl,
        "signature_details": {
            "method": method,
            "path": path,
            "timestamp": timestamp,
            "terminal_id": terminal_id,
            "terminal_secret_used": terminal_secret,
            "body_hash": hashlib.sha256(body.encode()).hexdigest(),
            "canonical_string": f"{method.upper()}|{path}|{timestamp}|{hashlib.sha256(body.encode()).hexdigest()}",
            "generated_signature": signature
        }
    }


@router.get("/generate-curl-command")
async def generate_curl_command():
    """
    Generate a curl command with correct HMAC signature.
    Available only in non-production environments.
    The generated command will be valid for hmac_clock_skew_seconds period.
    """
    # Check if we're in production environment
    settings = get_settings()
    if settings.env == "PROD":
        raise HTTPException(status_code=404, detail="Endpoint not available in production")

    # Use current timestamp to ensure validity for hmac_clock_skew_seconds
    timestamp = str(int(time.time()))
    # Sample data with the correct timestamp
    method = "POST"
    path = "/api/v1/sales/deduct-stock"
    data = {
        "sales": [
            {"product_id": "ABC123", "quantity": 5},
            {"product_id": "DEF456", "quantity": 2}
        ],
        "timestamp": time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(int(timestamp)))
    }

    # Use the same format as in the actual request processing
    body_with_updated_time = json.dumps(data, separators=(',', ':'))

    # Log for debugging
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"Generated body for signature: {body_with_updated_time}")
    logger.info(f"Body hash: {hashlib.sha256(body_with_updated_time.encode()).hexdigest()}")

    # Fixed values for demo purposes
    terminal_id = "T-1"
    terminal_secret = "secret"

    # Generate signature
    signature = _generate_hmac_signature(method, path, body_with_updated_time, terminal_secret, timestamp)

    # Create curl command
    curl_command = f"curl --request POST --url http://localhost:8001{path} --header 'X-Signature: {signature}' --header 'X-Terminal-ID: {terminal_id}' --header 'X-Timestamp: {timestamp}' --header 'content-type: application/json' --data '{body_with_updated_time}'"

    # Return plain text response
    return PlainTextResponse(content=curl_command)

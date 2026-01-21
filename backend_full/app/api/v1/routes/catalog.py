from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.api.v1.deps.auth import get_db
from app.services.catalog_service import CatalogService

router = APIRouter(prefix="/catalog", tags=["catalog"])


@router.get("")
def get_catalog(location: int = Query(...), db: Session = Depends(get_db)):
    service = CatalogService(db)
    return {"location_id": location, "items": service.catalog_for_location(location)}

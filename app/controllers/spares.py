from fastapi import APIRouter
from app.services.spares_service import SparesService
from app.schemas.spares import SparesResponse

router = APIRouter(prefix="/api/spares", tags=["Spares"])

@router.get("/data", response_model=SparesResponse)
def get_spares_data():
    data = SparesService.get_all_spares()
    return SparesService.get_spares_summary(data)


@router.get("/pool-data")
def get_pool_data():
    data = SparesService.get_all_pool_spares()
    return SparesService.get_pool_summary(data)


@router.get("/meta")
def get_spares_meta(search: str = None):
    return SparesService.get_spares_meta(search)
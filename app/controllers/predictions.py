# app/controllers/predictions.py
from fastapi import APIRouter, Query, UploadFile, File, HTTPException
import pandas as pd
from io import BytesIO
from typing import List, Optional

from app.services.prediction_service import PredictionService
from app.schemas.alternate import AlternateUploadResponse
from app.services.prediction_service import PredictionService

from app.schemas.spares_upload import SparesUploadResponse

router = APIRouter(prefix="/predictions", tags=["predictions"])

service = PredictionService()


@router.post("/upload-spares", response_model=SparesUploadResponse)
async def upload_spares_data(file: UploadFile = File(...)):
    """
    Upload spares data file and upsert records into database.
    Replicates logic from db-export.py.
    """
    try:
        contents = await file.read()
        file_like = BytesIO(contents)
        
        df = None
        
        # Try reading as Excel first
        if file.filename.lower().endswith(('.xlsx', '.xls')):
            try:
                df = pd.read_excel(file_like)
                # print(f"Loaded {len(df)} rows as standard Excel")
            except Exception:
                # If Excel fails, try the specific format from db-export.py
                # (UTF-16LE TSV often used in SAP exports with .xlsx extension)
                print("Excel load failed, trying UTF-16LE TSV format (db-export style)...")
                file_like.seek(0)
                try:
                    df = pd.read_csv(file_like, encoding='utf-16-le', sep='\t', low_memory=False)
                    print(f"Loaded {len(df)} rows as UTF-16LE TSV")
                except Exception as csv_err:
                    raise HTTPException(
                        status_code=400, 
                        detail=f"Could not read file as Excel or UTF-16 TSV: {str(csv_err)}"
                    )
        elif file.filename.lower().endswith('.csv'):
            df = pd.read_csv(file_like)
        else:
            raise HTTPException(
                status_code=400, 
                detail="Unsupported file format. Use .xlsx, .xls, or .csv"
            )

        if df is None or df.empty:
            raise HTTPException(status_code=400, detail="File is empty")

        # Process (upsert) into database
        result = service.upsert_spares_data(df)

        return {
            "message": "Spares data uploaded and processed successfully",
            "total_records": result.get("total_records", 0),
            "processed": result.get("processed", 0),
            "inserted_or_updated": result.get("inserted_or_updated", 0)
        }

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500, 
            detail=f"Error processing file: {str(e)}"
        )


@router.get("/top-materials")
async def get_top_materials(
    plant: str = Query("5502", description="Plant code"),
    top_n: int = Query(10, ge=1, le=50)
):
    try:
        df = service.get_sales_data(plant)
        df_mapped = service.map_to_master_material(df)
        materials = service.get_top_materials(df_mapped, top_n)
        return {"plant": plant, "top_materials": materials}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/forecast/{material}")
async def forecast_material(
    material: str,
    plant: str = Query("5502"),
    forecast_weeks: int = Query(12, ge=4, le=52)
):
    try:
        df = service.get_sales_data(plant)
        df_mapped = service.map_to_master_material(df)
        
        result = service.forecast_material(material, df_mapped, forecast_weeks)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/forecast-batch")
async def forecast_batch(
    plant: str = Query("5502"),
    top_n: int = Query(5, ge=1, le=20),
    forecast_weeks: int = Query(12, ge=4, le=52)
):
    """Forecast top N materials - This can be heavy, use background tasks later"""
    try:
        df = service.get_sales_data(plant)
        df_mapped = service.map_to_master_material(df)
        materials = service.get_top_materials(df_mapped, top_n)
        
        results = []
        for mat in materials:
            res = service.forecast_material(mat, df_mapped, forecast_weeks)
            results.append(res)
        
        return {
            "plant": plant,
            "total_materials": len(results),
            "results": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/upload-alternates", response_model=AlternateUploadResponse)
async def upload_alternate_parts(file: UploadFile = File(...)):
    """
    Upload AlternatePartNumbers.xlsx and upsert records into database
    """
    if not file.filename.lower().endswith(('.xlsx', '.xls')):
        raise HTTPException(
            status_code=400, 
            detail="Only Excel files (.xlsx, .xls) are allowed"
        )

    try:
        # Read file contents as bytes
        contents = await file.read()
        
        # Convert bytes to file-like object for pandas
        excel_file = BytesIO(contents)
        
        print(f"UPLOADED FILE: {file.filename} | Size: {len(contents)/1024:.2f} KB")

        # Read Excel
        df = pd.read_excel(excel_file)
        
        print(f"LOADED {len(df)} ROWS FROM EXCEL")

        # Process (upsert) into database
        result = service.upsert_alternate_parts(df)

        return {
            "message": "`Alternate parts uploaded and processed successfully`",
            "total_records": result.get("total_records", len(df)),
            "inserted": result.get("inserted", 0),
            "updated": result.get("updated", 0)
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Error processing file: {str(e)}"
        )
# app/db/import_alternates.py
import pandas as pd
from sqlalchemy import create_engine, text
from app.config import settings  # or directly from .env

engine = create_engine(settings.DATABASE_URL)

def import_alternate_parts(excel_path: str = "AlternatePartNumbers.xlsx"):
    print("Reading Excel file...")
    df = pd.read_excel(excel_path, header=0)
    
    # Clean column names
    df.columns = df.columns.str.strip()
    
    print(f"Loaded {len(df)} rows with columns: {df.columns.tolist()}")
    
    # Insert into DB
    df.to_sql(
        'alternate_parts', 
        engine, 
        schema='spares', 
        if_exists='append', 
        index=False,
        method='multi'
    )
    
    print("Import completed successfully!")

if __name__ == "__main__":
    import_alternate_parts()
# app/services/prediction_service.py
import pandas as pd
import numpy as np
from datetime import datetime
from sqlalchemy import text, MetaData
from pmdarima import auto_arima
from sklearn.preprocessing import PowerTransformer
from statsmodels.tsa.stattools import adfuller
from sqlalchemy.dialects.postgresql import insert
from tqdm import tqdm

from app.db.connection import engine


class PredictionService:
    def __init__(self):
        self.alternate_df = None


    def load_alternate_mapping(self):
        """Load full alternate parts mapping from DB"""
        if self.alternate_df is None:
            query = """
                SELECT 
                    "Master Mat",
                    "Master Material Description",
                    "Substitute",
                    "Substitute Material Description",
                    "Material T",
                    "Branch",
                    "Stock @ Lo",
                    "Obsolete",
                    "Bidi Flag",
                    "Doc. Type",
                    "Purch.Org.",
                    "CoCode",
                    "Plant",
                    "Valid From",
                    "Valid To"
                FROM spares.alternate_parts
            """
            self.alternate_df = pd.read_sql(query, engine)
            
            # Clean column names (optional but helpful)
            self.alternate_df.columns = self.alternate_df.columns.str.strip()
            
            # Drop duplicates to avoid row expansion during merge
            self.alternate_df = self.alternate_df.drop_duplicates(subset=['Substitute'])
            
            # Drop rows where both Master and Substitute are missing
            self.alternate_df = self.alternate_df.dropna(
                subset=['Master Mat', 'Substitute'], 
                how='all'
            )
        return self.alternate_df


    def get_sales_data(self, plant: str = '5502') -> pd.DataFrame:
        """Fetch clean sales data"""
        query = text("""
            SELECT 
                po_date,
                material,
                inv_qty
            FROM spares.spares_data 
            WHERE plnt = :plant 
              AND po_date IS NOT NULL 
              AND material IS NOT NULL 
              AND inv_qty IS NOT NULL
            ORDER BY po_date
        """)
        df = pd.read_sql(query, engine, params={"plant": plant})
        
        # Critical: Force clean column names and remove any duplicates
        df.columns = df.columns.str.strip().str.lower()  # Normalize
        df = df.loc[:, ~df.columns.duplicated()]         # Remove duplicate columns
        
        df['po_date'] = pd.to_datetime(df['po_date'], errors='coerce')
        return df.dropna(subset=['po_date', 'material', 'inv_qty'])


    def map_to_master_material(self, df_sales: pd.DataFrame) -> pd.DataFrame:
        if df_sales.empty:
            return df_sales

        alt = self.load_alternate_mapping()
        
        df_sales = df_sales.copy()
        # Ensure sales data columns are unique before merge
        df_sales = df_sales.loc[:, ~df_sales.columns.duplicated()]

        df_mapped = df_sales.merge(
            alt[['Master Mat', 'Substitute']], 
            left_on='material', 
            right_on='Substitute', 
            how='left'
        )
        
        # Update 'material' column: use 'Master Mat' if it exists, else keep original
        df_mapped['material'] = df_mapped['Master Mat'].fillna(df_mapped['material'])
        
        # Select only the needed columns (this avoids keeping 'Substitute' and 'Master Mat' columns)
        # and ensures no duplicate 'material' column exists.
        final_df = df_mapped[['po_date', 'material', 'inv_qty']].copy()
        return final_df


    def get_top_materials(self, df: pd.DataFrame, top_n: int = 10):
        """Safe top materials"""
        if df.empty:
            return []
        
        df = df.loc[:, ~df.columns.duplicated()]  # Extra safety
        
        grouped = (df.groupby('material', as_index=False)['inv_qty']
                   .sum()
                   .sort_values('inv_qty', ascending=False))
        
        return grouped.head(top_n)['material'].tolist()


    def forecast_material(self, material: str, df: pd.DataFrame, forecast_weeks: int = 12):
        """Forecast with heavy duplicate column protection"""
        # Deep copy + full cleanup
        temp = df[df['material'] == material].copy()
        temp = temp.loc[:, ~temp.columns.duplicated(keep='first')]  # Remove duplicate columns

        total_qty = temp['inv_qty'].sum() if not temp.empty else 0
        
        if temp.empty or total_qty <= 36:
            return {
                "material": material,
                "status": "skipped",
                "reason": "low_volume" if total_qty > 0 else "no_data"
            }

        # Ensure proper datetime index
        temp['po_date'] = pd.to_datetime(temp['po_date'], errors='coerce')
        temp = temp.dropna(subset=['po_date', 'inv_qty'])
        
        if len(temp) < 10:
            return {"material": material, "status": "skipped", "reason": "insufficient_data"}

        # Create time series - VERY CLEAN
        ts = (temp.groupby('po_date', as_index=False)['inv_qty']
              .sum()
              .set_index('po_date')
              .sort_index())

        # Resample to weekly
        weekly_ts = ts['inv_qty'].resample('W').sum().fillna(0)

        if len(weekly_ts) < 20:
            return {"material": material, "status": "skipped", "reason": "insufficient_data"}

        # === Forecasting Logic ===
        results = []
        errors = []
        train_weeks = 52
        test_weeks = 4

        for end_train in range(train_weeks, len(weekly_ts) - test_weeks + 1, test_weeks):
            train = weekly_ts.iloc[:end_train]
            test = weekly_ts.iloc[end_train : end_train + test_weeks]

            if len(train) < 10:
                continue

            # Transform
            pt = PowerTransformer(method='yeo-johnson')
            train_trans = pt.fit_transform(train.values.reshape(-1, 1)).flatten()

            # Fit model
            model = auto_arima(
                train_trans,
                seasonal=True,
                stepwise=True,
                suppress_warnings=True,
                error_action='ignore',
                maxiter=50
            )

            # Predict
            forecast_trans = model.predict(n_periods=len(test))
            forecast = pt.inverse_transform(forecast_trans.reshape(-1, 1)).flatten()

            rmse = np.sqrt(np.mean((forecast - test.values) ** 2))
            errors.append(rmse)

            for d, pred, act in zip(test.index, forecast, test.values):
                results.append({
                    "date": d.strftime('%Y-%m-%d'),
                    "predicted": round(float(pred), 2),
                    "actual": round(float(act), 2)
                })

        # === Final Forecast ===
        pt_final = PowerTransformer(method='yeo-johnson')
        full_trans = pt_final.fit_transform(weekly_ts.values.reshape(-1, 1)).flatten()
        
        final_model = auto_arima(
            full_trans, 
            seasonal=False, 
            stepwise=True, 
            suppress_warnings=True
        )

        future_trans = final_model.predict(n_periods=forecast_weeks)
        future_forecast = pt_final.inverse_transform(future_trans.reshape(-1, 1)).flatten()

        future_dates = pd.date_range(
            start=weekly_ts.index[-1] + pd.Timedelta(weeks=1),
            periods=forecast_weeks,
            freq='W'
        )

        return {
            "material": material,
            "status": "success",
            "historical": [
                {"date": d.strftime('%Y-%m-%d'), "qty": round(float(q), 2)}
                for d, q in weekly_ts.items()
            ],
            "forecast": [
                {"date": d.strftime('%Y-%m-%d'), "predicted": round(float(p), 2)}
                for d, p in zip(future_dates, future_forecast)
            ],
            "avg_rmse": round(float(np.mean(errors)), 2) if errors else None,
            "total_historical_weeks": len(weekly_ts)
        }


    def upsert_alternate_parts(self, df: pd.DataFrame) -> dict:
        """Proper UPSERT using PostgreSQL ON CONFLICT"""
        if df.empty:
            return {"total_records": 0, "inserted": 0, "updated": 0}

        df.columns = df.columns.str.strip()

        # Clean numeric columns
        numeric_cols = ["Stock @ Lo", "Branch", "CoCode"]
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
                df[col] = df[col].where(pd.notnull(df[col]), None)

        # Clean date columns
        date_cols = ["Valid From", "Valid To"]
        for col in date_cols:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], dayfirst=True, errors='coerce')

        # Clean ID columns to strings (avoid .0 from floats)
        id_cols = ["Master Mat", "Substitute", "Branch", "CoCode", "Plant"]
        for col in id_cols:
            if col in df.columns:
                df[col] = df[col].astype(str).str.replace(r'\.0$', '', regex=True).replace('nan', None)

        # Deduplicate to avoid bulk upsert failure (cannot update same row twice in one batch)
        df = df.drop_duplicates(subset=['Master Mat', 'Substitute'], keep='last')

        # Use SQLAlchemy core for bulk upsert
        from sqlalchemy import table, column, MetaData
        from sqlalchemy.dialects.postgresql import insert

        metadata = MetaData()
        alt_table = table(
            'alternate_parts',
            *[column(c) for c in df.columns],
            schema='spares'
        )

        records = df.to_dict('records')

        inserted = 0
        updated = 0

        with engine.connect() as conn:
            batch_size = 5000
            pbar = tqdm(total=len(records), desc="Upserting Alternate Parts", unit="row")
            
            for i in range(0, len(records), batch_size):
                batch = records[i:i + batch_size]
                
                # Clean records while keeping consistent keys for bulk execution
                batch_clean = []
                for r in batch:
                    if pd.isnull(r.get('Master Mat')) or pd.isnull(r.get('Substitute')):
                        continue
                    clean_r = {k: (v if pd.notnull(v) else None) for k, v in r.items()}
                    batch_clean.append(clean_r)

                if not batch_clean:
                    pbar.update(len(batch))
                    continue

                stmt = insert(alt_table)
                stmt = stmt.on_conflict_do_update(
                    index_elements=['Master Mat', 'Substitute'],
                    set_={c.name: c for c in stmt.excluded if c.name not in ['Master Mat', 'Substitute']}
                )
                
                conn.execute(stmt, batch_clean)
                conn.commit()
                pbar.update(len(batch))
            
            pbar.close()

        total = len(df)
        return {
            "total_records": total,
            "processed": len(records),
            "inserted": 0, # Cannot easily distinguish in bulk without RETURNING
            "updated": len(records) # Returning total as 'updated' for compatibility
        }


    def upsert_spares_data(self, df: pd.DataFrame) -> dict:
        """Upsert spares data with cleaning logic from db-export.py"""
        if df.empty:
            return {"total_records": 0, "inserted": 0, "updated": 0}

        # --- Cleaning logic from db-export.py ---
        # Clean column names
        df.columns = [col.strip().lower()
                      .replace(' ', '_').replace('.', '').replace('-', '_').replace(',', '')
                      for col in df.columns]

        # Uppercase
        for col in ['city', 'material_description']:
            if col in df.columns:
                df[col] = df[col].astype(str).str.upper()

        # Dates
        for col in ['po_date', 'bill_date']:
            if col in df.columns:
                if not pd.api.types.is_datetime64_any_dtype(df[col]):
                    # Try multiple formats if needed, but db-export used %d.%m.%Y
                    df[col] = pd.to_datetime(df[col], format='%d.%m.%Y', errors='coerce')
                else:
                    # Already datetime, just ensure it's normalized if needed
                    df[col] = pd.to_datetime(df[col], errors='coerce')

        # Numerics
        num_cols = ['inv_qty', 'dealer_pri', 'basic_rate', 'net_value', 'tax', 'gross_val']
        for col in num_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(
                    df[col].astype(str).str.replace(',', '', regex=False).str.strip(), 
                    errors='coerce'
                )

        # Time
        if 'bill_time' in df.columns:
            df['bill_time'] = pd.to_datetime(df['bill_time'], format='%H:%M:%S', errors='coerce').dt.time

        # ID columns to strings (avoid .0 from floats)
        id_cols = ['billdoc', 'material', 'plnt', 'dv', 'dchl', 'sold_to_pt', 'ship_to', 'delivery', 'po_number', 'po_number1']
        for col in id_cols:
            if col in df.columns:
                df[col] = df[col].astype(str).str.replace(r'\.0$', '', regex=True).replace('nan', None)

        # Deduplicate to avoid bulk upsert failure (cannot update same row twice in one batch)
        df = df.drop_duplicates(subset=['billdoc', 'material'], keep='last')

        # --- Upsert logic ---
        from sqlalchemy import table, column, MetaData
        from sqlalchemy.dialects.postgresql import insert

        metadata = MetaData()
        # Define table structure for SQLAlchemy core
        # We only include columns that exist in the dataframe and the database
        db_columns = [
            "plnt", "billt", "dv", "dchl", "po_number", "po_date", "city", 
            "bill_date", "billdoc", "sold_to_pt", "ship_to_party_name", "ship_to", 
            "sold_party_name", "material", "material_description", "matl_group", 
            "inv_qty", "dealer_pri", "basic_rate", "net_value", "tax", "gross_val", 
            "bill_time", "delivery", "po_number1"
        ]
        
        valid_cols = [col for col in df.columns if col in db_columns]
        spares_table = table(
            'spares_data',
            *[column(c) for c in valid_cols],
            schema='spares'
        )

        records = df[valid_cols].to_dict('records')
        
        inserted = 0
        updated = 0

        with engine.connect() as conn:
            batch_size = 5000
            pbar = tqdm(total=len(records), desc="Upserting Spares Data", unit="row")
            
            for i in range(0, len(records), batch_size):
                batch = records[i:i + batch_size]
                
                # Clean and filter records
                batch_clean = []
                for r in batch:
                    if pd.isnull(r.get('billdoc')) or pd.isnull(r.get('material')):
                        continue
                    
                    clean_r = {k: (v if pd.notnull(v) else None) for k, v in r.items()}
                    batch_clean.append(clean_r)
                
                if not batch_clean:
                    pbar.update(len(batch))
                    continue

                stmt = insert(spares_table)
                stmt = stmt.on_conflict_do_update(
                    index_elements=['billdoc', 'material'],
                    set_={c.name: c for c in stmt.excluded if c.name not in ['billdoc', 'material']}
                )
                
                conn.execute(stmt, batch_clean)
                conn.commit()
                pbar.update(len(batch))
            
            pbar.close()

            # Refresh material master for fast search
            conn.execute(text("""
                INSERT INTO spares.material_master (material, material_description)
                SELECT material, MAX(material_description) 
                FROM spares.spares_data
                GROUP BY material
                ON CONFLICT (material) DO UPDATE SET material_description = EXCLUDED.material_description, last_updated = CURRENT_TIMESTAMP;
            """))
            conn.commit()

        return {
            "total_records": len(df),
            "processed": len(records),
            "inserted_or_updated": len(records)
        }

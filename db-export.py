import pandas as pd
from sqlalchemy import create_engine
from tqdm import tqdm
import time
import sys

# ==================== CONFIG ====================
DB_USER = 'sparesuser'      # ← UPDATE
DB_PASSWORD = 'spares1234#$'  # ← UPDATE
DB_HOST = 'localhost'
DB_PORT = '5432'
DB_NAME = 'spares_db' # ← UPDATE

# ==================== LOAD & CLEAN ====================
print("Loading data...")
df = pd.read_csv('Maha_Spare_Data.xlsx', 
                 encoding='utf-16-le', sep='\t', header=0, low_memory=False)

print(f"Data loaded: {df.shape[0]:,} rows × {df.shape[1]} columns")

# Clean column names
df.columns = [col.strip().lower()
              .replace(' ', '_').replace('.', '').replace('-', '_').replace(',', '')
              for col in df.columns]

# Uppercase
for col in ['city', 'material_description']:
    if col in df.columns:
        df[col] = df[col].astype(str).str.upper()

# Data cleaning
print("\nCleaning data types...")
for col in ['po_date', 'bill_date']:
    if col in df.columns:
        df[col] = pd.to_datetime(df[col], format='%d.%m.%Y', errors='coerce')

num_cols = ['inv_qty', 'dealer_pri', 'basic_rate', 'net_value', 'tax', 'gross_val']
for col in num_cols:
    if col in df.columns:
        df[col] = pd.to_numeric(
            df[col].astype(str).str.replace(',', '', regex=False).str.strip(), 
            errors='coerce'
        )

if 'bill_time' in df.columns:
    df['bill_time'] = pd.to_datetime(df['bill_time'], format='%H:%M:%S', errors='coerce').dt.time

print("Data cleaning completed.")

# Save CSV
print("\nSaving to data.csv...")
df.to_csv('data.csv', index=False)
print(f"[SUCCESS] data.csv saved with {len(df):,} rows!")

# ==================== POSTGRESQL INSERT ====================
print("\nConnecting to PostgreSQL...")
connection_string = f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
engine = create_engine(connection_string, pool_pre_ping=True)

try:
    with engine.connect() as conn:
        print("✅ Connected successfully!")

    before_count = pd.read_sql("SELECT COUNT(*) FROM spares.spares_data", engine).iloc[0, 0]
    print(f"Rows before insert: {before_count:,}")

    chunk_size = 500          # Safe and reasonable speed
    total_rows = len(df)
    inserted = 0
    start_time = time.time()

    print(f"\n🚀 Inserting {total_rows:,} rows in chunks of {chunk_size}...\n")

    for i in tqdm(range(0, total_rows, chunk_size), desc="Inserting chunks", unit="chunk"):
        chunk = df.iloc[i:i + chunk_size]
        try:
            chunk.to_sql(
                name='spares_data',
                con=engine,
                schema='spares',
                if_exists='append',
                index=False,
                method=None   # Avoids huge parameter lists
            )
            inserted += len(chunk)
        except Exception as chunk_err:
            print(f"\n[WARNING] Error in chunk starting at row {i}")
            print(f"   → {chunk_err}")
            print("   → Continuing with next chunks... (you may have some data loss in this chunk)")
            # Optional: break if you want to stop on first error

    elapsed_min = (time.time() - start_time) / 60

    after_count = pd.read_sql("SELECT COUNT(*) FROM spares.spares_data", engine).iloc[0, 0]
    print(f"\n[SUCCESS] Insert finished in {elapsed_min:.1f} minutes!")
    print(f"   → New rows inserted: {after_count - before_count:,}")
    print(f"   → Total rows now: {after_count:,}")

except Exception as e:
    print(f"\n[CRITICAL ERROR] {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
from app.db.connection import get_connection

def init_db():
    sql = """
    CREATE SCHEMA IF NOT EXISTS spares;
    CREATE SEQUENCE IF NOT EXISTS spares_data_id_seq;

    -- DROP TABLE spares.spares_data;
    -- DROP TABLE spares.alternate_parts;

    -- TRUNCATE TABLE spares.spares_data CASCADE;
    -- TRUNCATE TABLE spares.alternate_parts CASCADE;

    CREATE TABLE IF NOT EXISTS spares.spares_data
    (
        id integer NOT NULL DEFAULT nextval('spares_data_id_seq'::regclass),
        plnt character varying(255) COLLATE pg_catalog."default",
        billt character varying(255) COLLATE pg_catalog."default",
        dv integer,
        dchl integer,
        po_number character varying(255) COLLATE pg_catalog."default",
        po_date date,
        city character varying(255) COLLATE pg_catalog."default",
        bill_date date,
        billdoc character varying(255) COLLATE pg_catalog."default",
        sold_to_pt character varying(255) COLLATE pg_catalog."default",
        ship_to_party_name text COLLATE pg_catalog."default",
        ship_to character varying(255) COLLATE pg_catalog."default",
        sold_party_name text COLLATE pg_catalog."default",
        material character varying(255) COLLATE pg_catalog."default",
        material_description text COLLATE pg_catalog."default",
        matl_group character varying(255) COLLATE pg_catalog."default",
        inv_qty numeric(12,2),
        dealer_pri numeric(18,2),
        basic_rate numeric(18,2),
        net_value numeric(18,2),
        tax numeric(18,2),
        gross_val numeric(18,2),
        bill_time time without time zone,
        delivery character varying(255) COLLATE pg_catalog."default",
        po_number1 character varying(255) COLLATE pg_catalog."default",
        loaded_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
        CONSTRAINT spares_data_pkey PRIMARY KEY (id),
        CONSTRAINT unique_bill_material UNIQUE (billdoc, material)
    );

    CREATE TABLE IF NOT EXISTS spares.alternate_parts (
        id SERIAL PRIMARY KEY,
        
        -- Master Material
        "Master Mat" VARCHAR(100),
        "Master Material Description" TEXT,
        
        -- Substitute
        "Substitute" VARCHAR(100),
        "Substitute Material Description" TEXT,
        
        -- Other columns
        "Material T" VARCHAR(20),
        "Branch" VARCHAR(10),
        "Stock @ Lo" VARCHAR(100),
        "Obsolete" VARCHAR(10),
        "Bidi Flag" VARCHAR(10),
        "Doc. Type" VARCHAR(20),
        "Purch.Org." VARCHAR(20),
        "CoCode" VARCHAR(10),
        "Plant" VARCHAR(10),
        "Valid From" DATE,
        "Valid To" DATE,
        
        loaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        
        CONSTRAINT unique_master_substitute UNIQUE("Master Mat", "Substitute")
    );

    -- ALTER TABLE spares.alternate_parts 
    -- ADD CONSTRAINT IF NOT EXISTS unique_master_substitute 
    -- UNIQUE ("Master Mat", "Substitute");

    DO $$
    BEGIN
        IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'unique_bill_material') THEN
            ALTER TABLE spares.spares_data ADD CONSTRAINT unique_bill_material UNIQUE (billdoc, material);
        END IF;
    END;
    $$;

    -- Search Optimization
    CREATE EXTENSION IF NOT EXISTS pg_trgm;

    CREATE TABLE IF NOT EXISTS spares.material_master (
        material VARCHAR(255) PRIMARY KEY,
        material_description TEXT,
        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE INDEX IF NOT EXISTS idx_mat_master_trgm ON spares.material_master USING GIN (material gin_trgm_ops);
    CREATE INDEX IF NOT EXISTS idx_mat_desc_trgm ON spares.material_master USING GIN (material_description gin_trgm_ops);
    
    -- Populate if empty
    INSERT INTO spares.material_master (material, material_description)
    SELECT material, MAX(material_description) 
    FROM spares.spares_data
    GROUP BY material
    ON CONFLICT (material) DO UPDATE SET material_description = EXCLUDED.material_description;
    """
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(sql)
        conn.commit()
        cur.close()
        print("DATABASE INITIALIZED SUCCESSFULLY!")
    except Exception as e:
        print(f"ERROR INITIALIZING DATABASE: {e}")
        conn.rollback()
    finally:
        conn.close()

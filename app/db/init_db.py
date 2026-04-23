from app.db.connection import get_connection

def init_db():
    sql = """
    CREATE SCHEMA IF NOT EXISTS spares;
    CREATE SEQUENCE IF NOT EXISTS spares_data_id_seq;
    
    CREATE TABLE IF NOT EXISTS spares.spares_data
    (
        id integer NOT NULL DEFAULT nextval('spares_data_id_seq'::regclass),
        plnt character varying(20) COLLATE pg_catalog."default",
        billt character varying(20) COLLATE pg_catalog."default",
        dv integer,
        dchl integer,
        po_number character varying(100) COLLATE pg_catalog."default",
        po_date date,
        city character varying(100) COLLATE pg_catalog."default",
        bill_date date,
        billdoc character varying(100) COLLATE pg_catalog."default",
        sold_to_pt character varying(100) COLLATE pg_catalog."default",
        ship_to_party_name text COLLATE pg_catalog."default",
        ship_to character varying(100) COLLATE pg_catalog."default",
        sold_party_name text COLLATE pg_catalog."default",
        material character varying(100) COLLATE pg_catalog."default",
        material_description text COLLATE pg_catalog."default",
        matl_group character varying(50) COLLATE pg_catalog."default",
        inv_qty numeric(12,2),
        dealer_pri numeric(18,2),
        basic_rate numeric(18,2),
        net_value numeric(18,2),
        tax numeric(18,2),
        gross_val numeric(18,2),
        bill_time time without time zone,
        delivery character varying(100) COLLATE pg_catalog."default",
        po_number1 character varying(100) COLLATE pg_catalog."default",
        loaded_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
        CONSTRAINT spares_data_pkey PRIMARY KEY (id)
    );
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

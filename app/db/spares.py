from decimal import Decimal
from datetime import date, datetime
from app.db.connection import get_connection

def get_spares_data():
    conn = get_connection()
    try:
        cur = conn.cursor()

        cur.execute(
            """
            SELECT *
            FROM spares.spares_data
            WHERE plnt = '5502'
            """
        )

        rows = cur.fetchall()
        cur.close()
        conn.close()

        print(f"Rows returned: {len(rows)}")   # Better debugging

        if not rows:
            return []

        spares_data = []
        for r in rows:
            spares_data.append({
                "id": r[0],                    # assuming first column is id
                "plant": r[1],
                "billt": r[2],
                "dv": r[3],
                "dchl": r[4],
                "po_number": r[5],
                "po_date": r[6],
                "city": r[7],
                "bill_date": r[8],
                "bill_doc": r[9],
                "sold_to_pt": r[10],
                "ship_to_party_name": r[11],
                "ship_to": r[12],
                "sold_party_name": r[13],
                "material_code": r[14],
                "material_desc": r[15],
                "material_group": r[16],
                "inventory_qty": float(r[17]) if r[17] else None,        # Decimal → float
                "dealer_price": float(r[18]) if r[18] else None,
                "basic_rate": float(r[19]) if r[19] else None,
                "net_value": float(r[20]) if r[20] else None,
                "tax": float(r[21]) if r[21] else None,
                "gross_value": float(r[22]) if r[22] else None,
                "delivery": r[23],
            })

        return spares_data

    except Exception as e:
        print(f"Database Error: {e}")
        if 'conn' in locals():
            conn.close()
        raise
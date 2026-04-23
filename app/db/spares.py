from decimal import Decimal
from datetime import date, datetime
from app.db.connection import get_connection

def get_spares_data():
    conn = get_connection()
    try:
        cur = conn.cursor()

        cur.execute(
            """
                WITH monthly AS (
                    SELECT
                        material,
                        material_description,
                        city AS branch,
                        plnt::int AS plant,
                        DATE_TRUNC('month', bill_date::date) AS month_date,
                        SUM(inv_qty) AS qty,
                        SUM(gross_val) AS sales_value
                    FROM spares_data
                    GROUP BY material, material_description, city, plnt, DATE_TRUNC('month', bill_date::date)
                ),

                summary AS (
                    SELECT
                        material,
                        material_description,
                        branch,
                        plant,

                        AVG(qty) FILTER (
                            WHERE month_date >= CURRENT_DATE - INTERVAL '6 months'
                        ) AS avg6m,

                        AVG(qty) FILTER (
                            WHERE month_date >= CURRENT_DATE - INTERVAL '3 months'
                        ) * 0.25 AS weekly,

                        SUM(qty) FILTER (
                            WHERE EXTRACT(MONTH FROM month_date) =
                                EXTRACT(MONTH FROM CURRENT_DATE - INTERVAL '1 year')
                        ) AS lysm,

                        SUM(sales_value) AS total_value

                    FROM monthly
                    GROUP BY material, material_description, branch, plant
                ),

                ranked AS (
                    SELECT *,
                        SUM(total_value) OVER (ORDER BY total_value DESC) AS running_total,
                        SUM(total_value) OVER () AS grand_total
                    FROM summary
                )

                SELECT
                    ROW_NUMBER() OVER () AS id,

                    material,
                    material_description AS description,
                    branch,
                    plant,

                    CASE
                        WHEN running_total / grand_total <= 0.80 THEN 'A'
                        WHEN running_total / grand_total <= 0.95 THEN 'B'
                        ELSE 'C'
                    END AS abc,

                    FLOOR(random() * 50 + 1)::int AS stock,
                    FLOOR(random() * 50 + 1)::int AS netavl,

                    ROUND(COALESCE(weekly,0),2) AS weekly,
                    ROUND(COALESCE(avg6m,0),2) AS avg6m,
                    COALESCE(lysm,0)::int AS lysm,

                    GREATEST(
                        CEIL((COALESCE(avg6m,0)/30)*10)
                        - FLOOR(random() * 50 + 1)::int,
                        0
                    ) AS sugqty,

                    CONCAT('₹', ROUND(total_value/1000.0,1), 'K') AS value,

                    'Draft' AS status,

                    CASE
                        WHEN COALESCE(avg6m,0) > COALESCE(lysm,0)/12 THEN true
                        ELSE false
                    END AS trend

                FROM ranked
                ORDER BY total_value DESC;
            """
        )

        rows = cur.fetchall()
        cur.close()
        conn.close()

        print(f"Rows returned: {len(rows)}")
        print("ROW 0", rows[0])

        if not rows:
            return []

        spares_data = []
        for r in rows:
            spares_data.append({
                "id": r[0],                    # assuming first column is id
                "material": r[1],
                "description": r[2],
                "branch": r[3],
                "plant": r[4],
                "abc": r[5],
                "stock": r[6],
                "netavl": r[7],
                "weekly": r[8],
                "avg6m": r[9],
                "lysm": r[10],
                "sugqty": r[11],
                "value": r[12],
                "status": r[13],
                "trend": r[14]
            })

        return spares_data

    except Exception as e:
        print(f"Database Error: {e}")
        if 'conn' in locals():
            conn.close()
        raise
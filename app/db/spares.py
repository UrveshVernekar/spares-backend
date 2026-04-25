from decimal import Decimal
from datetime import date, datetime
from app.db.connection import get_connection

BRANCH_COORDS = {
    "MUMBAI": {"lat": 19.0760, "lng": 72.8777},
    "PUNE": {"lat": 18.5204, "lng": 73.8567},
    "PARBHANI": {"lat": 19.2608, "lng": 76.7765},
    "THANE": {"lat": 19.2183, "lng": 72.9781},
    "SATARA": {"lat": 17.6859, "lng": 74.0183},
    # Add more branches as needed
}

def haversine_distance(lat1, lon1, lat2, lon2):
    from math import radians, sin, cos, sqrt, atan2
    R = 6371  # Earth radius in km
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    return round(R * c)

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

def get_pool_data():
    conn = get_connection()
    try:
        cur = conn.cursor()

        cur.execute("""
            WITH last_sale AS (
                SELECT 
                    material,
                    city AS branch,
                    MAX(bill_date::date) AS last_sale_date,
                    CURRENT_DATE - MAX(bill_date::date) AS days_since_sale
                FROM spares.spares_data
                GROUP BY material, city
            ),
            monthly AS (
                SELECT
                    material,
                    material_description,
                    city AS branch,
                    plnt::int AS plant,
                    DATE_TRUNC('month', bill_date::date) AS month_date,
                    SUM(inv_qty) AS qty,
                    SUM(gross_val) AS sales_value
                FROM spares.spares_data
                GROUP BY material, material_description, city, plnt, DATE_TRUNC('month', bill_date::date)
            ),
            summary AS (
                SELECT
                    material,
                    material_description,
                    branch,
                    plant,
                    AVG(qty) FILTER (WHERE month_date >= CURRENT_DATE - INTERVAL '6 months') AS avg6m,
                    SUM(sales_value) AS total_value
                FROM monthly
                GROUP BY material, material_description, branch, plant
            )
            SELECT 
                ROW_NUMBER() OVER () AS id,
                s.material,
                s.material_description AS description,
                s.branch,
                s.plant,
                COALESCE(ls.days_since_sale, 999) AS days_since_sale,
                s.avg6m,
                FLOOR(random() * 50 + 1)::int AS stock,
                CONCAT('₹', ROUND(s.total_value/1000.0, 1), 'K') AS value,
                GREATEST(CEIL(COALESCE(s.avg6m, 0) * 0.6), 0) AS sugqty
            FROM summary s
            LEFT JOIN last_sale ls 
                ON ls.material = s.material AND ls.branch = s.branch
            ORDER BY s.total_value DESC
            LIMIT 50000;
        """)

        rows = cur.fetchall()
        cur.close()
        conn.close()

        pool_candidates = []
        pool_management = []

        for r in rows:
            days_since = int(r[5]) if r[5] is not None else 999
            stock = int(r[7])
            sugqty = int(r[9])

            # Derive Aging
            if days_since >= 180:
                aging = "180+"
            elif days_since >= 90:
                aging = "90+"
            elif days_since >= 60:
                aging = "60+"
            else:
                aging = "30+"

            pool_qty = max(int(sugqty * 0.7), int(stock * 0.5))

            # Nearest Branch & Distance
            branch = str(r[3]).strip().upper()
            nearest = "PUNE" if branch != "PUNE" else "MUMBAI"
            distance_str = "(12u, 45km)"

            if branch in BRANCH_COORDS and nearest in BRANCH_COORDS:
                dist = haversine_distance(
                    BRANCH_COORDS[branch]["lat"], BRANCH_COORDS[branch]["lng"],
                    BRANCH_COORDS[nearest]["lat"], BRANCH_COORDS[nearest]["lng"]
                )
                distance_str = f"({int(stock/10)}u, {dist}km)"

            # Candidate Item
            candidate = {
                "id": int(r[0]),
                "material": r[1],
                "description": r[2] or "",
                "branch": branch,
                "stock": stock,
                "daysSinceSale": days_since,
                "aging": aging,
                "poolQty": pool_qty,
                "nearestBranch": nearest,
                "distance": distance_str,
                "value": r[8] or "₹0.0K",
            }
            pool_candidates.append(candidate)

            # Management Item (only slow moving)
            if days_since >= 60:
                pool_management.append({
                    "id": int(r[0]),
                    "material": r[1],
                    "description": r[2] or "",
                    "branch": branch,
                    "qty": pool_qty,
                    "agingDays": f"{days_since}d",
                    "aging": aging,
                    "added": "Auto",
                    "status": "Available",
                })

        return {
            "success": True,
            "count": len(pool_candidates),
            "candidates": pool_candidates,
            "management": pool_management[:1500]   # Limit for performance
        }

    except Exception as e:
        print(f"Pool API Error: {e}")
        if 'conn' in locals() and conn:
            conn.close()
        return {"success": False, "error": str(e)}

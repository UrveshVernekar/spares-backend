from typing import List, Dict, Any
from app.db.spares import get_spares_data as get_spares_data_from_db

class SparesService:
    @staticmethod
    def get_all_spares() -> List[Dict[str, Any]]:
        """
        Fetch all spares data from the database and perform any necessary business logic.
        """
        # In a more complex app, you might do filtering, sorting, or additional calculations here.
        data = get_spares_data_from_db()
        return data

    @staticmethod
    def get_spares_summary(data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Example of business logic: summarizing the data.
        """
        return {
            "success": True,
            "count": len(data),
            "data": data
        }

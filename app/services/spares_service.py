from typing import List, Dict, Any
from app.db.spares import get_spares_data as get_spares_data_from_db
from app.db.spares import get_pool_data as get_pool_data_from_db
from app.db.spares import get_spares_meta as get_spares_meta_from_db

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
    def get_spares_meta(search: str = None) -> Dict[str, Any]:
        """
        Fetch unique materials and plants for dropdowns.
        """
        return get_spares_meta_from_db(search)

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
    
    @staticmethod
    def get_all_pool_spares() -> List[Dict[str, Any]]:
        """
        Fetch all spares data from the database and perform any necessary business logic.
        """
        # In a more complex app, you might do filtering, sorting, or additional calculations here.
        data = get_pool_data_from_db()
        return data

    @staticmethod
    def get_pool_summary(data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Example of business logic: summarizing the data.
        """
        return {
            "success": True,
            "count": len(data),
            "data": data
        }
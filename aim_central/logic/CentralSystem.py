import json
import os

from . import DatabaseOperations as db_ops


script_dir = os.path.dirname(os.path.abspath(__file__))
file_path = os.path.join(script_dir, "testInventory.json")

class CentralSystem():
    def __init__(self):
        db_ops.database_init()

    def findContainer(self, containerId):
        return db_ops.find_container(containerId)

    def getStockLevel(self, containerId):
        return db_ops.get_stock_level(containerId)
    
    def getStock(self, containerId):
        return db_ops.get_stock(containerId)
    
    def changeStock(self, containerId, changeAmount):
        return db_ops.change_stock(containerId, changeAmount)
    
    def getContainerDetails(self, containerId):
        container = self.findContainer(containerId)
        if container:
            return {
                "id": container["container_id"],
                "contents": container["item_name"],
                "neededStock": container["needed_stock"],
                "currentStock": container["current_stock"],
                "currentWeight": "N/A"
            }
        return None
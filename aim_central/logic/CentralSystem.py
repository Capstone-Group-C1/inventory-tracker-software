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

    def getStockLevel(self, item_id):
        """
        Returns Red, Yellow, or Green based on stock levels.
        """
        item = db_ops.find_item(item_id)
        if item:
            if item["current_stock"] == 0:
                return "Red"
            elif item["current_stock"] <= item["needed_stock"] * 0.5:
                return "Yellow"
        return "Green"
    
    def getStock(self, item_id):
        """
        Returns the current stock of the item or -1 if we can't find the item.
        """
        item = db_ops.find_item(item_id)
        if item:
            return item["current_stock"]
        return -1
    
    def getNumContainers(self):
        return db_ops.get_num_containers()
    
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
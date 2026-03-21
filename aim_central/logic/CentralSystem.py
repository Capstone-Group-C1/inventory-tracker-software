import json
import os

import DatabaseOperations as db_ops


script_dir = os.path.dirname(os.path.abspath(__file__))
file_path = os.path.join(script_dir, "testInventory.json")

class CentralSystem():
    def __init__(self):
        db_ops.database_init()
        #self.inv = json.load(open(file_path))

    def findContainer(self, containerId):
        return db_ops.find_container(containerId)
        # for container in self.inv["containers"]:
        #     if container["id"] == containerId:
        #         return container

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
                "id": container["id"],
                "contents": container["contents"],
                "neededStock": container["neededStock"],
                "currentStock": container["currentStock"],
                "currentWeight": container["currentWeight"]
            }
        return None
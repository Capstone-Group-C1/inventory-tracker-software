from . import DatabaseOperations as db_ops

class CentralSystem():
    def __init__(self):
        db_ops.database_init()

    def findContainer(self, containerId):
        return db_ops.find_container(containerId)

    def getStockLevel(self, item_id):
        return db_ops.get_stock_level(item_id)

    def getStock(self, item_id):
        return db_ops.get_stock(item_id)
    
    def changeStock(self, item_id, change_amount):
        return db_ops.change_stock(item_id, change_amount)

    def tareAllBins(self, bridge):
        bridge.tare_all_containers()

    def getNumContainers(self):
        return db_ops.get_num_containers()
    
    def getContainerDetails(self, containerId):
        container = self.findContainer(containerId)
        if container:
            return {
                "id": containerId,
                "items": container["items"],
                "currentWeight": "N/A"
            }
        return None

    def import_db(self, file_path):
        return db_ops.import_from_csv(file_path)
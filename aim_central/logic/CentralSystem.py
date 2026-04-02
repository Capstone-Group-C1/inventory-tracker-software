from . import DatabaseOperations as db_ops

class CentralSystem():
    def __init__(self):
        db_ops.database_init()

    def findContainer(self, containerId):
        return db_ops.find_container(containerId)
    
    def findItem(self, itemId):
        return db_ops.find_item(itemId)
    
    def getContainerWeight(self, containerId):
        return db_ops.get_container_weight(containerId)

    def getStockLevel(self, item_id):
        return db_ops.get_stock_level(item_id)
    
    def getContainerStockLevel(self, containerId):
        return db_ops.get_container_stock_level(containerId)

    def getStock(self, item_id):
        return db_ops.get_stock(item_id)
    
    def changeStock(self, item_id, change_amount):
        return db_ops.change_stock(item_id, change_amount)

    def tareAllBins(self, bridge):
        bridge.tare_all_containers()

    def getNumContainers(self):
        return db_ops.get_num_containers()

    def import_db(self, file_path):
        return db_ops.import_from_csv(file_path)
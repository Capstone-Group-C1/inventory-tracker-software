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

    def setContainerWeight(self, containerId, weight):
        return db_ops.set_container_weight(containerId, weight)

    def getStockLevel(self, item_id):
        return db_ops.get_stock_level(item_id)

    def getContainerStockLevel(self, containerId):
        return db_ops.get_container_stock_level(containerId)

    def setStock(self, item_id, new_stock):
        return db_ops.set_stock(item_id, new_stock)

    def getStock(self, item_id):
        return db_ops.get_stock(item_id)

    def changeStock(self, item_id, change_amount):
        return db_ops.change_stock(item_id, change_amount)

    def getNumContainers(self):
        return db_ops.get_num_containers()
    
    def getContainerName(self, containerId):
        container_info = db_ops.find_container(containerId)
        if container_info and container_info['items'] and len(container_info['items']) == 1:
            return container_info['items'][0]['item_name']
        elif container_info and container_info['items'] and len(container_info['items']) > 1:
            item_names = [item['item_name'] for item in container_info['items']]
            return self.longest_common_substring(item_names)
        else:
            return f"Container {containerId} (no items)"
        
    def longest_common_substring(self, strs):
        if not strs: return ""
        shortest = min(strs, key=len)
        for length in range(len(shortest), 0, -1):
            for start in range(len(shortest) - length + 1):
                sub = shortest[start:start+length]
                if all(c.isalnum() or c.isspace() for c in sub) and all(sub in s for s in strs):
                    return sub
        return ""

    def import_db(self, file_path):
        return db_ops.import_from_csv(file_path)
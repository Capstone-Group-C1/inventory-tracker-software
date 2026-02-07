import json
import os

script_dir = os.path.dirname(os.path.abspath(__file__))
file_path = os.path.join(script_dir, "testInventory.json")

class CentralSystem():
    def __init__(self):
        self.inv = json.load(open(file_path))

    def findContainer(self, containerId):
        for container in self.inv["containers"]:
            if container["id"] == containerId:
                return container
    
    def getStockLevel(self, containerId):
        container = self.findContainer(containerId)
        if container:
            if container["currentStock"] == 0:
                return "Red"
            elif container["currentStock"] <= container["neededStock"] * 0.5:
                return "Yellow"
        return "Green"
    
    def getStock(self, containerId):
        container = self.findContainer(containerId)
        if container:
            return container["currentStock"]
        return -1
    
    def changeStock(self, containerId, changeAmount):
        container = self.findContainer(containerId)
        if container:
            if container["currentStock"] + changeAmount < 0:
                print("Error: Attempting to set stock below zero.")
            else:
                container["currentStock"] += changeAmount
                with open(file_path, "w") as f:
                    json.dump(self.inv, f, indent=2)
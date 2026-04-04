class Controller():
    def __init__(self, view):
        self.view = view
        self.view.addFeatures(self)
        self.model = None
        self.bridge = None

    def set_bridge(self, bridge):
        self.bridge = bridge

    
    def manualStockChange(self, itemId, newAmt):
        print(f"Manual stock change for item {itemId} to new amount: {newAmt}")
        if self.model:
            self.model.setStock(itemId, newAmt)
            self.view.refreshContainerButtons()
            self.view.refreshContainerSettings()

    def tareContainer(self, containerId):
        print(f"Tare container {containerId}")
        if self.model and self.bridge:
            self.bridge.tare_single_container(containerId)
            self.view.refreshContainerButtons()
            self.view.refreshContainerSettings()
    
    def tareAllContainers(self):
        print("Tare all containers")
        if self.bridge:
            self.bridge.tare_all_containers()
        self.view.refreshContainerButtons()
        self.view.refreshContainerSettings()
    
    def toggleGPSWindow(self, curWindow):
        self.view.toggleGPSWindow(curWindow)

    def toggleCalibrateWindow(self, curWindow):
        self.view.toggleCalibrateWindow(curWindow)
    
    def toggleHomeWindow(self, curWindow):
        self.view.toggleHomeWindow(curWindow)

    def launch(self, model):
        print("Controller launched with model:", model)
        self.model = model
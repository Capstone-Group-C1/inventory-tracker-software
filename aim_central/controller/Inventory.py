class Controller():
    def __init__(self, view):
        self.view = view
        self.view.addFeatures(self)
        self.model = None
        self.bridge = None

    def set_bridge(self, bridge):
        self.bridge = bridge

    def ContainerButtonClick(self, containerId):
        print("container " + str(containerId) + " button clicked")
        if self.model:
            stockLevel = self.model.getContainerStockLevel(containerId)
            self.view.updateContainerDisplay(containerId, stockLevel)

            containerDetails = self.model.findContainer(containerId)
            self.view.openContainerDetails(containerDetails)
    
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
        if self.model:
            self.model.tareAllContainers() 
            # after taring, we should update the display for all containers since stock levels may have changed
            # self.refreshContainerButtons() # also make this function - calls getContainerStockLevel for each container and updates display
            pass
    
    def toggleGPSWindow(self, curWindow):
        self.view.toggleGPSWindow(curWindow)

    def toggleCalibrateWindow(self, curWindow):
        self.view.toggleCalibrateWindow(curWindow)
    
    def toggleHomeWindow(self, curWindow):
        self.view.toggleHomeWindow(curWindow)
    
    def refreshContainerButtons(self):
        for button in self.view.container_buttons_list:
            containerId = button.containerId
            stockLevel = self.model.getContainerStockLevel(containerId)
            button.stockLevel = stockLevel
            self.view.updateContainerDisplay(containerId, stockLevel)
    
    def refreshContainerSettings(self):
        print("Refreshing container settings...")
        self.view.refreshContainerSettings()

    def refreshGPSSettings(self):
        pass

    def launch(self, model):
        print("Controller launched with model:", model)
        self.model = model
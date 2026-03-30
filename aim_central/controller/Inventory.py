class Controller():
    def __init__(self, view):
        self.view = view
        self.view.addFeatures(self)
        self.model = None

    def ContainerButtonClick(self, containerId):
        print("container " + str(containerId) + " button clicked")
        if self.model:
            containerContents = self.model.findContainer(containerId)
            print("Container Contents: ", containerContents)
            stockLevel = self.model.getStockLevel(containerId)
            stockAmt = self.model.getStock(containerId)
            print("Current Stock: ", stockAmt)
            print("Stock Level: ", stockLevel)

            self.view.updateContainerDisplay(containerId, stockLevel)

            containerDetails = self.model.getContainerDetails(containerId)
            self.view.openContainerDetails(containerDetails)
    
    def toggleGPSWindow(self, curWindow):
        self.view.toggleGPSWindow(curWindow)

    def toggleCalibrateWindow(self, curWindow):
        self.view.toggleCalibrateWindow(curWindow)
    
    def toggleHomeWindow(self, curWindow):
        self.view.toggleHomeWindow(curWindow)

    def launch(self, model):
        print("Controller launched with model:", model)
        self.model = model
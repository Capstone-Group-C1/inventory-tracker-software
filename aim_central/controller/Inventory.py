class Controller():
    def __init__(self, view):
        self.view = view
        self.view.addFeatures(self)
        self.model = None

    def ContainerButtonClick(self, containerId):
        print("container " + str(containerId) + " button clicked")
        if self.model:
            containerDetails = self.model.getContainerDetails(containerId)
            print("Container Details: ", containerDetails)

            if containerDetails and containerDetails["items"]:
                # Use the first item's stock level to drive the LED colour on the button.
                # For multi-item containers Anya's UI can iterate containerDetails["items"].
                first_item_id = containerDetails["items"][0]["item_id"]
                stockLevel = self.model.getStockLevel(first_item_id)
                stockAmt = self.model.getStock(first_item_id)
                print("Current Stock: ", stockAmt)
                print("Stock Level: ", stockLevel)
                self.view.updateContainerDisplay(containerId, stockLevel)

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
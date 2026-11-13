import adsk.core

# 20 - hide the layout grid for the screenshots (UI display toggle; restored at the end by toggling again)
def run(_context: str):
    ui = adsk.core.Application.get().userInterface
    cd = ui.commandDefinitions.itemById('ViewLayoutGridOnCommand')
    print(cd.controlDefinition.objectType if cd.controlDefinition else None)
    cd.execute()

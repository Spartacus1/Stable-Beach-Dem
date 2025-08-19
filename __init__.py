from .main import StableBeachDEMPlugin

def classFactory(iface):
    return StableBeachDEMPlugin(iface)

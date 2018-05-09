from qgis.gui import QgsMapCanvas, QgsMapToolEmitPoint
from PyQt4.QtCore import *
from qgis.core import *


class PrintClickedPoint(QgsMapToolEmitPoint):
    def __init__(self, canvas):
        self.canvas = canvas
        QgsMapToolEmitPoint.__init__(self, self.canvas)

    def canvasPressEvent(self, e):
        registry = QgsMapLayerRegistry.instance()
        try:
            shaft_layer = registry.mapLayersByName('shafts_point')[0]

            shaft_index = QgsSpatialIndex()
            shafts = shaft_layer.getFeatures()
            shaft_feat = QgsFeature()
            while shafts.nextFeature(shaft_feat):
                shaft_index.insertFeature(shaft_feat)

            if e.button() == Qt.LeftButton:
                point = self.toMapCoordinates(self.canvas.mouseLastXY())

                nextNearestIds = shaft_index.nearestNeighbor(point, 1)
                feature = shaft_layer.getFeatures(QgsFeatureRequest().setFilterFid(nextNearestIds[0]))
                nextF = QgsFeature()
                feature.nextFeature(nextF)

                shaft_layer.setSelectedFeatures([nextF.id()])

        except IndexError:
            self.iface.messageBar().pushMessage("Error", "Need to create shafts before selecting",
                                                level=QgsMessageBar.WARNING, duration=3)
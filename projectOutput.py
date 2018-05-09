# -*- coding: utf-8 -*-

from PyQt4.QtCore import *
from PyQt4.QtGui import *
from qgis.core import *
from qgis.gui import *
from qgis.utils import *

import os.path

from create_project_dialog import CreateProjectDialog
from graph import Graph

class Project():
    def __init__(self, iface):
        # Save reference to the QGIS interface
        self.iface = iface
        self.create_project_dlg = CreateProjectDialog()

        # clear the previously loaded text (if any) in the line edit widget
        self.create_project_dlg.save_lineEdit.clear()
        # connect the select_output_file method to the clicked signal of the tool button widget
        self.create_project_dlg.save_toolButton.clicked.connect(self.select_output_dir)

        self.create_project_dlg.add_pushButton.clicked.connect(self.add_layer_to_w2)
        self.create_project_dlg.remove_pushButton.clicked.connect(self.add_layer_to_w1)
        self.create_project_dlg.add_all_pushButton.clicked.connect(self.add_all_layers_to_w2)
        self.create_project_dlg.remove_all_pushButton.clicked.connect(self.add_all_layers_to_w1)

        self.dir_name = ""

    # open directory browser and populate the line edit widget
    def select_output_dir(self):
        self.dir_name = QFileDialog.getExistingDirectory(self.create_project_dlg , "Select directory ", "/home")
        self.create_project_dlg.save_lineEdit.setText(self.dir_name)

    def load_coefficients(self):
        row = []
        file = open(os.path.abspath(os.path.dirname(__file__) + '/koeficienty.csv'), 'r')
        for line in file.readlines():
            r = line.rstrip()
            row.append(r.split(';'))
        file.close

        coefficients = []
        for r in sorted(row):
            coefficients.append(float(r[2]))
        return coefficients

    def count_budget(self, round):
        budget = 0
        coefficients = self.load_coefficients()

        vyskyt = []
        for coef in coefficients:
            vyskyt.append(coef*round)

        registry = QgsMapLayerRegistry.instance()
        try:
            typy_vykopu_layer = registry.mapLayersByName('typy_vykopu')[0]
            costs = []
            for vykop in typy_vykopu_layer.getFeatures():
                costs.append(float(vykop[typy_vykopu_layer.attributeDisplayName(2)]))

            ceny_jednotlive = []
            for i in range(len(vyskyt)):
                ceny_jednotlive.append(vyskyt[i] * costs[i])

            for cena in ceny_jednotlive:
                budget = budget + cena
        except IndexError:
            self.iface.messageBar().pushMessage("Error", "Budget is 0, first fill database table",
                                                level=QgsMessageBar.WARNING, duration=3)
        return budget

    def add_layer_to_w1(self):
        items = self.create_project_dlg.layers_listWidget_2.selectedItems()
        item_list = []
        for item in items:
            item_list.append(item.text())
            self.create_project_dlg.layers_listWidget_2.takeItem(
                self.create_project_dlg.layers_listWidget_2.currentRow())
        self.create_project_dlg.layers_listWidget_1.addItems(item_list)

    def add_layer_to_w2(self):
        items = self.create_project_dlg.layers_listWidget_1.selectedItems()
        item_list = []
        for item in items:
            item_list.append(item.text())
            self.create_project_dlg.layers_listWidget_1.takeItem(
                self.create_project_dlg.layers_listWidget_1.currentRow())
        self.create_project_dlg.layers_listWidget_2.addItems(item_list)

    def add_all_layers_to_w1(self):
        self.create_project_dlg.layers_listWidget_1.clear()

        layers = self.iface.legendInterface().layers()
        layer_list = []
        for layer in layers:
            if layer.name() != "typy_vykopu":
                layer_list.append(layer.name())
        self.create_project_dlg.layers_listWidget_1.addItems(layer_list)

        self.create_project_dlg.layers_listWidget_2.clear()

    def add_all_layers_to_w2(self):
        self.create_project_dlg.layers_listWidget_2.clear()

        layers = self.iface.legendInterface().layers()
        layer_list = []
        for layer in layers:
            if layer.name() != "typy_vykopu":
                layer_list.append(layer.name())
        self.create_project_dlg.layers_listWidget_2.addItems(layer_list)

        self.create_project_dlg.layers_listWidget_1.clear()

    def sum_length(self, layer):
        length = 0
        for feature in layer.getFeatures():
            if feature['Length'] != None:
                length = length + float(feature['Length'])

        return int(round(length, 0))

    def add_label(self, composer, text, x, y):
        label = QgsComposerLabel(composer)
        label.setText(text.decode('utf-8'))
        label.adjustSizeToText()
        label.setItemPosition(x, y)
        composer.addItem(label)

    def add_label_number(self, composer, text, x, y):
        label = QgsComposerLabel(composer)
        label.setText(str(text))
        label.adjustSizeToText()
        label.setItemPosition(x, y)
        composer.addItem(label)

    def save_views(self):
        if self.dir_name == "":
            self.iface.messageBar().pushMessage("Error", "First select output directory please.",
                                                level=QgsMessageBar.WARNING, duration=3)
        else:
            layers = self.iface.legendInterface().layers()
            selected_layer = None

            for layer in layers:
                selected_features = layer.selectedFeatures()
                if selected_features:
                    selected_layer = layer
                    box = selected_layer.boundingBoxOfSelected()
                    self.iface.mapCanvas().zoomToSelected(selected_layer)
                    self.iface.mapCanvas().setExtent(box)
                    break

            item = ""
            if self.create_project_dlg.layers_listWidget_2.item(0) != None:
                item = self.create_project_dlg.layers_listWidget_2.item(0).text()

            if selected_layer == None:
                if item != "":
                    for lyr in QgsMapLayerRegistry.instance().mapLayers().values():
                        if lyr.name() == item:
                            selected_layer = lyr
                            break
                    self.iface.mapCanvas().setExtent(selected_layer.extent())

            if selected_layer != None or selected_features:
                width = self.iface.mapCanvas().mapSettings().outputSize().width()
                height = self.iface.mapCanvas().mapSettings().outputSize().height()
                pixmap = QPixmap(width, height)
                mapfile = self.dir_name + "/" + "raster" + ".png"
                self.iface.mapCanvas().saveAsImage(mapfile, pixmap)

                mapRenderer = self.iface.mapCanvas().mapRenderer()
                c = QgsComposition(mapRenderer)
                w, h = c.paperWidth(), c.paperHeight()

                # add label
                composerLabel = QgsComposerLabel(c)
                composerLabel.setFont(QFont("Cambria", 30, QFont.Bold))
                composerLabel.setText("Output Project")
                composerLabel.adjustSizeToText()
                composerLabel.setItemPosition(h / 2, 10, QgsComposerItem.UpperMiddle, 1)
                c.addItem(composerLabel)

                # add picture
                x, y, = 30, 30
                composerPicture = QgsComposerPicture(c)
                composerPicture.setPictureFile(self.dir_name + "/" + "raster" + ".png")
                composerPicture.setFrameEnabled(False)
                composerPicture.setSceneRect(QRectF(x, y, h-x-30, w-y-30))
                c.addItem(composerPicture)

                self.add_label(c, "Jméno sítě", x-20, h-y-50)
                self.add_label(c, "Délka vedení [m]", x+20, h-y-50)
                self.add_label(c, "Nejdelší trasa [m]", x+55, h-y-50)
                self.add_label(c, "Rozpočet [Kč]", x+90, h-y-50)

                items = []
                for index in xrange(self.create_project_dlg.layers_listWidget_2.count()):
                    items.append(self.create_project_dlg.layers_listWidget_2.item(index))

                layer_list = []
                for item in items:
                    layer = self.find_layer(item.text())
                    if layer.attributeDisplayName(9) == "Length":
                        layer_list.append(layer)

                i = 40
                for layer in layer_list:
                    self.add_label(c, layer.name(), x-20, h-y-i)

                    length = self.sum_length(layer)
                    self.add_label_number(c, length, x + 20, h-y-i)

                    if layer.name() != "connections_line":
                        longest_path = self.find_longest_path(layer)
                    else:
                        longest_path = 0
                    self.add_label_number(c, longest_path, x+55, h-y-i)

                    budget = self.count_budget(length)
                    self.add_label_number(c, round(budget, 2), x+90, h-y-i)
                    i = i - 5

                # add legend
                legend = QgsComposerLegend(c)
                legend.setTitle('Vrstvy v projektu')
                lyrGroup = QgsLayerTreeGroup()
                for legendLyr in self.iface.mapCanvas().layers():
                    lyrGroup.addLayer(legendLyr)
                legend.modelV2().setRootGroup(lyrGroup)
                legendSize = legend.paintAndDetermineSize(None)
                legend.setFrameEnabled(True)
                legend.setItemPosition(h - legendSize.width() - 10, w - legendSize.height() - 20 - 80)
                c.addItem(legend)

                printer = QPrinter()
                printer.setOutputFormat(QPrinter.PdfFormat)
                printer.setOutputFileName(self.dir_name + "/" + "Project info" + ".pdf")
                printer.setPaperSize(QSizeF(h,w), QPrinter.Millimeter)
                printer.setFullPage(True)

                printer.setResolution(c.printResolution())
                pdfPainter = QPainter(printer)
                paperRectMM = printer.pageRect(QPrinter.Millimeter)
                paperRectPixel = printer.pageRect(QPrinter.DevicePixel)
                c.render(pdfPainter, paperRectPixel, paperRectMM)
                pdfPainter.end()

                mapRenderer2 = self.iface.mapCanvas().mapRenderer()
                c2 = QgsComposition(mapRenderer2)
                c2.setPlotStyle(QgsComposition.Print)

                x, y = 0, 0
                composerMap = QgsComposerMap(c2, x, y, w, h)
                c2.addItem(composerMap)

                printer2 = QPrinter()
                printer2.setOutputFormat(QPrinter.PdfFormat)
                printer2.setOutputFileName(self.dir_name + "/" + "vector" + ".pdf")
                printer2.setPaperSize(QSizeF(w,h), QPrinter.Millimeter)
                printer2.setFullPage(True)
                printer2.setColorMode(QPrinter.Color)
                printer2.setResolution(c2.printResolution())
                pdfPainter2 = QPainter(printer2)
                paperRectMM2 = printer2.pageRect(QPrinter.Millimeter)
                paperRectPixel2 = printer2.pageRect(QPrinter.DevicePixel)
                c2.render(pdfPainter2, paperRectPixel2, paperRectMM2)
                pdfPainter2.end()

                self.iface.messageBar().pushMessage("Document successfully generated.", level=QgsMessageBar.INFO)

    def set_visible_layers(self):
        items = []
        for index in xrange(self.create_project_dlg.layers_listWidget_2.count()):
            items.append(self.create_project_dlg.layers_listWidget_2.item(index))

        for item in items:
            layer = self.find_layer(item.text())
            self.iface.legendInterface().setLayerVisible(layer, True)

        items2 = []
        for index in xrange(self.create_project_dlg.layers_listWidget_1.count()):
            items2.append(self.create_project_dlg.layers_listWidget_1.item(index))

        for item in items2:
            layer = self.find_layer(item.text())
            self.iface.legendInterface().setLayerVisible(layer, False)

    def find_layer(self, name):
        selected_layer = None
        for lyr in QgsMapLayerRegistry.instance().mapLayers().values():
            if lyr.name() == name:
                selected_layer = lyr
                break
        return selected_layer

    def find_longest_path(self, edges_layer):
        registry = QgsMapLayerRegistry.instance()
        shaft_layer = registry.mapLayersByName('shafts_point')[0]
        #edges_layer = registry.mapLayersByName('edges_line')[0]

        start_point_feat = None
        for feat in shaft_layer.getFeatures():
            if feat['StartPoint'] == 'Start':
                start_point_feat = feat

        if start_point_feat == None:
            fid = 1
            iterator = shaft_layer.getFeatures(QgsFeatureRequest().setFilterFid(fid))
            start_point_feat = next(iterator)

        g = Graph()
        gg = g.create_graph(shaft_layer, edges_layer)
        graph = g.change_graph_repre(gg)
        distance = g.dijkstra(graph, gg['vertices'], (start_point_feat['ID']))

        longest_path = 0
        for dist in distance:
            if distance[dist] > longest_path:
                longest_path = distance[dist]

        return longest_path

    def run4(self):
        self.create_project_dlg.layers_listWidget_1.clear()
        self.create_project_dlg.layers_listWidget_2.clear()

        self.add_all_layers_to_w1()

        self.create_project_dlg.show()
        # Run the dialog event loop
        result = self.create_project_dlg.exec_()
        # See if OK was pressed
        if result:
            self.set_visible_layers()
            QTimer.singleShot(1000, self.save_views)
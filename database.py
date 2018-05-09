# -*- coding: utf-8 -*-

from PyQt4.QtCore import *
from PyQt4.QtGui import *
from qgis.core import *
from qgis.gui import *
from qgis.utils import *
from PyQt4.QtSql import *
from sqlite3 import OperationalError

import psycopg2
import os.path

from join_db_dialog import JoinDBDialog
from projectOutput import Project

class Database():
    def __init__(self, iface):
        # Save reference to the QGIS interface
        self.iface = iface
        self.joinDB_dlg = JoinDBDialog()

        self.new_project = Project(self.iface)

        self.joinDB_dlg.lineEdit_address.setText("10.1.1.4")
        self.joinDB_dlg.lineEdit_dbname.setText("gis")
        self.joinDB_dlg.lineEdit_user.setText("wing")
        #self.joinDB_dlg.lineEdit_password.setText("***")
        self.joinDB_dlg.textEdit_sql.setText("SELECT * from public.typy_vykopu")

        self.joinDB_dlg.pushButton_connect.clicked.connect(self.connect_to_db)
        self.joinDB_dlg.pushButton_standard.clicked.connect(self.fill_standard_values)

        self.joinDB_dlg.tableWidget.setHorizontalHeaderItem(0, QTableWidgetItem("typ"))
        self.joinDB_dlg.tableWidget.setHorizontalHeaderItem(1, QTableWidgetItem("popis"))
        self.joinDB_dlg.tableWidget.setHorizontalHeaderItem(2, QTableWidgetItem("cena"))

        self.joinDB_dlg.tableWidget.clear()
        values = [(1, 'Výkop - prostý terén - trávník, zeleň'.decode('utf-8'), 0),
                  (2, 'Podvrt - průjezd, chodník, vjezd'.decode('utf-8'), 0),
                  (3, 'Protlak'.decode('utf-8'), 0),
                  (4, 'Překop - kostky'.decode('utf-8'), 0),
                  (5, 'Překop - asfalt'.decode('utf-8'), 0),
                  (6, 'Překop -polní cesta'.decode('utf-8'), 0),
                  (7, 'Výkop chodník - stará dlažba'.decode('utf-8'), 0),
                  (8, 'Výkop chodník - zámková dlažba nová'.decode('utf-8'), 0),
                  (9, 'Výkop chodník - kostky'.decode('utf-8'), 0)]

        i = 0
        for row in values:
            one = QTableWidgetItem(str(row[0]))
            two = QTableWidgetItem(str(row[1]))
            three = QTableWidgetItem(str(row[2]))
            self.joinDB_dlg.tableWidget.setItem(i, 0, one)
            self.joinDB_dlg.tableWidget.setItem(i, 1, two)
            self.joinDB_dlg.tableWidget.setItem(i, 2, three)
            i = i + 1

    def not_empty(self, lineEdit):
        if lineEdit == "":
            return False
        else:
            return True

    def connect_to_db(self):
        address = self.joinDB_dlg.lineEdit_address.text()
        database_name = self.joinDB_dlg.lineEdit_dbname.text()
        user = self.joinDB_dlg.lineEdit_user.text()
        password = self.joinDB_dlg.lineEdit_password.text()
        sql = self.joinDB_dlg.textEdit_sql.toPlainText()

        if self.not_empty(address) and self.not_empty(database_name) and self.not_empty(user) and self.not_empty(
                password) and self.not_empty(sql):

            try:
                self.joinDB_dlg.tableWidget.clear()
                conn = psycopg2.connect(dbname=database_name, host=address, user=user, password=password)
                cur = conn.cursor()
                cur.execute(sql)

                vykopy = []
                for row in cur:
                    vykopy.append(row)

                i = 0
                for row in sorted(vykopy):
                    one = QTableWidgetItem(str(row[0]))
                    two = QTableWidgetItem(str(row[1]))
                    three = QTableWidgetItem(str(row[2]))
                    self.joinDB_dlg.tableWidget.setItem(i, 0, one)
                    self.joinDB_dlg.tableWidget.setItem(i, 1, two)
                    self.joinDB_dlg.tableWidget.setItem(i, 2, three)
                    i = i + 1

                if not self.find_layer("typy_vykopu"):
                    self.create_memory_layer()

            except OperationalError:
                self.iface.messageBar().pushMessage("Error", "Failed to connect to the database",
                                                level=QgsMessageBar.WARNING, duration=10)
        else:
            self.iface.messageBar().pushMessage("Error", "Some edit line is empty", level=QgsMessageBar.WARNING, duration=3)

    def fill_standard_values(self):
        values = [(1, 'Výkop - prostý terén - trávník, zeleň'.decode('utf-8'), 100.00),
                  (2, 'Podvrt - průjezd, chodník, vjezd'.decode('utf-8'), 200.00),
                  (3, 'Protlak'.decode('utf-8'), 700.00),
                  (4, 'Překop - kostky'.decode('utf-8'), 540.00),
                  (5, 'Překop - asfalt'.decode('utf-8'), 633.00),
                  (6, 'Překop -polní cesta'.decode('utf-8'), 200.00),
                  (7, 'Výkop chodník - stará dlažba'.decode('utf-8'), 193.00),
                  (8, 'Výkop chodník - zámková dlažba nová'.decode('utf-8'), 216.00),
                  (9, 'Výkop chodník - kostky'.decode('utf-8'), 540.00)]

        i = 0
        for row in values:
            one = QTableWidgetItem(str(row[0]))
            two = QTableWidgetItem(str(row[1]))
            three = QTableWidgetItem(str(row[2]))
            self.joinDB_dlg.tableWidget.setItem(i, 0, one)
            self.joinDB_dlg.tableWidget.setItem(i, 1, two)
            self.joinDB_dlg.tableWidget.setItem(i, 2, three)
            i = i + 1

        if not self.find_layer("typy_vykopu"):
            self.create_memory_layer()

    def find_layer(self, name):
        v = False
        for lyr in QgsMapLayerRegistry.instance().mapLayers().values():
            if lyr.name() == name:
                v = True
        return v

    def create_memory_layer(self):
        layer = QgsVectorLayer("Polygon?crs=epsg:5514", "typy_vykopu", "memory")

        layer.startEditing()
        layer.dataProvider().addAttributes(
            [QgsField("typ", QVariant.Int), QgsField("popis", QVariant.String), QgsField("cena", QVariant.Double)])
        layer.updateFields()

        for row in xrange(self.joinDB_dlg.tableWidget.rowCount()):
            item_list = []
            for column in xrange(self.joinDB_dlg.tableWidget.columnCount()):
                item = self.joinDB_dlg.tableWidget.item(row, column)
                item_list.append(item.text())

            feat = QgsFeature()
            feat.setAttributes([item_list[0], item_list[1], item_list[2]])
            layer.dataProvider().addFeatures([feat])

        layer.commitChanges()

        QgsVectorFileWriter.writeAsVectorFormat(layer,
                                                os.path.abspath(os.path.dirname(__file__)) + '/layers/' + 'typy_vykopu',
                                                "utf-8", None, "ESRI Shapefile")
        self.load_shp_layer_to_qgis('typy_vykopu')

    def load_shp_layer_to_qgis(self, layer_name):
        layer = QgsVectorLayer(os.path.abspath(os.path.dirname(__file__)) + '/layers/' + layer_name + '.shp',
                               layer_name, 'ogr')
        if not layer.isValid():
            self.iface.messageBar().pushMessage("Error", "Layer %s did not load" % layer.name(),
                                                level=QgsMessageBar.WARNING, duration=3)

        layer.setCrs(QgsCoordinateReferenceSystem(5514, QgsCoordinateReferenceSystem.EpsgCrsId))
        QgsMapLayerRegistry.instance().addMapLayers([layer])

    def actualization_memory_layer(self, memory_layer):
        features = memory_layer.getFeatures()
        feat_list = []
        for feat in features:
            feat_list.append(feat)

        for row in xrange(self.joinDB_dlg.tableWidget.rowCount()):
            for column in xrange(self.joinDB_dlg.tableWidget.columnCount()):
                item = self.joinDB_dlg.tableWidget.item(row, column)

                memory_layer.startEditing()
                memory_layer.changeAttributeValue(feat_list[row].id(), column, item.text())
                memory_layer.commitChanges()

    def run3(self):
        self.joinDB_dlg.show()
        # Run the dialog event loop
        result = self.joinDB_dlg.exec_()
        # See if OK was pressed
        if result:
            if not self.find_layer("typy_vykopu"):
                self.create_memory_layer()
            else:
                registry = QgsMapLayerRegistry.instance()
                typy_vykopu_layer = registry.mapLayersByName('typy_vykopu')[0]
                self.actualization_memory_layer(typy_vykopu_layer)

            self.new_project.run4()
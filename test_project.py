# -*- coding: utf-8 -*-

from qgis.core import *
import sys
import os.path
from PyQt4.QtGui import QApplication
from PyQt4.QtCore import Qt
from PyQt4.QtTest import QTest
from qgis.gui import *
from qgis.utils import *

import projectOutput
from unittest import TestCase

class DummyInterface(object):
    def __getattr__(self, *args, **kwargs):
        def dummy(*args, **kwargs):
            return self
        return dummy
    def __iter__(self):
        return self
    def next(self):
        raise StopIteration
    def layers(self):
        # simulate iface.legendInterface().layers()
        return QgsMapLayerRegistry.instance().mapLayers().values()

iface = DummyInterface()

class TestProject(TestCase):
    def setUp(self):
        self.app = QApplication(sys.argv)

        # create gui
        self.form = projectOutput.Project(iface)
        self.ui = self.form.create_project_dlg

        layer_list = []
        layer = QgsVectorLayer(os.path.join("C:\Users\Miroslav\.qgis2\python\plugins\FiberOpticNetworkDesignSystem\\test_data\\", 'test_data_shafts.shp'), 'test_data_shafts', 'ogr')
        layer_list.append(layer.name())
        layer = QgsVectorLayer(os.path.join("C:\Users\Miroslav\.qgis2\python\plugins\FiberOpticNetworkDesignSystem\\test_data\\", 'test_data_edges.shp'), 'test_data_edges', 'ogr')
        layer_list.append(layer.name())
        self.ui.layers_listWidget_1.addItems(layer_list)
        self.ui.layers_listWidget_2.addItems([""])

    # test default values
    def test_defaults(self):
        self.assertEqual(self.ui.save_lineEdit.text(), "")
        for i in xrange(self.ui.layers_listWidget_1.count()):
            self.assertNotEqual(str(self.ui.layers_listWidget_1.item(i).text()), "")
        for i in xrange(self.ui.layers_listWidget_2.count()):
            self.assertEqual(str(self.ui.layers_listWidget_2.item(i).text()), "")

    # test dialog name
    def test_dlg_name(self):
        self.assertEqual(self.ui.windowTitle(), 'Create Project')

    # test OK button close dialog
    def test_click_widget(self):
        self.ui.show()
        self.assertEqual(self.ui.isVisible(), True)
        okWidget = self.ui.button_box.button(self.ui.button_box.Save)
        QTest.mouseClick(okWidget, Qt.LeftButton)
        self.assertEqual(self.ui.isVisible(), False)

    def test_click_add_all_pushButton(self):
        self.ui.add_all_pushButton.click()
        for i in xrange(self.ui.layers_listWidget_1.count()):
            self.assertEqual(str(self.ui.layers_listWidget_1.item(i).text()), "")
            print self.ui.layers_listWidget_1.item(i).text()
        for i in xrange(self.ui.layers_listWidget_2.count()):
            self.assertNotEqual(str(self.ui.layers_listWidget_2.item(i).text()), "")

    def test_load_coefficients(self):
        coef = self.form.load_coefficients()
        self.assertIsInstance(coef, list)
        for c in coef:
            self.assertIsNotNone(c)
            self.assertIsInstance(c, float)

    def test_count_budget(self):
        budget = self.form.count_budget(7000)
        self.assertIsNotNone(budget)
        self.assertIsInstance(budget, int)

    def test_sum_length(self):
        layer = QgsVectorLayer(os.path.join("C:/Users/Miroslav/.qgis2/python/plugins/FiberOpticNetworkDesignSystem/test_data/", 'test_data_edges.shp'), 'test_data_edges', 'ogr')
        length = self.form.sum_length(layer)
        self.assertIsNotNone(length)
        self.assertIsInstance(length, int)


# -*- coding: utf-8 -*-

import  qgis.core
import sys
from PyQt4 import QtCore
from PyQt4.QtGui import QApplication
from PyQt4.QtCore import *
from PyQt4.QtTest import QTest
from qgis.core import *
from qgis.gui import *
from qgis.utils import *

import fonds
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

class TestFiberOpticNetworkDesignSystem(TestCase):
    def setUp(self):
        self.app = QApplication(sys.argv)

        # create gui
        self.form = fonds.FiberOpticNetworkDesignSystem(iface)
        self.ui = self.form.dlg

    # test default values
    def test_defaults(self):
        self.assertEqual(self.ui.select_output_lineEdit.text(), "")
        self.assertEqual(self.ui.max_connections_spinBox.value(), 10)
        self.assertEqual(self.ui.max_distance_spinBox.value(), 50)

        self.assertEqual(self.ui.radius_spinBox.value(), 1)
        self.assertEqual(self.ui.name_lineEdit.text(), "")
        self.assertEqual(self.ui.start_point_lineEdit.text(), "(0,0)")

    # test dialog name
    def test_dlg_name(self):
        self.assertEqual(self.ui.windowTitle(), 'Create Optic Net')

    # test not empty values
    def test_not_empty(self):
        self.assertNotEqual(self.ui.start_point_lineEdit.text(), "")

    # test OK button close dialog
    def test_click_widget(self):
        self.ui.show()
        self.assertEqual(self.ui.isVisible(), True)
        okWidget = self.ui.button_box.button(self.ui.button_box.Ok)
        QTest.mouseClick(okWidget, Qt.LeftButton)
        self.assertEqual(self.ui.isVisible(), False)

    def test_change_coordinates(self):
        self.ui.start_point_pushButton.click()
        self.assertNotEqual(self.ui.start_point_lineEdit.text(), "(0,0)")
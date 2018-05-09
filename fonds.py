# -*- coding: utf-8 -*-
"""
/***************************************************************************
 FiberOpticNetworkDesignSystem
                                 A QGIS plugin
 This plugin designing network from RUIAN data
                              -------------------
        begin                : 2017-11-02
        git sha              : $Format:%H$
        copyright            : (C) 2017 by Miroslav Starý
        email                : stary.mirosla@gmail.com
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
from PyQt4.QtCore import QSettings, QTranslator, qVersion, QCoreApplication
from PyQt4.QtGui import QAction, QIcon, QFileDialog, QColor, QPixmap
# Initialize Qt resources from file resources.py
import resources
# Import the code for the dialog
from fonds_dialog import FiberOpticNetworkDesignSystemDialog

import os.path

from PyQt4.QtCore import *
from PyQt4.QtGui import *
from qgis.core import *
from qgis.gui import *
from qgis.utils import *

from projectOutput import Project
from database import Database
from graph import Graph
from printClickedPoint import PrintClickedPoint

class FiberOpticNetworkDesignSystem():
    """QGIS Plugin Implementation."""
    # inicialize plugin, connect buttons with methods
    def __init__(self, iface):
        """Constructor.
        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """
        # Save reference to the QGIS interface
        self.iface = iface
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)

        # Create the dialog (after translation) and keep reference
        self.dlg = FiberOpticNetworkDesignSystemDialog()

        self.new_project = Project(self.iface)
        self.new_database = Database(self.iface)

        self.shaft_ID = 0
        self.net_line_ID = -1
        self.uses_points = set()

        self.dlg.create_shaft_pushButton.clicked.connect(self.create_shafts)
        self.dlg.create_connection_pushButton.clicked.connect(self.create_connect_to_house)
        self.dlg.create_net_pushButton.clicked.connect(self.start_choosen_alg)

        self.dlg.select_output_lineEdit.clear()
        self.dlg.select_output_toolButton.clicked.connect(self.select_output_file)

        self.help_variable = 0

        self.dlg.start_point_pushButton.clicked.connect(self.handle_click)

        self.dlg.max_distance_spinBox.setMinimum(10)
        self.dlg.max_connections_spinBox.setMinimum(1)
        self.dlg.radius_spinBox.setMinimum(1)

        self.dlg.max_distance_spinBox.setValue(50)
        self.dlg.max_connections_spinBox.setValue(10)
        self.dlg.radius_spinBox.setValue(1)
        self.dlg.start_point_lineEdit.setText("(0,0)")

    # noinspection PyMethodMayBeStatic
    def tr(self, message):
        """Get the translation for a string using Qt translation API.

        We implement this ourselves since we do not inherit QObject.

        :param message: String for translation.
        :type message: str, QString

        :returns: Translated version of message.
        :rtype: QString
        """
        return QCoreApplication.translate('FiberOpticNetworkDesignSystem', message)

    # connect toolbar icon with actions and run method
    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""
        self.act = QAction(QIcon(":/plugins/FiberOpticNetworkDesignSystem/icons/net_icon.png"),
                            QCoreApplication.translate("Plugin Toolbar", "Create Net"), self.iface.mainWindow())
        self.iface.addToolBarIcon(self.act)
        QObject.connect(self.act, SIGNAL("triggered()"), self.run)

        self.act2 = QAction(QIcon(":/plugins/FiberOpticNetworkDesignSystem/icons/db_icon.png"),
                            QCoreApplication.translate("Plugin Toolbar", "Connect to DB"), self.iface.mainWindow())
        self.iface.addToolBarIcon(self.act2)
        QObject.connect(self.act2, SIGNAL("triggered()"), self.new_database.run3)

        self.act4 = QAction(QIcon(":/plugins/FiberOpticNetworkDesignSystem/icons/project_icon.png"),
                            QCoreApplication.translate("Plugin Toolbar", "Create Project"), self.iface.mainWindow())
        self.iface.addToolBarIcon(self.act4)
        QObject.connect(self.act4, SIGNAL("triggered()"), self.new_project.run4)

        self.canvas_clicked = PrintClickedPoint(self.iface.mapCanvas())

    # after reload plugin remove toolbar icon
    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        self.iface.removeToolBarIcon(self.act)
        self.iface.removeToolBarIcon(self.act2)
        self.iface.removeToolBarIcon(self.act4)

    def find_layer(self, name):
        v = False
        for lyr in QgsMapLayerRegistry.instance().mapLayers().values():
            if lyr.name() == name:
                v = True
        return v

    # creating new empty layer
    def create_layer(self, type, name, list_of_attr):
        layer = QgsVectorLayer(type, name, "memory")
        layer.startEditing()
        layer_data = layer.dataProvider()
        layer_data.addAttributes(list_of_attr)
        layer.commitChanges()

        #QgsMapLayerRegistry.instance().addMapLayer(layer)#, addToLegend=False)
        return layer, layer_data

    # adding feature to line layer by 2 points in list
    def add_feature_to_line_layer(self, layer_data, points, attr_values):
        line = QgsGeometry.fromPolyline(points)
        line_feat = QgsFeature()
        line_feat.setAttributes(attr_values)
        line_feat.setGeometry(line)
        layer_data.addFeatures([line_feat])

    # finding nearest feature
    # layer to find, its index, start point, if you want del founded feat
    def find_closest_feat(self, layer, qgs_index, point, del_feat):
        nextNearestIds = qgs_index.nearestNeighbor(point, 1)
        feature = layer.getFeatures(QgsFeatureRequest().setFilterFid(nextNearestIds[0]))
        nextF = QgsFeature()
        feature.nextFeature(nextF)
        if del_feat:
            qgs_index.deleteFeature(nextF)
        return nextF

    # load layer from filepath to registry QGIS and set 5514 crs
    def load_shp_layer_to_qgis(self, filepath, layer_name):
        layer = QgsVectorLayer(filepath + layer_name + '.shp',
                               layer_name, 'ogr')
        if not layer.isValid():
            self.iface.messageBar().pushMessage("Error", "Layer %s did not load" % layer.name(),
                                                level=QgsMessageBar.WARNING, duration=3)

        layer.setCrs(QgsCoordinateReferenceSystem(5514, QgsCoordinateReferenceSystem.EpsgCrsId))
        QgsMapLayerRegistry.instance().addMapLayers([layer])

    # find point which is the most far from point in paramater
    def find_long_distance_points(self, point, multi_line_feat_geom):
        d = QgsDistanceArea()
        longest_distance = 0
        longest_point = QgsPoint()
        for i in range(len(multi_line_feat_geom)):
            for j in range(len(multi_line_feat_geom[i])):
                distance = d.measureLine(point, multi_line_feat_geom[i][j])
                if distance > longest_distance:
                    longest_distance = distance
                    longest_point = multi_line_feat_geom[i][j]

        return longest_point

    # find points where are crosses and put them to the set()
    def find_cross(self, line_layer, set_of_points):
        for i in line_layer.getFeatures():
            if i.geometry() != None:
                for j in line_layer.getFeatures():
                    if j.geometry() != None:
                        if i.geometry().intersects(j.geometry()):
                            p = i.geometry().intersection(j.geometry()).asPoint()
                            if p != QgsPoint(0,0): # if intersection is with MultiPolyline, we get point(0,0)
                                set_of_points.add(p)

                # Solve problem with MultiPolyLine
                # for every PolyLine in MultiPolyLine find start and end point
                # this solution fix start, end and cross points
                geom = i.geometry().asPolyline()
                if not geom:
                    geom = i.geometry().asMultiPolyline()

                    for g in geom:
                        start_point = QgsPoint(g[0])
                        end_point = QgsPoint(g[-1])
                        set_of_points.add(start_point)
                        set_of_points.add(end_point)

    # find start and end of lines and put them as points to the set()
    def find_start_end_of_lines(self, line_layer, set_of_points):
        for feature in line_layer.getFeatures():
            if feature.geometry() != None:
                geom = feature.geometry().asPolyline()

                if not geom: # layer ulice has PolyLine and MultiPolyLine
                    geom = feature.geometry().asMultiPolyline()
                    point = QgsPoint(geom[0][0])
                    start_point = self.find_long_distance_points(point, geom)
                    end_point = self.find_long_distance_points(start_point, geom)
                else:
                    start_point = QgsPoint(geom[0])
                    end_point = QgsPoint(geom[-1])

                set_of_points.add(start_point)
                set_of_points.add(end_point)

    # Create point on all ends of streets
    def put_points_on_end(self, line_layer, index_streets, point_layer):
        pr = point_layer.dataProvider()
        point_layer.startEditing()

        # Start and end of street
        self.find_start_end_of_lines(line_layer, self.uses_points)

        # Touching street
        self.find_cross(line_layer, self.uses_points)

        # Creating features on points
        max_count = 0
        self.shafts_streets_dict = {}
        for pp in self.uses_points:
            self.shaft_ID += 1
            feat = QgsFeature()
            feat.setGeometry(QgsGeometry.fromPoint(pp))

            count = 0  # count of streets, which are in touch with point feat
            connected_streets = []
            for line_feat in line_layer.getFeatures():
                if feat.geometry().intersects(line_feat.geometry()):
                    count += 1
                    connected_streets.append(line_feat)
                    if max_count < count:
                        max_count = count

            closest_street_feat = self.find_closest_feat(line_layer, index_streets, pp, False)
            feat.setAttributes([self.shaft_ID, count, 0, closest_street_feat['Kod'], "No"])
            self.shafts_streets_dict[self.shaft_ID] = connected_streets
            pr.addFeatures([feat])

        point_layer.commitChanges()

    # if exist shaft closer than x m?, find all shafts on street by street code in dictionary
    def put_shafts_on_street(self, house_point, closest_street_code, shafts_layer):
        # find the shafts on street
        d = QgsDistanceArea()
        close_shaft_bool = True

        selected_shafts_ids = []  # all shafts ID with selected Street code
        for shaft_id in self.shafts_streets_dict:  # finding shafts which have selected Street code
            for i in range(len(self.shafts_streets_dict[shaft_id])):
                if self.shafts_streets_dict[shaft_id][i]['Kod'] == closest_street_code:
                    selected_shafts_ids.append(shaft_id)

        # we have all ID shafts on street and we need to get features
        selected_shafts_feats = []  # all shafts feats with selected Street code
        for shaft_id in selected_shafts_ids:
            expr = QgsExpression("\"ID\"= %s " % shaft_id)  # Get a featureIterator from an expression
            it = shafts_layer.getFeatures(QgsFeatureRequest(expr))
            for f in it:
                selected_shafts_feats.append(f)

        # if this shaft has less then 10 connections and it is closer than 100 m:
        for shaft_feat in selected_shafts_feats:
            # if house is closer than 101 m and if shaft has less then 10 connections
            shaft_point = QgsPoint(shaft_feat.geometry().asPoint()[0], shaft_feat.geometry().asPoint()[1])
            if (d.measureLine(house_point, shaft_point)) <= self.max_connections_distance:
                if shaft_feat['Houses'] < self.max_house_connection:
                    shafts_layer.startEditing()
                    house_count = shaft_feat['Houses'] + 1  # number of houses connected to shafts
                    shafts_layer.changeAttributeValue(shaft_feat.id(), 2, house_count)
                    shafts_layer.commitChanges()

                    close_shaft_bool = False
                    break

        return close_shaft_bool

    # if exist any free shaft close to some house create connection
    def find_possible_connections(self, shafts_layer, index_shafts, house_point):
        d = QgsDistanceArea()
        close_shaft_bool = True

        closest_shaft = self.find_closest_feat(shafts_layer, index_shafts, house_point, False)

        shaft_point = QgsPoint(closest_shaft.geometry().asPoint()[0], closest_shaft.geometry().asPoint()[1])

        if (d.measureLine(house_point, shaft_point)) <= self.max_connections_distance:
            if closest_shaft['Houses'] < self.max_house_connection:
                shafts_layer.startEditing()
                house_count = closest_shaft['Houses'] + 1  # number of houses connected to shafts
                shafts_layer.changeAttributeValue(closest_shaft.id(), 2, house_count)
                shafts_layer.commitChanges()
                close_shaft_bool = False  # connection can be created

        return close_shaft_bool

    # else find the clostest point on street line and create new shaft
    def create_new_shaft_on_closest_point(self, ulice_layer, shafts_layer, net_layer, house_point,
                                          points, index_shafts, index_streets):
        d = QgsDistanceArea()
        close_shaft_bool = True

        # connect new shaft to house
        min_dist = 99999
        closer_point = QgsPoint()
        for field_of_fields_of_points in points:
            for field__of_points in field_of_fields_of_points:
                for p in field__of_points:
                    if p not in self.uses_points:
                        if (d.measureLine(house_point, p)) < min_dist:
                            min_dist = d.measureLine(house_point, p)
                            closer_point = p

        if (d.measureLine(house_point, closer_point)) <= self.max_connections_distance:
            self.uses_points.add(closer_point)
            shafts_layer.startEditing()
            net_layer.startEditing()

            # add point feat to layer
            pr = shafts_layer.dataProvider()
            self.shaft_ID += 1
            point_feat = QgsFeature()
            closest_street_feat = self.find_closest_feat(ulice_layer, index_streets, closer_point, False)
            point_feat.setAttributes([self.shaft_ID, 1, 1, closest_street_feat['Kod'], "No"])
            point_feat.setGeometry(QgsGeometry.fromPoint(closer_point))

            pr.addFeatures([point_feat])

            for u in ulice_layer.getFeatures():
                if point_feat.geometry().intersects(u.geometry()):
                    street = u

            shafts_layer.commitChanges()
            self.shafts_streets_dict[self.shaft_ID] = [street]
            net_layer.commitChanges()
            index_shafts.insertFeature(point_feat)
            close_shaft_bool = False  # connection can be created

        return close_shaft_bool

    # function create shafts for network
    def create_shafts(self):
        if not self.find_layer("shafts_point") and not self.find_layer("edges_line"):
            dir_path = self.dlg.select_output_lineEdit.text()
            if dir_path == "":
                self.iface.messageBar().pushMessage("Error", "First select output directory please.",
                                                    level=QgsMessageBar.WARNING, duration=3)
            else:
                try:
                    registry = QgsMapLayerRegistry.instance()
                    adresnimista_layer = registry.mapLayersByName('adresnimista')[0]
                    ulice_layer = registry.mapLayersByName('ulice')[0]

                    # creating new layers
                    shafts_layer = self.create_layer("Point?crs=epsg:5514", "shafts_point",
                                                  [QgsField("ID", QVariant.String), QgsField("Streets", QVariant.String),
                                                   QgsField("Houses", QVariant.String),
                                                   QgsField("StrCode", QVariant.String),
                                                   QgsField("StartPoint", QVariant.String)])[0]
                    net_layer = self.create_layer("LineString?crs=epsg:5514", "net",
                                                  [QgsField("ID", QVariant.String), QgsField("Street", QVariant.String),
                                                   QgsField("Name", QVariant.String), QgsField("Type", QVariant.String),
                                                   QgsField("Shaft_1", QVariant.String),
                                                   QgsField("Shaft_2", QVariant.String), QgsField("House", QVariant.String),
                                                   QgsField("Net Type", QVariant.String),
                                                   QgsField("R|FN", QVariant.String),
                                                   QgsField("Length", QVariant.String)])[0]
                    
                    # work with new layers ---------------------------------------------------------------------------------
                    index_streets = QgsSpatialIndex()
                    features = ulice_layer.getFeatures()
                    feat = QgsFeature()
                    while features.nextFeature(feat):
                        index_streets.insertFeature(feat)

                    self.put_points_on_end(ulice_layer, index_streets, shafts_layer)

                    self.max_connections_distance = self.dlg.max_distance_spinBox.value()
                    self.max_house_connection = self.dlg.max_connections_spinBox.value()

                    points = []
                    for feature in ulice_layer.getFeatures():
                        if feature.geometry() != None:
                            geom = feature.geometry().asPolyline()

                            if not geom:  # layer ulice has PolyLine and MultiPolyLine
                                geom = feature.geometry().asMultiPolyline()
                                points.append(geom)
                            else:
                                points.append([geom])

                    for house_feat in adresnimista_layer.getFeatures():
                        if house_feat.geometry() != None:
                            point = QgsPoint(house_feat.geometry().asPoint()[0], house_feat.geometry().asPoint()[1])
                            closest_street_feat = self.find_closest_feat(ulice_layer, index_streets, point, False)
                            closest_street_code = closest_street_feat['Kod']  # select street code

                            index_shafts = QgsSpatialIndex()
                            features_shafts = shafts_layer.getFeatures()
                            feat_shaft = QgsFeature()
                            while features_shafts.nextFeature(feat_shaft):
                                index_shafts.insertFeature(feat_shaft)

                            close_shaft_bool = True

                            # if exist, find all shafts on street by street code in dictionary and create connection
                            if close_shaft_bool:
                                close_shaft_bool = self.put_shafts_on_street(point, closest_street_code, shafts_layer)

                            # if exist any free shaft close to some house create connection
                            if close_shaft_bool:  # if connection was not created
                                close_shaft_bool = self.find_possible_connections(shafts_layer,index_shafts, point)

                            # else find the clostest point on street line and create new shaft
                            if close_shaft_bool:  # if connection was not created
                                # connect new shaft to house
                                close_shaft_bool = self.create_new_shaft_on_closest_point(ulice_layer, shafts_layer, net_layer,
                                                                                          point, points, index_shafts,
                                                                                          index_streets)
                                # update value of Shaft_1 attr
                                for net_feat in net_layer.getFeatures():
                                    if net_feat['Shaft_1'] == 0:
                                        for shaft_feat in shafts_layer.getFeatures():
                                            if net_feat.geometry().intersects(shaft_feat.geometry()):
                                                net_layer.startEditing()
                                                net_layer.changeAttributeValue(net_feat.id(), 4, shaft_feat.id())
                                                net_layer.commitChanges()
                    # ------------------------------------------------------------------------------------------------------

                    # reset shaft house connections
                    for shaft_f in shafts_layer.getFeatures():
                        shafts_layer.startEditing()
                        shafts_layer.changeAttributeValue(shaft_f.id(), 2, 0)
                        shafts_layer.commitChanges()

                    self.help_variable = net_layer
                    # save new layers as a Shapefile and load them to QGIS
                    QgsVectorFileWriter.writeAsVectorFormat(shafts_layer, dir_path + '\shafts_point',
                                                            "utf-8", None, "ESRI Shapefile")
                    self.load_shp_layer_to_qgis(dir_path + '/', 'shafts_point')

                    self.split_line_layer(ulice_layer, shafts_layer, net_layer)
                    self.iface.legendInterface().setLayerVisible(net_layer, False)
                    self.iface.messageBar().pushMessage("Shafts and edges line created.",
                                                        level=QgsMessageBar.INFO)

                    # fill lineEdit by coordinates of firs shaft
                    for shaft in shafts_layer.getFeatures():
                        if shaft['ID'] == 1:
                            point_to_lineEdit = QgsPoint(shaft.geometry().asPoint()[0], shaft.geometry().asPoint()[1])
                            self.dlg.start_point_lineEdit.setText(str(point_to_lineEdit))
                            break
                    self.iface.setActiveLayer(shafts_layer)

                except IndexError:
                    self.iface.messageBar().pushMessage("Error", "Please download street and address layers from RUIAN",
                                                        level=QgsMessageBar.WARNING, duration=3)
        else:
            self.iface.messageBar().pushMessage("Error", "Shaft layer or edges layer are already created",
                                                level=QgsMessageBar.WARNING, duration=10)

    # find street (edge) between two shafts (vertices)
    def find_edge(self, edge_layer, shaft_id_1, shaft_id_2):
        find_edge = QgsFeature()
        for edge in edge_layer.getFeatures():
            if (edge['Shaft_1'] == shaft_id_1) and (edge['Shaft_2'] == shaft_id_2):
                find_edge = edge
        return find_edge

    # Split line layer by point layer, create new layers and copy geom to new layer
    def split_line_layer(self, line_layer, point_layer, net_layer):
        dir_path = self.dlg.select_output_lineEdit.text()
        if dir_path == "":
            self.iface.messageBar().pushMessage("Error", "First select output directory please.",
                                                level=QgsMessageBar.WARNING, duration=3)
        else:
            layer = line_layer
            feats = [feat for feat in layer.getFeatures()]

            mem_layer = QgsVectorLayer("LineString?crs=epsg:5514", "duplicated_layer", "memory")

            mem_layer_data = mem_layer.dataProvider()
            attr = layer.dataProvider().fields().toList()
            mem_layer_data.addAttributes(attr)
            mem_layer_data.addFeatures(feats)

            for i in [1,2]:
                mem_layer.startEditing()

                for feat in point_layer.getFeatures():
                    cut = feat.geometry().asPoint()
                    mem_layer.splitFeatures([cut], True)

                mem_layer.commitChanges()

            edges_line = QgsVectorLayer("LineString?crs=epsg:5514", "edges_line", "memory")
            edges_line.startEditing()
            layer_data = edges_line.dataProvider()
            layer_data.addAttributes([QgsField("ID", QVariant.String), QgsField("Street", QVariant.String),
                                      QgsField("Name", QVariant.String), QgsField("Type", QVariant.String),
                                      QgsField("Shaft_1", QVariant.String), QgsField("Shaft_2", QVariant.String),
                                      QgsField("House", QVariant.String), QgsField("Net Type", QVariant.String),
                                      QgsField("R|FN", QVariant.String),
                                      QgsField("Length", QVariant.String)])
            edges_line.commitChanges()

            number_feat_net = net_layer.featureCount()
            self.copy_geom(mem_layer, edges_line, point_layer, number_feat_net)
            # save memory edges layer to PC, remove it from QGIS and back from file
            # now layer is not empty after restart QGIS

            QgsVectorFileWriter.writeAsVectorFormat(edges_line, dir_path + '\edges_line',
                                                "utf-8", None, "ESRI Shapefile")
            self.load_shp_layer_to_qgis(dir_path + '/', 'edges_line')

    # Copy split geometries to layer
    def copy_geom(self, from_line_layer, to_line_layer, point_layer, number_feat_net):
        to_line_layer.startEditing()

        id = number_feat_net
        for u in from_line_layer.getFeatures():
            if u.geometry() != None:
                geom = u.geometry().asPolyline()

                id += 1
                if not geom:
                    g = u.geometry().asMultiPolyline()
                    for geom in g:
                        intersect_shafts = []
                        for point_feat in point_layer.getFeatures():
                            t_geom = QgsGeometry.fromPolyline(geom)
                            if t_geom.intersects(point_feat.geometry()):
                                intersect_shafts.append(point_feat)

                        feat = QgsFeature()
                        int_shaft_point_1 = QgsPoint(intersect_shafts[0].geometry().asPoint()[0],
                                                     intersect_shafts[0].geometry().asPoint()[1])
                        int_shaft_point_2 = QgsPoint(intersect_shafts[1].geometry().asPoint()[0],
                                                     intersect_shafts[1].geometry().asPoint()[1])
                        d = QgsDistanceArea()
                        distance = d.measureLine(int_shaft_point_1, int_shaft_point_2)

                        feat.setAttributes([id, u['Kod'], u['Nazev'], 'Path', intersect_shafts[0].id(),
                                            intersect_shafts[1].id(), -1, 0, 0, distance])
                        feat.setGeometry(QgsGeometry.fromPolyline(geom))
                        to_line_layer.dataProvider().addFeatures([feat])
                        id += 1

                else:
                    intersect_shafts = self.find_intersect_layer(u, point_layer)

                    feat = QgsFeature()
                    int_shaft_point_1 = QgsPoint(intersect_shafts[0].geometry().asPoint()[0],
                                                 intersect_shafts[0].geometry().asPoint()[1])
                    int_shaft_point_2 = QgsPoint(intersect_shafts[1].geometry().asPoint()[0],
                                                 intersect_shafts[1].geometry().asPoint()[1])
                    d = QgsDistanceArea()
                    distance = d.measureLine(int_shaft_point_1, int_shaft_point_2)

                    feat.setAttributes([id, u['Kod'], u['Nazev'], 'Path', intersect_shafts[0].id(),
                                        intersect_shafts[1].id(), -1, 0, 0, distance])
                    feat.setGeometry(QgsGeometry.fromPolyline(geom))
                    to_line_layer.dataProvider().addFeatures([feat])

            to_line_layer.commitChanges()

    # find all intersect for feat in layer
    def find_intersect_layer(self, feat, layer):
        intersect_feats = []
        for layer_feat in layer.getFeatures():
            if feat.geometry().intersects(layer_feat.geometry()):
                intersect_feats.append(layer_feat)
        return intersect_feats

    # find feature in layer by point
    def find_point_feature(self, point, layer):
        for feat in layer.getFeatures():
            if str(feat.geometry().asPoint()) == str(point):
                point_feat = feat

                return point_feat

    # creating connections to houses
    def create_connect_to_house(self):
        if not self.find_layer("connections_line"):
            registry = QgsMapLayerRegistry.instance()
            house_layer = registry.mapLayersByName('adresnimista')[0]
            street_layer = registry.mapLayersByName('ulice')[0]
            try:
                dir_path = self.dlg.select_output_lineEdit.text()
                if dir_path == "":
                    self.iface.messageBar().pushMessage("Error", "First select output directory please.",
                                                        level=QgsMessageBar.WARNING, duration=3)
                else:
                    shaft_layer = registry.mapLayersByName('shafts_point')[0]

                    layer_name = self.dlg.name_lineEdit.text()
                    if layer_name == "":
                        layer_name = "connections_line"

                    QgsVectorFileWriter.writeAsVectorFormat(self.help_variable, dir_path + '/' + layer_name,
                                                    "utf-8", None, "ESRI Shapefile")
                    self.load_shp_layer_to_qgis(dir_path + '/', layer_name)
                    connections_layer = registry.mapLayersByName(layer_name)[0]

                    shaft_index = QgsSpatialIndex()
                    shafts = shaft_layer.getFeatures()
                    shaft_feat = QgsFeature()
                    while shafts.nextFeature(shaft_feat):
                        shaft_index.insertFeature(shaft_feat)

                    net_type, radfib = self.get_net_parameters()

                    # connect shafts with houses
                    for house in house_layer.getFeatures():
                        if house.geometry() != None:
                            house_point = QgsPoint(house.geometry().asPoint()[0], house.geometry().asPoint()[1])
                            # find closest shaft
                            shaft = self.find_closest_feat(shaft_layer, shaft_index, house_point, False)
                            shaft_point = QgsPoint(shaft.geometry().asPoint()[0], shaft.geometry().asPoint()[1])

                            d = QgsDistanceArea()
                            self.max_connections_distance = self.dlg.max_distance_spinBox.value()
                            self.max_house_connection = self.dlg.max_connections_spinBox.value()

                            if (d.measureLine(house_point, shaft_point)) <= self.max_connections_distance:
                                if int(shaft['Houses']) < int(self.max_house_connection):
                                    connections_layer.startEditing()
                                    self.net_line_ID += 1
                                    street = self.find_intersect_layer(shaft, street_layer)
                                    self.add_feature_to_line_layer(connections_layer, [house_point, shaft_point],
                                                                   [self.net_line_ID, street[0]['Kod'], street[0]['Nazev'],
                                                                    'Connection', shaft.id(), -1, house.id(), net_type, radfib, d.measureLine(house_point, shaft_point) ])
                                    connections_layer.commitChanges()

                                    shaft_layer.startEditing()
                                    # update Houses by intersection
                                    intersections = self.find_intersect_layer(shaft, connections_layer)
                                    shaft_layer.changeAttributeValue(shaft.id(), 2, len(intersections))
                                    shaft_layer.commitChanges()

                    self.dlg.name_lineEdit.clear()
                    self.iface.messageBar().pushMessage("Connections complete.", level=QgsMessageBar.INFO)
                    self.iface.setActiveLayer(shaft_layer)
            except IndexError:
                self.iface.messageBar().pushMessage("Error", "Need to create shafts before connecting houses",
                                                    level=QgsMessageBar.WARNING, duration=3)
        else:
            self.iface.messageBar().pushMessage("Error", "Connections layer already created",
                                                level=QgsMessageBar.WARNING, duration=10)

    # create new net by kruskal algorithm
    def create_net_by_kruskal(self):
        registry = QgsMapLayerRegistry.instance()

        try:
            dir_path = self.dlg.select_output_lineEdit.text()
            if dir_path == "":
                self.iface.messageBar().pushMessage("Error", "Please select output directory",
                                                    level=QgsMessageBar.WARNING, duration=3)
            else:
                shaft_layer = registry.mapLayersByName('shafts_point')[0]

                layer_name = self.dlg.name_lineEdit.text()
                if layer_name == "":
                    layer_name = "kruskal_net"

                net_layer = self.create_layer("LineString?crs=epsg:5514", layer_name,
                                              [QgsField("ID", QVariant.String), QgsField("Street", QVariant.String),
                                               QgsField("Name", QVariant.String), QgsField("Type", QVariant.String),
                                               QgsField("Shaft_1", QVariant.String),
                                               QgsField("Shaft_2", QVariant.String), QgsField("House", QVariant.String),
                                               QgsField("Net Type", QVariant.String),
                                               QgsField("R|FN", QVariant.String),
                                               QgsField("Length", QVariant.String),
                                               QgsField("Algorithm", QVariant.String),
                                               QgsField("Digging_t", QVariant.String)])[0]

                start_point = self.dlg.start_point_lineEdit.text()
                if start_point != "":
                    QgsVectorFileWriter.writeAsVectorFormat(net_layer, dir_path + '/' + layer_name,
                                                "utf-8", None, "ESRI Shapefile")
                    self.load_shp_layer_to_qgis(dir_path + '/', layer_name)
                    net_layer = registry.mapLayersByName(layer_name)[0]
                    edges_layer = registry.mapLayersByName('edges_line')[0]

                    g = Graph()
                    graph = g.create_graph(shaft_layer, edges_layer)
                    parent = {}
                    rank = {}
                    spanning_tree = g.kruskal(parent, rank, graph)

                    start_feat = self.find_point_feature(start_point, shaft_layer)
                    shaft_layer.startEditing()
                    shaft_layer.changeAttributeValue(start_feat.id(), 4, "Start")
                    shaft_layer.commitChanges()

                    net_type, radfib = self.get_net_parameters()

                    for edge in spanning_tree:
                        weight, shaft_id_1, shaft_id_2 = edge
                        find_edge = self.find_edge(edges_layer, shaft_id_1, shaft_id_2)

                        if find_edge.geometry() == None:
                            find_edge = self.find_edge(edges_layer, shaft_id_2, shaft_id_1)

                        if find_edge.geometry() != None:
                            net_layer.startEditing()
                            geom = find_edge.geometry().asPolyline()
                            feat = QgsFeature()
                            feat.setAttributes(
                                [find_edge['ID'], find_edge['Street'], find_edge['Name'], find_edge['Type'],
                                 find_edge['Shaft_1'], find_edge['Shaft_2'], -1, net_type, radfib, find_edge['Length'],
                                 'Kruskal'])
                            feat.setGeometry(QgsGeometry.fromPolyline(geom))
                            net_layer.dataProvider().addFeatures([feat])
                            net_layer.commitChanges()

                    self.dlg.name_lineEdit.clear()
                    self.iface.setActiveLayer(shaft_layer)
                    self.iface.messageBar().pushMessage("Kruskal algorithm complete.", level=QgsMessageBar.INFO)
                else:
                    self.iface.messageBar().pushMessage("Error", "Please select start point",
                                                    level=QgsMessageBar.WARNING, duration=3)
        except IndexError:
            self.iface.messageBar().pushMessage("Error", "Please create shafts layer first",
                                                level=QgsMessageBar.WARNING, duration=5)

    # create new net by bellman/ford algorithm
    def create_net_by_bellman(self):
        registry = QgsMapLayerRegistry.instance()

        try:
            dir_path = self.dlg.select_output_lineEdit.text()
            if dir_path == "":
                self.iface.messageBar().pushMessage("Error", "First select output directory please.",
                                                    level=QgsMessageBar.WARNING, duration=3)
            else:
                layer_name = self.dlg.name_lineEdit.text()
                if layer_name == "":
                    layer_name = "bellman-ford_net"

                net_layer = self.create_layer("LineString?crs=epsg:5514", layer_name,
                                              [QgsField("ID", QVariant.String), QgsField("Street", QVariant.String),
                                               QgsField("Name", QVariant.String), QgsField("Type", QVariant.String),
                                               QgsField("Shaft_1", QVariant.String),
                                               QgsField("Shaft_2", QVariant.String), QgsField("House", QVariant.String),
                                               QgsField("Net Type", QVariant.String),
                                               QgsField("R|FN", QVariant.String),
                                               QgsField("Length", QVariant.String),
                                               QgsField("Algorithm", QVariant.String),
                                               QgsField("Digging_t", QVariant.String)])[0]

                start_point = self.dlg.start_point_lineEdit.text()
                if start_point != "":
                    shaft_layer = registry.mapLayersByName('shafts_point')[0]
                    QgsVectorFileWriter.writeAsVectorFormat(net_layer, dir_path + '/' + layer_name,
                                                        "utf-8", None, "ESRI Shapefile")
                    self.load_shp_layer_to_qgis(dir_path + '/', layer_name)
                    net_layer = registry.mapLayersByName(layer_name)[0]
                    edges_layer = registry.mapLayersByName('edges_line')[0]

                    g = Graph()
                    gg = g.create_graph(shaft_layer, edges_layer)
                    graph = g.change_graph_repre(gg)
                    start_feat = self.find_point_feature(start_point, shaft_layer)
                    distance, predecessor = g.bellman_ford(graph, source=str(start_feat['ID']))

                    shaft_layer.startEditing()
                    shaft_layer.changeAttributeValue(start_feat.id(), 4, "Start")
                    shaft_layer.commitChanges()

                    net_type, radfib = self.get_net_parameters()
                    for node, pred in predecessor.items():
                        if pred != None:
                            find_edge = self.find_edge(edges_layer, node, pred)
                            if find_edge.geometry() == None:
                                find_edge = self.find_edge(edges_layer, pred, node)

                        if find_edge.geometry() != None:
                            net_layer.startEditing()
                            geom = find_edge.geometry().asPolyline()
                            feat = QgsFeature()
                            feat.setAttributes(
                                [find_edge['ID'], find_edge['Street'], find_edge['Name'], find_edge['Type'],
                                 find_edge['Shaft_1'], find_edge['Shaft_2'], -1, net_type, radfib, find_edge['Length'],
                                 'Bellman-Ford'])
                            feat.setGeometry(QgsGeometry.fromPolyline(geom))
                            net_layer.dataProvider().addFeatures([feat])
                            net_layer.commitChanges()

                    self.dlg.name_lineEdit.clear()
                    self.iface.setActiveLayer(shaft_layer)
                    self.iface.messageBar().pushMessage("Bellman-Ford algorithm complete.", level=QgsMessageBar.INFO)
                else:
                    self.iface.messageBar().pushMessage("Error", "Please select start point",
                                                        level=QgsMessageBar.WARNING, duration=3)

        except IndexError:
            self.iface.messageBar().pushMessage("Error", "Please create shafts layer first",
                                                level=QgsMessageBar.WARNING, duration=5)

    # return parameters of net in dialog
    def get_net_parameters(self):
        selectedIndex = self.dlg.net_type_comboBox.currentIndex()
        net_type = 'Undefined'
        if selectedIndex == 0:
            net_type = 'Pipe'
        else:
            if selectedIndex == 1:
                net_type = 'Fiber'

        radfib = self.dlg.radius_spinBox.value()

        return net_type, radfib

    # start algorithm selected by user
    def start_choosen_alg(self):
        selectedIndex = self.dlg.select_algorithm_comboBox.currentIndex()
        if selectedIndex == 1:
            self.create_net_by_kruskal()
        else:
            if selectedIndex == 2:
                self.create_net_by_bellman()

    # select outupt directory
    def select_output_file(self):
        dir_path = QFileDialog.getExistingDirectory(self.dlg, "Select output directory ", "")
        self.dlg.select_output_lineEdit.setText(dir_path)

    # method use next class to get mouse click coordinates
    def handle_click(self):
        self.dlg.start_point_lineEdit.clear()
        registry = QgsMapLayerRegistry.instance()
        try:
            shaft_layer = registry.mapLayersByName('shafts_point')[0]

            self.iface.mapCanvas().setMapTool(self.canvas_clicked)
            features = shaft_layer.selectedFeatures()

            self.dlg.start_point_lineEdit.setText(str(features[0].geometry().asPoint()))

        except IndexError:
            self.iface.messageBar().pushMessage("Error", "Please create shafts layer first",
                                                level=QgsMessageBar.WARNING, duration=3)

    # run method that performs all the real work
    def run(self):
        # fill comboBox with algorithms
        self.dlg.select_algorithm_comboBox.clear()
        alg_list = ['------ Choose algorithm ------', 'Kruskal', 'Bellman-Ford']
        self.dlg.select_algorithm_comboBox.addItems(alg_list)

        # fill comboBox with net types
        self.dlg.net_type_comboBox.clear()
        net_list = ['Pipe', 'Fiber']
        self.dlg.net_type_comboBox.addItems(net_list)

        # change choosen tool on my select tool
        self.iface.mapCanvas().setMapTool(self.canvas_clicked)

        self.dlg.show()
        # Run the dialog event loop
        result = self.dlg.exec_()
        # See if OK was pressed
        if result:
            self.new_database.run3()

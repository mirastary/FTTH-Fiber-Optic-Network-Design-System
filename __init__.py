# -*- coding: utf-8 -*-
"""
/***************************************************************************
 FiberOpticNetworkDesignSystem
                                 A QGIS plugin
 This plugin designing network from RUIAN data
                             -------------------
        begin                : 2017-11-02
        copyright            : (C) 2017 by Miroslav Starý
        email                : stary.mirosla@gmail.com
        git sha              : $Format:%H$
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
 This script initializes the plugin, making it known to QGIS.
"""


# noinspection PyPep8Naming
def classFactory(iface):  # pylint: disable=invalid-name
    """Load FiberOpticNetworkDesignSystem class from file FiberOpticNetworkDesignSystem.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    #
    from .fonds import FiberOpticNetworkDesignSystem
    return FiberOpticNetworkDesignSystem(iface)

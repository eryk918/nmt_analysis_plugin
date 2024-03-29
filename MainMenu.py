# -*- coding: utf-8 -*-
"""
/***************************************************************************
 NMTAnalysis
                                 A QGIS plugin
 Wtyczka QGIS umożliwiająca zautomatyzowane analizy numerycznych modeli terenu.
 Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
                              -------------------
        begin                : 2020-12-12
        git sha              : $Format:%H$
        copyright            : (C) 2020 by Eryk Chełchowski
        email                : erwinek1998@gmail.com
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
import os.path

from qgis.PyQt import QtGui
from qgis.PyQt.QtCore import QCoreApplication
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction

from .MainMenu_UI.MainMenu_UI import NMTMainMenu


class NMTAnalysis:

    def __init__(self, iface):
        self.iface = iface
        self.plugin_dir = os.path.dirname(__file__)
        self.actions = []
        self.menu = self.tr(u'&Analizy NMT')
        self.first_start = None

    def tr(self, message):
        return QCoreApplication.translate('NMTAnalysis', message)

    def add_action(
            self,
            icon_path,
            text,
            callback,
            enabled_flag=True,
            status_tip=None,
            whats_this=None,
            parent=None):

        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        self.iface.addToolBarIcon(action)
        self.iface.addPluginToMenu(self.menu, action)
        self.actions.append(action)
        return action

    def initGui(self):
        icon_path = os.path.join(self.plugin_dir, 'images/icon_s.png')
        self.add_action(
            icon_path,
            text=self.tr('Analizy NMT'),
            callback=self.run,
            parent=self.iface.mainWindow())
        self.first_start = True

    def unload(self):
        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr('Analizy NMT'),
                action)
            self.iface.removeToolBarIcon(action)

    def run(self):
        if self.first_start:
            self.first_start = False
            self.dlg = NMTMainMenu(plugin_path=self.plugin_dir)
            self.dlg.setWindowIcon(
                QtGui.QIcon(os.path.join(self.plugin_dir, 'images/icon.png')))
        else:
            self.dlg.btn_gen_model3d.setEnabled(True)

        self.dlg.show()
        result = self.dlg.exec_()

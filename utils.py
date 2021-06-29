# -*- coding: utf-8 -*-

import os
import re
import subprocess
import sys

from PyQt5.QtCore import Qt
from qgis.PyQt.QtWidgets import QComboBox, QApplication, QProgressDialog, \
    QMessageBox
from qgis.core import QgsProject, QgsVectorLayer, \
    QgsRasterLayer
from qgis.utils import iface

project = QgsProject.instance()


class CreateTemporaryLayer(QgsVectorLayer):
    parent_layer = None

    def __init__(self, *args, **kwargs):
        super(CreateTemporaryLayer, self).__init__(*args, **kwargs)

    def set_layer_fields(self, fields):
        self.dataProvider().addAttributes(fields)
        self.updateFields()


def repair_comboboxes(dlg):
    dialog_obj_list = [dlg.__getattribute__(obj) for obj in dlg.__dir__()]
    combo_list = list(
        filter(lambda elem: isinstance(elem, QComboBox), dialog_obj_list))
    if not combo_list:
        return
    for combo in combo_list:
        combo.installEventFilter(dlg)
        temp_value = combo.isEditable()
        combo.setEditable(True)
        combo_css = 'QComboBox { combobox-popup: 0; }'
        combo.setStyleSheet(f"{combo.styleSheet()} {combo_css}")
        combo.setMaxVisibleItems(10)
        combo.view().setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        combo.setEditable(temp_value)


def get_project_settings(parameter, key, default=''):
    return project.readEntry(parameter, key, default)[0]


def set_project_settings(parameter, key, value):
    return project.writeEntry(parameter, key, value)


def create_progress_bar(max_len, title='Proszę czekać',
                        txt='Trwa przetwarzanie danych.', start_val=0,
                        auto_close=True, cancel_btn=None, silent=False):
    progress_bar = QProgressDialog()
    progress_bar.setFixedWidth(500)
    progress_bar.setWindowTitle(title)
    progress_bar.setLabelText(txt)
    progress_bar.setMaximum(max_len)
    progress_bar.setValue(start_val)
    progress_bar.setAutoClose(auto_close)
    progress_bar.setCancelButton(cancel_btn)
    QApplication.processEvents()
    if silent:
        progress_bar.close()
    return progress_bar


def change_progressbar_value(progress, last_progress_value,
                             value, last_step=False, silent=False):
    if not silent:
        progress.show()
    QApplication.processEvents()
    last_progress_value += value
    if last_progress_value == 100 or last_step:
        progress.setValue(100)
        progress.close()
    else:
        progress.setValue(last_progress_value)


def add_layer_into_map(layer, group_name, parent_name=None, position=0):
    root = project.layerTreeRoot()
    if parent_name and root.findGroup(parent_name):
        group = root.findGroup(parent_name).findGroup(group_name)
    else:
        group = root.findGroup(group_name)
    if not group:
        project.addMapLayer(layer)
        return
    QApplication.processEvents()
    project.addMapLayer(layer, False)
    if group_name:
        group.insertLayer(position, layer)
        group.setExpanded(False)


def add_rasters_to_project(group_name, list_of_rasters, symbology=None):
    QApplication.processEvents()
    group_import = project.layerTreeRoot().findGroup(group_name)
    if not group_import:
        project.layerTreeRoot().addGroup(group_name)
    for raster_path in list_of_rasters:
        QApplication.processEvents()
        rlayer = QgsRasterLayer(raster_path, os.path.basename(raster_path))
        add_layer_into_map(rlayer, group_name)
        if symbology:
            rlayer.loadNamedStyle(symbology)
            rlayer.triggerRepaint()
            iface.layerTreeView().refreshLayerSymbology(rlayer.id())


def add_vectors_to_project(group_name, list_of_vectors, symbology=None):
    QApplication.processEvents()
    group_import = project.layerTreeRoot().findGroup(group_name)
    if not group_import:
        project.layerTreeRoot().addGroup(group_name)
    for vector_path in list_of_vectors:
        QApplication.processEvents()
        if isinstance(vector_path, QgsVectorLayer):
            vlayer = vector_path
        else:
            vlayer = QgsVectorLayer(vector_path, os.path.basename(vector_path),
                                    "ogr")
        add_layer_into_map(vlayer, group_name)
        if symbology:
            vlayer.loadNamedStyle(symbology)
            vlayer.triggerRepaint()
            iface.layerTreeView().refreshLayerSymbology(vlayer.id())


def open_other_files(filepath):
    if sys.platform.startswith('darwin'):
        subprocess.call(('open', filepath))
    elif os.name == 'nt':
        try:
            os.startfile(filepath)
        except WindowsError:
            ext = os.path.splitext(filepath)[-1]
            QMessageBox.critical(
                None, 'Analiza NMT',
                f'''Błąd przy otwieraniu pliku z rozszerzeniem *.{ext}.
Zainstaluj program obsługujący format *.{ext} i spróbuj ponownie.''',
                QMessageBox.Ok)
            return
    elif os.name == 'posix':
        subprocess.call(('xdg-open', filepath))


def standarize_path(path):
    return os.path.normpath(os.sep.join(re.split(r'\\|/', path)))

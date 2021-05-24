# -*- coding: utf-8 -*-

import os
import re
import subprocess
import sys
from tempfile import mkstemp

from PyQt5.QtCore import Qt
from qgis.PyQt.QtWidgets import QFontComboBox, \
    QComboBox, QApplication, QProgressDialog, QMessageBox
from qgis.core import QgsProject, QgsVectorLayer, \
    QgsFeature, QgsRasterLayer
from qgis.utils import iface

project = QgsProject.instance()
i_iface = iface


class CreateTemporaryLayer(QgsVectorLayer):
    parent_layer = None

    def __init__(self, *args, **kwargs):
        if 'parent_layer' in kwargs:
            self.parent_layer = kwargs['parent_layer']
            del kwargs['parent_layer']
        super(CreateTemporaryLayer, self).__init__(*args, **kwargs)

    def set_symbolization_from_layer(self, layer):
        file_handle, tmp_qml = mkstemp(suffix='.qml')
        os.close(file_handle)
        layer.saveNamedStyle(tmp_qml)
        self.loadNamedStyle(tmp_qml)
        os.remove(tmp_qml)

    def set_fields(self, fields):
        self.dataProvider().addAttributes(fields)
        self.updateFields()

    def set_fields_from_layer(self, layer):
        fields = layer.fields()
        self.set_fields(fields)

    def add_features(self, features):
        feats = []
        for feature in features:
            feat = QgsFeature(feature)
            feats.append(feat)
        if feats:
            self.dataProvider().addFeatures(feats)
        iface.mapCanvas().refresh()

    def add_to_group(self, group_name, main_group=None, pos=0):
        add_map_layer(self, group_name, main_group, position=pos)
        self.triggerRepaint()


def repair_comboboxes(dlg_instance):
    dir_list = [dlg_instance.__getattribute__(dir_elem) for dir_elem in
                dlg_instance.__dir__()]
    filter_dir_list = list(filter(
        lambda elem: isinstance(elem, QComboBox) or isinstance(elem,
                                                               QFontComboBox),
        dir_list))
    if not filter_dir_list:
        return
    for cbbx in filter_dir_list:
        cbbx.installEventFilter(dlg_instance)
        temp_value = cbbx.isEditable()
        cbbx.setEditable(True)
        cbbx.setStyleSheet(
            cbbx.styleSheet() + " QComboBox { combobox-popup: 0; }")
        cbbx.setMaxVisibleItems(10)
        cbbx.view().setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        cbbx.setEditable(temp_value)


def get_project_config(parameter, key, default=''):
    value = project.readEntry(parameter, key, default)[0]
    return value


def set_project_config(parameter, key, value):
    if isinstance(project, QgsProject):
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


def add_map_layer(layer, group_name, main_group_name=None, position=0):
    root = project.layerTreeRoot()
    if main_group_name and root.findGroup(main_group_name):
        group = root.findGroup(main_group_name).findGroup(group_name)
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
        add_map_layer(rlayer, group_name)
        if symbology:
            rlayer.loadNamedStyle(symbology)
            rlayer.triggerRepaint()


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
        add_map_layer(vlayer, group_name)
        if symbology:
            vlayer.loadNamedStyle(symbology)
            vlayer.triggerRepaint()


def open_other_files(filepath, send_by=None):
    if sys.platform.startswith('darwin'):
        subprocess.call(('open', filepath))
    elif os.name == 'nt':
        try:
            os.startfile(filepath)
        except WindowsError:
            ext = os.path.splitext(filepath)[-1]
            QMessageBox.critical(
                None, 'Analiza NMT',
                f'''Błąd przy otwieraniu pliku z rozszerzeniem *.{ext}!
Zainstaluj program obsługujący format *.{ext} i spróbuj ponownie.''',
                QMessageBox.Ok)
            return
    elif os.name == 'posix':
        subprocess.call(('xdg-open', filepath))


def normalize_path(path):
    return os.path.normpath(os.sep.join(re.split(r'\\|/', path)))

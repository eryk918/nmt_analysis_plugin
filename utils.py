# -*- coding: utf-8 -*-

import os
import re
from tempfile import mkstemp
from typing import Union

from PyQt5.QtCore import Qt
from qgis.PyQt.QtGui import QPixmap, QIcon
from qgis.PyQt.QtWidgets import QMessageBox, \
    QScrollArea, QWidget, QGridLayout, QLabel, QDialogButtonBox, QFontComboBox, \
    QComboBox, QApplication, QProgressDialog
from qgis.core import QgsMessageLog, Qgis, QgsProject, QgsVectorLayer, QgsFeature, \
    QgsMapLayer
from qgis.utils import iface

project = QgsProject.instance()
i_iface = iface


class TmpCopyLayer(QgsVectorLayer):
    parent_layer = None

    def __init__(self, *args, **kwargs):
        if 'parent_layer' in kwargs:
            self.parent_layer = kwargs['parent_layer']
            del kwargs['parent_layer']
        super(TmpCopyLayer, self).__init__(*args, **kwargs)

    def set_symbolization_from_layer(self, layer):
        copy_symbolization(layer, self)

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
        add_map_layer_to_group(self, group_name, main_group, position=pos)
        self.triggerRepaint()


def copy_symbolization(src_layer, dest_layer):
    tmp_qml = get_tmp_symbolization_file(src_layer)
    save_symbolization_and_remove_tmp(dest_layer, tmp_qml)


def get_tmp_symbolization_file(layer):
    file_handle, tmp_qml = mkstemp(suffix='.qml')
    os.close(file_handle)
    layer.saveNamedStyle(tmp_qml)

    return tmp_qml


def save_symbolization_and_remove_tmp(layer, tmp_qml):
    layer.loadNamedStyle(tmp_qml)
    os.remove(tmp_qml)


def lazy_repair_combobox_in_dialog(dlg_instance, brutal_change=False):
    dir_list = [dlg_instance.__getattribute__(dir_elem) for dir_elem in dlg_instance.__dir__()]

    filter_dir_list = list(filter(lambda elem: isinstance(elem, QComboBox)
                                               or isinstance(elem, QFontComboBox),
                                  dir_list))
    if not filter_dir_list:
        return
    for cbbx in filter_dir_list:
        cbbx.installEventFilter(dlg_instance)
        make_combobox_great_again(cbbx)


def get_project_config(parameter, key, default=''):
    value = project.readEntry(parameter, key, default)[0]
    return value


def make_combobox_great_again(cbbx):
    temp_bool = cbbx.isEditable()
    cbbx.setEditable(1)
    cbbx.setStyleSheet(cbbx.styleSheet() + " QComboBox { combobox-popup: 0; }")
    cbbx.setMaxVisibleItems(10)
    cbbx.view().setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
    cbbx.setEditable(temp_bool)


def set_project_config(parameter, key, value):
    if isinstance(project, QgsProject):
        return project.writeEntry(parameter, key, value)


def get_simple_progressbar(max_len, title='Proszę czekać',
                           txt='Trwa przetwarzanie danych.'):
    progress = QProgressDialog()
    progress.setFixedWidth(500)
    progress.setWindowTitle(title)
    progress.setLabelText(txt)
    progress.setMaximum(max_len)
    progress.setValue(0)
    progress.setAutoClose(True)
    progress.setCancelButton(None)
    QApplication.processEvents()
    return progress


class CustomMessageBox(QMessageBox):
    stylesheet = """
        * {
            background-color: rgb(53, 85, 109, 220);
            color: rgb(255, 255, 255);
            font: 10pt "Segoe UI";
            border: 0px;
        }

        QAbstractItemView {
            selection-background-color:  rgb(87, 131, 167);
        }

        QPushButton {
            border: none;
            border-width: 2px;
            border-radius: 6px;
            background-color: qlineargradient(spread:pad, x1:0, y1:1, x2:0, y2:0, stop:0 rgba(65, 97, 124, 255), stop:1 rgba(90, 135, 172, 255));
            padding: 5px 15px;
        }

        QPushButton:checked { 
            background-color: qlineargradient(spread:pad, x1:1, y1:1, x2:1, y2:0, stop:0 rgba(65, 97, 124, 255), stop:1 rgba(31, 65, 90, 255));
            border: solid;
            border-width: 2px;
            border-color: rgb(65, 97, 124);
        }

        QPushButton:pressed { 
            background-color: qlineargradient(spread:pad, x1:1, y1:1, x2:1, y2:0, stop:0 rgba(65, 97, 124, 255), stop:1 rgba(31, 65, 90, 255));
            border: solid;
            border-width: 2px;
            border-color: rgb(65, 97, 124);
        }
    """

    def __init__(self, parent=None, text='', image=''):
        if parent:
            super(CustomMessageBox, self).__init__(parent)
        else:
            super(CustomMessageBox, self).__init__(iface.mainWindow())
        self.text = text
        self.rebuild_layout(text, image)

    def rebuild_layout(self, text, image):
        self.setStyleSheet(self.stylesheet)

        scrll = QScrollArea(self)
        scrll.setWidgetResizable(True)
        self.qwdt = QWidget()
        self.qwdt.setLayout(QGridLayout(self))
        grd = self.findChild(QGridLayout)
        if text:
            lbl = QLabel(text, self)
            lbl.setStyleSheet(self.stylesheet)
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setWordWrap(False)
            lbl.setTextInteractionFlags(
                Qt.TextSelectableByMouse)
            self.qwdt.layout().addWidget(lbl, 1, 0)
        if image:
            px_lbl = QLabel(self)
            img_path = normalize_path(image)
            pixmap = QPixmap(img_path)
            px_lbl.setPixmap(pixmap)
            px_lbl.setMinimumSize(pixmap.width(), pixmap.height())
            px_lbl.setAlignment(Qt.AlignCenter)
            px_lbl.setWordWrap(False)
            self.qwdt.layout().addWidget(px_lbl, 0, 0)

        scrll.setWidget(self.qwdt)
        scrll.setContentsMargins(15, 5, 15, 10)
        scrll.setStyleSheet(self.stylesheet)
        grd.addWidget(scrll, 0, 1)
        self.layout().removeItem(self.layout().itemAt(0))
        self.layout().removeItem(self.layout().itemAt(0))
        self.setWindowTitle('GIAP - WODGiK')
        self.setWindowIcon(QIcon())

    def button_ok(self):
        self.setStandardButtons(QMessageBox.Ok)
        self.setDefaultButton(QMessageBox.Ok)
        self.set_proper_size()
        QMessageBox.exec_(self)

    def button_yes_no(self):
        self.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        self.setDefaultButton(QMessageBox.No)
        self.set_proper_size()
        return QMessageBox.exec_(self)

    def button_yes_no_cancel(self):
        self.setStandardButtons(
            QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel)
        self.setDefaultButton(QMessageBox.Cancel)
        self.set_proper_size()
        return QMessageBox.exec_(self)

    def button_yes_no_open(self):
        self.setStandardButtons(
            QMessageBox.Yes | QMessageBox.No | QMessageBox.Open)
        self.setDefaultButton(QMessageBox.No)
        self.set_proper_size()
        return QMessageBox.exec_(self)

    def button_ok_open(self):
        self.setStandardButtons(QMessageBox.Ok | QMessageBox.Open)
        self.setDefaultButton(QMessageBox.Open)
        self.set_proper_size()
        return QMessageBox.exec_(self)

    def button_edit_close(self):
        self.setStandardButtons(
            QMessageBox.Save | QMessageBox.Cancel | QMessageBox.Discard)
        self.setDefaultButton(QMessageBox.Discard)
        self.set_proper_size()
        return QMessageBox.exec_(self)

    def set_proper_size(self):
        scrll = self.findChild(QScrollArea)
        new_size = self.qwdt.sizeHint()
        if self.qwdt.sizeHint().height() > 600:
            new_size.setHeight(600)
        else:
            new_size.setHeight(self.qwdt.sizeHint().height())
        if self.qwdt.sizeHint().width() > 800:
            new_size.setWidth(800)
            new_size.setHeight(new_size.height() + 20)
        else:
            btn_box_width = self.findChild(QDialogButtonBox).sizeHint().width()
            if self.qwdt.sizeHint().width() > btn_box_width:
                new_size.setWidth(self.qwdt.sizeHint().width())
            else:
                new_size.setWidth(btn_box_width)
        scrll.setFixedSize(new_size)
        scrll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scrll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.show()
        scrll.horizontalScrollBar().setValue(
            int(scrll.horizontalScrollBar().maximum() / 2))


def add_map_layer_to_group(layer: Union[QgsVectorLayer, QgsMapLayer], group_name: str, main_group_name: str = None, important=False, position=0):
    if not layer.isValid():
        QgsMessageLog.logMessage(
            f'Warstwa nieprawidłowa {layer.name()}. Wymagana interwencja.',
            "GIAP - WODGiK",
            Qgis.Info)
    root = project.layerTreeRoot()
    if main_group_name and root.findGroup(main_group_name):
        group = root.findGroup(main_group_name).findGroup(group_name)
    else:
        group = root.findGroup(group_name)
    if not group:
        project.addMapLayer(layer)
        return
    if layer.id() in [layer_name.layer().id() for layer_name in
                      group.findLayers()] and not important:
        current_layer = identify_layer_by_id(layer.id())
        return
    project.addMapLayer(layer, False)
    if group_name:
        group.insertLayer(position, layer)
        group.setExpanded(False)


def identify_layer_by_id(layer_id, layer_list=None):
    if not layer_list:
        layers_list = QgsProject.instance().mapLayers().values()
    else:
        layers_list = layer_list
    for lyr in layers_list:
        if lyr.id() == layer_id:
            return lyr


def normalize_path(path):
    return os.path.normpath(os.sep.join(re.split(r'\\|/', path)))

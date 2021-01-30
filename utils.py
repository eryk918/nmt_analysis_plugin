# -*- coding: utf-8 -*-

import os
import re
from tempfile import mkstemp

from PyQt5.QtCore import Qt
from qgis.PyQt.QtGui import QPixmap, QIcon
from qgis.PyQt.QtWidgets import QMessageBox, \
    QScrollArea, QWidget, QGridLayout, QLabel, QDialogButtonBox, QFontComboBox, \
    QComboBox, QApplication, QProgressDialog
from qgis.core import QgsProject, QgsVectorLayer, \
    QgsFeature
from qgis.utils import iface

project = QgsProject.instance()
i_iface = iface


class CreateTMPCopy(QgsVectorLayer):
    parent_layer = None

    def __init__(self, *args, **kwargs):
        if 'parent_layer' in kwargs:
            self.parent_layer = kwargs['parent_layer']
            del kwargs['parent_layer']
        super(CreateTMPCopy, self).__init__(*args, **kwargs)

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


def repair_dialog_combos(dlg_instance):
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
                        auto_close=True, cancel_btn=None):
    progress_bar = QProgressDialog()
    progress_bar.setFixedWidth(500)
    progress_bar.setWindowTitle(title)
    progress_bar.setLabelText(txt)
    progress_bar.setMaximum(max_len)
    progress_bar.setValue(start_val)
    progress_bar.setAutoClose(auto_close)
    progress_bar.setCancelButton(cancel_btn)
    progress_bar.setStyleSheet(
        'QProgressBar::chunk{background:qlineargradient(spread:reflect, x1:0, y1:0.494, x2:0, y2:1, stop:0.269231 rgba(55, 165, 126, 255), stop:1 rgba(38, 115, 85, 255));}*{text-align:center; color:#000;}')
    QApplication.processEvents()
    return progress_bar


class InfoBox(QMessageBox):
    def __init__(self, parent=None, text='', image='', title='',
                 stylesheet=''):
        if not stylesheet:
            self.stylesheet = """
               * {
                    font: 10pt "Segoe MainMenu_UI";
                    border: 0px;
                }
                
                QPushButton {
                    border: 1px solid rgb(132, 132, 132, 120);
                    background: rgb(122, 122, 122, 90);
                    border-radius: 6px;
                    padding: 5px 15px;
                    color: rgb(255, 255, 255);
                }

                QPushButton:checked { 
                    border: 1px solid rgb(132, 132, 132, 120);
                }

                QPushButton:pressed { 
                    border: 1px solid rgb(132, 132, 132, 220);
                }
            """
        else:
            self.stylesheet = stylesheet
        if parent:
            super(InfoBox, self).__init__(parent)
        else:
            super(InfoBox, self).__init__(iface.mainWindow())
        self.text = text
        self.rebuild_layout(text, image, title)

    def rebuild_layout(self, text, image, title):
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
            lbl.setTextInteractionFlags(Qt.TextSelectableByMouse)
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
        self.setWindowTitle(title)
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


def add_map_layer(layer, group_name, main_group_name=None, position=0):
    root = project.layerTreeRoot()
    if main_group_name and root.findGroup(main_group_name):
        group = root.findGroup(main_group_name).findGroup(group_name)
    else:
        group = root.findGroup(group_name)
    if not group:
        project.addMapLayer(layer)
        return
    project.addMapLayer(layer, False)
    if group_name:
        group.insertLayer(position, layer)
        group.setExpanded(False)


def normalize_path(path):
    return os.path.normpath(os.sep.join(re.split(r'\\|/', path)))

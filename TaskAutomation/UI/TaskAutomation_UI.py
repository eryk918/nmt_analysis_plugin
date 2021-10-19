# -*- coding: utf-8 -*-
import os

from PyQt5.QtCore import Qt
from qgis.PyQt import uic, QtWidgets
from qgis.PyQt.QtWidgets import QDialog, QSizePolicy, QMessageBox, QComboBox, \
     QLabel

from ...utils import repair_comboboxes

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'TaskAutomation_UI.ui'))


class TaskAutomation_UI(QDialog, FORM_CLASS):
    def __init__(self, TaskAutomation, parent=None):
        super(TaskAutomation_UI, self).__init__(parent)
        self.setupUi(self)
        self.taskAutomation = TaskAutomation
        repair_comboboxes(self)
        self.setWindowIcon(self.taskAutomation.main.icon)
        self.mecha_dict = {
            'Generowanie punktów wysokościowych': 'GeneratePoints_UI',
            'Generowanie poligonów': 'GeneratePolygons_UI',
            'Generowanie statystyki': 'GenerateStatistics_UI',
            'Generowanie modelu nachylenia': 'GenerateSlope_UI',
            'Generowanie modelu cieniowania': 'GenerateHillshade_UI',
            'Generowanie modelu ekspozycji': 'GenerateAspect_UI',
            'Nadaj/przypisz odwzorowanie': 'SetProjection_UI',
            'Potnij raster': 'RasterCutter_UI'
        }

    def setup_dialog(self):
        self.pushButton_zapisz.clicked.connect(self.taskAutomation.run_tasks_mechanism)
        self.add_cbbx_btn.clicked.connect(self.add_cbbx)
        self.remove_cbbx_btn.clicked.connect(self.remove_cbbx)
        self.setWindowFlags(Qt.WindowStaysOnTopHint)
        self.cbbx_list = [self.task_cbbx_0, self.task_cbbx_1]
        self.label_list = []
        self.cbbx_nbr = 1
        for cbbx in self.cbbx_list:
            cbbx.addItems(self.mecha_dict.keys())
            if cbbx != self.cbbx_list[0]:
                cbbx.setCurrentIndex(1)

    def add_cbbx(self):
        if QtWidgets.QDesktopWidget().screenGeometry(-1).height() - 50 < \
                self.frame_2.sizeHint().height() + 120:
            QMessageBox.warning(
                self, 'Ostrzeżenie',
                'Nie można dodać kolejnego pola!\n'
                'Rozdzielczość ekranu jest za niska by zmieścić okno dialogowe!',
                QMessageBox.Ok)
            return
        self.cbbx_nbr += 1
        new_cbbx_name = f'self.task_cbbx_{self.cbbx_nbr}'
        new_label = f'self.label_{self.cbbx_nbr}'
        exec(f'{new_cbbx_name} = QComboBox()')
        exec(f'{new_label} = QLabel()')
        self.cbbx_list.append(eval(new_cbbx_name))
        self.label_list.append(eval(new_label))
        self.label_list[-1].setText('▼')
        self.label_list[-1].setAlignment(Qt.AlignCenter)
        self.cbbx_list[-1].addItems(self.mecha_dict.keys())
        self.cbbx_widget.layout().addWidget(self.label_list[-1])
        self.cbbx_widget.layout().addWidget(self.cbbx_list[-1])
        self.setFixedHeight(self.frame_2.sizeHint().height() + 120)
        if self.sizePolicy().verticalPolicy() != 7:
            self.setSizePolicy(QSizePolicy.Expanding)

    def remove_cbbx(self):
        if self.cbbx_list[-1] != self.task_cbbx_1:
            self.cbbx_widget.layout().removeWidget(self.cbbx_list[-1])
            self.cbbx_widget.layout().removeWidget(self.label_list[-1])
            self.cbbx_nbr -= 1
            self.cbbx_list.pop()
            self.label_list.pop()
            self.setFixedHeight(self.frame_2.sizeHint().height())
            if self.sizePolicy().verticalPolicy() != 7:
                self.setSizePolicy(QSizePolicy.Expanding)

    def run_dialog(self):
        self.show()
        self.exec_()

# -*- coding: utf-8 -*-
"""
    Antenna Array Analysis
    Copyright (C) 2019  Zhengyu Peng

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

import sys
import res_rc
from PyQt5 import QtWidgets, uic, QtCore
from PyQt5.QtCore import QThread

from linear_array import Linear_Array

import pyqtgraph as pg
#pg.setConfigOption('background', 'w')
#pg.setConfigOption('foreground', 'k')
#pg.setConfigOption('antialias', True)
QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)

import numpy as np

class MyApp(QtWidgets.QMainWindow):
    def __init__(self):
        super(QtWidgets.QMainWindow, self).__init__()
        self.ui = uic.loadUi('ui_array_analysis.ui', self)

        self.pgCanvas = pg.GraphicsLayoutWidget()
        self.figureLayout.addWidget(self.pgCanvas)
        self.plotView = self.pgCanvas.addPlot()
        self.pgFigure = pg.PlotDataItem()
        self.pgFigure.setDownsampling(auto=True, method='peak')
        self.pgFigureHold = pg.PlotDataItem()
        self.plotView.setXRange(-90, 90)
        self.plotView.setYRange(-80, 0)

        self.plotView.addItem(self.pgFigure)
        self.plotView.setLabel(axis='bottom', text='Angle', units='°')
        self.plotView.setLabel(
            axis='left', text='Normalized amplitude', units='dB')
        self.plotView.showGrid(x=True, y=True, alpha=0.5)

        self.penActive = pg.mkPen(color=(179, 229, 252), width=1)
        self.pgFigure.setPen(self.penActive)
        self.penHold = pg.mkPen(color=(158, 158, 158), width=1)
        self.pgFigureHold.setPen(self.penHold)

        self.initUI()

        self.ui.spinBox_ArraySize.valueChanged.connect(
            self.arraySizeValueChanged)

        self.ui.doubleSpinBox_Spacing.valueChanged.connect(
            self.spacingValueChanged)

        self.ui.doubleSpinBox_Step.valueChanged.connect(
            self.plotStepValueChanged)

        self.ui.doubleSpinBox_SteeringAngle.valueChanged.connect(
            self.steeringAngleValueChanged)
        self.ui.horizontalSlider_SteeringAngle.valueChanged.connect(
            self.steeringAngleSliderMoved)

        self.ui.comboBox_Window.currentIndexChanged.connect(
            self.windowComboBoxChanged)

        self.ui.spinBox_SLL.valueChanged.connect(self.sllValueChange)
        self.ui.horizontalSlider_SLL.valueChanged.connect(self.sllSliderMoved)

        self.ui.spinBox_nbar.valueChanged.connect(self.nbarValueChange)
        self.ui.horizontalSlider_nbar.valueChanged.connect(
            self.nbarSliderMoved)

        self.ui.holdButton.clicked.connect(self.holdFigure)
        self.ui.clearButton.clicked.connect(self.clearFigure)

        self.linear_array = Linear_Array()
        self.linear_array_thread = QThread()
        self.linear_array.patternReady.connect(self.updatePattern)
        self.linear_array_thread.started.connect(
            self.linear_array.calculatePattern)
        self.linear_array.moveToThread(self.linear_array_thread)
        self.linear_array_thread.start()

        self.updateLinearArrayParameter()
        self.ui.show()

    def initUI(self):
        self.ui.spinBox_SLL.setVisible(False)
        self.ui.label_SLL.setVisible(False)
        self.ui.horizontalSlider_SLL.setVisible(False)
        self.ui.spinBox_nbar.setVisible(False)
        self.ui.label_nbar.setVisible(False)
        self.ui.horizontalSlider_nbar.setVisible(False)
        self.ui.clearButton.setEnabled(False)

        self.window_dict = {
            0: self.Square(),
            1: self.Chebyshev(),
            2: self.Taylor(),
            3: self.Hamming(),
            4: self.Hann()
        }

        self.ui.comboBox_Window.addItems(
            ['Square', 'Chebyshev', 'Taylor', 'Hamming', 'Hann'])

    def arraySizeValueChanged(self, value):
        self.updateLinearArrayParameter()

    def spacingValueChanged(self, value):
        self.updateLinearArrayParameter()

    def plotStepValueChanged(self):
        self.updateLinearArrayParameter()

    def steeringAngleValueChanged(self, value):
        self.ui.horizontalSlider_SteeringAngle.setValue(
            self.ui.doubleSpinBox_SteeringAngle.value() * 10)
        self.updateLinearArrayParameter()

    def steeringAngleSliderMoved(self, value):
        self.ui.doubleSpinBox_SteeringAngle.setValue(value / 10)
        self.updateLinearArrayParameter()

    def windowComboBoxChanged(self, value):
        self.window_dict[value]
        self.updateLinearArrayParameter()

    def sllValueChange(self, value):
        self.ui.horizontalSlider_SLL.setValue(self.ui.spinBox_SLL.value())
        self.updateLinearArrayParameter()

    def sllSliderMoved(self, value):
        self.ui.spinBox_SLL.setValue(value)
        self.updateLinearArrayParameter()

    def nbarValueChange(self, value):
        self.ui.horizontalSlider_nbar.setValue(self.ui.spinBox_nbar.value())
        self.updateLinearArrayParameter()

    def nbarSliderMoved(self, value):
        self.ui.spinBox_nbar.setValue(value)
        self.updateLinearArrayParameter()

    def updateLinearArrayParameter(self):
        self.array_size = self.ui.spinBox_ArraySize.value()
        self.spacing = self.ui.doubleSpinBox_Spacing.value()
        self.beam_loc = self.ui.doubleSpinBox_SteeringAngle.value()
        self.plot_step = self.ui.doubleSpinBox_Step.value()
        self.window_type = self.ui.comboBox_Window.currentIndex()
        self.window_sll = self.ui.spinBox_SLL.value()
        self.window_nbar = self.ui.spinBox_nbar.value()

        self.linear_array.updateData(
            self.array_size, self.spacing, self.beam_loc, self.plot_step,
            self.window_type, self.window_sll, self.window_nbar)

    def updatePattern(self, angle, pattern):
        self.pgFigure.setData(angle, pattern)
        self.angle = angle
        self.pattern = pattern

    def holdFigure(self):
        self.pgFigureHold.setData(self.angle, self.pattern)
        self.plotView.addItem(self.pgFigureHold)
        self.ui.clearButton.setEnabled(True)

    def clearFigure(self):
        self.plotView.removeItem(self.pgFigureHold)
        self.ui.clearButton.setEnabled(False)

    def Square(self):
        self.ui.spinBox_SLL.setVisible(False)
        self.ui.label_SLL.setVisible(False)
        self.ui.horizontalSlider_SLL.setVisible(False)
        self.ui.spinBox_nbar.setVisible(False)
        self.ui.label_nbar.setVisible(False)
        self.ui.horizontalSlider_nbar.setVisible(False)

    def Chebyshev(self):
        self.ui.spinBox_SLL.setVisible(True)
        self.ui.label_SLL.setVisible(True)
        self.ui.horizontalSlider_SLL.setVisible(True)
        self.ui.spinBox_nbar.setVisible(False)
        self.ui.label_nbar.setVisible(False)
        self.ui.horizontalSlider_nbar.setVisible(False)

    def Taylor(self):
        self.ui.spinBox_SLL.setVisible(True)
        self.ui.label_SLL.setVisible(True)
        self.ui.horizontalSlider_SLL.setVisible(True)
        self.ui.spinBox_nbar.setVisible(True)
        self.ui.label_nbar.setVisible(True)
        self.ui.horizontalSlider_nbar.setVisible(True)

    def Hamming(self):
        self.ui.spinBox_SLL.setVisible(False)
        self.ui.label_SLL.setVisible(False)
        self.ui.horizontalSlider_SLL.setVisible(False)
        self.ui.spinBox_nbar.setVisible(False)
        self.ui.label_nbar.setVisible(False)
        self.ui.horizontalSlider_nbar.setVisible(False)

    def Hann(self):
        self.ui.spinBox_SLL.setVisible(False)
        self.ui.label_SLL.setVisible(False)
        self.ui.horizontalSlider_SLL.setVisible(False)
        self.ui.spinBox_nbar.setVisible(False)
        self.ui.label_nbar.setVisible(False)
        self.ui.horizontalSlider_nbar.setVisible(False)

if __name__ == '__main__':
    # app = QtWidgets.QApplication.instance()
    # if not app:  # create QApplication if it doesn't exist
    #     app = QtWidgets.QApplication(sys.argv)
    app = QtWidgets.QApplication(sys.argv)
    window = MyApp()
    window.show()

    ##!
    app.exec_()
    #sys.exit(app.exec_())

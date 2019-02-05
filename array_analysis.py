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
from PyQt5 import QtWidgets, uic, QtCore, QtGui
QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)

import numpy as np
from linear_array import Linear_Array

import pyqtgraph as pg
pg.setConfigOption('background', 'w')
pg.setConfigOption('foreground', 'k')
pg.setConfigOption('antialias', True)

font = QtGui.QFont()
font.setPixelSize(16)


class MyApp(QtWidgets.QMainWindow):
    def __init__(self):
        super(QtWidgets.QMainWindow, self).__init__()
        self.ui = uic.loadUi('array_analysis.ui', self)

        self.pgCanvas = pg.GraphicsLayoutWidget()
        self.figureLayout.addWidget(self.pgCanvas)
        self.plotView = self.pgCanvas.addPlot()
        self.pgFigure = pg.PlotCurveItem()
        self.pen = pg.mkPen({'color': '1565C0', 'width': 3})

        self.plotView.addItem(self.pgFigure)
        self.plotView.setLabel(
            axis='bottom', text='<a style="font-size:16px">Angle (°)</a>')
        self.plotView.setLabel(
            axis='left',
            text='<a style="font-size:16px">Normalized amplitude (dB)</a>')
        self.plotView.showGrid(x=True, y=True, alpha=0.5)

        self.plotView.getAxis('bottom').tickFont = font
        self.plotView.getAxis('bottom').setStyle(tickTextOffset=8)

        self.plotView.getAxis('left').tickFont = font
        self.plotView.getAxis('left').setStyle(tickTextOffset=8)

        self.initUI()

        self.ui.spinBox_ArraySize.valueChanged.connect(
            self.arraySizeValueChanged)

        self.ui.doubleSpinBox_Spacing.valueChanged.connect(
            self.spacingValueChanged)
        
        self.ui.doubleSpinBox_Step.valueChanged.connect(
            self.plotStepValueChanged)

        self.ui.doubleSpinBox_SteeringAngle.valueChanged.connect(
            self.steeringAngleValueChanged)
        self.ui.horizontalSlider_SteeringAngle.sliderMoved.connect(
            self.steeringAngleSliderMoved)

        self.ui.comboBox_Window.currentIndexChanged.connect(self.windowComboBoxChanged)

        self.ui.show()

    def initUI(self):
        self.ui.spinBox_SLL.setVisible(False)
        self.ui.label_SLL.setVisible(False)
        self.ui.horizontalSlider_SLL.setVisible(False)

        self.ui.comboBox_Window.addItems(['Square', 'Chebyshev'])

    def arraySizeValueChanged(self, value):
        self.updatePattern()

    def spacingValueChanged(self, value):
        self.updatePattern()
        
    def plotStepValueChanged(self):
        self.updatePattern()

    def steeringAngleValueChanged(self, value):
        self.ui.horizontalSlider_SteeringAngle.setValue(
                self.ui.doubleSpinBox_SteeringAngle.value() * 10)
        self.updatePattern()

    def steeringAngleSliderMoved(self, value):
        self.ui.doubleSpinBox_SteeringAngle.setValue(value / 10)
        self.updatePattern()


        
    def windowComboBoxChanged(self, value):
        if value==0:
            self.ui.spinBox_SLL.setVisible(False)
            self.ui.label_SLL.setVisible(False)
            self.ui.horizontalSlider_SLL.setVisible(False)
        elif value==1:
            self.ui.spinBox_SLL.setVisible(True)
            self.ui.label_SLL.setVisible(True)
            self.ui.horizontalSlider_SLL.setVisible(True)
            

    def updatePattern(self):
        array_size = self.ui.spinBox_ArraySize.value()
        spacing = self.ui.doubleSpinBox_Spacing.value()
        beam_loc = self.ui.doubleSpinBox_SteeringAngle.value()
        plot_step = self.ui.doubleSpinBox_Step.value()

        array = Linear_Array(array_size, spacing, beam_loc, plot_step)
        self.angle = array.getPattern()['angle']
        self.pattern = array.getPattern()['pattern']

        self.pgFigure.setData(self.angle, self.pattern, pen=self.pen)


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    window = MyApp()
    window.show()
    sys.exit(app.exec_())
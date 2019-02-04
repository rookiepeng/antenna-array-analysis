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
#pg.setConfigOption('antialias', True)

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
        self.pen = pg.mkPen({'color': '2196F3', 'width': 4})

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

        self.ui.plotButton.clicked.connect(self.updatePattern)

        self.initUI()

        self.ui.lineEdit_ArraySize.editingFinished.connect(self.updatePattern)
        self.ui.lineEdit_Spacing.editingFinished.connect(self.updatePattern)

        #        self.ui.lineEdit_SteeringAngle.editingFinished.connect(self.updatePattern)
        #        self.ui.lineEdit_SteeringAngle.editingFinished.connect(self.steeringAngleTextChanged)
        #        self.ui.lineEdit_SteeringAngle.textEdited.connect(self.updatePattern)
        self.ui.lineEdit_SteeringAngle.textEdited.connect(
            self.steeringAngleTextChanged)

        self.ui.horizontalSlider_SteeringAngle.sliderMoved.connect(
            self.steeringAngleSliderMoved)

        self.ui.show()

    def initUI(self):
        self.ui.lineEdit_SLL.setVisible(False)
        self.ui.label_SLL.setVisible(False)

        self.ui.comboBox_Window.addItems(['Square', 'Chebyshev'])
        self.ui.lineEdit_ArraySize.setText('128')
        self.ui.lineEdit_Spacing.setText('0.5')
        self.ui.lineEdit_SteeringAngle.setText('10')

    def steeringAngleTextChanged(self):
        try:
            self.ui.horizontalSlider_SteeringAngle.setValue(
                np.round(
                    np.array(
                        self.ui.lineEdit_SteeringAngle.text(), dtype=float) *
                    10).astype(int))
            self.updatePattern()
        except:
            print('Wrong value')

    def steeringAngleSliderMoved(self, value):
        self.ui.lineEdit_SteeringAngle.setText(str(value / 10))
        self.updatePattern()

    def updatePattern(self):
        array_size = np.array(self.ui.lineEdit_ArraySize.text(), dtype=int)
        spacing = np.array(self.ui.lineEdit_Spacing.text(), dtype=float)
        beam_loc = np.array(self.ui.lineEdit_SteeringAngle.text(), dtype=float)

        array = Linear_Array(array_size, spacing, beam_loc)
        self.angle = array.getPattern()['angle']
        self.pattern = array.getPattern()['pattern']

        self.pgFigure.setData(self.angle, self.pattern, pen=self.pen)


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    window = MyApp()
    window.show()
    sys.exit(app.exec_())
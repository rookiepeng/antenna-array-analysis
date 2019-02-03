# -*- coding: utf-8 -*-
"""
Created on Fri Feb  1 14:48:19 2019

@author: zjx8rj
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
        self.plotView.setXRange(-90, 90)

        self.ui.plotButton.clicked.connect(self.updatePattern)

        self.initUI()

        self.ui.show()

    def initUI(self):
        self.ui.lineEdit_SLL.setVisible(False)
        self.ui.label_SLL.setVisible(False)

        self.ui.comboBox_Window.addItems(['Square', 'Chebyshev'])

    def updatePattern(self):
        array_size = np.array(self.ui.lineEdit_ArraySize.text(), dtype=int)
        spacing = np.array(self.ui.lineEdit_Spacing.text(), dtype=float)
        beam_loc = np.array(self.ui.lineEdit_MainBeamAngle.text(), dtype=float)

        array = Linear_Array(array_size, spacing, beam_loc)
        self.angle = array.getPattern()['angle']
        self.pattern = array.getPattern()['pattern']

        self.pgFigure.setData(self.angle, self.pattern, pen=self.pen)


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    window = MyApp()
    window.show()
    sys.exit(app.exec_())
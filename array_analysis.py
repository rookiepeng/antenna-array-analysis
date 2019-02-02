# -*- coding: utf-8 -*-
"""
Created on Fri Feb  1 14:48:19 2019

@author: zjx8rj
"""

import sys
from PyQt5 import QtWidgets, uic, QtCore, QtGui
QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)

import numpy as np

import pyqtgraph as pg
pg.setConfigOption('background', 'w')
pg.setConfigOption('foreground', 'k')
pg.setConfigOption('antialias', True)

font=QtGui.QFont()
font.setPixelSize(16)

class MyApp(QtWidgets.QMainWindow):
    def __init__(self):
        super(QtWidgets.QMainWindow, self).__init__()
        self.ui = uic.loadUi('array_analysis.ui', self)
        
        self.pgcanvas = pg.GraphicsLayoutWidget()
        self.figureLayout.addWidget(self.pgcanvas)
        self.plotView=self.pgcanvas.addPlot()
        self.pattern = pg.PlotCurveItem()
        self.pen=pg.mkPen({'color':'2196F3', 'width':5})
        
        self.plotView.addItem(self.pattern)
        self.plotView.setLabel(axis='bottom', text='<a style="font-size:16px">Angle (°)</a>')
        self.plotView.setLabel(axis='left', text='<a style="font-size:16px">Normalized amplitude (dB)</a>')
        self.plotView.showGrid(x=True, y=True, alpha=0.8)
        
        self.plotView.getAxis('bottom').tickFont = font
        self.plotView.getAxis('bottom').setStyle(tickTextOffset = 8)
        
        self.plotView.getAxis('left').tickFont = font
        self.plotView.getAxis('left').setStyle(tickTextOffset = 8)
        
        #self.updatePattern(np.arange(-90,90,1), 20*np.log10(np.cos(np.arange(-90,90,1)/180*np.pi)+0.000001))

        self.ui.show()
        
    def updatePattern(self, angle, pattern):
        self.pattern.setData(angle,pattern, pen=self.pen)


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    window = MyApp()
    window.show()
    sys.exit(app.exec_())
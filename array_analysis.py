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

# pg.setConfigOption('background', 'w')
# pg.setConfigOption('foreground', 'k')
QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)

import numpy as np


class MyApp(QtWidgets.QMainWindow):
    def __init__(self):
        super(QtWidgets.QMainWindow, self).__init__()
        self.theta = np.linspace(-90, 90, num=1801, endpoint=True)
        self.window_dict = {
            0: self.disable_window_config,
            1: self.chebyshev,
            2: self.taylor,
            3: self.disable_window_config,
            4: self.disable_window_config
        }
        self.plotType = 'Cartesian'
        self.ampOffset = 60

        self.ui = uic.loadUi('ui_array_analysis.ui', self)

        self.pgCanvas = pg.GraphicsLayoutWidget()
        self.figureLayout.addWidget(self.pgCanvas)

        self.cartesianPlot = pg.PlotItem()

        self.pgFigure = pg.PlotDataItem()
        self.pgFigureHold = pg.PlotDataItem()
        self.cartesianPlot.setXRange(-90, 90)
        self.cartesianPlot.setYRange(-80, 0)

        self.cartesianPlot.addItem(self.pgFigure)
        self.cartesianPlot.setLabel(axis='bottom', text='Angle', units='°')
        self.cartesianPlot.setLabel(
            axis='left', text='Normalized amplitude', units='dB')
        self.cartesianPlot.showGrid(x=True, y=True, alpha=0.5)

        self.penActive = pg.mkPen(color=(244, 143, 177), width=1)
        self.pgFigure.setPen(self.penActive)
        self.penHold = pg.mkPen(color=(158, 158, 158), width=1)
        self.pgFigureHold.setPen(self.penHold)

        self.cartesianPlot.setLimits(
            xMin=-90, xMax=90, yMin=-110, yMax=1, minXRange=0.1, minYRange=0.1)

        self.cartesianPlot.sigXRangeChanged.connect(
            self.plotview_x_range_changed)

        #############
        self.polarPlot = pg.PlotItem()
        # self.polarPlot.setLimits(xMin=-self.ampOffset, xMax=self.ampOffset, minXRange=0.1, minYRange=0.1)
        self.polarPlot.setAspectLocked()
        self.polarPlot.hideAxis('left')
        self.polarPlot.hideAxis('bottom')

        # Add polar grid lines


        self.circleList = []
        self.circleLabel = []
        self.circleLabel.append(pg.TextItem('0 dB'))
        self.polarPlot.addItem(self.circleLabel[0])
        self.circleLabel[0].setPos(self.ampOffset, 0)
        for circle_idx in range(0, 6):
            self.circleList.append(
                pg.QtGui.QGraphicsEllipseItem(
                    -self.ampOffset + self.ampOffset / 6 * circle_idx,
                    -self.ampOffset + self.ampOffset / 6 * circle_idx,
                    (self.ampOffset - self.ampOffset / 6 * circle_idx) * 2,
                    (self.ampOffset - self.ampOffset / 6 * circle_idx) * 2))
            self.circleList[circle_idx].setStartAngle(2880)
            self.circleList[circle_idx].setSpanAngle(2880)
            self.circleList[circle_idx].setPen(pg.mkPen(0.2))
            self.polarPlot.addItem(self.circleList[circle_idx])

            self.circleLabel.append(
                pg.TextItem(str(-self.ampOffset / 6 * (circle_idx + 1))))
            self.circleLabel[circle_idx + 1].setPos(
                self.ampOffset - self.ampOffset / 6 * (circle_idx + 1), 0)
            self.polarPlot.addItem(self.circleLabel[circle_idx + 1])

        self.polarPlot.addLine(x=0, pen=0.6)
        self.polarPlot.addLine(y=0, pen=0.6)
        self.pgPolarPlot = pg.PlotDataItem()
        self.pgPolarPlot.setPen(self.penActive)
        self.polarPlot.addItem(self.pgPolarPlot)
        self.polarPlot.setMouseEnabled(x=False, y=False)

        ######################

        self.show_cartesian_plot()

        self.init_ui()

        self.linear_array = Linear_Array()
        self.linear_array_thread = QThread()
        self.linear_array.patternReady.connect(self.update_pattern)
        self.linear_array.patternReady.connect(self.update_polar_pattern)
        self.linear_array_thread.started.connect(
            self.linear_array.calculatePattern)
        self.linear_array.moveToThread(self.linear_array_thread)
        self.linear_array_thread.start()

        self.update_linear_array_parameter()
        self.ui.show()

    def init_ui(self):
        self.ui.spinBox_SLL.setVisible(False)
        self.ui.label_SLL.setVisible(False)
        self.ui.horizontalSlider_SLL.setVisible(False)
        self.ui.spinBox_nbar.setVisible(False)
        self.ui.label_nbar.setVisible(False)
        self.ui.horizontalSlider_nbar.setVisible(False)
        self.ui.clearButton.setEnabled(False)

        self.ui.comboBox_Window.addItems(
            ['Square', 'Chebyshev', 'Taylor', 'Hamming', 'Hann'])

        self.ui.spinBox_ArraySize.valueChanged.connect(
            self.update_linear_array_parameter)

        self.ui.doubleSpinBox_Spacing.valueChanged.connect(
            self.update_linear_array_parameter)

        self.ui.doubleSpinBox_SteeringAngle.valueChanged.connect(
            self.steering_angle_value_changed)
        self.ui.horizontalSlider_SteeringAngle.valueChanged.connect(
            self.steering_angle_slider_moved)

        self.ui.comboBox_Window.currentIndexChanged.connect(
            self.window_combobox_changed)

        self.ui.spinBox_SLL.valueChanged.connect(self.sll_value_change)
        self.ui.horizontalSlider_SLL.valueChanged.connect(
            self.sll_slider_moved)

        self.ui.spinBox_nbar.valueChanged.connect(self.nbar_value_changed)
        self.ui.horizontalSlider_nbar.valueChanged.connect(
            self.nbar_slider_moved)

        self.ui.spinBox_polarMinAmp.valueChanged.connect(
            self.polar_min_amp_value_changed)
        self.ui.horizontalSlider_polarMinAmp.valueChanged.connect(
            self.polar_min_amp_slider_moved)

        self.ui.label_polarMinAmp.setVisible(False)
        self.ui.spinBox_polarMinAmp.setVisible(False)
        self.ui.horizontalSlider_polarMinAmp.setVisible(False)

        self.ui.holdButton.clicked.connect(self.hold_figure)
        self.ui.clearButton.clicked.connect(self.clear_figure)

        self.ui.radioButton_Cartesian.toggled.connect(
            self.cartesian_plot_toggled)
        self.ui.radioButton_Polar.toggled.connect(self.polar_plot_toggled)

    def steering_angle_value_changed(self, value):
        self.ui.horizontalSlider_SteeringAngle.setValue(value * 10)
        self.update_linear_array_parameter()

    def steering_angle_slider_moved(self, value):
        self.ui.doubleSpinBox_SteeringAngle.setValue(value / 10)
        self.update_linear_array_parameter()

    def window_combobox_changed(self, value):
        self.window_dict[value]()
        self.update_linear_array_parameter()

    def sll_value_change(self, value):
        self.ui.horizontalSlider_SLL.setValue(value)
        self.update_linear_array_parameter()

    def sll_slider_moved(self, value):
        self.ui.spinBox_SLL.setValue(value)
        self.update_linear_array_parameter()

    def nbar_value_changed(self, value):
        self.ui.horizontalSlider_nbar.setValue(value)
        self.update_linear_array_parameter()

    def nbar_slider_moved(self, value):
        self.ui.spinBox_nbar.setValue(value)
        self.update_linear_array_parameter()

    def polar_min_amp_value_changed(self, value):
        self.ui.horizontalSlider_polarMinAmp.setValue(value)
        self.ampOffset = -value
        self.update_linear_array_parameter()

    def polar_min_amp_slider_moved(self, value):
        self.ui.spinBox_polarMinAmp.setValue(value)
        self.ampOffset = -value
        self.update_linear_array_parameter()

    def update_linear_array_parameter(self):
        self.array_size = self.ui.spinBox_ArraySize.value()
        self.spacing = self.ui.doubleSpinBox_Spacing.value()
        self.beam_loc = self.ui.doubleSpinBox_SteeringAngle.value()
        self.window_type = self.ui.comboBox_Window.currentIndex()
        self.window_sll = self.ui.spinBox_SLL.value()
        self.window_nbar = self.ui.spinBox_nbar.value()

        self.linear_array.updateData(
            self.array_size, self.spacing, self.beam_loc, self.theta,
            self.window_type, self.window_sll, self.window_nbar)

    def update_pattern(self, angle, pattern):
        self.pgFigure.setData(angle, pattern)
        self.angle = angle
        self.pattern = pattern

    def update_polar_pattern(self, angle, pattern):
        self.angle = angle
        self.pattern = pattern
        pattern = pattern + self.ampOffset
        pattern[np.where(pattern < 0)] = 0
        x = pattern * np.sin(angle / 180 * np.pi)
        y = pattern * np.cos(angle / 180 * np.pi)

        self.circleLabel[0].setPos(self.ampOffset, 0)
        for circle_idx in range(0, 6):
            self.circleList[circle_idx].setRect(
                -self.ampOffset + self.ampOffset / 6 * circle_idx,
                -self.ampOffset + self.ampOffset / 6 * circle_idx,
                (self.ampOffset - self.ampOffset / 6 * circle_idx) * 2,
                (self.ampOffset - self.ampOffset / 6 * circle_idx) * 2)
            self.circleLabel[circle_idx + 1].setText(
                str(round(-self.ampOffset / 6 * (circle_idx + 1), 1)))
            self.circleLabel[circle_idx + 1].setPos(
                self.ampOffset - self.ampOffset / 6 * (circle_idx + 1), 0)
        self.pgPolarPlot.setData(x, y)

    def hold_figure(self):
        self.pgFigureHold.setData(self.angle, self.pattern)
        self.cartesianPlot.addItem(self.pgFigureHold)
        self.ui.clearButton.setEnabled(True)

    def clear_figure(self):
        self.cartesianPlot.removeItem(self.pgFigureHold)
        self.ui.clearButton.setEnabled(False)

    def disable_window_config(self):
        self.ui.spinBox_SLL.setVisible(False)
        self.ui.label_SLL.setVisible(False)
        self.ui.horizontalSlider_SLL.setVisible(False)
        self.ui.spinBox_nbar.setVisible(False)
        self.ui.label_nbar.setVisible(False)
        self.ui.horizontalSlider_nbar.setVisible(False)

    def chebyshev(self):
        self.ui.spinBox_SLL.setVisible(True)
        self.ui.label_SLL.setVisible(True)
        self.ui.horizontalSlider_SLL.setVisible(True)
        self.ui.spinBox_nbar.setVisible(False)
        self.ui.label_nbar.setVisible(False)
        self.ui.horizontalSlider_nbar.setVisible(False)

    def taylor(self):
        self.ui.spinBox_SLL.setVisible(True)
        self.ui.label_SLL.setVisible(True)
        self.ui.horizontalSlider_SLL.setVisible(True)
        self.ui.spinBox_nbar.setVisible(True)
        self.ui.label_nbar.setVisible(True)
        self.ui.horizontalSlider_nbar.setVisible(True)

    def plotview_x_range_changed(self, item):
        self.theta = np.linspace(
            item.viewRange()[0][0],
            item.viewRange()[0][1],
            num=1801,
            endpoint=True)
        self.update_linear_array_parameter()

    def cartesian_plot_toggled(self, checked):
        if checked and self.plotType is not 'Cartesian':
            self.pgCanvas.removeItem(self.polarPlot)
            self.pgCanvas.addItem(self.cartesianPlot)
            self.ui.label_polarMinAmp.setVisible(False)
            self.ui.spinBox_polarMinAmp.setVisible(False)
            self.ui.horizontalSlider_polarMinAmp.setVisible(False)

            self.theta = np.linspace(-90, 90, num=1801, endpoint=True)
            self.update_linear_array_parameter()
            self.cartesianPlot.setXRange(-90, 90)
            self.cartesianPlot.setYRange(-80, 0)

            self.plotType = 'Cartesian'

    def polar_plot_toggled(self, checked):
        if checked and self.plotType is not 'Polar':
            self.pgCanvas.removeItem(self.cartesianPlot)
            self.pgCanvas.addItem(self.polarPlot)
            self.ui.label_polarMinAmp.setVisible(True)
            self.ui.spinBox_polarMinAmp.setVisible(True)
            self.ui.horizontalSlider_polarMinAmp.setVisible(True)

            self.theta = np.linspace(-90, 90, num=1801, endpoint=True)
            self.update_linear_array_parameter()
            self.plotType = 'Polar'

    def show_cartesian_plot(self):
        self.pgCanvas.addItem(self.cartesianPlot)

    def show_polar_plot(self):
        self.pgCanvas.addItem(self.polarPlot)


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    window = MyApp()
    window.show()
    sys.exit(app.exec_())

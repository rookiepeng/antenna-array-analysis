"""
    Antenna Array Analysis

    Copyright (C) 2019  Zhengyu Peng
    E-mail: zpeng.me@gmail.com
    Website: https://zpeng.me

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

    `                      `
    -:.                  -#:
    -//:.              -###:
    -////:.          -#####:
    -/:.://:.      -###++##:
    ..   `://:-  -###+. :##:
           `:/+####+.   :##:
    .::::::::/+###.     :##:
    .////-----+##:    `:###:
     `-//:.   :##:  `:###/.
       `-//:. :##:`:###/.
         `-//:+######/.
           `-/+####/.
             `+##+.
              :##:
              :##:
              :##:
              :##:
              :##:
               .+:

"""

import sys
import res_rc
from PyQt5 import QtWidgets, uic, QtCore, QtGui
from PyQt5.QtCore import QThread

import numpy as np

from lineararray import LinearArray

import pyqtgraph as pg

# pg.setConfigOption('background', 'w')
# pg.setConfigOption('foreground', 'k')
QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)


class MyApp(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        super(QtWidgets.QMainWindow, self).__init__()
        self.ui = uic.loadUi('ui_array_analysis.ui', self)
        self.pgCanvas = pg.GraphicsLayoutWidget()
        self.figureLayout.addWidget(self.pgCanvas)

        self.linearArrayConfig = {'array_size': 64,
                                  'spacing': 0.5,
                                  'beam_loc': 0,
                                  'window_type_idx': 0,
                                  'window_sll': 60,
                                  'window_nbar': 20
                                  }

        self.theta = np.linspace(-90, 90, num=1801, endpoint=True)
        self.angle = np.linspace(-90, 90, num=1801, endpoint=True)
        self.pattern = np.zeros(np.shape(self.theta))

        self.plotType = 'Cartesian'  # 'Cartesian' or 'Polar'
        self.polarAmpOffset = 60

        self.holdAngle = np.linspace(-90, 90, num=1801, endpoint=True)
        self.holdPattern = np.zeros(np.shape(self.theta))
        self.holdEnabled = False

        self.windowDict = {
            0: self.disable_window_config,
            1: self.chebyshev,
            2: self.taylor,
            3: self.disable_window_config,
            4: self.disable_window_config
        }

        self.cartesianView = pg.PlotItem()
        self.cartesianPlot = pg.PlotDataItem()
        self.cartesianPlotHold = pg.PlotDataItem()

        self.polarView = pg.PlotItem()
        self.polarPlot = pg.PlotDataItem()
        self.polarPlotHold = pg.PlotDataItem()
        self.circleList = []
        self.circleLabel = []

        self.penActive = pg.mkPen(color=(244, 143, 177), width=1)
        self.penHold = pg.mkPen(color=(158, 158, 158), width=1)

        self.init_plot_view()
        self.init_ui()

        self.linear_array = LinearArray()
        self.linear_array_thread = QThread()
        self.linear_array.patternReady.connect(self.update_pattern)
        self.linear_array_thread.started.connect(
            self.linear_array.calculate_pattern)
        self.linear_array.moveToThread(self.linear_array_thread)
        self.linear_array_thread.start()

        self.update_linear_array_parameter(self.plotType)
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
            self.array_changed)

        self.ui.doubleSpinBox_Spacing.valueChanged.connect(
            self.array_changed)

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

        self.ui.actionQuit.triggered.connect(QtWidgets.qApp.quit)

    def init_plot_view(self):
        ############################################
        # Cartesian View
        self.cartesianPlot.setPen(self.penActive)
        self.cartesianPlotHold.setPen(self.penHold)
        self.cartesianView.addItem(self.cartesianPlot)

        self.cartesianView.setXRange(-90, 90)
        self.cartesianView.setYRange(-80, 0)
        self.cartesianView.setLabel(axis='bottom', text='Angle', units='°')
        self.cartesianView.setLabel(
            axis='left', text='Normalized amplitude', units='dB')
        self.cartesianView.showGrid(x=True, y=True, alpha=0.5)
        self.cartesianView.setLimits(
            xMin=-90, xMax=90, yMin=-110, yMax=1, minXRange=0.1, minYRange=0.1)

        ############################################
        # Polar View
        self.polarPlot.setPen(self.penActive)
        self.polarPlotHold.setPen(self.penHold)
        self.polarView.addItem(self.polarPlot)

        self.polarView.setAspectLocked()
        self.polarView.hideAxis('left')
        self.polarView.hideAxis('bottom')

        self.circleLabel.append(pg.TextItem('0 dB'))
        self.polarView.addItem(self.circleLabel[0])
        self.circleLabel[0].setPos(self.polarAmpOffset, 0)
        for circle_idx in range(0, 6):
            self.circleList.append(
                QtGui.QGraphicsEllipseItem(
                    -self.polarAmpOffset + self.polarAmpOffset / 6 * circle_idx,
                    -self.polarAmpOffset + self.polarAmpOffset / 6 * circle_idx,
                    (self.polarAmpOffset - self.polarAmpOffset / 6 * circle_idx) * 2,
                    (self.polarAmpOffset - self.polarAmpOffset / 6 * circle_idx) * 2))
            self.circleList[circle_idx].setStartAngle(2880)
            self.circleList[circle_idx].setSpanAngle(2880)
            self.circleList[circle_idx].setPen(pg.mkPen(0.2))
            self.polarView.addItem(self.circleList[circle_idx])

            self.circleLabel.append(
                pg.TextItem(str(-self.polarAmpOffset / 6 * (circle_idx + 1))))
            self.circleLabel[circle_idx + 1].setPos(
                self.polarAmpOffset - self.polarAmpOffset / 6 * (circle_idx + 1), 0)
            self.polarView.addItem(self.circleLabel[circle_idx + 1])

        self.polarView.addLine(x=0, pen=0.6)
        self.polarView.addLine(y=0, pen=0.6)
        self.polarView.addLine(y=0, pen=0.3).setAngle(45)
        self.polarView.addLine(y=0, pen=0.3).setAngle(-45)
        self.polarView.setMouseEnabled(x=False, y=False)

        ############################################
        self.cartesianView.sigXRangeChanged.connect(
            self.plotview_x_range_changed)
        self.show_cartesian_plot()

    def array_changed(self):
        self.update_linear_array_parameter(self.plotType)

    def steering_angle_value_changed(self, value):
        self.ui.horizontalSlider_SteeringAngle.setValue(value * 10)
        self.update_linear_array_parameter(self.plotType)

    def steering_angle_slider_moved(self, value):
        self.ui.doubleSpinBox_SteeringAngle.setValue(value / 10)
        self.update_linear_array_parameter(self.plotType)

    def window_combobox_changed(self, value):
        self.windowDict[value]()
        self.update_linear_array_parameter(self.plotType)

    def sll_value_change(self, value):
        self.ui.horizontalSlider_SLL.setValue(value)
        self.update_linear_array_parameter(self.plotType)

    def sll_slider_moved(self, value):
        self.ui.spinBox_SLL.setValue(value)
        self.update_linear_array_parameter(self.plotType)

    def nbar_value_changed(self, value):
        self.ui.horizontalSlider_nbar.setValue(value)
        self.update_linear_array_parameter(self.plotType)

    def nbar_slider_moved(self, value):
        self.ui.spinBox_nbar.setValue(value)
        self.update_linear_array_parameter(self.plotType)

    def polar_min_amp_value_changed(self, value):
        self.ui.horizontalSlider_polarMinAmp.setValue(value)
        self.polarAmpOffset = -value
        self.update_linear_array_parameter(self.plotType)

    def polar_min_amp_slider_moved(self, value):
        self.ui.spinBox_polarMinAmp.setValue(value)
        self.polarAmpOffset = -value
        self.update_linear_array_parameter(self.plotType)

    def update_linear_array_parameter(self, plot_type):
        self.linearArrayConfig['array_size'] = self.ui.spinBox_ArraySize.value(
        )
        self.linearArrayConfig['spacing'] = self.ui.doubleSpinBox_Spacing.value(
        )
        self.linearArrayConfig['beam_loc'] = self.ui.doubleSpinBox_SteeringAngle.value(
        )
        self.linearArrayConfig['window_type_idx'] = self.ui.comboBox_Window.currentIndex(
        )
        self.linearArrayConfig['window_sll'] = self.ui.spinBox_SLL.value()
        self.linearArrayConfig['window_nbar'] = self.ui.spinBox_nbar.value()

        self.linear_array.update_config(
            self.linearArrayConfig, self.theta, plot_type)

    def update_pattern(self, angle, pattern, plot_type):
        if plot_type is 'Cartesian':
            self.cartesianPlot.setData(angle, pattern)
            self.angle = angle
            self.pattern = pattern

        elif plot_type is 'Polar':
            self.angle = angle
            self.pattern = pattern
            pattern = pattern + self.polarAmpOffset
            pattern[np.where(pattern < 0)] = 0
            x = pattern * np.sin(angle / 180 * np.pi)
            y = pattern * np.cos(angle / 180 * np.pi)

            self.circleLabel[0].setPos(self.polarAmpOffset, 0)
            for circle_idx in range(0, 6):
                self.circleList[circle_idx].setRect(
                    -self.polarAmpOffset + self.polarAmpOffset / 6 * circle_idx,
                    -self.polarAmpOffset + self.polarAmpOffset / 6 * circle_idx,
                    (self.polarAmpOffset - self.polarAmpOffset / 6 * circle_idx) * 2,
                    (self.polarAmpOffset - self.polarAmpOffset / 6 * circle_idx) * 2)
                self.circleLabel[circle_idx + 1].setText(
                    str(round(-self.polarAmpOffset / 6 * (circle_idx + 1), 1)))
                self.circleLabel[circle_idx + 1].setPos(
                    self.polarAmpOffset - self.polarAmpOffset / 6 * (circle_idx + 1), 0)
            self.polarPlot.setData(x, y)

            pattern = self.holdPattern + self.polarAmpOffset
            pattern[np.where(pattern < 0)] = 0
            x = pattern * np.sin(self.holdAngle / 180 * np.pi)
            y = pattern * np.cos(self.holdAngle / 180 * np.pi)
            self.polarPlotHold.setData(x, y)

        elif plot_type is 'Cartesian_Hold':
            self.holdAngle = angle
            self.holdPattern = pattern
            self.cartesianPlotHold.setData(angle, pattern)
            self.cartesianView.addItem(self.cartesianPlotHold)

        elif plot_type is 'Polar_Hold':
            self.holdAngle = angle
            self.holdPattern = pattern
            pattern = pattern + self.polarAmpOffset
            pattern[np.where(pattern < 0)] = 0
            x = pattern * np.sin(angle / 180 * np.pi)
            y = pattern * np.cos(angle / 180 * np.pi)
            self.polarPlotHold.setData(x, y)
            self.polarView.addItem(self.polarPlotHold)

    def hold_figure(self):
        self.theta = np.linspace(-90, 90, num=1801, endpoint=True)
        if self.plotType is 'Cartesian':
            self.update_linear_array_parameter('Cartesian_Hold')
        elif self.plotType is 'Polar':
            self.update_linear_array_parameter('Polar_Hold')
        self.ui.clearButton.setEnabled(True)
        self.holdEnabled = True

    def clear_figure(self):
        if self.plotType is 'Cartesian':
            self.cartesianView.removeItem(self.cartesianPlotHold)
        elif self.plotType is 'Polar':
            self.polarView.removeItem(self.polarPlotHold)

        self.ui.clearButton.setEnabled(False)
        self.holdEnabled = False

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
        self.update_linear_array_parameter(self.plotType)

    def cartesian_plot_toggled(self, checked):
        if checked and self.plotType is not 'Cartesian':
            if self.holdEnabled:
                self.polarView.removeItem(self.polarPlotHold)
                self.holdEnabled = False
                self.ui.clearButton.setEnabled(False)

            self.pgCanvas.removeItem(self.polarView)
            self.pgCanvas.addItem(self.cartesianView)
            self.ui.label_polarMinAmp.setVisible(False)
            self.ui.spinBox_polarMinAmp.setVisible(False)
            self.ui.horizontalSlider_polarMinAmp.setVisible(False)

            self.theta = np.linspace(-90, 90, num=1801, endpoint=True)
            self.plotType = 'Cartesian'
            self.update_linear_array_parameter(self.plotType)
            self.cartesianView.setXRange(-90, 90)
            self.cartesianView.setYRange(-80, 0)

    def polar_plot_toggled(self, checked):
        if checked and self.plotType is not 'Polar':
            if self.holdEnabled:
                self.cartesianView.removeItem(self.cartesianPlotHold)
                self.holdEnabled = False
                self.ui.clearButton.setEnabled(False)

            self.pgCanvas.removeItem(self.cartesianView)
            self.pgCanvas.addItem(self.polarView)
            self.ui.label_polarMinAmp.setVisible(True)
            self.ui.spinBox_polarMinAmp.setVisible(True)
            self.ui.horizontalSlider_polarMinAmp.setVisible(True)

            self.theta = np.linspace(-90, 90, num=1801, endpoint=True)
            self.plotType = 'Polar'
            self.update_linear_array_parameter(self.plotType)

    def show_cartesian_plot(self):
        self.pgCanvas.addItem(self.cartesianView)

    def show_polar_plot(self):
        self.pgCanvas.addItem(self.polarView)


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    window = MyApp()
    window.show()
    sys.exit(app.exec_())

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
import matplotlib.cm as cm

from calpattern import CalPattern

import pyqtgraph as pg
import pyqtgraph.opengl as gl

# pg.setConfigOption('background', 'w')
# pg.setConfigOption('foreground', 'k')
QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)


class MyApp(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        super(QtWidgets.QMainWindow, self).__init__()
        self.ui = uic.loadUi('ui_array_analysis.ui', self)
        self.pgCanvas = pg.GraphicsLayoutWidget()
        # self.layout_figure.addWidget(self.pgCanvas)

        self.cmap = cm.get_cmap('jet')

        self.minZ = -100
        self.maxZ = 0

        self.array_config = {'array_size': 64,
                             'spacing': 0.5,
                             'beam_loc': 0,
                             'window_type_idx': 0,
                             'window_sll': 60,
                             'window_nbar': 20
                             }

        self.theta = np.linspace(-1, 1, num=101, endpoint=True)
        self.phi = np.linspace(-1, 1, num=101, endpoint=True)
        self.angle = np.linspace(-90, 90, num=1801, endpoint=True)
        self.pattern = np.zeros(np.shape(self.theta))

        self.plotType = 'Cartesian'  # 'Cartesian' or 'Polar'
        self.polarAmpOffset = 60

        self.holdAngle = np.linspace(-90, 90, num=1801, endpoint=True)
        self.holdPattern = np.zeros(np.shape(self.theta))
        self.holdEnabled = False

        self.window_change_config = {
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

        self.surface_view = gl.GLViewWidget()
        self.surface_plot = gl.GLSurfacePlotItem(computeNormals=False)
        self.layout_figure.addWidget(self.surface_view)
        self.surface_view.addItem(self.surface_plot)
        self.surface_view.setCameraPosition(distance=5)
        # self.surface_plot.scale(1, 1, 1.0/50)

        self.xgrid = gl.GLGridItem()
        self.ygrid = gl.GLGridItem()
        self.zgrid = gl.GLGridItem()
        self.surface_view.addItem(self.xgrid)
        self.surface_view.addItem(self.ygrid)
        self.surface_view.addItem(self.zgrid)
        self.xgrid.setSpacing(x=0.1, y=0.1, z=10)

        # rotate x and y grids to face the correct direction
        self.xgrid.rotate(90, 0, 1, 0)
        self.ygrid.rotate(90, 1, 0, 0)

        self.penActive = pg.mkPen(color=(244, 143, 177), width=1)
        self.penHold = pg.mkPen(color=(158, 158, 158), width=1)

        self.init_plot_view()
        self.init_ui()

        self.calpattern = CalPattern()
        self.calpattern_thread = QThread()
        self.calpattern.patternReady.connect(self.update_pattern)
        self.calpattern_thread.started.connect(
            self.calpattern.cal_pattern)
        self.calpattern.moveToThread(self.calpattern_thread)
        self.calpattern_thread.start()

        self.update_array_parameters(self.plotType)
        self.ui.show()

    def init_ui(self):
        self.ui.sb_sidelobex.setVisible(False)
        self.ui.label_sidelobex.setVisible(False)
        self.ui.hs_sidelobex.setVisible(False)
        self.ui.sb_adjsidelobex.setVisible(False)
        self.ui.label_adjsidelobex.setVisible(False)
        self.ui.hs_adjsidelobex.setVisible(False)

        self.ui.sb_sidelobey.setVisible(False)
        self.ui.label_sidelobey.setVisible(False)
        self.ui.hs_sidelobey.setVisible(False)
        self.ui.sb_adjsidelobey.setVisible(False)
        self.ui.label_adjsidelobey.setVisible(False)
        self.ui.hs_adjsidelobey.setVisible(False)

        self.ui.clearButton.setEnabled(False)

        self.ui.cb_windowx.addItems(
            ['Square', 'Chebyshev', 'Taylor', 'Hamming', 'Hann'])
        self.ui.cb_windowy.addItems(
            ['Square', 'Chebyshev', 'Taylor', 'Hamming', 'Hann'])

        self.ui.sb_sizex.valueChanged.connect(
            self.array_changed)
        self.ui.sb_sizey.valueChanged.connect(
            self.array_changed)
        self.ui.dsb_spacingx.valueChanged.connect(
            self.array_changed)
        self.ui.dsb_spacingy.valueChanged.connect(
            self.array_changed)

        self.ui.dsb_angletheta.valueChanged.connect(
            self.theta_value_changed)
        self.ui.hs_angletheta.valueChanged.connect(
            self.theta_slider_moved)

        self.ui.dsb_anglephi.valueChanged.connect(
            self.phi_value_changed)
        self.ui.hs_anglephi.valueChanged.connect(
            self.phi_slider_moved)

        self.ui.cb_windowx.currentIndexChanged.connect(
            self.windowx_combobox_changed)
        
        self.ui.cb_windowy.currentIndexChanged.connect(
            self.windowy_combobox_changed)

        self.ui.sb_sidelobex.valueChanged.connect(self.sll_value_change)
        self.ui.hs_sidelobex.valueChanged.connect(
            self.sll_slider_moved)

        self.ui.sb_adjsidelobex.valueChanged.connect(self.nbar_value_changed)
        self.ui.hs_adjsidelobex.valueChanged.connect(
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

        self.ui.rb_cartesian.toggled.connect(
            self.cartesian_plot_toggled)
        self.ui.rb_polar.toggled.connect(self.polar_plot_toggled)

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

        # self.surface_view.addItem(self.surface_plot)

        ############################################
        self.cartesianView.sigXRangeChanged.connect(
            self.plotview_x_range_changed)
        # self.show_cartesian_plot()
        # self.show_3d_plot()

    def array_changed(self):
        self.update_array_parameters(self.plotType)

    def theta_value_changed(self, value):
        self.ui.hs_angletheta.setValue(value * 10)
        self.update_array_parameters(self.plotType)

    def phi_value_changed(self, value):
        self.ui.hs_anglephi.setValue(value * 10)
        self.update_array_parameters(self.plotType)

    def theta_slider_moved(self, value):
        self.ui.dsb_angletheta.setValue(value / 10)
        self.update_array_parameters(self.plotType)

    def phi_slider_moved(self, value):
        self.ui.dsb_anglephi.setValue(value / 10)
        self.update_array_parameters(self.plotType)

    def windowx_combobox_changed(self, value):
        self.window_change_config[value]()
        self.update_array_parameters(self.plotType)

    def windowy_combobox_changed(self, value):
        self.window_change_config[value]()
        self.update_array_parameters(self.plotType)

    def sll_value_change(self, value):
        self.ui.hs_sidelobex.setValue(value)
        self.update_array_parameters(self.plotType)

    def sll_slider_moved(self, value):
        self.ui.sb_sidelobex.setValue(value)
        self.update_array_parameters(self.plotType)

    def nbar_value_changed(self, value):
        self.ui.hs_adjsidelobex.setValue(value)
        self.update_array_parameters(self.plotType)

    def nbar_slider_moved(self, value):
        self.ui.sb_adjsidelobex.setValue(value)
        self.update_array_parameters(self.plotType)

    def polar_min_amp_value_changed(self, value):
        self.ui.horizontalSlider_polarMinAmp.setValue(value)
        self.polarAmpOffset = -value
        self.update_array_parameters(self.plotType)

    def polar_min_amp_slider_moved(self, value):
        self.ui.spinBox_polarMinAmp.setValue(value)
        self.polarAmpOffset = -value
        self.update_array_parameters(self.plotType)

    def update_array_parameters(self, plot_type):
        self.array_config['sizex'] = self.ui.sb_sizex.value()
        self.array_config['sizey'] = self.ui.sb_sizey.value()
        self.array_config['spacingx'] = self.ui.dsb_spacingx.value()
        self.array_config['spacingy'] = self.ui.dsb_spacingy.value()
        self.array_config['beam_theta'] = self.ui.dsb_angletheta.value()
        self.array_config['beam_phi'] = self.ui.dsb_anglephi.value()
        self.array_config['windowx'] = self.ui.cb_windowx.currentIndex()
        self.array_config['windowy'] = self.ui.cb_windowy.currentIndex()
        self.array_config['sllx'] = self.ui.sb_sidelobex.value()
        self.array_config['slly'] = self.ui.sb_sidelobey.value()
        self.array_config['nbarx'] = self.ui.sb_adjsidelobex.value()
        self.array_config['nbary'] = self.ui.sb_adjsidelobey.value()

        self.calpattern.update_config(
            self.array_config, self.theta, self.phi, plot_type)

    def update_pattern(self, angle, angle_phi, pattern, plot_type):
        print(np.shape(pattern))
        rgba_img = self.cmap((pattern-self.minZ)/(self.maxZ - self.minZ))
        self.surface_plot.setData(z=pattern+100, colors=rgba_img)
        if plot_type is 'Cartesian':
            # self.cartesianPlot.setData(angle, pattern)
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
            self.update_array_parameters('Cartesian_Hold')
        elif self.plotType is 'Polar':
            self.update_array_parameters('Polar_Hold')
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
        self.ui.sb_sidelobex.setVisible(False)
        self.ui.label_sidelobex.setVisible(False)
        self.ui.hs_sidelobex.setVisible(False)
        self.ui.sb_adjsidelobex.setVisible(False)
        self.ui.label_adjsidelobex.setVisible(False)
        self.ui.hs_adjsidelobex.setVisible(False)

    def chebyshev(self):
        self.ui.sb_sidelobex.setVisible(True)
        self.ui.label_sidelobex.setVisible(True)
        self.ui.hs_sidelobex.setVisible(True)
        self.ui.sb_adjsidelobex.setVisible(False)
        self.ui.label_adjsidelobex.setVisible(False)
        self.ui.hs_adjsidelobex.setVisible(False)

    def taylor(self):
        self.ui.sb_sidelobex.setVisible(True)
        self.ui.label_sidelobex.setVisible(True)
        self.ui.hs_sidelobex.setVisible(True)
        self.ui.sb_adjsidelobex.setVisible(True)
        self.ui.label_adjsidelobex.setVisible(True)
        self.ui.hs_adjsidelobex.setVisible(True)

    def plotview_x_range_changed(self, item):
        self.theta = np.linspace(
            item.viewRange()[0][0],
            item.viewRange()[0][1],
            num=1801,
            endpoint=True)
        self.update_array_parameters(self.plotType)

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
            self.update_array_parameters(self.plotType)
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
            self.update_array_parameters(self.plotType)

    def show_cartesian_plot(self):
        self.pgCanvas.addItem(self.cartesianView)

    def show_polar_plot(self):
        self.pgCanvas.addItem(self.polarView)

    # def show_3d_plot(self):
        # self.pgCanvas.addItem(self.surface_view)

    def colormap_lut(self, color='viridis', ncolors=None):
        # build lookup table
        if color == 'r':
            pos = np.array([0.0, 1.0])
            color = np.array([[0, 0, 0, 255], [255, 0, 0, 255]],
                             dtype=np.ubyte)
            ncolors = 512
        elif color == 'g':
            pos = np.array([0.0, 1.0])
            color = np.array([[0, 0, 0, 255], [0, 255, 0, 255]],
                             dtype=np.ubyte)
            ncolors = 512
        elif color == 'b':
            pos = np.array([0.0, 1.0])
            color = np.array([[0, 0, 0, 255], [0, 0, 255, 255]],
                             dtype=np.ubyte)
            ncolors = 512
        else:
            cmap = cm.get_cmap(color)
            if ncolors is None:
                ncolors = cmap.N
            pos = np.linspace(0.0, 1.0, ncolors)
            color = cmap(pos, bytes=True)

        cmap = pg.ColorMap(pos, color)
        return cmap.getLookupTable(0.0, 1.0, ncolors)


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    window = MyApp()
    window.show()
    sys.exit(app.exec_())

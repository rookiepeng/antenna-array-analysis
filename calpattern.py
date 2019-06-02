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

from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot
import numpy as np
from time import sleep
import antarray


class CalPattern(QObject):
    patternReady = pyqtSignal(np.ndarray, np.ndarray, np.ndarray, object)
    new_data = False

    def __init__(self):
        super(CalPattern, self).__init__()
        self.win_type = {
            0: 'Square',
            1: 'Chebyshev',
            2: 'Taylor',
            3: 'Hamming',
            4: 'Hanning'
        }
        self.sizex = 64
        self.sizey = 1
        self.spacingx = 0.5
        self.spacingy = 0.5
        self.rect_array = antarray.RectArray(
            self.sizex, self.sizey, self.spacingx, self.spacingy)
        self.beam_theta = 0
        self.beam_phi = 0
        self.u = np.linspace(-1, 1, num=101, endpoint=True)
        self.v = np.linspace(-1, 1, num=101, endpoint=True)
        self.windowx = 0
        self.windowy = 0
        self.sllx = 60
        self.slly = 60
        self.nbarx = 20
        self.nbary = 20
        self.new_data = False
        self.plot = 'Cartesian'

    def update_config(self, linear_array_config, u, v, plot):
        self.sizex = linear_array_config.get('sizex', 64)
        self.sizey = linear_array_config.get('sizey', 32)
        self.spacingx = linear_array_config['spacingx']
        self.spacingy = linear_array_config.get('spacingy', 0.5)
        self.beam_theta = linear_array_config['beam_theta']
        self.beam_phi = linear_array_config.get('beam_phi', 0)
        # self.u = u
        # self.v = v
        self.windowx = linear_array_config['windowx']
        self.windowy = linear_array_config.get('windowy', 0)
        self.sllx = linear_array_config['sllx']
        self.slly = linear_array_config.get('slly', 60)
        self.nbarx = linear_array_config['nbarx']
        self.nbary = linear_array_config.get('nbary', 20)
        self.new_data = True
        self.plot = plot
        self.rect_array.update_parameters(
            sizex=self.sizex, sizey=self.sizey, spacingx=self.spacingx,
            spacingy=self.spacingy)

    @pyqtSlot()
    def cal_pattern(self):
        while 1:
            if self.new_data:
                self.new_data = False

                AF_data = self.rect_array.get_pattern(
                    self.u, self.v, Nx=512,
                    Ny=512, beam_theta=self.beam_theta,
                    beam_phi=self.beam_phi, windowx=self.win_type[
                        self.windowx], sllx=self.sllx,
                    nbarx=self.nbarx, windowy=self.win_type[
                        self.windowy], slly=self.slly,
                    nbary=self.nbary, polar=False
                )

                AF = 20 * np.log10(np.abs(AF_data['array_factor']) + 0.00001)

                self.patternReady.emit(self.u, self.v, AF, self.plot)

            sleep(0.01)

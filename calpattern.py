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
    patternReady = pyqtSignal(np.ndarray, np.ndarray, np.ndarray)
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
        self.beam_az = 0
        self.beam_el = 0
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

    def update_config(self, linear_array_config):
        self.sizex = linear_array_config.get('sizex', 64)
        self.sizey = linear_array_config.get('sizey', 32)
        self.spacingx = linear_array_config['spacingx']
        self.spacingy = linear_array_config.get('spacingy', 0.5)
        self.beam_az = linear_array_config['beam_az']
        self.beam_el = linear_array_config.get('beam_el', 0)
        self.windowx = linear_array_config['windowx']
        self.windowy = linear_array_config.get('windowy', 0)
        self.sllx = linear_array_config['sllx']
        self.slly = linear_array_config.get('slly', 60)
        self.nbarx = linear_array_config['nbarx']
        self.nbary = linear_array_config.get('nbary', 20)
        self.nfft_az = linear_array_config.get('nfft_az')
        self.nfft_el = linear_array_config.get('nfft_el')
        self.plot_az = linear_array_config.get('plot_az')
        self.plot_el = linear_array_config.get('plot_el')
        self.new_data = True
        self.rect_array.update_parameters(
            sizex=self.sizex, sizey=self.sizey, spacingx=self.spacingx,
            spacingy=self.spacingy)

    @pyqtSlot()
    def cal_pattern(self):
        while 1:
            if self.new_data:
                self.new_data = False

                AF_data = self.rect_array.get_pattern(
                    nfft_az=self.nfft_az,
                    nfft_el=self.nfft_el,
                    beam_az=self.beam_az,
                    beam_el=self.beam_el,
                    windowx=self.win_type[self.windowx],
                    sllx=self.sllx,
                    nbarx=self.nbarx,
                    windowy=self.win_type[self.windowy],
                    slly=self.slly,
                    nbary=self.nbary,
                    plot_az=self.plot_az,
                    plot_el=self.plot_el
                )

                AF = 20 * np.log10(np.abs(AF_data['array_factor']) + 0.00001)

                self.patternReady.emit(
                    AF_data['azimuth'], AF_data['elevation'], AF)

            sleep(0.01)

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


class LinearArray(QObject):
    patternReady = pyqtSignal(np.ndarray, np.ndarray, object)
    new_data = False

    def __init__(self):
        super(LinearArray, self).__init__()
        self.win_type = {
            0: 'Square',
            1: 'Chebyshev',
            2: 'Taylor',
            3: 'Hamming',
            4: 'Hanning'
        }
        self.lin_array = antarray.LinearArray(64, 0.5)
        self.array_size = 64
        self.spacing = 0.5
        self.beam_loc = 0
        self.theta = np.linspace(-90, 90, num=1801, endpoint=True)
        self.window_type = 0
        self.window_sll = 60
        self.window_nbar = 20
        self.new_data = False
        self.plot = 'Cartesian'

    def update_config(self, linear_array_config, theta, plot):
        self.array_size = linear_array_config['array_size']
        self.spacing = linear_array_config['spacing']
        self.beam_loc = linear_array_config['beam_loc']
        self.theta = theta
        self.window_type = linear_array_config['window_type_idx']
        self.window_sll = linear_array_config['window_sll']
        self.window_nbar = linear_array_config['window_nbar']
        self.new_data = True
        self.plot = plot
        self.lin_array.update_parameters(
            size=self.array_size, spacing=self.spacing)

    @pyqtSlot()
    def calculate_pattern(self):
        while 1:
            if self.new_data:
                self.new_data = False

                AF_data = self.lin_array.get_pattern(
                    self.theta, beam_loc=self.beam_loc, window=self.win_type[self.window_type], sll=self.window_sll,
                    nbar=self.window_nbar)

                AF = 20 * np.log10(np.abs(AF_data['array_factor']) + 0.00001)

                self.patternReady.emit(self.theta, AF, self.plot)

            sleep(0.01)

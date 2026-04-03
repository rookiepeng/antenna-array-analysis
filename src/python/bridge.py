"""
Python bridge for antenna array pattern calculation.
Reads JSON config from stdin, writes JSON result to stdout.
"""

import sys
import json
import numpy as np

# Patch removed scipy.signal functions (deprecated/removed in scipy >= 1.11)
from scipy import signal
from scipy.signal import windows as _win
for _fn in ('chebwin', 'hamming', 'hann'):
    if not hasattr(signal, _fn):
        setattr(signal, _fn, getattr(_win, _fn))

# Add the antarray package path
sys.path.insert(0, sys.argv[1] if len(sys.argv) > 1 else '.')

from antarray.antarray import RectArray

WIN_TYPE = {
    0: 'Square',
    1: 'Chebyshev',
    2: 'Taylor',
    3: 'Hamming',
    4: 'Hanning'
}


def compute_pattern(config: dict) -> dict:
    sizex = config.get('sizex', 64)
    sizey = config.get('sizey', 32)
    spacingx = config.get('spacingx', 0.5)
    spacingy = config.get('spacingy', 0.5)

    rect_array = RectArray(sizex, sizey, spacingx, spacingy)

    windowx_idx = config.get('windowx', 0)
    windowy_idx = config.get('windowy', 0)
    windowx = WIN_TYPE.get(windowx_idx, 'Square')
    windowy = WIN_TYPE.get(windowy_idx, 'Square')

    AF_data = rect_array.get_pattern(
        nfft_az=config.get('nfftAz', 512),
        nfft_el=config.get('nfftEl', 512),
        beam_az=config.get('beamAz', 0),
        beam_el=config.get('beamEl', 0),
        windowx=windowx,
        sllx=-abs(config.get('sllx', 60)),
        nbarx=config.get('nbarx', 4),
        windowy=windowy,
        slly=-abs(config.get('slly', 60)),
        nbary=config.get('nbary', 4),
        plot_az=config.get('plotAz', 0),
        plot_el=config.get('plotEl', 0),
    )

    af = AF_data['array_factor']
    af_db = 20 * np.log10(np.abs(af) + 0.00001)

    azimuth = AF_data['azimuth']
    elevation = AF_data['elevation']
    x = rect_array.x
    y = rect_array.y
    weight = AF_data['weight'].ravel()

    result = {
        'azimuth': azimuth.tolist() if isinstance(azimuth, np.ndarray) else [float(azimuth)],
        'elevation': elevation.tolist() if isinstance(elevation, np.ndarray) else [float(elevation)],
        'x': x.tolist(),
        'y': y.tolist(),
        'weightRe': np.real(weight).tolist(),
        'weightIm': np.imag(weight).tolist(),
    }

    if af_db.ndim == 2:
        result['arrayFactor2D'] = af_db.tolist()
        result['arrayFactor'] = af_db.ravel().tolist()
    else:
        result['arrayFactor'] = af_db.tolist()

    return result


def main():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            config = json.loads(line)
            result = compute_pattern(config)
            out = json.dumps(result)
            sys.stdout.write(out + '\n')
            sys.stdout.flush()
        except Exception as e:
            err = json.dumps({'error': str(e)})
            sys.stdout.write(err + '\n')
            sys.stdout.flush()


if __name__ == '__main__':
    main()

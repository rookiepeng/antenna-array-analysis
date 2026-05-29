"""
Python bridge for antenna array pattern calculation.
Reads JSON config from stdin, writes JSON result to stdout.
"""

import sys
import json
import numpy as np
from scipy.signal import windows as sig_windows
from scipy.interpolate import interp1d

# Add the arraybeam package path.
# When frozen by PyInstaller (sys.frozen is set), all packages are bundled
# inside the executable and importable directly — no path manipulation needed.
# In development, sys.argv[1] points to the project src/ directory.
if not getattr(sys, 'frozen', False):
    sys.path.insert(0, sys.argv[1] if len(sys.argv) > 1 else '.')

from arraybeam import UniformRectangularArray, AntennaArray


def _make_window(win_idx: int, size: int, sll: float, nbar: int):
    """Return a taper window array, or None for uniform (Square)."""
    if win_idx == 0 or size < 2:  # Square
        return None
    if win_idx == 1:  # Chebyshev
        return sig_windows.chebwin(size, abs(sll))
    if win_idx == 2:  # Taylor
        return sig_windows.taylor(size, nbar=nbar, sll=abs(sll), norm=True)
    if win_idx == 3:  # Hamming
        return sig_windows.hamming(size)
    if win_idx == 4:  # Hann
        return sig_windows.hann(size)
    return None


def compute_pattern(config: dict) -> dict:
    mode = config.get('mode', 'uniform')

    if mode == 'custom':
        result = _compute_custom(config)
    else:
        result = _compute_uniform(config)

    # Apply element radiation pattern if provided
    result = _apply_element_pattern(config, result)

    return result


def _interpolate_pattern(angles, gains, target_angles):
    """Interpolate a 1-D element pattern onto target angles (dB)."""
    order = np.argsort(angles)
    angles = np.array(angles)[order]
    gains = np.array(gains)[order]
    f = interp1d(angles, gains, kind='linear', bounds_error=False,
                 fill_value=(gains[0], gains[-1]))
    return f(target_angles)


def _apply_element_pattern(config: dict, result: dict) -> dict:
    """Multiply the array factor by interpolated element patterns."""
    az_angles = config.get('elementPatternAzAngles')
    az_gains = config.get('elementPatternAzGains')
    el_angles = config.get('elementPatternElAngles')
    el_gains = config.get('elementPatternElGains')

    if az_angles is None and el_angles is None:
        return result

    af2d = np.array(result['arrayFactor2D'])  # shape: (nAz, nEl), dB
    azimuth = np.array(result['azimuth'])
    elevation = np.array(result['elevation'])

    if az_angles is not None and len(az_angles) >= 2:
        ep_az = _interpolate_pattern(az_angles, az_gains, azimuth)  # (nAz,)
        af2d = af2d + ep_az[:, np.newaxis]  # add dB

    if el_angles is not None and len(el_angles) >= 2:
        ep_el = _interpolate_pattern(el_angles, el_gains, elevation)  # (nEl,)
        af2d = af2d + ep_el[np.newaxis, :]  # add dB

    result['arrayFactor2D'] = af2d.tolist()
    result['arrayFactor'] = af2d.ravel().tolist()

    return result


def _compute_custom(config: dict) -> dict:
    custom_y = np.array(config['customY'], dtype=float)
    custom_z = np.array(config['customZ'], dtype=float)
    custom_amp = np.array(config['customAmp'], dtype=float)
    custom_phase = np.array(config['customPhase'], dtype=float)

    weight = custom_amp * np.exp(1j * np.radians(custom_phase))
    weight = weight / (np.sum(np.abs(weight)) + 1e-30)

    nfft_az = config.get('nfftAz', 512)
    nfft_el = config.get('nfftEl', 512)

    azimuth = np.linspace(-90, 90, nfft_az)
    elevation = np.linspace(-90, 90, nfft_el)

    arr = AntennaArray(x=custom_y, y=custom_z)
    AF_data = arr.get_pattern(azimuth, elevation, weight=weight)

    af = AF_data['array_factor']
    af_abs = np.abs(af)
    af_max = np.max(af_abs)
    if af_max > 0:
        af_abs = af_abs / af_max
    af_db = 20 * np.log10(af_abs + 1e-10)

    result = {
        'azimuth': azimuth.tolist(),
        'elevation': elevation.tolist(),
        'x': custom_y.tolist(),
        'y': custom_z.tolist(),
        'weightRe': np.real(weight).tolist(),
        'weightIm': np.imag(weight).tolist(),
        'arrayFactor2D': af_db.tolist(),
    }

    return result


def _compute_uniform(config: dict) -> dict:
    sizex = config.get('sizex', 64)
    sizey = config.get('sizey', 32)
    spacingx = config.get('spacingx', 0.5)
    spacingy = config.get('spacingy', 0.5)

    rect_array = UniformRectangularArray(sizex, sizey, spacingx, spacingy)

    weight_x = _make_window(
        config.get('windowx', 0), sizex,
        config.get('sllx', 60), config.get('nbarx', 4))
    weight_y = _make_window(
        config.get('windowy', 0), sizey,
        config.get('slly', 60), config.get('nbary', 4))

    AF_data = rect_array.get_pattern_2d(
        nfft_az=config.get('nfftAz', 512),
        nfft_el=config.get('nfftEl', 512),
        beam_az=config.get('beamAz', 0),
        beam_el=config.get('beamEl', 0),
        weight_x=weight_x,
        weight_y=weight_y,
    )

    af = AF_data['array_factor']
    af_db = 20 * np.log10(np.abs(af) + 0.00001)

    azimuth = AF_data['azimuth']
    elevation = AF_data['elevation']
    weight = AF_data['weight'].ravel()

    result = {
        'azimuth': azimuth.tolist(),
        'elevation': elevation.tolist(),
        'x': AF_data['x'].tolist(),
        'y': AF_data['y'].tolist(),
        'weightRe': np.real(weight).tolist(),
        'weightIm': np.imag(weight).tolist(),
        'arrayFactor2D': af_db.tolist(),
    }

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

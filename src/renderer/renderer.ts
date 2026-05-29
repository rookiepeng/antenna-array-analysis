/**
 * Renderer process - UI logic and Plotly visualization
 */

const { ipcRenderer, shell } = require('electron');

// Plotly types + runtime require
import type * as PlotlyType from 'plotly.js';
const Plotly: typeof PlotlyType = require('plotly.js-dist-min');

// ---- Types ----
interface PatternResult {
  arrayFactor2D: number[][];
  x: number[];
  y: number[];
  weightRe: number[];
  weightIm: number[];
  azimuth: number[];
  elevation: number[];
  error?: string;
}

type WindowType = 'Square' | 'Chebyshev' | 'Taylor' | 'Hamming' | 'Hann';

const WINDOW_INDEX: Record<WindowType, number> = {
  'Square': 0,
  'Chebyshev': 1,
  'Taylor': 2,
  'Hamming': 3,
  'Hann': 4,
};

// ---- State ----
let fixAzimuth = false;
let currentResult: PatternResult | null = null;
let plotType: string = '3d';
let arrayColorMode: string = 'amplitude';
let debounceTimer: ReturnType<typeof setTimeout> | null = null;
let computeId = 0;   // incremented per request; stale results are discarded
let firstRenderDone = false;
let arrayMode: 'uniform' | 'custom' = 'uniform';

// ---- DOM Elements ----
const $ = (id: string) => document.getElementById(id)!;

const sizexInput = $('sizex') as HTMLInputElement;
const sizeyInput = $('sizey') as HTMLInputElement;
const spacingxInput = $('spacingx') as HTMLInputElement;
const spacingyInput = $('spacingy') as HTMLInputElement;
const windowxSelect = $('windowx') as HTMLSelectElement;
const windowySelect = $('windowy') as HTMLSelectElement;
const sllxInput = $('sllx') as HTMLInputElement;
const sllxSlider = $('sllx-slider') as HTMLInputElement;
const sllyInput = $('slly') as HTMLInputElement;
const sllySlider = $('slly-slider') as HTMLInputElement;
const nbarxInput = $('nbarx') as HTMLInputElement;
const nbarxSlider = $('nbarx-slider') as HTMLInputElement;
const nbaryInput = $('nbary') as HTMLInputElement;
const nbarySlider = $('nbary-slider') as HTMLInputElement;
const beamAzInput = $('beam-az') as HTMLInputElement;
const beamAzSlider = $('beam-az-slider') as HTMLInputElement;
const beamElInput = $('beam-el') as HTMLInputElement;
const beamElSlider = $('beam-el-slider') as HTMLInputElement;
const plotTypeSelect = $('plot-type') as HTMLSelectElement;
const fixElevationRadio = $('fix-elevation') as HTMLInputElement;
const fixAzimuthRadio = $('fix-azimuth') as HTMLInputElement;
const plotElInput = $('plot-el') as HTMLInputElement;
const plotElSlider = $('plot-el-slider') as HTMLInputElement;
const plotAzInput = $('plot-az') as HTMLInputElement;
const plotAzSlider = $('plot-az-slider') as HTMLInputElement;
const polarMinInput = $('polar-min') as HTMLInputElement;
const polarMinSlider = $('polar-min-slider') as HTMLInputElement;
const arrayColorSelect = $('array-color') as HTMLSelectElement;
const plotContainer = $('plot-container');
const insetContainer = $('plot-3d-inset');
const layoutContainer = $('layout-container');
const tabUniform = $('tab-uniform') as HTMLButtonElement;
const tabCustom = $('tab-custom') as HTMLButtonElement;
const uniformConfigDiv = $('uniform-config');
const customConfigDiv = $('custom-config');
const customUnsyncedBanner = $('custom-unsynced-banner');
const elementTbody = $('element-tbody') as HTMLTableSectionElement;
const customErrorP = $('custom-error');
const elementPatternEnabled = $('element-pattern-enabled') as HTMLButtonElement;
const elementPatternBody = $('element-pattern-body');
const azPatternTbody = $('az-pattern-tbody') as HTMLTableSectionElement;
const elPatternTbody = $('el-pattern-tbody') as HTMLTableSectionElement;

// ---- Custom array helpers ----
interface CustomElement {
  y: number;
  z: number;
  amp: number;
  phase: number;
}

const DEFAULT_ELEMENTS: CustomElement[] = [
  { y: 0, z: 0, amp: 1, phase: 0 },
  { y: 0.5, z: 0, amp: 1, phase: 0 },
  { y: 1.0, z: 0, amp: 1, phase: 0 },
  { y: 1.5, z: 0, amp: 1, phase: 0 },
  { y: 2.0, z: 0, amp: 1, phase: 0 },
  { y: 2.5, z: 0, amp: 1, phase: 0 },
  { y: 3.0, z: 0, amp: 1, phase: 0 },
  { y: 3.5, z: 0, amp: 1, phase: 0 },
];

function addTableRow(elem?: CustomElement) {
  const e = elem || { y: 0, z: 0, amp: 1, phase: 0 };
  const row = elementTbody.insertRow();
  const idx = elementTbody.rows.length;
  row.innerHTML =
    `<td class="row-num">${idx}</td>` +
    `<td><input type="number" class="el-y" value="${e.y}" step="0.1"></td>` +
    `<td><input type="number" class="el-z" value="${e.z}" step="0.1"></td>` +
    `<td><input type="number" class="el-amp" value="${e.amp}" step="0.1" min="0"></td>` +
    `<td><input type="number" class="el-phase" value="${e.phase}" step="1"></td>` +
    `<td><button class="btn-remove-row" title="Remove">&times;</button></td>`;
  
  // Custom array inputs dirty state
  row.querySelectorAll('input').forEach(input => {
    input.addEventListener('input', () => {
      showCustomUnsyncedBanner();
      saveState();
    });
  });

  row.querySelector('.btn-remove-row')!.addEventListener('click', () => {
    row.remove();
    renumberRows();
    showCustomUnsyncedBanner();
    saveState();
  });
}

function showCustomUnsyncedBanner() {
  if (arrayMode === 'custom') {
    customUnsyncedBanner.style.display = 'block';
  }
}

function hideCustomUnsyncedBanner() {
  customUnsyncedBanner.style.display = 'none';
}

function renumberRows() {
  const rows = elementTbody.rows;
  for (let i = 0; i < rows.length; i++) {
    rows[i].cells[0].textContent = String(i + 1);
  }
}

function populateTable(elements: CustomElement[]) {
  elementTbody.innerHTML = '';
  elements.forEach(e => addTableRow(e));
}

function parseCustomElements(): CustomElement[] | null {
  const rows = elementTbody.rows;
  if (rows.length === 0) {
    customErrorP.textContent = 'Table is empty';
    return null;
  }
  const elements: CustomElement[] = [];
  for (let i = 0; i < rows.length; i++) {
    const inputs = rows[i].querySelectorAll('input[type="number"]');
    const y = parseFloat((inputs[0] as HTMLInputElement).value);
    const z = parseFloat((inputs[1] as HTMLInputElement).value);
    const amp = parseFloat((inputs[2] as HTMLInputElement).value);
    const phase = parseFloat((inputs[3] as HTMLInputElement).value);
    if ([y, z, amp, phase].some(isNaN)) {
      customErrorP.textContent = `Row ${i + 1}: invalid number`;
      return null;
    }
    elements.push({ y, z, amp, phase });
  }
  customErrorP.textContent = '';
  return elements;
}

// ---- Element pattern helpers ----
interface PatternPoint {
  angle: number;
  gain: number;
}

const DEFAULT_AZ_PATTERN: PatternPoint[] = [
  { angle: -90, gain: -20 },
  { angle: 0, gain: 0 },
  { angle: 90, gain: -20 },
];

const DEFAULT_EL_PATTERN: PatternPoint[] = [
  { angle: -90, gain: -20 },
  { angle: 0, gain: 0 },
  { angle: 90, gain: -20 },
];

function addPatternRow(tbody: HTMLTableSectionElement, point?: PatternPoint) {
  const p = point || { angle: 0, gain: 0 };
  const row = tbody.insertRow();
  row.innerHTML =
    `<td><input type="number" class="pat-angle" value="${p.angle}" step="1"></td>` +
    `<td><input type="number" class="pat-gain" value="${p.gain}" step="0.1"></td>` +
    `<td><button class="btn-remove-row" title="Remove">&times;</button></td>`;
  row.querySelectorAll('input').forEach(input => {
    input.addEventListener('input', () => scheduleUpdate());
  });
  row.querySelector('.btn-remove-row')!.addEventListener('click', () => {
    row.remove();
    scheduleUpdate();
  });
}

function populatePatternTable(tbody: HTMLTableSectionElement, points: PatternPoint[]) {
  tbody.innerHTML = '';
  points.forEach(p => addPatternRow(tbody, p));
}

function parsePatternTable(tbody: HTMLTableSectionElement): PatternPoint[] | null {
  const rows = tbody.rows;
  if (rows.length === 0) return null;
  const points: PatternPoint[] = [];
  for (let i = 0; i < rows.length; i++) {
    const inputs = rows[i].querySelectorAll('input[type="number"]');
    const angle = parseFloat((inputs[0] as HTMLInputElement).value);
    const gain = parseFloat((inputs[1] as HTMLInputElement).value);
    if (isNaN(angle) || isNaN(gain)) return null;
    points.push({ angle, gain });
  }
  points.sort((a, b) => a.angle - b.angle);
  return points;
}

function importPatternCSV(tbody: HTMLTableSectionElement) {
  const input = document.createElement('input');
  input.type = 'file';
  input.accept = '.csv,.txt';
  input.onchange = () => {
    const file = input.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => {
      const text = (reader.result as string).trim();
      const points: PatternPoint[] = [];
      for (const line of text.split('\n')) {
        const trimmed = line.trim();
        if (!trimmed || trimmed.startsWith('#')) continue;
        const parts = trimmed.split(',').map(s => s.trim());
        if (parts.length < 2) continue;
        const angle = parseFloat(parts[0]);
        const gain = parseFloat(parts[1]);
        if (isNaN(angle) || isNaN(gain)) continue;
        points.push({ angle, gain });
      }
      if (points.length > 0) {
        populatePatternTable(tbody, points);
        scheduleUpdate();
      }
    };
    reader.readAsText(file);
  };
  input.click();
}

// ---- Sync helpers ----
function syncSliderToInput(slider: HTMLInputElement, input: HTMLInputElement, scale: number = 1) {
  input.value = String(parseInt(slider.value) / scale);
  scheduleUpdate();
}

function syncInputToSlider(input: HTMLInputElement, slider: HTMLInputElement, scale: number = 1) {
  slider.value = String(Math.round(parseFloat(input.value) * scale));
  scheduleUpdate();
}

function syncPair(input: HTMLInputElement, slider: HTMLInputElement, scale: number = 1) {
  input.addEventListener('input', () => syncInputToSlider(input, slider, scale));
  slider.addEventListener('input', () => syncSliderToInput(slider, input, scale));
}

function syncPairDirect(input: HTMLInputElement, slider: HTMLInputElement) {
  input.addEventListener('input', () => { slider.value = input.value; scheduleUpdate(); });
  slider.addEventListener('input', () => { input.value = slider.value; scheduleUpdate(); });
}

// ---- Window visibility ----
function updateWindowControls(axis: 'x' | 'y', value: string) {
  const sllRow = $(`sll${axis}-row`);
  const nbarRow = $(`nbar${axis}-row`);

  if (value === 'Chebyshev') {
    sllRow.style.display = '';
    nbarRow.style.display = 'none';
  } else if (value === 'Taylor') {
    sllRow.style.display = '';
    nbarRow.style.display = '';
  } else {
    sllRow.style.display = 'none';
    nbarRow.style.display = 'none';
  }
}

// ---- Plot type changes ----
function updatePlotTypeUI() {
  const cutSection = $('cut-plane-section');
  const polarSection = $('polar-min-section');

  if (plotType === '3d' || plotType === '3d-polar') {
    cutSection.style.display = 'none';
    polarSection.style.display = 'none';
    insetContainer.style.display = 'none';
    $('inset-section').style.display = 'none';
  } else if (plotType === 'cartesian') {
    cutSection.style.display = '';
    polarSection.style.display = 'none';
    insetContainer.style.display = 'block';
    $('inset-section').style.display = 'none';
  } else if (plotType === 'polar') {
    cutSection.style.display = '';
    polarSection.style.display = '';
    insetContainer.style.display = 'block';
    $('inset-section').style.display = 'none';
  }

  updateFixPlaneUI();
}

function updateFixPlaneUI() {
  const fixElRow = $('fix-el-row');
  const fixAzRow = $('fix-az-row');

  if (fixAzimuth) {
    fixAzRow.style.display = '';
    fixElRow.style.display = 'none';
    fixAzimuthRadio.checked = true;
    fixElevationRadio.checked = false;
  } else {
    fixAzRow.style.display = 'none';
    fixElRow.style.display = '';
    fixElevationRadio.checked = true;
    fixAzimuthRadio.checked = false;
  }
}

// ---- Build config ----
function nextPow2(n: number): number {
  return Math.pow(2, Math.ceil(Math.log2(Math.max(n, 1))));
}

function getConfig() {
  const base: Record<string, any> = {
    plotAz: parseFloat(plotAzInput.value) || 0,
    plotEl: parseFloat(plotElInput.value) || 0,
  };

  if (arrayMode === 'custom') {
    const elems = parseCustomElements();
    if (!elems) return null;
    const nElem = elems.length;
    const MAX_NFFT = 2048;
    base.nfftAz = Math.min(nextPow2(8 * nElem), MAX_NFFT);
    base.nfftEl = Math.min(nextPow2(8 * nElem), MAX_NFFT);
    base.mode = 'custom';
    base.customY = elems.map(e => e.y);
    base.customZ = elems.map(e => e.z);
    base.customAmp = elems.map(e => e.amp);
    base.customPhase = elems.map(e => e.phase);
  } else {
    const sizex = parseInt(sizexInput.value) || 64;
    const sizey = parseInt(sizeyInput.value) || 32;
    const MAX_NFFT = 2048;
    base.nfftAz = Math.min(nextPow2(8 * sizex), MAX_NFFT);
    base.nfftEl = Math.min(nextPow2(8 * sizey), MAX_NFFT);
    base.mode = 'uniform';
    base.sizex = sizex;
    base.sizey = sizey;
    base.spacingx = parseFloat(spacingxInput.value) || 0.5;
    base.spacingy = parseFloat(spacingyInput.value) || 0.5;
    base.beamAz = parseFloat(beamAzInput.value) || 0;
    base.beamEl = parseFloat(beamElInput.value) || 0;
    base.windowx = WINDOW_INDEX[windowxSelect.value as WindowType] ?? 0;
    base.windowy = WINDOW_INDEX[windowySelect.value as WindowType] ?? 0;
    base.sllx = parseInt(sllxInput.value) || 60;
    base.slly = parseInt(sllyInput.value) || 60;
    base.nbarx = parseInt(nbarxInput.value) || 4;
    base.nbary = parseInt(nbaryInput.value) || 4;
  }

  // Element radiation pattern
  if (elementPatternEnabled.classList.contains('active')) {
    const azPat = parsePatternTable(azPatternTbody);
    if (azPat && azPat.length >= 2) {
      base.elementPatternAzAngles = azPat.map(p => p.angle);
      base.elementPatternAzGains = azPat.map(p => p.gain);
    }
    const elPat = parsePatternTable(elPatternTbody);
    if (elPat && elPat.length >= 2) {
      base.elementPatternElAngles = elPat.map(p => p.angle);
      base.elementPatternElGains = elPat.map(p => p.gain);
    }
  }

  return base;
}

// ---- Compute & Plot ----
function applyCustomAndCompute() {
  hideCustomUnsyncedBanner();
  scheduleUpdate();
}

// ---- Persistence ----
const STATE_KEY = 'antennaArrayState';
const STATE_VERSION = 2; // increment when saved schema changes

function readCustomElementsForSave(): CustomElement[] {
  const rows = elementTbody.rows;
  const elements: CustomElement[] = [];
  for (let i = 0; i < rows.length; i++) {
    const inputs = rows[i].querySelectorAll('input[type="number"]');
    const y   = parseFloat((inputs[0] as HTMLInputElement).value);
    const z   = parseFloat((inputs[1] as HTMLInputElement).value);
    const amp = parseFloat((inputs[2] as HTMLInputElement).value);
    const ph  = parseFloat((inputs[3] as HTMLInputElement).value);
    elements.push({
      y:     isNaN(y)   ? 0 : y,
      z:     isNaN(z)   ? 0 : z,
      amp:   isNaN(amp) ? 1 : amp,
      phase: isNaN(ph)  ? 0 : ph,
    });
  }
  return elements;
}

function readPatternTableForSave(tbody: HTMLTableSectionElement): PatternPoint[] {
  const rows = tbody.rows;
  const points: PatternPoint[] = [];
  for (let i = 0; i < rows.length; i++) {
    const inputs = rows[i].querySelectorAll('input[type="number"]');
    points.push({
      angle: parseFloat((inputs[0] as HTMLInputElement).value) || 0,
      gain: parseFloat((inputs[1] as HTMLInputElement).value) || 0,
    });
  }
  return points;
}

function saveState() {
  try {
    const state = {
      version: STATE_VERSION,
      arrayMode,
      sizex: sizexInput.value,
      sizey: sizeyInput.value,
      spacingx: spacingxInput.value,
      spacingy: spacingyInput.value,
      windowx: windowxSelect.value,
      windowy: windowySelect.value,
      sllx: sllxInput.value,
      slly: sllyInput.value,
      nbarx: nbarxInput.value,
      nbary: nbaryInput.value,
      beamAz: beamAzInput.value,
      beamEl: beamElInput.value,
      plotType,
      fixAzimuth,
      plotEl: plotElInput.value,
      plotAz: plotAzInput.value,
      polarMin: polarMinInput.value,
      arrayColorMode,
      customElements: readCustomElementsForSave(),
      elementPatternActive: elementPatternEnabled.classList.contains('active'),
      azPattern: readPatternTableForSave(azPatternTbody),
      elPattern: readPatternTableForSave(elPatternTbody),
      insetLeft: insetContainer.style.left,
      insetTop: insetContainer.style.top,
      insetVisible: insetContainer.style.display !== 'none',
    };
    localStorage.setItem(STATE_KEY, JSON.stringify(state));
  } catch { /* storage unavailable */ }
}

function loadState() {
  try {
    const raw = localStorage.getItem(STATE_KEY);
    if (!raw) return;
    const s = JSON.parse(raw);
    // Discard state saved by an older schema version
    if (s.version !== STATE_VERSION) {
      localStorage.removeItem(STATE_KEY);
      return;
    }

    // Uniform config
    if (s.sizex != null) sizexInput.value = s.sizex;
    if (s.sizey != null) sizeyInput.value = s.sizey;
    if (s.spacingx != null) spacingxInput.value = s.spacingx;
    if (s.spacingy != null) spacingyInput.value = s.spacingy;
    if (s.windowx != null) windowxSelect.value = s.windowx;
    if (s.windowy != null) windowySelect.value = s.windowy;
    if (s.sllx != null) { sllxInput.value = s.sllx; sllxSlider.value = s.sllx; }
    if (s.slly != null) { sllyInput.value = s.slly; sllySlider.value = s.slly; }
    if (s.nbarx != null) { nbarxInput.value = s.nbarx; nbarxSlider.value = s.nbarx; }
    if (s.nbary != null) { nbaryInput.value = s.nbary; nbarySlider.value = s.nbary; }
    if (s.beamAz != null) {
      beamAzInput.value = s.beamAz;
      beamAzSlider.value = String(Math.round(parseFloat(s.beamAz) * 10));
    }
    if (s.beamEl != null) {
      beamElInput.value = s.beamEl;
      beamElSlider.value = String(Math.round(parseFloat(s.beamEl) * 10));
    }

    // Plot controls
    if (s.plotType != null) { plotType = s.plotType; plotTypeSelect.value = s.plotType; }
    if (s.fixAzimuth != null) fixAzimuth = s.fixAzimuth;
    if (s.plotEl != null) {
      plotElInput.value = s.plotEl;
      plotElSlider.value = String(Math.round(parseFloat(s.plotEl) * 10));
    }
    if (s.plotAz != null) {
      plotAzInput.value = s.plotAz;
      plotAzSlider.value = String(Math.round(parseFloat(s.plotAz) * 10));
    }
    if (s.polarMin != null) { polarMinInput.value = s.polarMin; polarMinSlider.value = s.polarMin; }

    // Array color
    if (s.arrayColorMode != null) { arrayColorMode = s.arrayColorMode; arrayColorSelect.value = s.arrayColorMode; }

    // Custom elements table (overrides defaults already populated)
    if (Array.isArray(s.customElements) && s.customElements.length > 0) {
      populateTable(s.customElements);
    }

    // Array mode
    if (s.arrayMode === 'custom') {
      arrayMode = 'custom';
      tabCustom.classList.add('active');
      tabUniform.classList.remove('active');
      uniformConfigDiv.style.display = 'none';
      customConfigDiv.style.display = '';
    }

    // Element pattern
    if (s.elementPatternActive) {
      elementPatternEnabled.classList.add('active');
      elementPatternEnabled.setAttribute('aria-pressed', 'true');
      elementPatternEnabled.textContent = 'On';
      elementPatternBody.style.display = '';
    }
    if (Array.isArray(s.azPattern) && s.azPattern.length > 0) populatePatternTable(azPatternTbody, s.azPattern);
    if (Array.isArray(s.elPattern) && s.elPattern.length > 0) populatePatternTable(elPatternTbody, s.elPattern);

    // Inset position
    if (s.insetLeft) insetContainer.style.left = s.insetLeft;
    if (s.insetTop) insetContainer.style.top = s.insetTop;
    // Inset visibility (for cartesian/polar where inset is shown by default)
    if (!s.insetVisible && (plotType === 'cartesian' || plotType === 'polar')) {
      insetContainer.style.display = 'none';
      $('inset-section').style.display = '';
    }
  } catch { /* corrupted state, use defaults */ }
}

function scheduleUpdate() {
  saveState();
  if (debounceTimer) clearTimeout(debounceTimer);
  debounceTimer = setTimeout(computeAndPlot, 50);
}

function showComputingBadge() {
  const el = document.getElementById('computing-badge');
  if (el) el.style.display = '';
}

function hideComputingBadge() {
  const el = document.getElementById('computing-badge');
  if (el) el.style.display = 'none';
}

function dismissStartupOverlay() {
  if (firstRenderDone) return;
  firstRenderDone = true;
  const overlay = document.getElementById('startup-overlay');
  if (overlay) {
    overlay.classList.add('hidden');
    overlay.addEventListener('transitionend', () => overlay.remove(), { once: true });
  }
}

function computeAndPlot() {
  const config = getConfig();
  if (!config) return;

  const myId = ++computeId;
  // Only show overlay for larger computations that are perceptibly slow.
  const isLarge = (config.nfftAz ?? 512) * (config.nfftEl ?? 512) > 512 * 512;
  if (isLarge) showComputingBadge();

  ipcRenderer.invoke('compute-pattern', config)
    .then((result: PatternResult) => {
      if (myId !== computeId) return; // superseded by a newer request
      if ((result as any).superseded) { hideComputingBadge(); return; }
      hideComputingBadge();
      dismissStartupOverlay();
      if (result.error) {
        console.error('Python compute error:', result.error);
      } else {
        currentResult = result;
        renderPlot();
      }
    })
    .catch((err: Error) => {
      if (myId !== computeId) return; // superseded
      hideComputingBadge();
      dismissStartupOverlay();
      if (err.message !== 'superseded') {
        console.error('IPC error:', err.message);
      }
    });
}

function renderPlot() {
  if (!currentResult) return;

  switch (plotType) {
    case '3d':
      render3D(currentResult);
      insetContainer.style.display = 'none';
      break;
    case '3d-polar':
      render3DPolar(currentResult);
      insetContainer.style.display = 'none';
      break;
    case 'cartesian':
      renderCartesian(currentResult);
      if (insetContainer.style.display !== 'none') {
        render3DInset(currentResult);
      }
      break;
    case 'polar':
      renderPolar(currentResult);
      if (insetContainer.style.display !== 'none') {
        render3DInset(currentResult);
      }
      break;
  }

  renderArrayLayout(currentResult);
}

function render3DPolar(result: PatternResult) {
  if (!result.arrayFactor2D) return;

  const nAz = result.azimuth.length;
  const nEl = result.elevation.length;

  // Downsample for WebGL performance
  const stride = 3;
  const meshX: number[][] = [];
  const meshY: number[][] = [];
  const meshZ: number[][] = [];
  const surfColor: number[][] = [];

  for (let i = 0; i < nAz; i += stride) {
    const rowX: number[] = [];
    const rowY: number[] = [];
    const rowZ: number[] = [];
    const rowC: number[] = [];
    const azRad = result.azimuth[i] * Math.PI / 180;
    for (let j = 0; j < nEl; j += stride) {
      const elRad = result.elevation[j] * Math.PI / 180;
      const ampDb = result.arrayFactor2D[i][j];
      // Shift dB range to [0, 1]: 0 dB → 1.0, -60 dB → 0.0
      const r = Math.max(ampDb + 60, 0) / 60;
      // x = boresight, y = horizontal (left-right), z = vertical (up-down)
      rowX.push(r * Math.cos(elRad) * Math.cos(azRad));
      rowY.push(r * Math.cos(elRad) * Math.sin(azRad));
      rowZ.push(r * Math.sin(elRad));
      rowC.push(ampDb);
    }
    meshX.push(rowX);
    meshY.push(rowY);
    meshZ.push(rowZ);
    surfColor.push(rowC);
  }

  // Axis reference lines: x=boresight, y=horizontal, z=vertical
  function axisLine(x1: number, y1: number, z1: number, color: string): Plotly.Data {
    return {
      type: 'scatter3d' as const,
      x: [0, x1],
      y: [0, y1],
      z: [0, z1],
      mode: 'lines' as const,
      line: { color, width: 5 },
      showlegend: false,
      hoverinfo: 'skip' as const,
    } as unknown as Plotly.Data;
  }

  // YZ aperture plane grid (x = 0)
  const planeSize = 1.05;
  const planeSteps = 5;
  const yzPlaneTraces: Plotly.Data[] = [];
  // horizontal lines (sweep y, fixed z)
  for (let s = 0; s <= planeSteps; s++) {
    const zv = -planeSize + s * (2 * planeSize / planeSteps);
    yzPlaneTraces.push({
      type: 'scatter3d' as const,
      x: [0, 0],
      y: [-planeSize, planeSize],
      z: [zv, zv],
      mode: 'lines' as const,
      line: { color: '#3a3a6c', width: 1 },
      showlegend: false,
      hoverinfo: 'skip' as const,
    } as unknown as Plotly.Data);
  }
  // vertical lines (sweep z, fixed y)
  for (let s = 0; s <= planeSteps; s++) {
    const yv = -planeSize + s * (2 * planeSize / planeSteps);
    yzPlaneTraces.push({
      type: 'scatter3d' as const,
      x: [0, 0],
      y: [yv, yv],
      z: [-planeSize, planeSize],
      mode: 'lines' as const,
      line: { color: '#3a3a6c', width: 1 },
      showlegend: false,
      hoverinfo: 'skip' as const,
    } as unknown as Plotly.Data);
  }

  const data: Plotly.Data[] = [
    ...yzPlaneTraces,
    {
      type: 'surface' as const,
      x: meshX as any,
      y: meshY as any,
      z: meshZ as any,
      surfacecolor: surfColor as any,
      colorscale: 'Jet',
      cmin: -60,
      cmax: 0,
      showscale: true,
      colorbar: { title: { text: 'dB', side: 'right' } },
      contours: {
        x: { highlight: false } as any,
        y: { highlight: false } as any,
        z: { highlight: false } as any,
      },
    } as Plotly.Data,
    axisLine(1.35, 0, 0, '#80c0ff'),
    axisLine(0, 1.35, 0, '#80ffb0'),
    axisLine(0, 0, 1.35, '#ffb080'),
  ];

  const layout: Partial<Plotly.Layout> = {
    scene: {
      xaxis: {
        title: { text: '' },
        showgrid: false,
        zeroline: false,
        showticklabels: false,
        range: [-1.6, 1.6] as any,
      },
      yaxis: {
        title: { text: '' },
        showgrid: false,
        zeroline: false,
        showticklabels: false,
        range: [-1.6, 1.6] as any,
      },
      zaxis: {
        title: { text: '' },
        showgrid: false,
        zeroline: false,
        showticklabels: false,
        range: [-1.6, 1.6] as any,
      },
      annotations: [
        { x: 1.55, y: 0, z: 0, text: 'x', showarrow: false, font: { color: '#80c0ff', size: 12 } },
        { x: 0, y: 1.55, z: 0, text: 'y', showarrow: false, font: { color: '#80ffb0', size: 12 } },
        { x: 0, y: 0, z: 1.55, text: 'z', showarrow: false, font: { color: '#ffb080', size: 12 } },
      ] as any,
      aspectmode: 'cube' as const,
      bgcolor: '#1e1e2e',
      camera: {
        eye: { x: 1.6, y: 1.2, z: 0.8 },
      } as any,
    },
    margin: { l: 0, r: 0, t: 30, b: 0 },
    paper_bgcolor: '#1e1e2e',
    font: { color: '#e0e0f0' },
  };

  Plotly.react(plotContainer, data, layout, { responsive: true });
}

function render3D(result: PatternResult) {
  if (!result.arrayFactor2D) return;

  const data: Plotly.Data[] = [
    {
      type: 'surface' as const,
      z: result.arrayFactor2D,
      x: result.elevation,
      y: result.azimuth,
      colorscale: 'Jet',
      zmin: -100,
      zmax: 0,
      showscale: true,
      colorbar: {
        title: { text: 'dB', side: 'right' },
      },
    },
  ];

  const layout: Partial<Plotly.Layout> = {
    scene: {
      xaxis: { title: { text: 'Elevation (°)' } },
      yaxis: { title: { text: 'Azimuth (°)' } },
      zaxis: { title: { text: 'Amplitude (dB)' }, range: [-100, 0] },
    },
    margin: { l: 0, r: 0, t: 30, b: 0 },
    paper_bgcolor: '#1e1e2e',
    font: { color: '#e0e0f0' },
  };

  Plotly.react(plotContainer, data, layout, { responsive: true });
}

function extractCut(result: PatternResult): { angles: number[]; pattern: number[] } {
  if (fixAzimuth) {
    // Fix azimuth → sweep elevation
    const targetAz = parseFloat(plotAzInput.value) || 0;
    let azIdx = 0;
    let minDist = Math.abs(result.azimuth[0] - targetAz);
    for (let i = 1; i < result.azimuth.length; i++) {
      const d = Math.abs(result.azimuth[i] - targetAz);
      if (d < minDist) { minDist = d; azIdx = i; }
    }
    return { angles: result.elevation, pattern: result.arrayFactor2D[azIdx] };
  } else {
    // Fix elevation → sweep azimuth
    const targetEl = parseFloat(plotElInput.value) || 0;
    let elIdx = 0;
    let minDist = Math.abs(result.elevation[0] - targetEl);
    for (let i = 1; i < result.elevation.length; i++) {
      const d = Math.abs(result.elevation[i] - targetEl);
      if (d < minDist) { minDist = d; elIdx = i; }
    }
    const pattern = result.arrayFactor2D.map((row) => row[elIdx]);
    return { angles: result.azimuth, pattern };
  }
}

function renderCartesian(result: PatternResult) {
  const { angles, pattern } = extractCut(result);

  const data: Plotly.Data[] = [
    {
      type: 'scatter' as const,
      x: angles,
      y: pattern,
      mode: 'lines' as const,
      line: { color: '#f48fb1', width: 2 },
      name: 'Pattern',
    },
  ];

  const xLabel = fixAzimuth ? 'Elevation (°)' : 'Azimuth (°)';

  const layout: Partial<Plotly.Layout> = {
    xaxis: { title: { text: xLabel }, range: [-90, 90], gridcolor: '#3a3a5c' },
    yaxis: {
      title: { text: 'Normalized Amplitude (dB)' },
      range: [-80, 0],
      gridcolor: '#3a3a5c',
    },
    plot_bgcolor: '#1e1e2e',
    paper_bgcolor: '#1e1e2e',
    font: { color: '#e0e0f0' },
    margin: { l: 60, r: 20, t: 30, b: 50 },
    showlegend: false,
  };

  Plotly.react(plotContainer, data, layout, { responsive: true });
}

function renderPolar(result: PatternResult) {
  const { angles, pattern } = extractCut(result);
  const minAmp = parseFloat(polarMinInput.value) || -60;

  // Clamp pattern values
  const clamped = pattern.map((v) => Math.max(v, minAmp));
  // Shift to make minAmp -> 0
  const shifted = clamped.map((v) => v - minAmp);

  const data: Plotly.Data[] = [
    {
      type: 'scatterpolar' as const,
      r: shifted,
      theta: angles,
      mode: 'lines' as const,
      line: { color: '#f48fb1', width: 2 },
      name: 'Pattern',
    },
  ];

  const layout: Partial<Plotly.Layout> = {
    polar: {
      bgcolor: '#1e1e2e',
      sector: [0, 180],
      radialaxis: {
        visible: true,
        range: [0, -minAmp],
        gridcolor: '#3a3a5c',
        color: '#e0e0f0',
      },
      angularaxis: {
        gridcolor: '#3a3a5c',
        color: '#e0e0f0',
        direction: 'clockwise' as const,
        rotation: 90,
      },
    },
    paper_bgcolor: '#1e1e2e',
    font: { color: '#e0e0f0' },
    margin: { l: 40, r: 40, t: 30, b: 40 },
    showlegend: false,
  };

  Plotly.react(plotContainer, data, layout, { responsive: true });
}

function render3DInset(result: PatternResult) {
  if (!result.arrayFactor2D) return;

  // Transpose arrayFactor2D from [az][el] to [el][az] so x=Az, y=El
  const nAz = result.azimuth.length;
  const nEl = result.elevation.length;
  const transposed: number[][] = Array.from({ length: nEl }, (_, ei) =>
    Array.from({ length: nAz }, (_, ai) => result.arrayFactor2D![ai][ei])
  );

  const traces: Plotly.Data[] = [
    {
      type: 'heatmap' as const,
      z: transposed,
      x: result.azimuth,
      y: result.elevation,
      colorscale: 'Jet',
      zmin: -60,
      zmax: 0,
      showscale: false,
      hoverinfo: 'skip' as const,
    },
  ];

  // Add cut-plane line
  if (fixAzimuth) {
    const targetAz = parseFloat(plotAzInput.value) || 0;
    let azIdx = 0;
    let minDist = Math.abs(result.azimuth[0] - targetAz);
    for (let i = 1; i < result.azimuth.length; i++) {
      const d = Math.abs(result.azimuth[i] - targetAz);
      if (d < minDist) { minDist = d; azIdx = i; }
    }
    const cutAz = result.azimuth[azIdx];
    const elMin = result.elevation[0];
    const elMax = result.elevation[result.elevation.length - 1];
    const elPad = (elMax - elMin) * 0.1;
    traces.push({
      type: 'scatter' as const,
      x: [cutAz, cutAz],
      y: [elMin - elPad, elMax + elPad],
      mode: 'lines' as const,
      line: { color: '#ffffff', width: 2, dash: 'dash' },
      showlegend: false,
      hoverinfo: 'skip' as const,
    });
  } else {
    const targetEl = parseFloat(plotElInput.value) || 0;
    let elIdx = 0;
    let minDist = Math.abs(result.elevation[0] - targetEl);
    for (let i = 1; i < result.elevation.length; i++) {
      const d = Math.abs(result.elevation[i] - targetEl);
      if (d < minDist) { minDist = d; elIdx = i; }
    }
    const cutEl = result.elevation[elIdx];
    const azMin = result.azimuth[0];
    const azMax = result.azimuth[result.azimuth.length - 1];
    const azPad = (azMax - azMin) * 0.1;
    traces.push({
      type: 'scatter' as const,
      x: [azMin - azPad, azMax + azPad],
      y: [cutEl, cutEl],
      mode: 'lines' as const,
      line: { color: '#ffffff', width: 2, dash: 'dash' },
      showlegend: false,
      hoverinfo: 'skip' as const,
    });
  }

  const layout: Partial<Plotly.Layout> = {
    xaxis: {
      title: { text: 'Az (°)', standoff: 2 },
      gridcolor: '#3a3a5c',
      tickfont: { size: 9 },
    },
    yaxis: {
      title: { text: 'El (°)', standoff: 2 },
      gridcolor: '#3a3a5c',
      tickfont: { size: 9 },
    },
    margin: { l: 36, r: 4, t: 20, b: 30 },
    plot_bgcolor: '#1e1e2e',
    paper_bgcolor: '#1e1e2e',
    font: { color: '#e0e0f0', size: 9 },
  };

  Plotly.react(insetContainer, traces, layout, { responsive: true, displayModeBar: false });
}

function renderArrayLayout(result: PatternResult) {
  const weightAmp = result.weightRe.map((re, i) => Math.sqrt(re * re + result.weightIm[i] * result.weightIm[i]));
  const maxW = Math.max(...weightAmp) || 1;

  let colorValues: number[];
  let colorscale: [number, string][];
  let colorbarTitle: string;
  let cmin: number;
  let cmax: number;

  if (arrayColorMode === 'phase') {
    colorValues = result.weightRe.map((re, i) => (Math.atan2(result.weightIm[i], re) / Math.PI) * 180);
    colorscale = [
      [0, '#3a3a8c'],
      [0.25, '#80c0ff'],
      [0.5, '#f0f0f0'],
      [0.75, '#f48fb1'],
      [1, '#8c1a40'],
    ];
    colorbarTitle = 'Phase (°)';
    cmin = -180;
    cmax = 180;
  } else {
    colorValues = weightAmp.map((w) => w / maxW);
    colorscale = [
      [0, '#3a3a5c'],
      [1, '#f48fb1'],
    ];
    colorbarTitle = 'Amplitude';
    cmin = 0;
    cmax = 1;
  }

  const data: Plotly.Data[] = [
    {
      type: 'scatter' as const,
      x: result.x,
      y: result.y,
      mode: 'markers' as const,
      marker: {
        size: 6,
        color: colorValues,
        colorscale: colorscale as any,
        cmin,
        cmax,
        showscale: true,
        colorbar: {
          title: { text: colorbarTitle, side: 'right' },
        },
      },
      name: 'Elements',
    },
  ];

  const layout: Partial<Plotly.Layout> = {
    xaxis: {
      title: { text: 'Horizontal y (\u03bb)' },
      scaleanchor: 'y',
      gridcolor: '#3a3a5c',
    },
    yaxis: { title: { text: 'Vertical z (\u03bb)' }, gridcolor: '#3a3a5c' },
    plot_bgcolor: '#1e1e2e',
    paper_bgcolor: '#1e1e2e',
    font: { color: '#e0e0f0' },
    margin: { l: 60, r: 20, t: 30, b: 50 },
    showlegend: false,
  };

  Plotly.react(layoutContainer, data, layout, { responsive: true });
}

// ---- CSV Export ----
function downloadCSV(filename: string, content: string) {
  const blob = new Blob([content], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

function exportArrayConfig() {
  if (!currentResult) return;
  const lines = ['x (wavelength),y (wavelength),amplitude (linear),phase (degree)'];
  for (let i = 0; i < currentResult.x.length; i++) {
    const re = currentResult.weightRe[i];
    const im = currentResult.weightIm[i];
    const amp = Math.sqrt(re * re + im * im);
    const phase = (Math.atan2(im, re) / Math.PI) * 180;
    lines.push(
      `${currentResult.x[i].toExponential(8)},${currentResult.y[i].toExponential(8)},${amp.toExponential(8)},${phase.toExponential(8)}`
    );
  }
  downloadCSV('array_config.csv', lines.join('\n'));
}

function exportPattern() {
  if (!currentResult) return;
  const lines = ['azimuth (degree),elevation (degree),pattern (dB)'];
  const { azimuth, elevation, arrayFactor2D } = currentResult;

  for (let ai = 0; ai < azimuth.length; ai++) {
    for (let ei = 0; ei < elevation.length; ei++) {
      lines.push(
        `${azimuth[ai].toExponential(8)},${elevation[ei].toExponential(8)},${arrayFactor2D[ai][ei].toExponential(8)}`
      );
    }
  }
  downloadCSV('pattern.csv', lines.join('\n'));
}

// ---- Event wiring ----
function init() {
  // Array config
  [sizexInput, sizeyInput, spacingxInput, spacingyInput].forEach((el) =>
    el.addEventListener('input', scheduleUpdate)
  );

  // Window selects
  windowxSelect.addEventListener('change', () => {
    updateWindowControls('x', windowxSelect.value);
    scheduleUpdate();
  });
  windowySelect.addEventListener('change', () => {
    updateWindowControls('y', windowySelect.value);
    scheduleUpdate();
  });

  // Slider/input pairs
  syncPair(beamAzInput, beamAzSlider, 10);
  syncPair(beamElInput, beamElSlider, 10);
  syncPair(plotAzInput, plotAzSlider, 10);
  syncPair(plotElInput, plotElSlider, 10);
  syncPairDirect(sllxInput, sllxSlider);
  syncPairDirect(sllyInput, sllySlider);
  syncPairDirect(nbarxInput, nbarxSlider);
  syncPairDirect(nbaryInput, nbarySlider);
  syncPairDirect(polarMinInput, polarMinSlider);

  // Plot type
  plotTypeSelect.addEventListener('change', () => {
    plotType = plotTypeSelect.value;
    updatePlotTypeUI();
    scheduleUpdate();
  });

  // Fix plane radio
  fixElevationRadio.addEventListener('change', () => {
    fixAzimuth = false;
    updateFixPlaneUI();
    scheduleUpdate();
  });
  fixAzimuthRadio.addEventListener('change', () => {
    fixAzimuth = true;
    updateFixPlaneUI();
    scheduleUpdate();
  });

  // Export dropdown
  const exportBtn = $('btn-export');
  const exportMenu = $('export-menu');
  exportBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    exportMenu.style.display = exportMenu.style.display === 'none' ? '' : 'none';
  });
  document.addEventListener('click', () => { exportMenu.style.display = 'none'; });
  $('btn-export-config').addEventListener('click', () => { exportMenu.style.display = 'none'; exportArrayConfig(); });
  $('btn-export-pattern').addEventListener('click', () => { exportMenu.style.display = 'none'; exportPattern(); });

  // Array color mode
  arrayColorSelect.addEventListener('change', () => {
    arrayColorMode = arrayColorSelect.value;
    if (currentResult) renderArrayLayout(currentResult);
    saveState();
  });

  // About dialog
  const pkg = require('../../package.json');
  const aboutVersionEl = document.getElementById('about-version');
  if (aboutVersionEl) aboutVersionEl.textContent = `Version ${pkg.version}`;
  const aboutDialog = $('about-dialog');
  $('btn-about').addEventListener('click', () => {
    aboutDialog.style.display = 'flex';
  });
  const closeAbout = () => { aboutDialog.style.display = 'none'; };
  $('btn-about-close').addEventListener('click', closeAbout);
  aboutDialog.addEventListener('click', (e) => {
    if (e.target === aboutDialog) closeAbout();
  });
  $('link-about-help').addEventListener('click', (e) => {
    e.preventDefault();
    shell.openExternal('https://github.com/rookiepeng/antenna-array-analysis/issues');
  });

  // Inset close / show
  $('inset-close').addEventListener('click', (e: Event) => {
    e.stopPropagation();
    insetContainer.style.display = 'none';
    $('inset-section').style.display = '';
    saveState();
  });

  $('btn-show-inset').addEventListener('click', () => {
    insetContainer.style.display = 'block';
    $('inset-section').style.display = 'none';
    if (currentResult) render3DInset(currentResult);
    saveState();
  });

  // Inset drag
  const dragHandle = $('inset-drag-handle');
  let dragging = false;
  let dragStartX = 0, dragStartY = 0;
  let dragStartLeft = 0, dragStartTop = 0;

  dragHandle.addEventListener('mousedown', (e: MouseEvent) => {
    dragging = true;
    dragStartX = e.clientX;
    dragStartY = e.clientY;
    dragStartLeft = insetContainer.offsetLeft;
    dragStartTop = insetContainer.offsetTop;
    e.preventDefault();
  });

  document.addEventListener('mousemove', (e: MouseEvent) => {
    if (!dragging) return;
    const parent = insetContainer.parentElement!;
    const maxLeft = parent.clientWidth - insetContainer.offsetWidth;
    const maxTop = parent.clientHeight - insetContainer.offsetHeight;
    insetContainer.style.left = Math.max(0, Math.min(dragStartLeft + e.clientX - dragStartX, maxLeft)) + 'px';
    insetContainer.style.top  = Math.max(0, Math.min(dragStartTop  + e.clientY - dragStartY, maxTop))  + 'px';
  });

  document.addEventListener('mouseup', () => {
    if (dragging) { dragging = false; saveState(); }
    else { dragging = false; }
  });

  // Resize handling
  window.addEventListener('resize', () => {
    Plotly.Plots.resize(plotContainer);
    if (insetContainer.style.display !== 'none') {
      Plotly.Plots.resize(insetContainer);
    }
    Plotly.Plots.resize(layoutContainer);
  });

  // Initial state
  updatePlotTypeUI();
  updateWindowControls('x', windowxSelect.value);
  updateWindowControls('y', windowySelect.value);

  // Array mode toggle
  tabUniform.addEventListener('click', () => {
    if (arrayMode === 'uniform') return;
    arrayMode = 'uniform';
    tabUniform.classList.add('active');
    tabCustom.classList.remove('active');
    uniformConfigDiv.style.display = '';
    customConfigDiv.style.display = 'none';
    scheduleUpdate();
  });
  tabCustom.addEventListener('click', () => {
    if (arrayMode === 'custom') return;
    arrayMode = 'custom';
    tabCustom.classList.add('active');
    tabUniform.classList.remove('active');
    uniformConfigDiv.style.display = 'none';
    customConfigDiv.style.display = '';
    // Apply when switching to custom mode
    applyCustomAndCompute();
  });

  // Custom array apply
  $('btn-apply-custom').addEventListener('click', applyCustomAndCompute);

  // Custom array add row
  $('btn-add-row').addEventListener('click', () => {
    addTableRow();
    showCustomUnsyncedBanner();
    saveState();
  });

  // Custom array CSV import
  $('btn-import-csv').addEventListener('click', () => {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.csv,.txt';
    input.onchange = () => {
      const file = input.files?.[0];
      if (!file) return;
      const reader = new FileReader();
      reader.onload = () => {
        const text = (reader.result as string).trim();
        const elements: CustomElement[] = [];
        for (const line of text.split('\n')) {
          const trimmed = line.trim();
          if (!trimmed || trimmed.startsWith('#')) continue;
          const parts = trimmed.split(',').map(s => s.trim());
          if (parts.length < 2) continue;
          const y = parseFloat(parts[0]);
          const z = parseFloat(parts[1]);
          const amp = parts.length > 2 ? parseFloat(parts[2]) : 1;
          const phase = parts.length > 3 ? parseFloat(parts[3]) : 0;
          if ([y, z, amp, phase].some(isNaN)) continue;
          elements.push({ y, z, amp, phase });
        }
        if (elements.length > 0) {
          populateTable(elements);
          customErrorP.textContent = '';
          showCustomUnsyncedBanner();
          saveState();
        } else {
          customErrorP.textContent = 'No valid rows found in file';
        }
      };
      reader.readAsText(file);
    };
    input.click();
  });

  // Populate default table rows
  populateTable(DEFAULT_ELEMENTS);

  // Element pattern toggle
  elementPatternEnabled.addEventListener('click', () => {
    const isActive = elementPatternEnabled.classList.toggle('active');
    elementPatternEnabled.setAttribute('aria-pressed', String(isActive));
    elementPatternEnabled.textContent = isActive ? 'On' : 'Off';
    elementPatternBody.style.display = isActive ? '' : 'none';
    scheduleUpdate();
  });

  // Element pattern table buttons
  $('btn-add-az-pattern').addEventListener('click', () => addPatternRow(azPatternTbody));
  $('btn-add-el-pattern').addEventListener('click', () => addPatternRow(elPatternTbody));
  $('btn-import-az-pattern').addEventListener('click', () => importPatternCSV(azPatternTbody));
  $('btn-import-el-pattern').addEventListener('click', () => importPatternCSV(elPatternTbody));

  // Populate default element patterns
  populatePatternTable(azPatternTbody, DEFAULT_AZ_PATTERN);
  populatePatternTable(elPatternTbody, DEFAULT_EL_PATTERN);

  // Restore previous session state (overrides defaults above)
  loadState();
  updateWindowControls('x', windowxSelect.value);
  updateWindowControls('y', windowySelect.value);
  updatePlotTypeUI();

  // Initial compute
  computeAndPlot();
}

document.addEventListener('DOMContentLoaded', init);

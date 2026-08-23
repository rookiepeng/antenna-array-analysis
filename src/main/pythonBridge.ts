/**
 * Manages the Python child process for antenna array computation.
 * Spawns a persistent Python process and communicates over stdin/stdout JSON lines.
 */

import { spawn, ChildProcess } from 'child_process';
import * as path from 'path';
import { app } from 'electron';

export interface ComputeConfig {
  mode?: 'uniform' | 'custom';
  sizex?: number;
  sizey?: number;
  spacingx?: number;
  spacingy?: number;
  beamAz?: number;
  beamEl?: number;
  windowx?: number;
  windowy?: number;
  sllx?: number;
  slly?: number;
  nbarx?: number;
  nbary?: number;
  nfftAz: number;
  nfftEl: number;
  plotAz: number;
  plotEl: number;
  customY?: number[];
  customZ?: number[];
  customAmp?: number[];
  customPhase?: number[];
}

export interface ComputeResult {
  azimuth: number[];
  elevation: number[];
  arrayFactor2D: number[][];
  x: number[];
  y: number[];
  weightRe: number[];
  weightIm: number[];
  error?: string;
}

type PendingResolve = (result: ComputeResult) => void;
type PendingReject = (err: Error) => void;
type QueueItem = { resolve: PendingResolve; reject: PendingReject };

export class PythonBridge {
  private proc: ChildProcess | null = null;
  private buffer: string = '';
  private queue: QueueItem[] = [];
  private arraybeamPath: string;
  private bridgePath: string;
  private stopped: boolean = false;

  constructor() {
    if (app.isPackaged) {
      // In the packaged app, electron-builder places extra resources in
      // process.resourcesPath.  The bridge executable is a self-contained
      // PyInstaller binary — no separate Python interpreter needed.
      const exe = process.platform === 'win32' ? 'bridge.exe' : 'bridge';
      this.bridgePath = path.join(process.resourcesPath, 'bridge', exe);
      this.arraybeamPath = '';  // bundled inside the executable, not used
    } else {
      // Development: run bridge.py with the system Python interpreter.
      const projectRoot = path.join(__dirname, '..', '..');
      this.arraybeamPath = path.join(projectRoot, 'src', 'arraybeam');
      this.bridgePath = path.join(projectRoot, 'src', 'python', 'bridge.py');
    }
  }

  start(): void {
    if (this.proc) return;

    if (app.isPackaged) {
      // Packaged: bridge is a PyInstaller executable — spawn it directly.
      this.proc = spawn(this.bridgePath, [], {
        stdio: ['pipe', 'pipe', 'pipe'],
      });
    } else {
      // Development: run the .py script with Python.
      this.proc = spawn('python', [this.bridgePath, this.arraybeamPath], {
        stdio: ['pipe', 'pipe', 'pipe'],
      });
    }

    this.proc.stdout!.on('data', (data: Buffer) => {
      this.buffer += data.toString();
      const lines = this.buffer.split('\n');
      this.buffer = lines.pop() || '';

      for (const line of lines) {
        if (!line.trim()) continue;
        const item = this.queue.shift();
        if (!item) continue;
        try {
          const result: ComputeResult = JSON.parse(line);
          item.resolve(result);
        } catch (e) {
          item.reject(new Error(`Failed to parse Python output: ${line}`));
        }
      }
    });

    this.proc.stderr!.on('data', (data: Buffer) => {
      console.error('Python stderr:', data.toString());
    });

    this.proc.on('exit', (code) => {
      console.error('Python process exited with code', code);
      this.proc = null;
      for (const item of this.queue) {
        item.reject(new Error(`Python process exited with code ${code}`));
      }
      this.queue = [];
      // Auto-restart after a short delay (unless stop() was called)
      if (!this.stopped) {
        setTimeout(() => this.start(), 500);
      }
    });
  }

  compute(config: ComputeConfig): Promise<ComputeResult> {
    return new Promise((resolve, reject) => {
      // Cancel any in-flight computation: kill Python so it stops immediately,
      // reject superseded promises, then restart fresh for the new request.
      if (this.queue.length > 0) {
        for (const item of this.queue) {
          item.reject(new Error('superseded'));
        }
        this.queue = [];
        if (this.proc) {
          this.proc.removeAllListeners();
          this.proc.kill();
          this.proc = null;
        }
        this.start(); // restart Python immediately
      }

      if (!this.proc || !this.proc.stdin) {
        reject(new Error('Python process not started'));
        return;
      }

      this.queue.push({ resolve, reject });
      this.proc.stdin.write(JSON.stringify(config) + '\n');
    });
  }

  stop(): void {
    if (this.proc) {
      this.stopped = true;
      this.proc.stdin!.end();
      this.proc.kill();
      this.proc = null;
    }
  }
}

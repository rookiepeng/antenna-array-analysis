/**
 * Manages the Python child process for antenna array computation.
 * Spawns a persistent Python process and communicates over stdin/stdout JSON lines.
 */

import { spawn, ChildProcess } from 'child_process';
import * as path from 'path';
import { app } from 'electron';

export interface ComputeConfig {
  sizex: number;
  sizey: number;
  spacingx: number;
  spacingy: number;
  beamAz: number;
  beamEl: number;
  windowx: number;
  windowy: number;
  sllx: number;
  slly: number;
  nbarx: number;
  nbary: number;
  nfftAz: number;
  nfftEl: number;
  plotAz: number;
  plotEl: number;
}

export interface ComputeResult {
  azimuth: number[];
  elevation: number[];
  arrayFactor: number[];
  arrayFactor2D?: number[][];
  x: number[];
  y: number[];
  weightRe: number[];
  weightIm: number[];
  error?: string;
}

type PendingResolve = (result: ComputeResult) => void;
type PendingReject = (err: Error) => void;

export class PythonBridge {
  private proc: ChildProcess | null = null;
  private buffer: string = '';
  private pending: { resolve: PendingResolve; reject: PendingReject } | null = null;
  private antarrayPath: string;
  private bridgePath: string;
  private stopped: boolean = false;

  constructor() {
    if (app.isPackaged) {
      // In the packaged app, electron-builder places extra resources in
      // process.resourcesPath.  The bridge executable is a self-contained
      // PyInstaller binary — no separate Python interpreter needed.
      const exe = process.platform === 'win32' ? 'bridge.exe' : 'bridge';
      this.bridgePath = path.join(process.resourcesPath, 'bridge', exe);
      this.antarrayPath = '';  // bundled inside the executable, not used
    } else {
      // Development: run bridge.py with the system Python interpreter.
      const projectRoot = path.join(__dirname, '..', '..');
      this.antarrayPath = path.join(projectRoot, 'src');
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
      this.proc = spawn('python', [this.bridgePath, this.antarrayPath], {
        stdio: ['pipe', 'pipe', 'pipe'],
      });
    }

    this.proc.stdout!.on('data', (data: Buffer) => {
      this.buffer += data.toString();
      const lines = this.buffer.split('\n');
      this.buffer = lines.pop() || '';

      for (const line of lines) {
        if (!line.trim()) continue;
        try {
          const result: ComputeResult = JSON.parse(line);
          if (this.pending) {
            const { resolve } = this.pending;
            this.pending = null;
            resolve(result);
          }
        } catch (e) {
          if (this.pending) {
            const { reject } = this.pending;
            this.pending = null;
            reject(new Error(`Failed to parse Python output: ${line}`));
          }
        }
      }
    });

    this.proc.stderr!.on('data', (data: Buffer) => {
      console.error('Python stderr:', data.toString());
    });

    this.proc.on('exit', (code) => {
      console.error('Python process exited with code', code);
      this.proc = null;
      if (this.pending) {
        const { reject } = this.pending;
        this.pending = null;
        reject(new Error(`Python process exited with code ${code}`));
      }
      // Auto-restart after a short delay (unless stop() was called)
      if (!this.stopped) {
        setTimeout(() => this.start(), 500);
      }
    });
  }

  compute(config: ComputeConfig): Promise<ComputeResult> {
    return new Promise((resolve, reject) => {
      if (!this.proc || !this.proc.stdin) {
        reject(new Error('Python process not started'));
        return;
      }

      // If there's already a pending request, cancel it — don't write it to
      // stdin (the Python side hasn't seen it yet) and reject the promise.
      if (this.pending) {
        this.pending.reject(new Error('Superseded by new request'));
        this.pending = null;
      }

      this.pending = { resolve, reject };
      const json = JSON.stringify(config) + '\n';
      this.proc.stdin.write(json);
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

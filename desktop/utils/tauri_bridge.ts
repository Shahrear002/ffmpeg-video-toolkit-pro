import type { ProgressParser } from './progress_parser'
import type { SidecarRunner, SidecarProcess } from '../stores/queue'

export function isTauriEnvironment(): boolean {
  if (typeof window === 'undefined') return false
  return '__TAURI_INTERNALS__' in window || '__TAURI__' in window
}

/**
 * Creates the production sidecar runner using @tauri-apps/plugin-shell.
 * In development or browser fallback, runs a simulated mock execution.
 */
export async function createSidecarRunner(): Promise<SidecarRunner> {
  if (!isTauriEnvironment()) {
    console.warn('[Desktop] Running in non-Tauri browser environment. Mock runner enabled.')
    return async (args, onData, onError) => {
      onData(`{"event":"start","subcommand":"${args[0]}","input":"test","output":"test"}\n`)
      for (let p = 10; p <= 100; p += 25) {
        await new Promise((r) => setTimeout(r, 100))
        onData(`{"event":"progress","data":{"percent":${p},"fps":30,"speed":"2.0x","eta_s":${(100 - p) / 10}}}\n`)
      }
      onData('{"event":"done","output":"mock-output.mp4","bytes":1048576}\n')
      return { code: 0 }
    }
  }

  // Inside Tauri environment: import Tauri shell plugin dynamically
  const { Command } = await import('@tauri-apps/plugin-shell')

  return async (args, onData, onError) => {
    // Spawn sidecar: video_toolkit binary
    const command = Command.sidecar('binaries/video_toolkit', args)

    let childProcess: any = null

    command.on('close', (data) => {
      // Process finished
    })

    command.on('error', (error) => {
      onError(`Process error: ${error}\n`)
    })

    command.stdout.on('data', (line) => {
      onData(line + '\n')
    })

    command.stderr.on('data', (line) => {
      onError(line + '\n')
    })

    const child = await command.spawn()
    childProcess = child

    const sidecarProcess: SidecarProcess = {
      kill: async () => {
        if (childProcess) {
          await childProcess.kill()
        }
      }
    }

    return new Promise((resolve) => {
      command.on('close', (data) => {
        resolve({ code: data.code ?? 0, process: sidecarProcess })
      })
      command.on('error', () => {
        resolve({ code: 1, process: sidecarProcess })
      })
    })
  }
}

/**
 * Run a quick self-check via sidecar --check
 */
export async function runSelfCheck(): Promise<{ success: boolean; output: string }> {
  if (!isTauriEnvironment()) {
    return {
      success: true,
      output: 'FFmpeg Video Toolkit Pro v1.0.0 (Browser Preview Mode)\nFFmpeg detected: mock ffmpeg 7.1\nCodecs: h264, aac, mp3, flac, gif'
    }
  }

  const { Command } = await import('@tauri-apps/plugin-shell')
  const command = Command.sidecar('binaries/video_toolkit', ['--check'])
  const output = await command.execute()
  return {
    success: output.code === 0,
    output: output.stdout || output.stderr
  }
}

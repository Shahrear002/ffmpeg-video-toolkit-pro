import type { Subcommand, AppSettings } from '../types/toolkit'

export interface ToolFormState {
  // Common
  input: string
  output: string
  overwrite: boolean
  quiet: boolean
  verbose: boolean

  // compress
  targetMb?: number
  preset?: string
  scale?: string
  audioBitrate?: string

  // trim-silence
  noiseDb?: number
  minSilenceSec?: number
  padSec?: number

  // shorts
  shortsMode?: 'crop' | 'blur'
  xOffset?: number

  // convert
  recursive?: boolean
  copyCompatible?: boolean

  // extract-audio
  audioFormat?: 'mp3' | 'wav' | 'flac'
  audioQuality?: string

  // cut
  startTime?: string
  endTime?: string
  duration?: string
  precise?: boolean

  // merge
  mergeInputs?: string[]
  reencode?: boolean

  // gif
  fps?: number
  width?: number
  maxSeconds?: number
  gifFormat?: 'gif' | 'webp'
  dither?: string

  // speed
  speedFactor?: number

  // strip-meta
  // no extra args

  // thumbs
  timestamps?: string
  sheet?: boolean
  cols?: number
  rows?: number
}

export function buildCommandArgs(
  subcommand: Subcommand,
  state: ToolFormState,
  settings?: Partial<AppSettings>
): string[] {
  const args: string[] = [subcommand]

  if (state.input) {
    args.push('-i', state.input)
  }

  if (state.output) {
    args.push('-o', state.output)
  }

  if (state.overwrite || settings?.overwritePolicy) {
    args.push('--overwrite')
  }

  if (settings?.customFfmpegPath) {
    args.push('--ffmpeg', settings.customFfmpegPath)
  }

  if (settings?.customFfprobePath) {
    args.push('--ffprobe', settings.customFfprobePath)
  }

  switch (subcommand) {
    case 'compress':
      if (state.preset) {
        args.push('--preset', state.preset)
      } else if (state.targetMb !== undefined && state.targetMb > 0) {
        args.push('--target-mb', state.targetMb.toString())
      }
      if (state.scale) {
        args.push('--scale', state.scale)
      }
      if (state.audioBitrate) {
        args.push('--audio-bitrate', state.audioBitrate)
      }
      break

    case 'trim-silence':
      if (state.noiseDb !== undefined) {
        args.push('--noise', `${state.noiseDb}dB`)
      }
      if (state.minSilenceSec !== undefined) {
        args.push('--min-silence', state.minSilenceSec.toString())
      }
      if (state.padSec !== undefined) {
        args.push('--pad', state.padSec.toString())
      }
      break

    case 'shorts':
      if (state.shortsMode) {
        args.push('--mode', state.shortsMode)
      }
      if (state.shortsMode === 'crop' && state.xOffset !== undefined) {
        args.push('--x-offset', state.xOffset.toString())
      }
      break

    case 'convert':
      if (state.recursive) {
        args.push('--recursive')
      }
      break

    case 'extract-audio':
      if (state.audioFormat) {
        args.push('--format', state.audioFormat)
      }
      if (state.audioQuality) {
        args.push('--quality', state.audioQuality)
      }
      break

    case 'cut':
      if (state.startTime) {
        args.push('--start', state.startTime)
      }
      if (state.endTime) {
        args.push('--end', state.endTime)
      } else if (state.duration) {
        args.push('--duration', state.duration)
      }
      if (state.precise) {
        args.push('--precise')
      }
      break

    case 'merge':
      if (state.mergeInputs && state.mergeInputs.length > 0) {
        for (const input of state.mergeInputs) {
          args.push('-i', input)
        }
      }
      if (state.reencode) {
        args.push('--reencode')
      }
      break

    case 'gif':
      if (state.fps) {
        args.push('--fps', state.fps.toString())
      }
      if (state.width) {
        args.push('--width', state.width.toString())
      }
      if (state.maxSeconds) {
        args.push('--max-seconds', state.maxSeconds.toString())
      }
      if (state.gifFormat) {
        args.push('--format', state.gifFormat)
      }
      if (state.dither) {
        args.push('--dither', state.dither)
      }
      break

    case 'speed':
      if (state.speedFactor !== undefined) {
        args.push('--factor', state.speedFactor.toString())
      }
      break

    case 'strip-meta':
      // no additional flags
      break

    case 'thumbs':
      if (state.sheet) {
        args.push('--sheet')
        if (state.cols) args.push('--cols', state.cols.toString())
        if (state.rows) args.push('--rows', state.rows.toString())
      } else if (state.timestamps) {
        args.push('--timestamps', state.timestamps)
      }
      break
  }

  // Desktop sidecar always appends --json-progress for reactive progress
  args.push('--json-progress')

  return args
}

export function formatCommandPreview(args: string[]): string {
  // Quote arguments that contain spaces or special characters
  const formatted = args.map((arg) => {
    if (arg.includes(' ') || arg.includes('"') || arg.includes("'")) {
      return `"${arg.replace(/"/g, '\\"')}"`
    }
    return arg
  })
  return `video_toolkit ${formatted.join(' ')}`
}

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

export function getDefaultOutputPath(inputPath: string, subcommand: Subcommand, outDir?: string): string {
  if (!inputPath) return ''
  const normalized = inputPath.replace(/\\/g, '/')
  const lastSlash = normalized.lastIndexOf('/')
  const filename = lastSlash >= 0 ? normalized.slice(lastSlash + 1) : normalized
  const dir = outDir || (lastSlash >= 0 ? normalized.slice(0, lastSlash) : '')

  const dotIndex = filename.lastIndexOf('.')
  const baseName = dotIndex > 0 ? filename.slice(0, dotIndex) : filename
  const origExt = dotIndex > 0 ? filename.slice(dotIndex) : '.mp4'

  let targetExt = origExt
  let suffix = '_processed'

  switch (subcommand) {
    case 'compress':
      suffix = '_compressed'
      targetExt = '.mp4'
      break
    case 'trim-silence':
      suffix = '_trimmed'
      break
    case 'shorts':
      suffix = '_shorts'
      targetExt = '.mp4'
      break
    case 'convert':
      suffix = '_converted'
      targetExt = '.mp4'
      break
    case 'extract-audio':
      suffix = '_audio'
      targetExt = '.mp3'
      break
    case 'cut':
      suffix = '_cut'
      break
    case 'merge':
      suffix = '_merged'
      targetExt = '.mp4'
      break
    case 'gif':
      suffix = '_anim'
      targetExt = '.gif'
      break
    case 'speed':
      suffix = '_speed'
      break
    case 'strip-meta':
      suffix = '_clean'
      break
    case 'thumbs':
      suffix = '_thumb'
      targetExt = '.jpg'
      break
  }

  const outName = `${baseName}${suffix}${targetExt}`
  return dir ? `${dir}/${outName}` : outName
}

export function buildCommandArgs(
  subcommand: Subcommand,
  state: ToolFormState,
  settings?: Partial<AppSettings>
): string[] {
  const args: string[] = [subcommand]
  const effectiveOutput = state.output || (state.input ? getDefaultOutputPath(state.input, subcommand, settings?.outputDirectory) : '')

  // Positional arguments handling per subcommand
  if (subcommand === 'merge') {
    if (state.mergeInputs && state.mergeInputs.length > 0) {
      args.push(...state.mergeInputs)
    } else if (state.input) {
      args.push(state.input)
    }
    if (effectiveOutput) {
      args.push('--output', effectiveOutput)
    }
  } else {
    if (state.input) {
      args.push(state.input)
    }
    if (effectiveOutput && subcommand !== 'convert') {
      args.push(effectiveOutput)
    } else if (effectiveOutput && subcommand === 'convert' && effectiveOutput !== state.input) {
      args.push(effectiveOutput)
    }
  }

  // Common options
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
      if (state.preset === 'auto') {
        args.push('--percent', '50')
      } else if (state.preset === 'max_comp') {
        args.push('--percent', '25')
      } else if (state.preset === 'light_comp') {
        args.push('--percent', '75')
      } else if (state.preset && state.preset !== 'custom') {
        args.push('--preset', state.preset)
      } else if (state.targetMb !== undefined && state.targetMb > 0) {
        args.push('--target-size-mb', state.targetMb.toString())
      }
      if (state.scale) {
        args.push('--scale', state.scale)
      }
      if (state.audioBitrate) {
        const kbps = state.audioBitrate.replace(/[^0-9]/g, '')
        if (kbps) {
          args.push('--audio-bitrate', kbps)
        }
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
        args.push('--bitrate', state.audioQuality)
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

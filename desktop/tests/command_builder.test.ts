import { describe, it, expect } from 'vitest'
import { buildCommandArgs, getDefaultOutputPath } from '../utils/command_builder'

describe('command_builder', () => {
  it('generates appropriate default output paths based on subcommand', () => {
    const input = 'C:/Videos/my_project.mov'
    expect(getDefaultOutputPath(input, 'compress')).toBe('C:/Videos/my_project_compressed.mp4')
    expect(getDefaultOutputPath(input, 'trim-silence')).toBe('C:/Videos/my_project_trimmed.mov')
    expect(getDefaultOutputPath(input, 'shorts')).toBe('C:/Videos/my_project_shorts.mp4')
    expect(getDefaultOutputPath(input, 'extract-audio')).toBe('C:/Videos/my_project_audio.mp3')
    expect(getDefaultOutputPath(input, 'gif')).toBe('C:/Videos/my_project_anim.gif')
    expect(getDefaultOutputPath(input, 'cut')).toBe('C:/Videos/my_project_cut.mov')
    expect(getDefaultOutputPath(input, 'speed')).toBe('C:/Videos/my_project_speed.mov')
    expect(getDefaultOutputPath(input, 'strip-meta')).toBe('C:/Videos/my_project_clean.mov')
    expect(getDefaultOutputPath(input, 'thumbs')).toBe('C:/Videos/my_project_thumb.jpg')
  })

  it('respects custom output directory', () => {
    const input = 'C:/Videos/raw.mp4'
    const outDir = 'D:/Exports'
    expect(getDefaultOutputPath(input, 'compress', outDir)).toBe('D:/Exports/raw_compressed.mp4')
  })

  it('builds positional compress command with target-size-mb', () => {
    const args = buildCommandArgs('compress', {
      input: 'C:/sample.mp4',
      output: 'C:/sample_out.mp4',
      targetMb: 25,
      preset: '',
      scale: '720p',
      audioBitrate: '96k',
      overwrite: true
    })
    expect(args).toContain('compress')
    expect(args).toContain('C:/sample.mp4')
    expect(args).toContain('C:/sample_out.mp4')
    expect(args).toContain('--overwrite')
    expect(args).toContain('--target-size-mb')
    expect(args).toContain('25')
    expect(args).toContain('--scale')
    expect(args).toContain('720p')
    expect(args).toContain('--audio-bitrate')
    expect(args).toContain('96')
  })

  it('builds compress command with auto preset (50% reduction)', () => {
    const args = buildCommandArgs('compress', {
      input: 'C:/sample.mp4',
      output: 'C:/sample_out.mp4',
      preset: 'auto',
      overwrite: true
    })
    expect(args).toContain('compress')
    expect(args).toContain('--percent')
    expect(args).toContain('50')
  })

  it('builds compress command with max_comp and light_comp presets', () => {
    const maxArgs = buildCommandArgs('compress', {
      input: 'C:/sample.mp4',
      preset: 'max_comp'
    })
    expect(maxArgs).toContain('--percent')
    expect(maxArgs).toContain('25')

    const lightArgs = buildCommandArgs('compress', {
      input: 'C:/sample.mp4',
      preset: 'light_comp'
    })
    expect(lightArgs).toContain('--percent')
    expect(lightArgs).toContain('75')
  })

  it('builds compress command with platform preset', () => {
    const discordArgs = buildCommandArgs('compress', {
      input: 'C:/sample.mp4',
      preset: 'discord'
    })
    expect(discordArgs).toContain('--preset')
    expect(discordArgs).toContain('discord')
  })

  it('builds extract-audio with bitrate option', () => {
    const args = buildCommandArgs('extract-audio', {
      input: 'video.mkv',
      output: 'audio.mp3',
      audioFormat: 'mp3',
      audioQuality: '192k'
    })
    expect(args).toContain('extract-audio')
    expect(args).toContain('video.mkv')
    expect(args).toContain('audio.mp3')
    expect(args).toContain('--format')
    expect(args).toContain('mp3')
    expect(args).toContain('--bitrate')
    expect(args).toContain('192k')
  })

  it('builds merge command with positional inputs and --output', () => {
    const args = buildCommandArgs('merge', {
      mergeInputs: ['clip1.mp4', 'clip2.mp4'],
      output: 'merged.mp4',
      reencode: true
    })
    expect(args).toContain('merge')
    expect(args).toContain('clip1.mp4')
    expect(args).toContain('clip2.mp4')
    expect(args).toContain('--output')
    expect(args).toContain('merged.mp4')
    expect(args).toContain('--reencode')
  })
})

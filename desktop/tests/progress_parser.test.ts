import { describe, it, expect } from 'vitest'
import { ProgressParser } from '../utils/progress_parser'

describe('ProgressParser', () => {
  it('parses valid start event', () => {
    const raw = '{"event":"start","subcommand":"compress","input":"in.mp4","output":"out.mp4"}'
    const ev = ProgressParser.parseLine(raw)
    expect(ev).not.toBeNull()
    expect(ev?.event).toBe('start')
    expect(ev?.subcommand).toBe('compress')
    expect(ev?.output).toBe('out.mp4')
  })

  it('parses valid progress event with data', () => {
    const raw = JSON.stringify({
      event: 'progress',
      data: {
        percent: 45.2,
        fps: 60.5,
        speed: '2.1x',
        eta_s: 14,
        pass: 2
      }
    })
    const ev = ProgressParser.parseLine(raw)
    expect(ev).not.toBeNull()
    expect(ev?.event).toBe('progress')
    expect(ev?.data?.percent).toBe(45.2)
    expect(ev?.data?.fps).toBe(60.5)
    expect(ev?.data?.speed).toBe('2.1x')
    expect(ev?.data?.eta_s).toBe(14)
    expect(ev?.data?.pass).toBe(2)
  })

  it('parses done event with bytes and output path', () => {
    const raw = '{"event":"done","output":"final.mp4","bytes":15482910}'
    const ev = ProgressParser.parseLine(raw)
    expect(ev).not.toBeNull()
    expect(ev?.event).toBe('done')
    expect(ev?.bytes).toBe(15482910)
    expect(ev?.output).toBe('final.mp4')
  })

  it('parses error event', () => {
    const raw = '{"event":"error","code":2,"message":"Computed bitrate too low for resolution"}'
    const ev = ProgressParser.parseLine(raw)
    expect(ev).not.toBeNull()
    expect(ev?.event).toBe('error')
    expect(ev?.code).toBe(2)
    expect(ev?.message).toContain('Computed bitrate too low')
  })

  it('ignores invalid non-JSON lines', () => {
    expect(ProgressParser.parseLine('')).toBeNull()
    expect(ProgressParser.parseLine('ffmpeg version 6.1.1 Copyright (c) 2000-2023')).toBeNull()
    expect(ProgressParser.parseLine('[libx264 @ 0x123] frame= 100 fps=30')).toBeNull()
  })

  it('handles fragmented chunks across feed() calls', () => {
    const parser = new ProgressParser()
    const part1 = '{"event":"progress","data":{"percent":10.5'
    const part2 = ',"speed":"1.5x"}}\n{"event":"warning","message":"frame drop"}\n{"event":"done"'

    const evs1 = parser.feed(part1)
    expect(evs1.length).toBe(0) // incomplete line buffered

    const evs2 = parser.feed(part2)
    expect(evs2.length).toBe(2) // 1st line completed and 2nd line
    expect(evs2[0].event).toBe('progress')
    expect(evs2[0].data?.percent).toBe(10.5)
    expect(evs2[1].event).toBe('warning')
    expect(evs2[1].message).toBe('frame drop')

    const part3 = ',"output":"out.mp4","bytes":500}\n'
    const evs3 = parser.feed(part3)
    expect(evs3.length).toBe(1)
    expect(evs3[0].event).toBe('done')
    expect(evs3[0].bytes).toBe(500)
  })

  it('flushes incomplete final line if flush() is called', () => {
    const parser = new ProgressParser()
    parser.feed('{"event":"done","output":"out.mp4","bytes":1234}')
    const flushed = parser.flush()
    expect(flushed.length).toBe(1)
    expect(flushed[0].event).toBe('done')
  })
})

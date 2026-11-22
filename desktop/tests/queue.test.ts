import { describe, it, expect } from 'vitest'
import { QueueManager, type SidecarRunner } from '../stores/queue'

describe('QueueManager', () => {
  it('enqueues a job and updates status to queued', () => {
    const queue = new QueueManager()
    const job = queue.addJob({
      subcommand: 'compress',
      name: 'compress-test.mp4',
      args: ['compress', '-i', 'in.mp4', '-o', 'out.mp4'],
      inputPath: 'in.mp4',
      outputPath: 'out.mp4'
    })

    expect(job.status).toBe('queued')
    expect(job.progress).toBe(0)
    expect(queue.jobs.value.length).toBe(1)
  })

  it('runs job through mock runner to completion with progress events', async () => {
    const mockRunner: SidecarRunner = async (args, onData) => {
      // simulate stream of json events
      onData('{"event":"start","subcommand":"compress","input":"in.mp4","output":"out.mp4"}\n')
      onData('{"event":"progress","data":{"percent":50,"fps":30,"speed":"1.8x","eta_s":5,"pass":1}}\n')
      onData('{"event":"done","output":"out.mp4","bytes":99999}\n')
      return { code: 0 }
    }

    const queue = new QueueManager(mockRunner)
    const job = queue.addJob({
      subcommand: 'compress',
      name: 'test.mp4',
      args: ['compress', '-i', 'in.mp4', '-o', 'out.mp4'],
      inputPath: 'in.mp4',
      outputPath: 'out.mp4'
    })

    // wait for async job processing
    await new Promise((r) => setTimeout(r, 50))

    expect(job.status).toBe('completed')
    expect(job.progress).toBe(100)
    expect(job.outputBytes).toBe(99999)
  })

  it('handles error exit code and records error message', async () => {
    const mockRunner: SidecarRunner = async (_args, onData) => {
      onData('{"event":"error","code":2,"message":"Bitrate too low"}\n')
      return { code: 2 }
    }

    const queue = new QueueManager(mockRunner)
    const job = queue.addJob({
      subcommand: 'compress',
      name: 'fail.mp4',
      args: ['compress', '-i', 'fail.mp4'],
      inputPath: 'fail.mp4',
      outputPath: 'out.mp4'
    })

    await new Promise((r) => setTimeout(r, 50))

    expect(job.status).toBe('error')
    expect(job.errorMessage).toContain('Bitrate too low')
  })

  it('cancels a queued job before it starts', async () => {
    // runner that blocks forever
    const mockRunner: SidecarRunner = () => new Promise(() => {})

    const queue = new QueueManager(mockRunner)
    const job1 = queue.addJob({
      subcommand: 'compress',
      name: 'job1.mp4',
      args: ['compress'],
      inputPath: 'j1.mp4',
      outputPath: 'o1.mp4'
    })
    const job2 = queue.addJob({
      subcommand: 'cut',
      name: 'job2.mp4',
      args: ['cut'],
      inputPath: 'j2.mp4',
      outputPath: 'o2.mp4'
    })

    expect(job1.status).toBe('running')
    expect(job2.status).toBe('queued')

    const cancelled = await queue.cancelJob(job2.id)
    expect(cancelled).toBe(true)
    expect(job2.status).toBe('cancelled')
  })

  it('retries a failed or cancelled job', async () => {
    let callCount = 0
    const mockRunner: SidecarRunner = async () => {
      callCount++
      if (callCount === 1) {
        return { code: 1 }
      }
      return { code: 0 }
    }

    const queue = new QueueManager(mockRunner)
    const job = queue.addJob({
      subcommand: 'extract-audio',
      name: 'audio.mp4',
      args: ['extract-audio'],
      inputPath: 'audio.mp4',
      outputPath: 'audio.mp3'
    })

    await new Promise((r) => setTimeout(r, 50))
    expect(job.status).toBe('error')

    // Retry the job
    const retried = queue.retryJob(job.id)
    expect(retried).toBe(true)

    await new Promise((r) => setTimeout(r, 50))
    expect(job.status).toBe('completed')
    expect(callCount).toBe(2)
  })

  it('processes batch jobs sequentially', async () => {
    const executed: string[] = []
    const mockRunner: SidecarRunner = async (args) => {
      const idx = args.indexOf('-i')
      const name = idx >= 0 ? args[idx + 1] : 'unknown'
      executed.push(name)
      return { code: 0 }
    }

    const queue = new QueueManager(mockRunner)
    queue.addBatch('convert', [
      { name: 'clip1', inputPath: 'c1.mov', outputPath: 'c1.mp4', args: ['convert', '-i', 'c1.mov'] },
      { name: 'clip2', inputPath: 'c2.mov', outputPath: 'c2.mp4', args: ['convert', '-i', 'c2.mov'] },
      { name: 'clip3', inputPath: 'c3.mov', outputPath: 'c3.mp4', args: ['convert', '-i', 'c3.mov'] }
    ])

    await new Promise((r) => setTimeout(r, 100))
    expect(executed).toEqual(['c1.mov', 'c2.mov', 'c3.mov'])
    expect(queue.jobs.value.every((j) => j.status === 'completed')).toBe(true)
  })
})

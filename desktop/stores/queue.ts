import { ref, computed } from 'vue'
import type { Job, JobStatus, ProgressEvent, Subcommand } from '../types/toolkit'
import { ProgressParser } from '../utils/progress_parser'

export interface SidecarProcess {
  kill: () => Promise<void>
}

export type SidecarRunner = (
  args: string[],
  onData: (chunk: string) => void,
  onError: (chunk: string) => void
) => Promise<{ code: number; process?: SidecarProcess }>

export class QueueManager {
  public jobs = ref<Job[]>([])
  public activeJobId = ref<string | null>(null)
  private runner: SidecarRunner | null = null
  private activeProcess: SidecarProcess | null = null

  constructor(runner?: SidecarRunner) {
    if (runner) {
      this.runner = runner
    }
  }

  public setRunner(runner: SidecarRunner) {
    this.runner = runner
    this.processNext()
  }

  public get activeJob(): Job | undefined {
    return this.jobs.value.find((j) => j.id === this.activeJobId.value)
  }

  public addJob(params: {
    subcommand: Subcommand
    name: string
    args: string[]
    inputPath: string
    outputPath: string
  }): Job {
    const job: Job = {
      id: `job-${Date.now()}-${Math.random().toString(36).substring(2, 7)}`,
      subcommand: params.subcommand,
      name: params.name,
      args: params.args,
      inputPath: params.inputPath,
      outputPath: params.outputPath,
      status: 'queued',
      progress: 0,
      logs: [],
      createdAt: Date.now()
    }
    this.jobs.value.push(job)
    this.processNext()
    return job
  }

  public addBatch(
    subcommand: Subcommand,
    files: Array<{ name: string; inputPath: string; outputPath: string; args: string[] }>
  ): Job[] {
    const created: Job[] = []
    for (const f of files) {
      const job: Job = {
        id: `job-${Date.now()}-${Math.random().toString(36).substring(2, 7)}`,
        subcommand,
        name: f.name,
        args: f.args,
        inputPath: f.inputPath,
        outputPath: f.outputPath,
        status: 'queued',
        progress: 0,
        logs: [],
        createdAt: Date.now()
      }
      this.jobs.value.push(job)
      created.push(job)
    }
    this.processNext()
    return created
  }

  public async cancelJob(id: string): Promise<boolean> {
    const job = this.jobs.value.find((j) => j.id === id)
    if (!job) return false

    if (job.status === 'queued') {
      job.status = 'cancelled'
      job.logs.push('[UI] Job cancelled before execution.')
      return true
    }

    if (job.status === 'running' && this.activeJobId.value === id) {
      job.status = 'cancelled'
      job.logs.push('[UI] Cancellation requested. Terminating process...')
      if (this.activeProcess) {
        try {
          await this.activeProcess.kill()
        } catch (e: any) {
          job.logs.push(`[UI] Kill failed or already terminated: ${e?.message ?? e}`)
        }
        this.activeProcess = null
      }
      this.activeJobId.value = null
      this.processNext()
      return true
    }

    return false
  }

  public retryJob(id: string): boolean {
    const job = this.jobs.value.find((j) => j.id === id)
    if (!job) return false
    if (job.status !== 'error' && job.status !== 'cancelled') return false

    job.status = 'queued'
    job.progress = 0
    job.fps = undefined
    job.speed = undefined
    job.etaSeconds = undefined
    job.errorMessage = undefined
    job.logs.push(`[UI] Job re-queued at ${new Date().toLocaleTimeString()}`)
    this.processNext()
    return true
  }

  public clearFinished() {
    this.jobs.value = this.jobs.value.filter(
      (j) => j.status === 'queued' || j.status === 'running'
    )
  }

  public async processNext() {
    if (this.activeJobId.value !== null) {
      // Already running a job
      return
    }

    const nextJob = this.jobs.value.find((j) => j.status === 'queued')
    if (!nextJob) {
      return
    }

    if (!this.runner) {
      // Runner is not registered yet (e.g. app mounting); leave job queued
      return
    }

    this.activeJobId.value = nextJob.id
    nextJob.status = 'running'
    nextJob.startedAt = Date.now()
    nextJob.logs.push(`[UI] Started processing job: ${nextJob.name}`)

    const parser = new ProgressParser()

    try {
      const result = await this.runner(
        nextJob.args,
        (dataChunk: string) => {
          nextJob.logs.push(dataChunk)
          const events = parser.feed(dataChunk)
          for (const ev of events) {
            this.handleProgressEvent(nextJob, ev)
          }
        },
        (errorChunk: string) => {
          nextJob.logs.push(`[STDERR] ${errorChunk}`)
          const trimmed = errorChunk.trim()
          if (trimmed && !nextJob.errorMessage) {
            const lines = trimmed.split('\n').map((l) => l.trim()).filter(Boolean)
            const errLine = lines.find((l) => l.toLowerCase().includes('error:') || l.startsWith('[ERROR') || l.startsWith('[FATAL'))
            nextJob.lastStderr = errLine || lines[lines.length - 1]
          }
        }
      )

      // Flush remaining events
      const remainingEvents = parser.flush()
      for (const ev of remainingEvents) {
        this.handleProgressEvent(nextJob, ev)
      }

      if (result.code === 0 && nextJob.status === 'running') {
        nextJob.status = 'completed'
        nextJob.progress = 100
        nextJob.finishedAt = Date.now()
        nextJob.logs.push('[UI] Job completed successfully.')
      } else if (nextJob.status === 'running') {
        nextJob.status = 'error'
        nextJob.finishedAt = Date.now()
        if (!nextJob.errorMessage) {
          nextJob.errorMessage = nextJob.lastStderr || `Process exited with code ${result.code}`
        }
      }
    } catch (err: any) {
      if (nextJob.status !== 'cancelled') {
        nextJob.status = 'error'
        nextJob.errorMessage = err?.message ?? String(err)
        nextJob.finishedAt = Date.now()
        nextJob.logs.push(`[FATAL] Exception during execution: ${nextJob.errorMessage}`)
      }
    } finally {
      this.activeProcess = null
      this.activeJobId.value = null
      // Automatically advance to the next queued job
      this.processNext()
    }
  }

  public handleProgressEvent(job: Job, ev: ProgressEvent) {
    switch (ev.event) {
      case 'start':
        job.logs.push(`[EVENT:START] ${ev.subcommand ?? ''} -> ${ev.output ?? ''}`)
        break
      case 'progress':
        if (ev.data) {
          job.progress = Math.min(100, Math.max(0, ev.data.percent))
          job.fps = ev.data.fps
          job.speed = ev.data.speed
          job.etaSeconds = ev.data.eta_s
          job.pass = ev.data.pass
        }
        break
      case 'warning':
        job.logs.push(`[WARNING] ${ev.message}`)
        break
      case 'done':
        job.status = 'completed'
        job.progress = 100
        job.outputBytes = ev.bytes
        job.logs.push(`[EVENT:DONE] Output saved: ${ev.output} (${ev.bytes ?? 0} bytes)`)
        break
      case 'error':
        job.status = 'error'
        job.errorMessage = ev.message ?? `Error code ${ev.code}`
        job.logs.push(`[EVENT:ERROR] Code ${ev.code}: ${ev.message}`)
        break
    }
  }
}

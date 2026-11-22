export type Subcommand =
  | 'compress'
  | 'trim-silence'
  | 'shorts'
  | 'convert'
  | 'extract-audio'
  | 'cut'
  | 'merge'
  | 'gif'
  | 'speed'
  | 'strip-meta'
  | 'thumbs'

export type JobStatus = 'queued' | 'running' | 'completed' | 'cancelled' | 'error'

export interface ProgressPayload {
  percent: number
  fps?: number
  speed?: string
  eta_s?: number
  pass?: number
}

export interface ProgressEvent {
  event: 'start' | 'progress' | 'warning' | 'done' | 'error'
  subcommand?: string
  input?: string
  output?: string
  data?: ProgressPayload
  message?: string
  code?: number
  bytes?: number
  timestamp?: number
}

export interface Job {
  id: string
  subcommand: Subcommand
  name: string
  args: string[]
  inputPath: string
  outputPath: string
  status: JobStatus
  progress: number
  fps?: number
  speed?: string
  etaSeconds?: number
  pass?: number
  outputBytes?: number
  errorMessage?: string
  logs: string[]
  createdAt: number
  startedAt?: number
  finishedAt?: number
}

export interface AppSettings {
  outputDirectory: string
  overwritePolicy: boolean
  customFfmpegPath: string
  customFfprobePath: string
  licenseKey: string
  theme: 'dark' | 'light'
}

export interface SelfCheckResult {
  passed: boolean
  ffmpegVersion?: string
  ffprobeVersion?: string
  ffmpegPath?: string
  ffprobePath?: string
  encoders?: string[]
  rawOutput?: string
  error?: string
}

export interface LicenseStatus {
  active: boolean
  licenseKey: string
  type: 'trial' | 'commercial' | 'unregistered'
  expiresAt?: string
  message: string
}

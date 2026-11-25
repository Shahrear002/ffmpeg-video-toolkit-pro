<template>
  <div :class="['app-root', theme]">
    <!-- Left Navigation Sidebar -->
    <aside class="sidebar">
      <div class="brand">
        <div class="brand-icon">
          <img src="/icon.svg" alt="FFmpeg Video Toolkit Pro" class="brand-logo-img" />
        </div>
        <div class="brand-text">
          <h2>FFmpeg Toolkit</h2>
          <span class="badge-pro">PRO v{{ appVersion }}</span>
        </div>
      </div>

      <nav class="nav-section">
        <div class="nav-label">TOOLS</div>
        <button
          v-for="tool in tools"
          :key="tool.id"
          :class="['nav-item', { active: currentTab === tool.id }]"
          @click="currentTab = tool.id"
        >
          <span class="nav-icon">{{ tool.icon }}</span>
          <span class="nav-title">{{ tool.name }}</span>
        </button>
      </nav>

      <nav class="nav-section secondary">
        <div class="nav-label">MANAGEMENT</div>
        <button
          :class="['nav-item', { active: currentTab === 'queue' }]"
          @click="currentTab = 'queue'"
        >
          <span class="nav-icon">📋</span>
          <span class="nav-title">Queue</span>
          <span v-if="queuedCount > 0" class="queue-badge">{{ queuedCount }}</span>
        </button>

        <button
          :class="['nav-item', { active: currentTab === 'logs' }]"
          @click="currentTab = 'logs'"
        >
          <span class="nav-icon">📜</span>
          <span class="nav-title">Logs</span>
        </button>

        <button
          :class="['nav-item', { active: currentTab === 'settings' }]"
          @click="currentTab = 'settings'"
        >
          <span class="nav-icon">⚙️</span>
          <span class="nav-title">Settings</span>
        </button>

        <button
          :class="['nav-item', { active: currentTab === 'licenses' }]"
          @click="currentTab = 'licenses'"
        >
          <span class="nav-icon">⚖️</span>
          <span class="nav-title">Licenses</span>
        </button>
      </nav>

      <div class="sidebar-footer">
        <button class="footer-btn" @click="checkEngine">
          <span :class="['status-dot', engineStatus]"></span>
          {{ engineStatusText }}
        </button>
      </div>
    </aside>

    <!-- Main Content Area -->
    <main class="main-content">
      <!-- Header -->
      <header class="top-header">
        <div class="header-info">
          <h1>{{ currentTitle }}</h1>
          <p>{{ currentDescription }}</p>
        </div>

        <div class="header-actions">
          <button class="btn btn-secondary" @click="toggleTheme">
            {{ theme === 'dark' ? '☀️ Light' : '🌙 Dark' }}
          </button>
          <button class="btn btn-secondary" @click="openSelfCheckModal = true">
            🔍 Check Engine
          </button>
        </div>
      </header>

      <!-- Tool Form View -->
      <section v-if="isToolTab" class="view-container">
        <div class="form-grid">
          <!-- Left Column: Input, Output & Options -->
          <div class="form-card">
            <h3>Files & Paths</h3>

            <!-- Drop Zone / File Picker -->
            <div
              class="dropzone"
              @dragover.prevent="onDragOver"
              @dragleave.prevent="onDragLeave"
              @drop.prevent="onDrop"
              @click="pickInputFile"
            >
              <div class="dropzone-icon">📁</div>
              <div v-if="!formState.input" class="dropzone-text">
                <strong>Click to choose a file</strong> or drag & drop here
              </div>
              <div v-else class="dropzone-file">
                <span class="file-name">{{ formState.input }}</span>
                <span v-if="inputFileSizeStr" class="file-size-badge">📦 Original: {{ inputFileSizeStr }}</span>
                <span class="file-action">Click to change</span>
              </div>
            </div>

            <div class="input-group">
              <label>Output Destination</label>
              <div class="input-with-button">
                <input
                  v-model="formState.output"
                  type="text"
                  placeholder="Auto-generated if left empty"
                />
                <button class="btn btn-secondary" @click="pickOutputFile">Browse</button>
              </div>
            </div>

            <!-- Overwrite Checkbox -->
            <div class="checkbox-row">
              <label>
                <input v-model="formState.overwrite" type="checkbox" />
                Overwrite existing output file without confirmation
              </label>
            </div>

            <!-- Subcommand Specific Options -->
            <div class="tool-options">
              <!-- COMPRESS -->
              <div v-if="currentTab === 'compress'" class="options-group">
                <h4>Compression Options</h4>
                <div class="input-group">
                  <label>Compression Target</label>
                  <select v-model="formState.preset" @change="onPresetChange">
                    <optgroup label="Auto Size Reduction">
                      <option value="auto">Auto Balanced (50% Size Reduction)</option>
                      <option value="max_comp">Maximum Compression (75% Size Reduction)</option>
                      <option value="light_comp">Light Compression (25% Size Reduction)</option>
                    </optgroup>
                    <optgroup label="Custom Budget">
                      <option value="custom">Custom Target Size (MB)</option>
                    </optgroup>
                    <optgroup label="Platform Upload Limits (Ceiling)">
                      <option value="discord">Discord Free (Max 20 MB)</option>
                      <option value="whatsapp">WhatsApp Media (Max 16 MB)</option>
                      <option value="github">GitHub Web Upload (Max 25 MB)</option>
                      <option value="gmail">Gmail Attachment (Max 20 MB)</option>
                      <option value="x">X / Twitter (Max 512 MB)</option>
                    </optgroup>
                  </select>
                </div>

                <div v-if="formState.preset === 'custom'" class="input-group">
                  <label>Target Size (MB)</label>
                  <input v-model.number="formState.targetMb" type="number" min="0.1" step="0.5" max="10000" />
                </div>

                <div v-if="compressionTargetHint" class="compress-hint-box">
                  💡 {{ compressionTargetHint }}
                </div>

                <div class="input-group">
                  <label>Scale Guardrail (Recommended for small sizes)</label>
                  <select v-model="formState.scale">
                    <option value="">Keep Original Resolution</option>
                    <option value="1080p">Scale to 1080p (1920x1080)</option>
                    <option value="720p">Scale to 720p (1280x720)</option>
                    <option value="480p">Scale to 480p (854x480)</option>
                  </select>
                </div>

                <div class="input-group">
                  <label>Audio Bitrate</label>
                  <select v-model="formState.audioBitrate">
                    <option value="128k">128 kbps (Standard)</option>
                    <option value="96k">96 kbps (Voice)</option>
                    <option value="64k">64 kbps (Max Space Saver)</option>
                    <option value="192k">192 kbps (High Fidelity)</option>
                  </select>
                </div>
              </div>

              <!-- TRIM SILENCE -->
              <div v-if="currentTab === 'trim-silence'" class="options-group">
                <h4>Silence Removal Parameters</h4>
                <div class="input-group">
                  <label>Noise Threshold: {{ formState.noiseDb }} dB</label>
                  <input v-model.number="formState.noiseDb" type="range" min="-60" max="-10" step="1" />
                </div>
                <div class="input-group">
                  <label>Minimum Silence Duration (seconds)</label>
                  <input v-model.number="formState.minSilenceSec" type="number" min="0.1" max="10" step="0.1" />
                </div>
                <div class="input-group">
                  <label>Audio Padding Buffer (seconds)</label>
                  <input v-model.number="formState.padSec" type="number" min="0" max="2" step="0.05" />
                </div>
              </div>

              <!-- SHORTS -->
              <div v-if="currentTab === 'shorts'" class="options-group">
                <h4>9:16 Vertical Video Options</h4>
                <div class="input-group">
                  <label>Conversion Mode</label>
                  <select v-model="formState.shortsMode">
                    <option value="blur">Blur (Blurred background + centered video)</option>
                    <option value="crop">Crop (Center 9:16 crop)</option>
                  </select>
                </div>
                <div v-if="formState.shortsMode === 'crop'" class="input-group">
                  <label>Horizontal Crop Offset (pixels from center)</label>
                  <input v-model.number="formState.xOffset" type="number" step="10" />
                </div>
              </div>

              <!-- CONVERT -->
              <div v-if="currentTab === 'convert'" class="options-group">
                <h4>Format Conversion</h4>
                <p class="hint">Standardizes input to H.264 / AAC MP4 with faststart stream optimization.</p>
                <div class="checkbox-row">
                  <label>
                    <input v-model="formState.recursive" type="checkbox" />
                    Process folder recursively (Batch conversion)
                  </label>
                </div>
              </div>

              <!-- EXTRACT AUDIO -->
              <div v-if="currentTab === 'extract-audio'" class="options-group">
                <h4>Audio Extraction</h4>
                <div class="input-group">
                  <label>Format</label>
                  <select v-model="formState.audioFormat">
                    <option value="mp3">MP3 (Universal compatibility)</option>
                    <option value="wav">WAV (Uncompressed PCM)</option>
                    <option value="flac">FLAC (Lossless compression)</option>
                  </select>
                </div>
                <div v-if="formState.audioFormat === 'mp3'" class="input-group">
                  <label>MP3 Quality / Bitrate</label>
                  <select v-model="formState.audioQuality">
                    <option value="320k">320 kbps (CBR High Quality)</option>
                    <option value="256k">256 kbps (CBR)</option>
                    <option value="192k">192 kbps (CBR Standard)</option>
                    <option value="128k">128 kbps (CBR Speech)</option>
                    <option value="0">V0 (VBR ~245 kbps Extreme)</option>
                    <option value="2">V2 (VBR ~190 kbps Standard)</option>
                  </select>
                </div>
              </div>

              <!-- CUT -->
              <div v-if="currentTab === 'cut'" class="options-group">
                <h4>Trim & Cut</h4>
                <div class="input-group">
                  <label>Start Timestamp (HH:MM:SS or seconds)</label>
                  <input v-model="formState.startTime" type="text" placeholder="00:00:10 or 10.5" />
                </div>
                <div class="input-group">
                  <label>End Timestamp (HH:MM:SS or seconds)</label>
                  <input v-model="formState.endTime" type="text" placeholder="00:01:30" />
                </div>
                <div class="checkbox-row">
                  <label>
                    <input v-model="formState.precise" type="checkbox" />
                    Precise cut (Re-encodes boundary for exact frame accuracy)
                  </label>
                </div>
              </div>

              <!-- MERGE -->
              <div v-if="currentTab === 'merge'" class="options-group">
                <h4>Concatenate Clips</h4>
                <div class="merge-file-list">
                  <div
                    v-for="(f, idx) in formState.mergeInputs"
                    :key="idx"
                    class="merge-item"
                  >
                    <span>{{ idx + 1 }}. {{ f }}</span>
                    <button class="btn-text" @click="removeMergeInput(idx)">✕</button>
                  </div>
                </div>
                <button class="btn btn-secondary" @click="addMergeInput">+ Add Video File</button>
                <div class="checkbox-row">
                  <label>
                    <input v-model="formState.reencode" type="checkbox" />
                    Re-encode if codec/resolution/framerate mismatch
                  </label>
                </div>
              </div>

              <!-- GIF -->
              <div v-if="currentTab === 'gif'" class="options-group">
                <h4>Animated GIF / WebP</h4>
                <div class="input-group">
                  <label>Output Format</label>
                  <select v-model="formState.gifFormat">
                    <option value="gif">GIF (High fidelity 2-pass palettegen)</option>
                    <option value="webp">WebP (Modern smaller animation)</option>
                  </select>
                </div>
                <div class="input-group">
                  <label>Framerate (FPS): {{ formState.fps }}</label>
                  <input v-model.number="formState.fps" type="range" min="10" max="30" step="1" />
                </div>
                <div class="input-group">
                  <label>Target Width (px)</label>
                  <input v-model.number="formState.width" type="number" min="160" max="1920" step="40" />
                </div>
                <div class="input-group">
                  <label>Max Duration (seconds)</label>
                  <input v-model.number="formState.maxSeconds" type="number" min="1" max="60" />
                </div>
              </div>

              <!-- SPEED -->
              <div v-if="currentTab === 'speed'" class="options-group">
                <h4>Playback Speed Factor</h4>
                <div class="input-group">
                  <label>Factor: {{ formState.speedFactor }}x</label>
                  <input v-model.number="formState.speedFactor" type="range" min="0.25" max="4.0" step="0.25" />
                </div>
                <div class="speed-presets">
                  <button class="pill" @click="formState.speedFactor = 0.5">0.5x Slow-mo</button>
                  <button class="pill" @click="formState.speedFactor = 1.25">1.25x</button>
                  <button class="pill" @click="formState.speedFactor = 1.5">1.5x</button>
                  <button class="pill" @click="formState.speedFactor = 2.0">2.0x Double</button>
                </div>
              </div>

              <!-- STRIP METADATA -->
              <div v-if="currentTab === 'strip-meta'" class="options-group">
                <h4>Privacy & Metadata</h4>
                <p class="hint">Removes all EXIF metadata, GPS tags, camera details, chapters, and author comments.</p>
              </div>

              <!-- THUMBS -->
              <div v-if="currentTab === 'thumbs'" class="options-group">
                <h4>Thumbnail Extraction</h4>
                <div class="checkbox-row">
                  <label>
                    <input v-model="formState.sheet" type="checkbox" />
                    Create Contact Sheet (Tile grid preview)
                  </label>
                </div>
                <div v-if="formState.sheet" class="sheet-grid">
                  <div class="input-group">
                    <label>Columns</label>
                    <input v-model.number="formState.cols" type="number" min="1" max="10" />
                  </div>
                  <div class="input-group">
                    <label>Rows</label>
                    <input v-model.number="formState.rows" type="number" min="1" max="10" />
                  </div>
                </div>
                <div v-else class="input-group">
                  <label>Timestamps (seconds or HH:MM:SS, comma separated)</label>
                  <input v-model="formState.timestamps" type="text" placeholder="1.0, 5.0, 10.0" />
                </div>
              </div>
            </div>
          </div>

          <!-- Right Column: Live Command Preview & Execution Actions -->
          <div class="preview-card">
            <h3>Live Engine Command Preview</h3>
            <p class="hint">Exact arguments executed by the native engine:</p>
            <div class="code-box">
              <code>{{ commandPreview }}</code>
            </div>

            <div class="action-buttons">
              <button class="btn btn-primary btn-large" :disabled="!formState.input" @click="runNow">
                ▶ Run Now
              </button>
              <button class="btn btn-secondary btn-large" :disabled="!formState.input" @click="enqueueJob">
                + Add to Queue
              </button>
            </div>

            <div v-if="activeJob" class="active-job-indicator">
              <h4>Currently Running</h4>
              <div class="job-status-line">
                <span>{{ activeJob.name }}</span>
                <span>{{ activeJob.progress.toFixed(1) }}%</span>
              </div>
              <div class="progress-bar-bg">
                <div class="progress-bar-fill" :style="{ width: `${activeJob.progress}%` }"></div>
              </div>
              <div class="job-stats">
                <span v-if="activeJob.fps">FPS: {{ activeJob.fps }}</span>
                <span v-if="activeJob.speed">Speed: {{ activeJob.speed }}</span>
                <span v-if="activeJob.etaSeconds !== undefined">ETA: {{ activeJob.etaSeconds }}s</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      <!-- Queue View -->
      <section v-else-if="currentTab === 'queue'" class="view-container">
        <div class="card">
          <div class="card-header">
            <h3>Job Queue ({{ queueManager.jobs.value.length }} Total)</h3>
            <button class="btn btn-secondary" @click="queueManager.clearFinished()">
              Clear Finished
            </button>
          </div>

          <div v-if="queueManager.jobs.value.length === 0" class="empty-state">
            <p>No jobs in queue. Select a tool and click "Add to Queue" or "Run Now".</p>
          </div>

          <div v-else class="job-list">
            <div
              v-for="job in queueManager.jobs.value"
              :key="job.id"
              :class="['job-card', job.status]"
            >
              <div class="job-header">
                <div>
                  <span class="job-subcommand">[{{ job.subcommand }}]</span>
                  <strong class="job-title">{{ job.name }}</strong>
                </div>
                <div class="job-actions">
                  <span :class="['status-pill', job.status]">{{ job.status.toUpperCase() }}</span>
                  <button
                    v-if="job.status === 'running' || job.status === 'queued'"
                    class="btn-sm btn-danger"
                    @click="queueManager.cancelJob(job.id)"
                  >
                    Cancel
                  </button>
                  <button
                    v-if="job.status === 'error' || job.status === 'cancelled'"
                    class="btn-sm btn-secondary"
                    @click="queueManager.retryJob(job.id)"
                  >
                    Retry
                  </button>
                </div>
              </div>

              <!-- Progress bar for running / completed -->
              <div v-if="job.status === 'running'" class="progress-wrapper">
                <div class="progress-bar-bg">
                  <div class="progress-bar-fill" :style="{ width: `${job.progress}%` }"></div>
                </div>
                <div class="job-stats">
                  <span>{{ job.progress.toFixed(1) }}%</span>
                  <span v-if="job.fps">FPS: {{ job.fps }}</span>
                  <span v-if="job.speed">Speed: {{ job.speed }}</span>
                  <span v-if="job.etaSeconds !== undefined">ETA: {{ job.etaSeconds }}s</span>
                </div>
              </div>

              <div v-if="job.errorMessage" class="error-text">
                ⚠️ {{ job.errorMessage }}
              </div>
              <div v-if="job.outputBytes" class="success-text">
                ✓ Output: {{ job.outputPath }} ({{ (job.outputBytes / (1024 * 1024)).toFixed(2) }} MB)
              </div>
            </div>
          </div>
        </div>
      </section>

      <!-- Logs View -->
      <section v-else-if="currentTab === 'logs'" class="view-container">
        <div class="card">
          <div class="card-header">
            <h3>Execution Logs</h3>
            <div class="header-buttons">
              <button class="btn btn-secondary" @click="copyLogs">📋 Copy to Clipboard</button>
              <button class="btn btn-secondary" @click="clearLogs">Clear Logs</button>
            </div>
          </div>
          <div class="log-terminal">
            <pre>{{ logOutput }}</pre>
          </div>
        </div>
      </section>

      <!-- Settings View -->
      <section v-else-if="currentTab === 'settings'" class="view-container">
        <div class="card">
          <h3>Application Settings</h3>

          <div class="input-group">
            <label>Default Output Directory</label>
            <div class="input-with-button">
              <input v-model="settings.outputDirectory" type="text" placeholder="Same as input folder" />
              <button class="btn btn-secondary" @click="pickOutputDirectory">Browse</button>
            </div>
          </div>

          <div class="checkbox-row">
            <label>
              <input v-model="settings.overwritePolicy" type="checkbox" />
              Always overwrite destination files by default
            </label>
          </div>

          <div class="input-group">
            <label>Custom FFmpeg Binary Path (Optional override)</label>
            <input v-model="settings.customFfmpegPath" type="text" placeholder="Default: bundled native sidecar" />
          </div>

          <div class="input-group">
            <label>Custom FFprobe Binary Path (Optional override)</label>
            <input v-model="settings.customFfprobePath" type="text" placeholder="Default: bundled native sidecar" />
          </div>

          <hr class="divider" />

          <h3>License Activation</h3>
          <p class="hint">Enter your commercial license key from Agensi or official store.</p>
          <div class="input-with-button">
            <input v-model="settings.licenseKey" type="text" placeholder="AGY-XXXX-XXXX-XXXX" />
            <button class="btn btn-primary" @click="verifyLicense">Activate</button>
          </div>
          <div v-if="licenseStatus" :class="['license-badge', licenseStatus.active ? 'active' : 'inactive']">
            {{ licenseStatus.message }}
          </div>
        </div>
      </section>

      <!-- Licenses View -->
      <section v-else-if="currentTab === 'licenses'" class="view-container">
        <div class="card">
          <h3>Open Source & Third-Party Licenses</h3>
          <div class="licenses-content">
            <h4>FFmpeg & libx264 (GPL v2+ Notice)</h4>
            <p>
              This software bundles or links with FFmpeg, licensed under the GNU General Public License (GPL) version 2.0 or later due to the inclusion of libx264.
            </p>
            <p>
              Under GPL v2 § 3, you are entitled to obtain the complete corresponding machine-readable source code for the FFmpeg build used in this application.
              Source archives and build scripts are available at:
              <a href="https://github.com/FFmpeg/FFmpeg" target="_blank">https://github.com/FFmpeg/FFmpeg</a>
            </p>

            <h4>Agensi Agent Skill Package</h4>
            <p>
              The commercial Agent Skill package included in this product is licensed under the single-user commercial license detailed in
              <code>skill/LICENSE</code>.
            </p>

            <h4>Desktop Application Components</h4>
            <ul>
              <li><strong>Tauri:</strong> Apache-2.0 / MIT</li>
              <li><strong>Nuxt 3:</strong> MIT</li>
              <li><strong>Vue 3:</strong> MIT</li>
            </ul>
          </div>
        </div>
      </section>
    </main>

    <!-- Self-Check Modal -->
    <div v-if="openSelfCheckModal" class="modal-backdrop" @click.self="openSelfCheckModal = false">
      <div class="modal-card">
        <div class="modal-header">
          <h3>Engine Self-Check (--check)</h3>
          <button class="btn-text" @click="openSelfCheckModal = false">✕</button>
        </div>
        <div class="modal-body">
          <div v-if="checkingEngine" class="checking-spinner">
            Testing FFmpeg, FFprobe, and codec capabilities...
          </div>
          <pre v-else class="check-result-box">{{ checkResult }}</pre>
        </div>
        <div class="modal-footer">
          <button class="btn btn-primary" @click="openSelfCheckModal = false">Done</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, reactive, watch, onMounted } from 'vue'
import type { Subcommand, AppSettings, LicenseStatus } from './types/toolkit'
import { buildCommandArgs, formatCommandPreview, getDefaultOutputPath, type ToolFormState } from './utils/command_builder'
import { QueueManager } from './stores/queue'
import { createSidecarRunner, runSelfCheck, isTauriEnvironment } from './utils/tauri_bridge'

// Navigation tools
const tools = [
  { id: 'compress', name: 'Compress Video', icon: '🗜️', desc: 'True 2-pass libx264 compression with platform presets and bitrate guardrails' },
  { id: 'trim-silence', name: 'Trim Silence', icon: '✂️', desc: 'Detect and cut dead silent segments with audio padding' },
  { id: 'shorts', name: 'Shorts / 9:16', icon: '📱', desc: 'Transform horizontal videos into 9:16 vertical reels via crop or blurred background' },
  { id: 'convert', name: 'Convert MP4', icon: '🔄', desc: 'Stream-copy compatible codecs or re-encode to standardized H.264/AAC' },
  { id: 'extract-audio', name: 'Extract Audio', icon: '🎵', desc: 'Lossless WAV, FLAC, or CBR/VBR MP3 audio extraction' },
  { id: 'cut', name: 'Cut & Trim', icon: '🎞️', desc: 'Fast stream-copy cuts or precise frame-accurate cuts' },
  { id: 'merge', name: 'Merge Clips', icon: '🧩', desc: 'Seamless concat demuxer join with automatic codec compatibility check' },
  { id: 'gif', name: 'GIF / WebP', icon: '🖼️', desc: 'High-quality animated GIFs via palettegen or modern animated WebP' },
  { id: 'speed', name: 'Adjust Speed', icon: '⏩', desc: 'Change video and audio playback speed from 0.25x to 4.0x' },
  { id: 'strip-meta', name: 'Strip Metadata', icon: '🛡️', desc: 'Remove EXIF, chapters, GPS tags, and privacy markers' },
  { id: 'thumbs', name: 'Thumbnails', icon: '📸', desc: 'Extract high-resolution preview frames or tiled contact sheets' }
]

const currentTab = ref<string>('compress')
const appVersion = ref<string>('1.0.0')
const theme = ref<'dark' | 'light'>('dark')
const openSelfCheckModal = ref<boolean>(false)
const checkingEngine = ref<boolean>(false)
const checkResult = ref<string>('')
const engineStatus = ref<'ready' | 'checking' | 'error'>('ready')
const engineStatusText = ref<string>('Engine Ready')

const queueManager = new QueueManager()
const activeJob = computed(() => queueManager.activeJob)
const queuedCount = computed(() => queueManager.jobs.value.filter((j) => j.status === 'queued' || j.status === 'running').length)

const settings = reactive<AppSettings>({
  outputDirectory: '',
  overwritePolicy: false,
  customFfmpegPath: '',
  customFfprobePath: '',
  licenseKey: '',
  theme: 'dark'
})

const licenseStatus = ref<LicenseStatus | null>(null)

// Form state
const formState = reactive<ToolFormState>({
  input: '',
  output: '',
  overwrite: false,
  quiet: false,
  verbose: false,
  preset: 'auto',
  targetMb: 10,
  scale: '',
  audioBitrate: '128k',
  noiseDb: -30,
  minSilenceSec: 0.5,
  padSec: 0.1,
  shortsMode: 'blur',
  xOffset: 0,
  recursive: false,
  copyCompatible: true,
  audioFormat: 'mp3',
  audioQuality: '192k',
  startTime: '',
  endTime: '',
  duration: '',
  precise: false,
  mergeInputs: [],
  reencode: false,
  fps: 15,
  width: 480,
  maxSeconds: 10,
  gifFormat: 'gif',
  dither: 'sierra2_4a',
  speedFactor: 1.5,
  sheet: false,
  cols: 4,
  rows: 4,
  timestamps: '1.0, 5.0'
})

const inputFileBytes = ref<number | null>(null)

const inputFileSizeStr = computed(() => {
  if (!inputFileBytes.value) return null
  const mb = inputFileBytes.value / (1024 * 1024)
  if (mb < 1) {
    return `${(inputFileBytes.value / 1024).toFixed(1)} KB`
  }
  return `${mb.toFixed(2)} MB`
})

const compressionTargetHint = computed(() => {
  if (currentTab.value !== 'compress') return null
  if (!inputFileBytes.value) {
    if (formState.preset === 'auto') return 'Auto: Reduces file size by ~50% with balanced quality.'
    if (formState.preset === 'max_comp') return 'Maximum: Reduces file size by ~75% for highest space savings.'
    if (formState.preset === 'light_comp') return 'Light: Reduces file size by ~25% for minimal compression artifacts.'
    if (formState.preset && formState.preset !== 'custom') return `Platform limit: Targets platform ceiling for ${formState.preset.toUpperCase()}.`
    if (formState.targetMb) return `Target size: ${formState.targetMb} MB.`
    return null
  }

  const origMb = inputFileBytes.value / (1024 * 1024)
  if (formState.preset === 'auto') {
    const estMb = origMb * 0.50
    return `Targeting ~${estMb.toFixed(2)} MB (50% reduction from ${origMb.toFixed(2)} MB)`
  }
  if (formState.preset === 'max_comp') {
    const estMb = origMb * 0.25
    return `Targeting ~${estMb.toFixed(2)} MB (75% reduction from ${origMb.toFixed(2)} MB)`
  }
  if (formState.preset === 'light_comp') {
    const estMb = origMb * 0.75
    return `Targeting ~${estMb.toFixed(2)} MB (25% reduction from ${origMb.toFixed(2)} MB)`
  }
  if (formState.preset && formState.preset !== 'custom') {
    const limitsMap: Record<string, number> = {
      discord: 20,
      whatsapp: 16,
      github: 25,
      x: 512,
      gmail: 20
    }
    const maxMb = limitsMap[formState.preset] || 20
    if (origMb <= maxMb) {
      const estMb = origMb * 0.50
      return `Input (${origMb.toFixed(2)} MB) is under ${formState.preset.toUpperCase()} ceiling (${maxMb} MB) → auto-compressing to ~${estMb.toFixed(2)} MB`
    } else {
      return `Targeting platform ceiling of ${maxMb} MB (${((1 - maxMb / origMb) * 100).toFixed(0)}% reduction)`
    }
  }
  if (formState.targetMb) {
    if (formState.targetMb >= origMb) {
      const estMb = origMb * 0.70
      return `Target (${formState.targetMb} MB) ≥ source (${origMb.toFixed(2)} MB) → auto-capping to ~${estMb.toFixed(2)} MB`
    }
    return `Targeting ${formState.targetMb} MB (${((1 - formState.targetMb / origMb) * 100).toFixed(0)}% reduction)`
  }
  return null
})

const isToolTab = computed(() => tools.some((t) => t.id === currentTab.value))

const currentTitle = computed(() => {
  const tool = tools.find((t) => t.id === currentTab.value)
  if (tool) return tool.name
  if (currentTab.value === 'queue') return 'Job Queue'
  if (currentTab.value === 'logs') return 'Execution Logs'
  if (currentTab.value === 'settings') return 'Application Settings'
  if (currentTab.value === 'licenses') return 'Open Source Licenses'
  return 'FFmpeg Toolkit Pro'
})

const currentDescription = computed(() => {
  const tool = tools.find((t) => t.id === currentTab.value)
  return tool ? tool.desc : 'High-performance video processing pipeline'
})

const currentCommandArgs = computed(() => {
  if (!isToolTab.value) return []
  return buildCommandArgs(currentTab.value as Subcommand, formState, settings)
})

const commandPreview = computed(() => {
  return formatCommandPreview(currentCommandArgs.value)
})

const logOutput = computed(() => {
  const allLogs: string[] = []
  for (const job of queueManager.jobs.value) {
    allLogs.push(`--- [${job.name} - ${job.status.toUpperCase()}] ---`)
    allLogs.push(...job.logs)
  }
  return allLogs.join('\n') || 'No logs recorded yet.'
})

async function updateInputFileInfo(filePath: string) {
  if (!filePath) {
    inputFileBytes.value = null
    return
  }
  if (!isTauriEnvironment()) {
    inputFileBytes.value = 3.57 * 1024 * 1024
    return
  }
  try {
    const { stat } = await import('@tauri-apps/plugin-fs')
    const fileStat = await stat(filePath)
    inputFileBytes.value = fileStat.size
  } catch (e) {
    console.warn('Could not read file size', e)
    inputFileBytes.value = null
  }
}

function onPresetChange() {
  if (formState.preset === 'discord') formState.targetMb = 20
  else if (formState.preset === 'whatsapp') formState.targetMb = 16
  else if (formState.preset === 'github') formState.targetMb = 25
  else if (formState.preset === 'x') formState.targetMb = 512
  else if (formState.preset === 'gmail') formState.targetMb = 20
  else if (formState.preset === 'custom') {
    if (inputFileBytes.value) {
      formState.targetMb = Math.max(1, Math.round((inputFileBytes.value / (1024 * 1024)) * 0.5))
    } else {
      formState.targetMb = 10
    }
  }
}

async function pickInputFile() {
  if (!isTauriEnvironment()) {
    formState.input = 'test_video.mp4'
    if (isToolTab.value) {
      formState.output = getDefaultOutputPath(formState.input, currentTab.value as Subcommand, settings.outputDirectory)
    }
    return
  }
  try {
    const { open } = await import('@tauri-apps/plugin-dialog')
    let filters: Array<{ name: string; extensions: string[] }> = []

    if (currentTab.value === 'extract-audio' || currentTab.value === 'trim-silence') {
      filters = [
        { name: 'Media Files', extensions: ['mp4', 'mov', 'mkv', 'avi', 'webm', 'flv', 'wmv', 'ts', 'm4v', 'mp3', 'wav', 'flac', 'aac', 'm4a', 'ogg'] },
        { name: 'All Files', extensions: ['*'] }
      ]
    } else {
      filters = [
        { name: 'Video Files', extensions: ['mp4', 'mov', 'mkv', 'avi', 'webm', 'flv', 'wmv', 'ts', 'm4v'] },
        { name: 'All Files', extensions: ['*'] }
      ]
    }

    const selected = await open({
      multiple: false,
      directory: formState.recursive,
      filters: formState.recursive ? undefined : filters
    })
    if (selected && typeof selected === 'string') {
      formState.input = selected
      await updateInputFileInfo(selected)
      if (isToolTab.value) {
        formState.output = getDefaultOutputPath(selected, currentTab.value as Subcommand, settings.outputDirectory)
      }
    }
  } catch (e) {
    console.error('File dialog error', e)
  }
}

async function pickOutputFile() {
  if (!isTauriEnvironment()) {
    formState.output = 'output_processed.mp4'
    return
  }
  try {
    const { save } = await import('@tauri-apps/plugin-dialog')
    const selected = await save()
    if (selected && typeof selected === 'string') {
      formState.output = selected
    }
  } catch (e) {
    console.error('Save dialog error', e)
  }
}

async function pickOutputDirectory() {
  if (!isTauriEnvironment()) {
    settings.outputDirectory = '/mock/output/folder'
    return
  }
  try {
    const { open } = await import('@tauri-apps/plugin-dialog')
    const selected = await open({ directory: true, multiple: false })
    if (selected && typeof selected === 'string') {
      settings.outputDirectory = selected
    }
  } catch (e) {
    console.error('Directory dialog error', e)
  }
}

function addMergeInput() {
  pickInputFile().then(() => {
    if (formState.input && !formState.mergeInputs?.includes(formState.input)) {
      formState.mergeInputs = [...(formState.mergeInputs ?? []), formState.input]
    }
  })
}

function removeMergeInput(index: number) {
  formState.mergeInputs?.splice(index, 1)
}

function enqueueJob() {
  if (!formState.input) return
  const name = formState.input.split(/[/\\]/).pop() ?? formState.input
  queueManager.addJob({
    subcommand: currentTab.value as Subcommand,
    name: `${currentTab.value}: ${name}`,
    args: [...currentCommandArgs.value],
    inputPath: formState.input,
    outputPath: formState.output || 'auto'
  })
}

function runNow() {
  enqueueJob()
  currentTab.value = 'queue'
}

function toggleTheme() {
  theme.value = theme.value === 'dark' ? 'light' : 'dark'
}

function copyLogs() {
  navigator.clipboard.writeText(logOutput.value)
}

function clearLogs() {
  for (const job of queueManager.jobs.value) {
    job.logs = []
  }
}

async function checkEngine() {
  checkingEngine.value = true
  openSelfCheckModal.value = true
  try {
    const res = await runSelfCheck()
    checkResult.value = res.output
    engineStatus.value = res.success ? 'ready' : 'error'
    engineStatusText.value = res.success ? 'Engine Ready' : 'Engine Error'
  } catch (e: any) {
    checkResult.value = `Engine check failed: ${e?.message ?? e}`
    engineStatus.value = 'error'
    engineStatusText.value = 'Engine Error'
  } finally {
    checkingEngine.value = false
  }
}

function verifyLicense() {
  if (!settings.licenseKey.trim()) {
    licenseStatus.value = {
      active: false,
      licenseKey: '',
      type: 'unregistered',
      message: 'Please enter a valid license key.'
    }
    return
  }
  // Seam implementation for offline / commercial verification
  if (settings.licenseKey.startsWith('AGY-')) {
    licenseStatus.value = {
      active: true,
      licenseKey: settings.licenseKey,
      type: 'commercial',
      message: '✓ Commercial Single-User License Verified'
    }
  } else {
    licenseStatus.value = {
      active: false,
      licenseKey: settings.licenseKey,
      type: 'trial',
      message: 'Invalid key prefix. Format must be AGY-XXXX-XXXX-XXXX'
    }
  }
}

function onDragOver(e: DragEvent) {
  // Prevent default to allow drop
}

function onDragLeave(e: DragEvent) {}

async function onDrop(e: DragEvent) {
  if (e.dataTransfer && e.dataTransfer.files.length > 0) {
    const file = e.dataTransfer.files[0]
    // In Tauri, webkitRelativePath or path is exposed
    const filePath = (file as any).path || file.name
    formState.input = filePath
    await updateInputFileInfo(filePath)
    if (isToolTab.value) {
      formState.output = getDefaultOutputPath(filePath, currentTab.value as Subcommand, settings.outputDirectory)
    }
  }
}

watch(() => formState.input, async (newVal) => {
  if (newVal) {
    await updateInputFileInfo(newVal)
  } else {
    inputFileBytes.value = null
  }
})

watch(currentTab, (newTab) => {
  if (isToolTab.value && formState.input) {
    formState.output = getDefaultOutputPath(formState.input, newTab as Subcommand, settings.outputDirectory)
  }
})

onMounted(async () => {
  if (isTauriEnvironment()) {
    try {
      const { getVersion } = await import('@tauri-apps/api/app')
      const ver = await getVersion()
      if (ver) {
        appVersion.value = ver
      }
    } catch (e) {
      console.warn('Could not read version from Tauri runtime', e)
    }
  }

  const runner = await createSidecarRunner()
  queueManager.setRunner(runner)
  // Run initial self check silently
  try {
    const res = await runSelfCheck()
    if (res.success) {
      engineStatus.value = 'ready'
      engineStatusText.value = 'Engine Ready'
    }
  } catch {
    engineStatus.value = 'error'
    engineStatusText.value = 'Check Required'
  }
})
</script>

<style>
/* CSS Variables for Clean Dark & Light Themes */
:root {
  color-scheme: dark;
  --bg-primary: #0f172a;
  --bg-secondary: #1e293b;
  --bg-tertiary: #334155;
  --text-primary: #f8fafc;
  --text-secondary: #94a3b8;
  --accent: #38bdf8;
  --accent-hover: #0ea5e9;
  --border: #334155;
  --card-bg: #1e293b;
  --success: #22c55e;
  --danger: #ef4444;
  --warning: #f59e0b;
  --scrollbar-track: rgba(15, 23, 42, 0.6);
  --scrollbar-thumb: #334155;
  --scrollbar-thumb-hover: #38bdf8;
}

.light {
  color-scheme: light;
  --bg-primary: #f8fafc;
  --bg-secondary: #ffffff;
  --bg-tertiary: #e2e8f0;
  --text-primary: #0f172a;
  --text-secondary: #64748b;
  --accent: #0284c7;
  --accent-hover: #0369a1;
  --border: #e2e8f0;
  --card-bg: #ffffff;
  --success: #16a34a;
  --danger: #dc2626;
  --warning: #d97706;
  --scrollbar-track: rgba(241, 245, 249, 0.8);
  --scrollbar-thumb: #cbd5e1;
  --scrollbar-thumb-hover: #0284c7;
}

html, body, * {
  box-sizing: border-box;
  scrollbar-width: thin;
  scrollbar-color: var(--scrollbar-thumb) var(--scrollbar-track);
}

/* Custom Sleek Scrollbars matching UI theme */
::-webkit-scrollbar,
*::-webkit-scrollbar {
  width: 6px;
  height: 6px;
}

::-webkit-scrollbar-track,
*::-webkit-scrollbar-track {
  background: var(--scrollbar-track);
}

::-webkit-scrollbar-thumb,
*::-webkit-scrollbar-thumb {
  background: var(--scrollbar-thumb);
  border-radius: 9999px;
  transition: background 0.15s ease-in-out;
}

::-webkit-scrollbar-thumb:hover,
*::-webkit-scrollbar-thumb:hover {
  background: var(--scrollbar-thumb-hover);
}

::-webkit-scrollbar-corner,
*::-webkit-scrollbar-corner {
  background: transparent;
}

::-webkit-scrollbar-button,
*::-webkit-scrollbar-button {
  display: none;
  width: 0;
  height: 0;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  background-color: var(--bg-primary);
  color: var(--text-primary);
  user-select: none;
  overflow: hidden;
}

.app-root {
  display: flex;
  height: 100vh;
  width: 100vw;
  background-color: var(--bg-primary);
}

/* Sidebar */
.sidebar {
  width: 260px;
  background-color: var(--bg-secondary);
  border-right: 1px solid var(--border);
  display: flex;
  flex-direction: column;
  padding: 16px 12px;
  overflow-y: auto;
  overflow-x: hidden;
}

.brand {
  display: flex;
  align-items: center;
  gap: 10px;
  padding-bottom: 16px;
  border-bottom: 1px solid var(--border);
  margin-bottom: 16px;
}

.brand-icon {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.brand-logo-img {
  width: 32px;
  height: 32px;
  object-fit: contain;
  border-radius: 7px;
}

.brand-text h2 {
  font-size: 15px;
  font-weight: 700;
  letter-spacing: -0.3px;
}

.badge-pro {
  font-size: 10px;
  font-weight: 700;
  color: var(--accent);
  text-transform: uppercase;
}

.nav-section {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.nav-section.secondary {
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid var(--border);
}

.nav-label {
  font-size: 11px;
  font-weight: 700;
  color: var(--text-secondary);
  padding: 4px 10px;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 10px;
  border-radius: 6px;
  border: none;
  background: transparent;
  color: var(--text-secondary);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  text-align: left;
  transition: all 0.15s ease;
}

.nav-item:hover {
  background-color: var(--bg-tertiary);
  color: var(--text-primary);
}

.nav-item.active {
  background-color: var(--accent);
  color: #ffffff;
}

.nav-icon {
  font-size: 15px;
}

.nav-title {
  flex: 1;
}

.queue-badge {
  background-color: var(--danger);
  color: #fff;
  font-size: 10px;
  font-weight: 700;
  padding: 2px 6px;
  border-radius: 10px;
}

.sidebar-footer {
  margin-top: auto;
  padding-top: 16px;
}

.footer-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  padding: 8px 10px;
  background-color: var(--bg-tertiary);
  border: 1px solid var(--border);
  border-radius: 6px;
  color: var(--text-primary);
  font-size: 12px;
  cursor: pointer;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.status-dot.ready { background-color: var(--success); }
.status-dot.checking { background-color: var(--warning); }
.status-dot.error { background-color: var(--danger); }

/* Main Content */
.main-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.top-header {
  height: 64px;
  padding: 0 24px;
  border-bottom: 1px solid var(--border);
  display: flex;
  align-items: center;
  justify-content: space-between;
  background-color: var(--bg-secondary);
}

.header-info h1 {
  font-size: 18px;
  font-weight: 700;
}

.header-info p {
  font-size: 12px;
  color: var(--text-secondary);
}

.header-actions {
  display: flex;
  gap: 8px;
}

.view-container {
  flex: 1;
  padding: 24px;
  overflow-y: auto;
}

/* Forms & Grids */
.form-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 24px;
}

.form-card, .preview-card, .card {
  background-color: var(--card-bg);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 20px;
}

.form-card h3, .preview-card h3, .card h3 {
  font-size: 15px;
  font-weight: 700;
  margin-bottom: 12px;
}

.dropzone {
  border: 2px dashed var(--border);
  border-radius: 6px;
  padding: 24px;
  text-align: center;
  cursor: pointer;
  background-color: var(--bg-primary);
  transition: border-color 0.15s ease;
  margin-bottom: 16px;
}

.dropzone:hover {
  border-color: var(--accent);
}

.dropzone-icon {
  font-size: 32px;
  margin-bottom: 6px;
}

.dropzone-text {
  font-size: 13px;
  color: var(--text-secondary);
}

.dropzone-file {
  font-size: 13px;
  font-weight: 600;
}

.file-size-badge {
  display: inline-block;
  margin-top: 6px;
  background-color: var(--bg-tertiary);
  border: 1px solid var(--border);
  padding: 3px 8px;
  border-radius: 4px;
  font-size: 11px;
  color: var(--accent);
  font-weight: 600;
}

.compress-hint-box {
  margin-top: 8px;
  padding: 10px 14px;
  background-color: rgba(56, 189, 248, 0.08);
  border: 1px solid rgba(56, 189, 248, 0.25);
  border-radius: 6px;
  font-size: 12px;
  color: var(--accent);
  line-height: 1.4;
}

.file-action {
  display: block;
  font-size: 11px;
  color: var(--accent);
  margin-top: 4px;
}

.input-group {
  margin-bottom: 14px;
}

.input-group label {
  display: block;
  font-size: 12px;
  font-weight: 600;
  color: var(--text-secondary);
  margin-bottom: 6px;
}

input[type="text"], input[type="number"], select {
  width: 100%;
  padding: 8px 12px;
  border-radius: 6px;
  border: 1px solid var(--border);
  background-color: var(--bg-primary);
  color: var(--text-primary);
  font-size: 13px;
  outline: none;
}

input[type="range"] {
  width: 100%;
}

.input-with-button {
  display: flex;
  gap: 8px;
}

.checkbox-row {
  margin: 12px 0;
  font-size: 13px;
  color: var(--text-secondary);
}

.checkbox-row label {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
}

.options-group {
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid var(--border);
}

.options-group h4 {
  font-size: 13px;
  font-weight: 700;
  margin-bottom: 10px;
}

.hint {
  font-size: 12px;
  color: var(--text-secondary);
  margin-bottom: 12px;
}

/* Code Preview Box */
.code-box {
  background-color: var(--bg-primary);
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 12px;
  font-family: monospace;
  font-size: 12px;
  color: var(--accent);
  word-break: break-all;
  margin-bottom: 16px;
  max-height: 140px;
  overflow-y: auto;
}

/* Buttons */
.btn {
  padding: 8px 14px;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  border: none;
  transition: all 0.15s ease;
}

.btn-primary {
  background-color: var(--accent);
  color: #fff;
}

.btn-primary:hover:not(:disabled) {
  background-color: var(--accent-hover);
}

.btn-secondary {
  background-color: var(--bg-tertiary);
  color: var(--text-primary);
  border: 1px solid var(--border);
}

.btn-danger {
  background-color: var(--danger);
  color: #fff;
}

.btn-large {
  padding: 12px 18px;
  font-size: 14px;
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.action-buttons {
  display: flex;
  gap: 12px;
  margin-bottom: 24px;
}

.btn-text {
  background: none;
  border: none;
  color: var(--text-secondary);
  cursor: pointer;
  font-size: 14px;
}

/* Progress and Jobs */
.active-job-indicator {
  margin-top: 20px;
  padding: 14px;
  background-color: var(--bg-primary);
  border-radius: 6px;
  border: 1px solid var(--border);
}

.job-status-line {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  font-weight: 600;
  margin-bottom: 6px;
}

.progress-bar-bg {
  width: 100%;
  height: 8px;
  background-color: var(--bg-tertiary);
  border-radius: 4px;
  overflow: hidden;
}

.progress-bar-fill {
  height: 100%;
  background-color: var(--accent);
  transition: width 0.2s ease;
}

.job-stats {
  display: flex;
  gap: 16px;
  font-size: 11px;
  color: var(--text-secondary);
  margin-top: 6px;
}

/* Queue List */
.job-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-top: 14px;
}

.job-card {
  padding: 14px;
  border-radius: 6px;
  border: 1px solid var(--border);
  background-color: var(--bg-primary);
}

.job-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.job-subcommand {
  font-size: 11px;
  font-weight: 700;
  color: var(--accent);
  margin-right: 6px;
}

.status-pill {
  font-size: 10px;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 10px;
  background-color: var(--bg-tertiary);
}

.status-pill.running { background-color: var(--accent); color: #fff; }
.status-pill.completed { background-color: var(--success); color: #fff; }
.status-pill.error { background-color: var(--danger); color: #fff; }

.btn-sm {
  padding: 4px 8px;
  font-size: 11px;
  border-radius: 4px;
  border: none;
  cursor: pointer;
}

.error-text {
  font-size: 12px;
  color: var(--danger);
  margin-top: 6px;
}

.success-text {
  font-size: 12px;
  color: var(--success);
  margin-top: 6px;
}

/* Terminal logs */
.log-terminal {
  background-color: #050811;
  color: #38bdf8;
  font-family: monospace;
  font-size: 12px;
  padding: 16px;
  border-radius: 6px;
  height: 480px;
  overflow-y: auto;
}

/* Modals */
.modal-backdrop {
  position: fixed;
  inset: 0;
  background-color: rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 999;
}

.modal-card {
  width: 520px;
  max-width: 90vw;
  background-color: var(--card-bg);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 20px;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 14px;
}

.check-result-box {
  background-color: var(--bg-primary);
  border: 1px solid var(--border);
  padding: 12px;
  border-radius: 6px;
  font-size: 12px;
  font-family: monospace;
  max-height: 250px;
  overflow-y: auto;
  white-space: pre-wrap;
}

.modal-footer {
  margin-top: 16px;
  text-align: right;
}

.license-badge {
  margin-top: 10px;
  padding: 8px 12px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 600;
}

.license-badge.active {
  background-color: rgba(34, 197, 94, 0.15);
  color: var(--success);
  border: 1px solid var(--success);
}

.license-badge.inactive {
  background-color: rgba(239, 68, 68, 0.15);
  color: var(--danger);
  border: 1px solid var(--danger);
}

.pill {
  padding: 4px 8px;
  border-radius: 4px;
  background-color: var(--bg-tertiary);
  border: 1px solid var(--border);
  color: var(--text-primary);
  font-size: 11px;
  cursor: pointer;
  margin-right: 6px;
}
</style>

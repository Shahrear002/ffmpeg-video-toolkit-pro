import type { ProgressEvent } from '../types/toolkit'

export class ProgressParser {
  private buffer: string = ''

  /**
   * Feed a raw chunk of text from stdout or stderr into the parser.
   * Returns an array of parsed valid ProgressEvents.
   */
  public feed(chunk: string): ProgressEvent[] {
    this.buffer += chunk
    const lines = this.buffer.split(/\r?\n/)
    // The last element is either empty (if ended with newline) or an incomplete line
    this.buffer = lines.pop() ?? ''

    const events: ProgressEvent[] = []
    for (const line of lines) {
      const trimmed = line.trim()
      if (!trimmed) continue

      const parsed = ProgressParser.parseLine(trimmed)
      if (parsed) {
        events.push(parsed)
      }
    }
    return events
  }

  /**
   * Flush any remaining line in buffer.
   */
  public flush(): ProgressEvent[] {
    if (!this.buffer.trim()) {
      this.buffer = ''
      return []
    }
    const line = this.buffer.trim()
    this.buffer = ''
    const parsed = ProgressParser.parseLine(line)
    return parsed ? [parsed] : []
  }

  /**
   * Parse a single string line into a ProgressEvent if valid JSON matching our schema.
   */
  public static parseLine(line: string): ProgressEvent | null {
    if (!line.startsWith('{') || !line.endsWith('}')) {
      return null
    }

    try {
      const obj = JSON.parse(line)
      if (typeof obj === 'object' && obj !== null && typeof obj.event === 'string') {
        const validEvents = ['start', 'progress', 'warning', 'done', 'error']
        if (validEvents.includes(obj.event)) {
          return {
            event: obj.event,
            subcommand: obj.subcommand,
            input: obj.input,
            output: obj.output,
            data: obj.data,
            message: obj.message,
            code: obj.code,
            bytes: obj.bytes,
            timestamp: obj.timestamp ?? Date.now()
          }
        }
      }
    } catch {
      // Ignore JSON parse errors for non-JSON console lines
    }

    return null
  }
}

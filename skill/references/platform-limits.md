# Platform Video Limits Reference

> Automatically generated from `engine/data/platform_limits.json` on 2026-11-19.

| Platform Preset | Target Size | Max Bytes | Last Verified | Status | Official Documentation |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `discord` | 20 MB | 20,971,520 | 2026-11-19 | VERIFIED | [Documentation](https://discord.com) |
| `discord-nitro-basic` | 50 MB | 52,428,800 | 2026-11-19 | VERIFIED | [Documentation](https://discord.com) |
| `discord-nitro` | 1 GB | 1,073,741,824 | 2026-11-19 | VERIFIED | [Documentation](https://discord.com) |
| `whatsapp` | 16 MB | 16,777,216 | 2026-11-19 | VERIFIED | [Documentation](https://faq.whatsapp.com) |
| `whatsapp-doc` | 2 GB | 2,147,483,648 | 2026-11-19 | VERIFIED | [Documentation](https://faq.whatsapp.com) |
| `github` | 25 MB | 26,214,400 | 2026-11-19 | VERIFIED | [Documentation](https://docs.github.com/en/get-started/writing-on-github/working-with-advanced-formatting/attaching-files) |
| `github-push` | 100 MB | 104,857,600 | 2026-11-19 | VERIFIED | [Documentation](https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-large-files-on-github) |
| `x-twitter` | 512 MB | 536,870,912 | 2026-11-19 | VERIFIED | [Documentation](https://help.twitter.com) |
| `email-gmail` | 20 MB | 20,971,520 | 2026-11-19 | VERIFIED | [Documentation](https://support.google.com/mail/answer/6584) |
| `slack` | 1 GB | 1,073,741,824 | 2026-11-19 | VERIFIED | [Documentation](https://slack.com/help/articles/201726587-Upload-files-to-Slack) |

## Usage in Engine & Agent

To target any platform preset directly with the toolkit, use `--preset`:

```bash
python scripts/video_toolkit.py compress input.mp4 output.mp4 --preset discord
python scripts/video_toolkit.py compress input.mp4 output.mp4 --preset whatsapp
python scripts/video_toolkit.py compress input.mp4 output.mp4 --preset github
```

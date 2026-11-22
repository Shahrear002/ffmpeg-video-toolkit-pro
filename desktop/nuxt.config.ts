// https://nuxt.com/docs/api/configuration/nuxt-config
export default defineNuxtConfig({
  compatibilityDate: '2024-11-01',
  devtools: { enabled: false },
  ssr: false,
  telemetry: false,
  app: {
    head: {
      title: 'FFmpeg Video Toolkit Pro',
      meta: [
        { charset: 'utf-8' },
        { name: 'viewport', content: 'width=device-width, initial-scale=1' }
      ]
    }
  },
  typescript: {
    strict: true,
    typeCheck: false
  },
  nitro: {
    output: {
      publicDir: '.output/public'
    }
  }
})

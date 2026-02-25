import { defineConfig } from '@playwright/test'

export default defineConfig({
  testDir: './tests',
  /* Maximum time one test can run — generous because LLM responses are slow */
  timeout: 60_000,
  /* Expect assertions timeout */
  expect: { timeout: 30_000 },
  /* Run tests sequentially — they share backend state */
  fullyParallel: false,
  /* Fail the build on CI if you accidentally left test.only in the source code */
  forbidOnly: !!process.env.CI,
  retries: 0,
  /* Reporter */
  reporter: 'html',

  use: {
    baseURL: 'http://localhost:5173',
    /* Collect trace on first retry for debugging */
    trace: 'on-first-retry',
    /* Screenshot on failure */
    screenshot: 'only-on-failure',
  },

  projects: [
    {
      name: 'chromium',
      use: { browserName: 'chromium' },
    },
  ],

  /* Start frontend dev server automatically.
   * Backend (port 8000) must be running separately. */
  webServer: {
    command: 'npm run dev',
    url: 'http://localhost:5173',
    reuseExistingServer: !process.env.CI,
    timeout: 15_000,
  },
})

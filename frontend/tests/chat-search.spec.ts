import { test, expect } from '@playwright/test'
import { sendMessage, waitForAssistantResponse } from './helpers'

test.describe('Chat product search', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/')
    // Wait for the initial greeting message to appear
    await expect(page.getByTestId('message-assistant')).toHaveCount(1)
  })

  test('user can search for products via chat', async ({ page }) => {
    await sendMessage(page, 'Show me running shoes')

    const response = await waitForAssistantResponse(page)

    // The assistant should mention at least one product with a price
    expect(response).toMatch(/\$\d+/)
    // Should have at least 2 messages now: greeting + new response
    await expect(page.getByTestId('message-assistant')).toHaveCount(2, {
      timeout: 5_000,
    })
  })

  test('brand-specific search returns relevant results', async ({ page }) => {
    await sendMessage(page, 'Show me Nike products')

    const response = await waitForAssistantResponse(page)

    // Response should reference Nike or contain product information
    const lowerResponse = response.toLowerCase()
    const hasProducts = /\$\d+/.test(response)
    const mentionsBrand = lowerResponse.includes('nike')
    expect(hasProducts || mentionsBrand).toBe(true)
  })
})

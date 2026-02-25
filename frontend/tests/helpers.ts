import { type Page, expect } from '@playwright/test'

/**
 * Type a message in the chat input and send it.
 */
export async function sendMessage(page: Page, text: string) {
  const input = page.getByTestId('chat-input')
  const sendBtn = page.getByTestId('send-button')

  await input.fill(text)
  await sendBtn.click()

  // Wait for the input to become disabled (loading started)
  await expect(input).toBeDisabled({ timeout: 5_000 })
}

/**
 * Wait for the assistant to finish streaming its response.
 * Returns the text content of the latest assistant message.
 */
export async function waitForAssistantResponse(page: Page): Promise<string> {
  const sendBtn = page.getByTestId('send-button')

  // Wait for the send button to be re-enabled — signals streaming is done
  await expect(sendBtn).toBeEnabled({ timeout: 45_000 })

  // Grab the last assistant message
  const assistantMessages = page.getByTestId('message-assistant')
  const count = await assistantMessages.count()
  const lastMessage = assistantMessages.nth(count - 1)

  const text = (await lastMessage.textContent()) ?? ''
  return text.trim()
}

# E2E Testing with Playwright

## Overview
Playwright E2E tests for the frontend, covering chat-based product search flows.

## Setup

### Prerequisites
- Backend running on port 8000 with database seeded
- Frontend running on port 5173 (or let Playwright start it automatically)

### Install
```bash
cd frontend
npm install
npx playwright install chromium
```

## Running Tests

```bash
# Headless (CI-friendly)
cd frontend && npm run test:e2e

# Headed (watch the browser)
cd frontend && npm run test:e2e:headed

# Run a specific test file
cd frontend && npx playwright test tests/chat-search.spec.ts
```

## Project Structure

```
frontend/
  playwright.config.ts    # Playwright configuration
  tests/
    helpers.ts            # Reusable utilities (sendMessage, waitForAssistantResponse)
    chat-search.spec.ts   # Product search E2E tests
```

## Configuration Details

| Setting | Value | Reason |
|---------|-------|--------|
| Browser | Chromium only | Speed during development |
| Test timeout | 60s | LLM responses can be slow |
| Expect timeout | 30s | SSE streaming needs generous waits |
| Parallel | false | Tests share backend state |
| Web server | `npm run dev` | Auto-starts frontend if not running |

## Test Selectors

We use `data-testid` attributes for stable selectors:

| Element | data-testid |
|---------|-------------|
| Chat input | `chat-input` |
| Send button | `send-button` |
| Message list | `message-list` |
| User messages | `message-user` |
| Assistant messages | `message-assistant` |

## Helper Utilities

### `sendMessage(page, text)`
Types text into the chat input and clicks Send. Waits for the input to become disabled (loading started).

### `waitForAssistantResponse(page)`
Waits for the send button to become re-enabled (streaming complete). Returns the text content of the last assistant message.

## Adding New Tests

1. Import helpers: `import { sendMessage, waitForAssistantResponse } from './helpers'`
2. Navigate to `/` in `beforeEach`
3. Use `sendMessage` to interact, `waitForAssistantResponse` to wait for the agent
4. Assert on the response text content

## Edge Cases from Test Plan

Reference: `docs/edge-case-test-plan.md`

Currently implemented:
- Test 6.6: Brand-specific search (Nike products)
- Basic product search ("Show me running shoes")

Future tests to add:
- Empty cart operations
- Multi-turn conversation context
- Price range queries
- Out-of-stock handling

## ADDED Requirements

### Requirement: Agent context includes stored user memories
The system SHALL load the current user's stored memories from the database and include them in the agent's system prompt before each conversation turn.

#### Scenario: User with stored preferences starts a new conversation
- **WHEN** a user with stored memories (e.g., "prefers Patagonia jackets", "shoe size 10") sends a message
- **THEN** the agent's system prompt includes a "Known user preferences" section with those memories

#### Scenario: User with no stored preferences starts a conversation
- **WHEN** a new user with no stored memories sends a message
- **THEN** the agent's system prompt does not include a preferences section and behaves as it does today

### Requirement: Memory injection respects token budget
The system SHALL cap the injected memory context to a maximum of 500 tokens. When memories exceed this limit, the system SHALL prioritize memories with the highest confidence scores.

#### Scenario: User has many stored preferences
- **WHEN** a user has 30+ stored memories that would exceed 500 tokens
- **THEN** only the highest-confidence memories fitting within 500 tokens are included in the system prompt

### Requirement: Agent uses memories to personalize recommendations
The agent SHALL reference stored user preferences when making product recommendations, without the user needing to repeat their preferences.

#### Scenario: Returning user searches for products
- **WHEN** a user with stored preference "prefers waterproof gear" asks "show me some jackets"
- **THEN** the agent prioritizes waterproof jackets in its search and response

#### Scenario: Agent acknowledges known preferences
- **WHEN** the agent uses a stored memory to inform its response
- **THEN** the agent MAY naturally reference the preference (e.g., "Since you prefer Patagonia, here are some options...")

### Requirement: Agent can explicitly query user preferences via tool
The system SHALL provide a `get_user_preferences` tool that the agent can call to retrieve stored memories filtered by category.

#### Scenario: Agent looks up size preferences before recommending
- **WHEN** the agent calls `get_user_preferences` with category="size"
- **THEN** the tool returns all stored size memories for the current user

#### Scenario: Agent queries all preferences
- **WHEN** the agent calls `get_user_preferences` with no category filter
- **THEN** the tool returns all stored memories for the current user, grouped by category

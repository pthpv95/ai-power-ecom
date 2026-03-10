## ADDED Requirements

### Requirement: System automatically extracts user preferences from conversations
The system SHALL analyze completed agent conversations and extract user preference facts (brand affinity, size, budget range, category interest, style preference) without requiring explicit user action.

#### Scenario: User mentions a brand preference during product search
- **WHEN** the user says "I usually go with Patagonia for jackets" during a conversation
- **THEN** the system extracts and stores a memory with category=brand, key="jackets", value="Patagonia" for that user

#### Scenario: User specifies a budget constraint
- **WHEN** the user says "I don't want to spend more than $150 on boots"
- **THEN** the system extracts and stores a memory with category=budget, key="boots", value="under $150" for that user

#### Scenario: User mentions sizing information
- **WHEN** the user says "I wear a size 10 in hiking boots"
- **THEN** the system extracts and stores a memory with category=size, key="hiking boots", value="10" for that user

### Requirement: Memory extraction runs asynchronously after agent response
The system SHALL perform memory extraction as a post-processing step after the agent's final response has been streamed to the user, so that extraction does not add latency to the user-facing response.

#### Scenario: Extraction does not delay response
- **WHEN** the agent finishes streaming its response to the user
- **THEN** memory extraction runs after the response is complete and does not block or delay the streamed output

### Requirement: Memories are stored with confidence scoring
The system SHALL assign a confidence score (0.0–1.0) to each extracted memory. Repeated mentions of the same preference across conversations SHALL increase its confidence.

#### Scenario: First mention of a preference
- **WHEN** a preference is extracted for the first time
- **THEN** it is stored with a confidence score of 0.5

#### Scenario: Repeated mention of the same preference
- **WHEN** a preference matching an existing memory (same user_id, category, key) is extracted again
- **THEN** the existing memory's confidence score is increased (capped at 1.0) and its value is updated if different

### Requirement: Memories are deduplicated by user, category, and key
The system SHALL upsert memories using the composite key (user_id, category, key) to prevent duplicate entries for the same preference.

#### Scenario: Updating an existing preference
- **WHEN** the user previously said "size 10 boots" and now says "actually I'm a size 11"
- **THEN** the existing memory is updated to value="11" rather than creating a duplicate entry

### Requirement: Extraction skips non-preference conversations
The system SHALL skip memory extraction when the conversation contains no product-related discussion or preference signals.

#### Scenario: Generic greeting conversation
- **WHEN** the user only says "hello" and the agent responds with a greeting
- **THEN** no memory extraction is performed

### Requirement: Users can ask the agent to forget preferences
The system SHALL provide a `manage_memory` tool that allows users to request deletion or correction of stored preferences through natural language in the chat.

#### Scenario: User asks to forget a preference
- **WHEN** the user says "forget that I prefer Nike"
- **THEN** the agent uses the `manage_memory` tool to delete the matching memory record

#### Scenario: User asks to correct a preference
- **WHEN** the user says "actually my shoe size is 11, not 10"
- **THEN** the agent uses the `manage_memory` tool to update the existing memory value

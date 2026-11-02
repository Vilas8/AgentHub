# AgentHub Database Architecture & Entity-Relationship Diagram

All tables use UUID v4 string primary keys and UTC timestamps. Financial values are strictly stored as integers representing minor currency units (cents / paise) to prevent floating point inaccuracies.

```mermaid
erDiagram
    USERS ||--o| USER_PROFILES : has
    USERS ||--o{ AGENTS : creates
    USERS ||--o{ EXECUTIONS : runs
    USERS ||--o{ SUBSCRIPTIONS : holds
    USERS ||--o{ PURCHASES : makes
    USERS ||--o| CREATOR_BALANCES : holds
    USERS ||--o{ CREATOR_LEDGER_ENTRIES : receives
    USERS ||--o{ NOTIFICATIONS : receives
    USERS ||--o{ AUDIT_LOGS : performs
    USERS ||--o{ ORGANIZATION_MEMBERS : belongs_to

    ORGANIZATIONS ||--o{ ORGANIZATION_MEMBERS : contains

    CATEGORIES ||--o{ AGENTS : classifies

    AGENTS ||--o{ AGENT_VERSIONS : versions
    AGENTS ||--o{ EXECUTIONS : executes
    AGENTS ||--o{ PURCHASES : purchased_in

    EXECUTIONS ||--o{ EXECUTION_STEPS : steps

    PLANS ||--o{ SUBSCRIPTIONS : subscribes_to

    USERS {
        string id PK
        string email
        string hashed_password
        string full_name
        string role
        boolean is_active
        boolean is_verified
        datetime created_at
        datetime updated_at
    }

    USER_PROFILES {
        string id PK
        string user_id FK
        text bio
        string avatar_url
        string website
        string location
        string creator_name
    }

    AGENTS {
        string id PK
        string creator_id FK
        string category_id FK
        string name
        string slug
        text description
        string icon
        string status
        string visibility
        string pricing_type
        int price_per_execution
        int total_executions
        numeric average_rating
        int review_count
        boolean is_platform_owned
    }

    AGENT_VERSIONS {
        string id PK
        string agent_id FK
        int version_number
        text system_prompt
        text objective
        string model_provider
        string model_name
        float temperature
        int max_tokens
        int max_steps
        int max_duration_seconds
        json tools_config
        boolean is_published
    }

    EXECUTIONS {
        string id PK
        string user_id FK
        string agent_id FK
        string agent_version_id FK
        string status
        json input_data
        json output_data
        string error_message
        int input_tokens
        int output_tokens
        int total_cost_minor
        string model_provider
        string model_name
        string correlation_id
    }

    EXECUTION_STEPS {
        string id PK
        string execution_id FK
        int step_number
        string step_type
        string status
        json input_data
        json output_data
        string tool_name
        string model_name
        int input_tokens
        int output_tokens
        int duration_ms
        boolean requires_approval
    }

    CREATOR_BALANCES {
        string id PK
        string creator_id FK
        int available_minor
        int pending_minor
        int total_earned_minor
        string currency
    }

    CREATOR_LEDGER_ENTRIES {
        string id PK
        string creator_id FK
        int amount_minor
        string entry_type
        text description
        string reference_id
        int balance_after_minor
    }
```

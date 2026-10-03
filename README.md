# study-analytics-hub
A web app designed to make your learning easier, track your progress, and improve your concentration

# data base

erDiagram
    SUBJECTS ||--o{ TASKS : "has (CASCADE DELETE)"
    SUBJECTS ||--o{ STUDY_SESSIONS : "has (CASCADE DELETE)"
    TASKS ||--o{ STUDY_SESSIONS : "tracks (SET NULL ON DELETE)"

    SUBJECTS {
        int id PK
        string name "NOT NULL"
        string color "Default #3B82F6"
        int target_hours_per_week "Default 5"
        datetime created_at
    }

    TASKS {
        int id PK
        int subject_id FK "NOT NULL"
        string title "NOT NULL"
        string status "todo | in_progress | done"
        int estimated_minutes "Nullable"
        datetime deadline "Nullable"
        datetime created_at
    }

    STUDY_SESSIONS {
        int id PK
        int subject_id FK "NOT NULL"
        int task_id FK "Nullable"
        int duration_minutes "NOT NULL"
        datetime created_at
    }

    SETTINGS {
        int id PK
        string university_name "Nullable"
        string country "Nullable"
        int daily_goal_minutes "Default 120"
    }
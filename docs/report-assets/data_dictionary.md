# Data dictionary

Every table and column, generated from the models.

## `courses`

| Column | Type | Null | Key |
|---|---|---|---|
| `id` | INTEGER | no | PK |
| `code` | VARCHAR(32) | no |  |
| `title` | VARCHAR(200) | no |  |
| `description` | TEXT | no |  |
| `created_at` | DATETIME | no |  |

## `model_runs`

| Column | Type | Null | Key |
|---|---|---|---|
| `id` | INTEGER | no | PK |
| `kind` | VARCHAR(32) | no |  |
| `run_date` | DATE | no |  |
| `status` | VARCHAR(24) | no |  |
| `triggered_by` | VARCHAR(32) | no |  |
| `started_at` | DATETIME | no |  |
| `finished_at` | DATETIME | yes |  |
| `metrics` | JSONB | no |  |
| `artifact` | BLOB | yes |  |
| `notes` | TEXT | no |  |

## `research_reports`

| Column | Type | Null | Key |
|---|---|---|---|
| `kind` | VARCHAR(40) | no | PK |
| `payload` | JSONB | no |  |
| `imported_at` | DATETIME | no |  |

## `settings`

| Column | Type | Null | Key |
|---|---|---|---|
| `key` | VARCHAR(64) | no | PK |
| `value` | JSONB | no |  |
| `version` | INTEGER | no |  |
| `updated_at` | DATETIME | no |  |

## `users`

| Column | Type | Null | Key |
|---|---|---|---|
| `id` | INTEGER | no | PK |
| `email` | VARCHAR(255) | no |  |
| `password_hash` | VARCHAR(255) | no |  |
| `full_name` | VARCHAR(120) | no |  |
| `role` | VARCHAR(24) | no |  |
| `is_active` | BOOLEAN | no |  |
| `is_synthetic` | BOOLEAN | no |  |
| `created_at` | DATETIME | no |  |
| `last_active_at` | DATETIME | yes |  |

## `classes`

| Column | Type | Null | Key |
|---|---|---|---|
| `id` | INTEGER | no | PK |
| `course_id` | INTEGER | no | FK → courses.id |
| `teacher_id` | INTEGER | no | FK → users.id |
| `name` | VARCHAR(120) | no |  |
| `join_code` | VARCHAR(12) | no |  |
| `created_at` | DATETIME | no |  |

## `concepts`

| Column | Type | Null | Key |
|---|---|---|---|
| `id` | INTEGER | no | PK |
| `course_id` | INTEGER | no | FK → courses.id |
| `slug` | VARCHAR(64) | no |  |
| `name` | VARCHAR(120) | no |  |
| `description` | TEXT | no |  |
| `order_index` | INTEGER | no |  |
| `bkt_prior` | FLOAT | no |  |
| `bkt_learn` | FLOAT | no |  |
| `bkt_guess` | FLOAT | no |  |
| `bkt_slip` | FLOAT | no |  |
| `params_version` | INTEGER | no |  |
| `params_source` | VARCHAR(32) | no |  |
| `is_study` | BOOLEAN | no |  |

## `consents`

| Column | Type | Null | Key |
|---|---|---|---|
| `user_id` | INTEGER | no | PK |
| `version` | VARCHAR(16) | no |  |
| `consented_at` | DATETIME | no |  |

## `learner_features`

| Column | Type | Null | Key |
|---|---|---|---|
| `user_id` | INTEGER | no | PK |
| `persona` | VARCHAR(40) | yes |  |
| `persona_label` | VARCHAR(80) | yes |  |
| `risk_score` | FLOAT | no |  |
| `risk_level` | VARCHAR(24) | no |  |
| `risk_reasons` | JSONB | no |  |
| `features` | JSONB | no |  |
| `notes` | TEXT | no |  |
| `updated_at` | DATETIME | no |  |

## `questionnaire_responses`

| Column | Type | Null | Key |
|---|---|---|---|
| `id` | INTEGER | no | PK |
| `user_id` | INTEGER | no | FK → users.id |
| `source` | VARCHAR(24) | no |  |
| `answers` | JSONB | no |  |
| `vector` | JSONB | no |  |
| `created_at` | DATETIME | no |  |

## `style_profiles`

| Column | Type | Null | Key |
|---|---|---|---|
| `user_id` | INTEGER | no | PK |
| `ar` | FLOAT | no |  |
| `si` | FLOAT | no |  |
| `vv` | FLOAT | no |  |
| `sg` | FLOAT | no |  |
| `prior_ar` | FLOAT | no |  |
| `prior_si` | FLOAT | no |  |
| `prior_vv` | FLOAT | no |  |
| `prior_sg` | FLOAT | no |  |
| `n_updates` | INTEGER | no |  |
| `ema_gain` | FLOAT | no |  |
| `updated_at` | DATETIME | no |  |

## `survey_responses`

| Column | Type | Null | Key |
|---|---|---|---|
| `id` | INTEGER | no | PK |
| `user_id` | INTEGER | no | FK → users.id |
| `kind` | VARCHAR(24) | no |  |
| `answers` | JSONB | no |  |
| `score` | FLOAT | yes |  |
| `created_at` | DATETIME | no |  |

## `teaching_aids`

| Column | Type | Null | Key |
|---|---|---|---|
| `id` | INTEGER | no | PK |
| `course_id` | INTEGER | no | FK → courses.id |
| `slug` | VARCHAR(96) | no |  |
| `title` | VARCHAR(200) | no |  |
| `description` | TEXT | no |  |
| `aid_type` | VARCHAR(24) | no |  |
| `delivery` | VARCHAR(24) | no |  |
| `url` | VARCHAR(500) | yes |  |
| `body_md` | TEXT | yes |  |
| `component_key` | VARCHAR(64) | yes |  |
| `source` | VARCHAR(120) | no |  |
| `difficulty` | INTEGER | no |  |
| `style_ar` | FLOAT | no |  |
| `style_si` | FLOAT | no |  |
| `style_vv` | FLOAT | no |  |
| `style_sg` | FLOAT | no |  |
| `interactivity` | VARCHAR(24) | no |  |
| `duration_min` | INTEGER | no |  |
| `language` | VARCHAR(8) | no |  |
| `default_order` | INTEGER | no |  |
| `is_active` | BOOLEAN | no |  |
| `created_by` | INTEGER | yes | FK → users.id |
| `created_at` | DATETIME | no |  |
| `updated_at` | DATETIME | no |  |

## `aid_concepts`

| Column | Type | Null | Key |
|---|---|---|---|
| `aid_id` | INTEGER | no | PK |
| `concept_id` | INTEGER | no | PK |
| `weight` | FLOAT | no |  |

## `aid_stats`

| Column | Type | Null | Key |
|---|---|---|---|
| `aid_id` | INTEGER | no | PK |
| `persona` | VARCHAR(40) | no | PK |
| `n_uses` | INTEGER | no |  |
| `n_completions` | INTEGER | no |  |
| `n_checked` | INTEGER | no |  |
| `n_improved` | INTEGER | no |  |
| `mean_gain` | FLOAT | no |  |
| `smoothed_gain` | FLOAT | no |  |
| `mean_rating` | FLOAT | yes |  |
| `updated_at` | DATETIME | no |  |

## `concept_prerequisites`

| Column | Type | Null | Key |
|---|---|---|---|
| `concept_id` | INTEGER | no | PK |
| `prereq_id` | INTEGER | no | PK |

## `enrollments`

| Column | Type | Null | Key |
|---|---|---|---|
| `class_id` | INTEGER | no | PK |
| `user_id` | INTEGER | no | PK |
| `joined_at` | DATETIME | no |  |
| `arm` | VARCHAR(24) | yes |  |
| `form_order` | VARCHAR(2) | yes |  |

## `mastery`

| Column | Type | Null | Key |
|---|---|---|---|
| `user_id` | INTEGER | no | PK |
| `concept_id` | INTEGER | no | PK |
| `p_known` | FLOAT | no |  |
| `n_answers` | INTEGER | no |  |
| `mastered_at` | DATETIME | yes |  |
| `updated_at` | DATETIME | no |  |

## `questions`

| Column | Type | Null | Key |
|---|---|---|---|
| `id` | INTEGER | no | PK |
| `course_id` | INTEGER | no | FK → courses.id |
| `key` | VARCHAR(64) | no |  |
| `concept_id` | INTEGER | no | FK → concepts.id |
| `stem` | TEXT | no |  |
| `options` | JSONB | no |  |
| `correct_index` | INTEGER | no |  |
| `explanation` | TEXT | no |  |
| `difficulty` | INTEGER | no |  |
| `pool` | VARCHAR(24) | no |  |
| `form` | VARCHAR(1) | yes |  |
| `aid_id` | INTEGER | yes | FK → teaching_aids.id |
| `is_active` | BOOLEAN | no |  |

## `recommendation_lists`

| Column | Type | Null | Key |
|---|---|---|---|
| `id` | INTEGER | no | PK |
| `user_id` | INTEGER | no | FK → users.id |
| `scope` | VARCHAR(24) | no |  |
| `concept_id` | INTEGER | yes | FK → concepts.id |
| `policy` | VARCHAR(32) | no |  |
| `arm` | VARCHAR(16) | yes |  |
| `phase` | VARCHAR(16) | no |  |
| `weights_version` | INTEGER | no |  |
| `bkt_params_version` | INTEGER | no |  |
| `model_run_id` | INTEGER | yes | FK → model_runs.id |
| `reason` | VARCHAR(32) | no |  |
| `is_current` | BOOLEAN | no |  |
| `created_at` | DATETIME | no |  |

## `recommendation_items`

| Column | Type | Null | Key |
|---|---|---|---|
| `id` | INTEGER | no | PK |
| `list_id` | INTEGER | no | FK → recommendation_lists.id |
| `user_id` | INTEGER | no | FK → users.id |
| `aid_id` | INTEGER | no | FK → teaching_aids.id |
| `concept_id` | INTEGER | no | FK → concepts.id |
| `rank` | INTEGER | no |  |
| `score` | FLOAT | no |  |
| `signals` | JSONB | no |  |
| `explanation` | TEXT | no |  |
| `is_explore` | BOOLEAN | no |  |
| `impression_at` | DATETIME | yes |  |
| `opened_at` | DATETIME | yes |  |
| `completed_at` | DATETIME | yes |  |
| `checked_at` | DATETIME | yes |  |
| `p_open` | FLOAT | yes |  |
| `gain` | FLOAT | yes |  |
| `check_status` | VARCHAR(24) | yes |  |
| `rating` | INTEGER | yes |  |

## `aid_uses`

| Column | Type | Null | Key |
|---|---|---|---|
| `id` | INTEGER | no | PK |
| `user_id` | INTEGER | no | FK → users.id |
| `aid_id` | INTEGER | no | FK → teaching_aids.id |
| `concept_id` | INTEGER | no | FK → concepts.id |
| `rec_item_id` | INTEGER | yes | FK → recommendation_items.id |
| `source` | VARCHAR(24) | no |  |
| `opened_at` | DATETIME | no |  |
| `completed_at` | DATETIME | yes |  |
| `dwell_sec` | INTEGER | no |  |
| `rating` | INTEGER | yes |  |
| `p_open` | FLOAT | no |  |
| `check_status` | VARCHAR(24) | no |  |
| `checked_at` | DATETIME | yes |  |
| `gain` | FLOAT | yes |  |
| `persona` | VARCHAR(40) | yes |  |

## `interactions`

| Column | Type | Null | Key |
|---|---|---|---|
| `id` | INTEGER | no | PK |
| `user_id` | INTEGER | no | FK → users.id |
| `aid_id` | INTEGER | no | FK → teaching_aids.id |
| `item_id` | INTEGER | yes | FK → recommendation_items.id |
| `event` | VARCHAR(24) | no |  |
| `source` | VARCHAR(24) | no |  |
| `value` | JSONB | no |  |
| `created_at` | DATETIME | no |  |

## `style_updates`

| Column | Type | Null | Key |
|---|---|---|---|
| `id` | INTEGER | no | PK |
| `user_id` | INTEGER | no | FK → users.id |
| `aid_id` | INTEGER | no | FK → teaching_aids.id |
| `item_id` | INTEGER | yes | FK → recommendation_items.id |
| `gain` | FLOAT | no |  |
| `baseline` | FLOAT | no |  |
| `before` | JSONB | no |  |
| `after` | JSONB | no |  |
| `created_at` | DATETIME | no |  |

## `attempts`

| Column | Type | Null | Key |
|---|---|---|---|
| `id` | INTEGER | no | PK |
| `user_id` | INTEGER | no | FK → users.id |
| `kind` | VARCHAR(24) | no |  |
| `concept_id` | INTEGER | yes | FK → concepts.id |
| `aid_id` | INTEGER | yes | FK → teaching_aids.id |
| `rec_item_id` | INTEGER | yes | FK → recommendation_items.id |
| `use_id` | INTEGER | yes | FK → aid_uses.id |
| `question_ids` | JSONB | no |  |
| `form` | VARCHAR(1) | yes |  |
| `started_at` | DATETIME | no |  |
| `finished_at` | DATETIME | yes |  |
| `n_correct` | INTEGER | no |  |
| `n_total` | INTEGER | no |  |

## `responses`

| Column | Type | Null | Key |
|---|---|---|---|
| `id` | INTEGER | no | PK |
| `attempt_id` | INTEGER | no | FK → attempts.id |
| `question_id` | INTEGER | no | FK → questions.id |
| `user_id` | INTEGER | no | FK → users.id |
| `concept_id` | INTEGER | no | FK → concepts.id |
| `chosen_index` | INTEGER | no |  |
| `correct` | BOOLEAN | no |  |
| `is_repeat` | BOOLEAN | no |  |
| `time_ms` | INTEGER | yes |  |
| `p_before` | FLOAT | no |  |
| `p_after` | FLOAT | no |  |
| `created_at` | DATETIME | no |  |

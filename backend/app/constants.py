"""
Project-wide constants.
"""
import re

# Time units
MINUTES_IN_HOUR = 60
HOURS_IN_WEEK = 7 * 24  # 168

# Auth
MIN_PASSWORD_LENGTH = 6

# Subjects
SUBJECT_NAME_MAX_LENGTH = 100  # used both for API validation and for the DB column size
DEFAULT_SUBJECT_COLOR = '#3B82F6'
HEX_COLOR_REGEX = re.compile(r'^#[0-9a-fA-F]{6}$')
DEFAULT_TARGET_HOURS_PER_WEEK = 5

# Tasks
TASK_STATUS_TODO = 'todo'
TASK_STATUS_IN_PROGRESS = 'in_progress'
TASK_STATUS_DONE = 'done'

# Ordered tuple: it is also used to build the DB CHECK constraint (models.py).
TASK_STATUSES = (TASK_STATUS_TODO, TASK_STATUS_IN_PROGRESS, TASK_STATUS_DONE)
VALID_TASK_STATUSES = frozenset(TASK_STATUSES)
DEFAULT_TASK_STATUS = TASK_STATUS_TODO

TASK_TITLE_MAX_LENGTH = 100  # used both for API validation and for the DB column size

# Timer (study sessions)
DEFAULT_SESSIONS_LIMIT = 10
MAX_SESSIONS_LIMIT = 50
MIN_DURATION_MINUTES = 1
MAX_DURATION_MINUTES = 720

# Analytics
VALID_PERIODS = frozenset({'day', 'week', 'month', 'all'})
DEFAULT_PERIOD = 'week'

# Rolling windows: "last N days counting back from now".
PERIOD_DAYS = {'week': 7, 'month': 30}

# Weekly goals are always measured over this period, whatever period was requested.
WEEKLY_GOAL_PERIOD = 'week'

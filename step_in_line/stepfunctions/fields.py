from enum import Enum


class Field(Enum):

    # Common fields
    Comment = "comment"
    InputPath = "input_path"
    OutputPath = "output_path"
    Parameters = "parameters"
    ResultPath = "result_path"
    Next = "next"
    Retry = "retry"
    Catch = "catch"
    Branches = "branches"
    End = "end"
    Version = "version"

    # Pass state fields
    Result = "result"

    # Fail state fields
    Error = "error"
    Cause = "cause"

    # Wait state fields
    Seconds = "seconds"
    Timestamp = "timestamp"
    SecondsPath = "seconds_path"
    TimestampPath = "timestamp_path"

    # Choice state fields
    Choices = "choices"
    Default = "default"

    # Map state fields
    Iterator = "iterator"
    ItemsPath = "items_path"
    MaxConcurrency = "max_concurrency"

    # Task state fields
    Resource = "resource"
    TimeoutSeconds = "timeout_seconds"
    TimeoutSecondsPath = "timeout_seconds_path"
    HeartbeatSeconds = "heartbeat_seconds"
    HeartbeatSecondsPath = "heartbeat_seconds_path"

    # Retry and catch fields
    ErrorEquals = "error_equals"
    IntervalSeconds = "interval_seconds"
    MaxAttempts = "max_attempts"
    BackoffRate = "backoff_rate"
    NextStep = "next_step"

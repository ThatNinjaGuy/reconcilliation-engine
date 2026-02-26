"""Connector error types."""


class ConnectorError(Exception):
    """Base exception for connector errors."""


class ConnectionError(ConnectorError):
    """Failed to establish connection."""


class QueryError(ConnectorError):
    """Query execution failed."""


class SchemaValidationError(ConnectorError):
    """Schema validation failed."""


class DataConversionError(ConnectorError):
    """Data conversion failed."""

import logging
import signal
import time
from functools import wraps
from typing import Any, Callable, Dict, Optional

from databricks import sql
from databricks.sdk import WorkspaceClient
from fastapi import Depends

from .config import Settings, get_settings

# Configure logging
from api.common.logging import setup_logging, get_logger
setup_logging(level=logging.INFO)
logger = get_logger(__name__)

class TimeoutError(Exception):
    """Exception raised when a function times out."""

class CachingWorkspaceClient(WorkspaceClient):
    def __init__(self, client: WorkspaceClient, timeout: int = 30):
        self._client = client
        self._cache: Dict[str, Any] = {}
        self._cache_times: Dict[str, float] = {}
        self._cache_duration = 300  # 5 minutes in seconds
        self._timeout = timeout

    def __call__(self, timeout: int = 30):
        return CachingWorkspaceClient(self._client, timeout=timeout)

    def _make_api_call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute a function with a timeout.
        
        Args:
            func: The function to execute
            *args: Positional arguments to pass to the function
            **kwargs: Keyword arguments to pass to the function
            
        Returns:
            The result of the function call
            
        Raises:
            TimeoutError: If the function call times out
        """
        def handler(signum, frame):
            raise TimeoutError(f"Function call timed out after {self._timeout} seconds")

        # Set the timeout handler
        original_handler = signal.signal(signal.SIGALRM, handler)
        signal.alarm(self._timeout)

        try:
            result = func(*args, **kwargs)
            return result
        finally:
            # Restore the original handler and cancel the alarm
            signal.alarm(0)
            signal.signal(signal.SIGALRM, original_handler)

    def _cache_result(self, key: str) -> Callable:
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs):
                current_time = time.time()
                # Check if we have a cached result that's still valid
                if (
                    key in self._cache
                    and key in self._cache_times
                    and current_time - self._cache_times[key] < self._cache_duration
                ):
                    logger.info(f"Cache hit for {key} (age: {current_time - self._cache_times[key]:.1f}s)")
                    return self._cache[key]

                # Call the actual function and cache the result
                logger.info(f"Cache miss for {key}, calling Databricks workspace")
                try:
                    result = self._make_api_call(func, *args, **kwargs)
                    self._cache[key] = result
                    self._cache_times[key] = current_time
                    return result
                except TimeoutError as e:
                    logger.error(f"Timeout while fetching {key}: {e}")
                    # Return cached data if available, even if expired
                    if key in self._cache:
                        logger.warning(f"Returning stale cached data for {key}")
                        return self._cache[key]
                    raise
                except Exception as e:
                    logger.error(f"Error fetching {key}: {e}")
                    # Return cached data if available, even if expired
                    if key in self._cache:
                        logger.warning(f"Returning stale cached data for {key}")
                        return self._cache[key]
                    raise
            return wrapper
        return decorator

    @property
    def clusters(self):
        class CachedClusters:
            def __init__(self, parent):
                self._parent = parent

            def list(self):
                return self._parent._cache_result('clusters.list')(
                    lambda: list(self._parent._client.clusters.list())
                )()

        return CachedClusters(self)

    @property
    def connections(self):
        class CachedConnections:
            def __init__(self, parent):
                self._parent = parent

            def list(self):
                return self._parent._cache_result('connections.list')(
                    lambda: list(self._parent._client.connections.list())
                )()

        return CachedConnections(self)

    @property
    def catalogs(self):
        class CachedCatalogs:
            def __init__(self, parent):
                self._parent = parent

            def list(self):
                return self._parent._cache_result('catalogs.list')(
                    lambda: list(self._parent._client.catalogs.list())
                )()

        return CachedCatalogs(self)

    @property
    def schemas(self):
        class CachedSchemas:
            def __init__(self, parent):
                self._parent = parent

            # Schemas are listed per catalog
            def list(self, catalog_name: str):
                cache_key = f'schemas.list::{catalog_name}' 
                return self._parent._cache_result(cache_key)(
                    # Convert generator to list for caching
                    lambda: list(self._parent._client.schemas.list(catalog_name=catalog_name))
                )()

        return CachedSchemas(self)

    @property
    def tables(self):
        class CachedTables:
            def __init__(self, parent):
                self._parent = parent

            # Tables are listed per catalog and schema
            def list(self, catalog_name: str, schema_name: str):
                cache_key = f'tables.list::{catalog_name}::{schema_name}'
                return self._parent._cache_result(cache_key)(
                    # Convert generator to list for caching
                    lambda: list(self._parent._client.tables.list(catalog_name=catalog_name, schema_name=schema_name))
                )()

        return CachedTables(self)

    # Delegate all other attributes to the original client
    def __getattr__(self, name):
        # Ensure we don't accidentally delegate properties we've explicitly handled
        if name in ['clusters', 'connections', 'catalogs', 'schemas', 'tables']:
            # This case shouldn't typically be hit due to @property lookups,
            # but added as a safeguard.
             raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}' - use the property")
        return getattr(self._client, name)

def get_workspace_client(settings: Optional[Settings] = None, timeout: int = 30) -> WorkspaceClient:
    """Get a configured Databricks workspace client with caching.
    
    Args:
        settings: Application settings (optional, will be fetched if not provided)
        timeout: Timeout in seconds for API calls
        
    Returns:
        Cached workspace client instance
    """
    if settings is None:
        settings = get_settings()

    # Log environment values with obfuscated token
    masked_token = f"{settings.DATABRICKS_TOKEN[:4]}...{settings.DATABRICKS_TOKEN[-4:]}" if settings.DATABRICKS_TOKEN else None
    logger.info(f"Initializing workspace client with host: {settings.DATABRICKS_HOST}, token: {masked_token}, timeout: {timeout}s")

    client = WorkspaceClient(
        host=settings.DATABRICKS_HOST,
        token=settings.DATABRICKS_TOKEN
    )
    return CachingWorkspaceClient(client, timeout=timeout)

def get_workspace_client_dependency(timeout: int = 30):
    """Returns the actual dependency function for FastAPI."""
    
    def _get_ws_client() -> Optional[WorkspaceClient]:
        """The actual FastAPI dependency function that gets the client."""
        client = get_workspace_client(timeout=timeout)
        return client

    return _get_ws_client

def get_sql_connection(settings: Settings = Depends(get_settings)):
    """Create and return a Databricks SQL connection.
    
    Args:
        settings: Application settings (injected by FastAPI)
        
    Returns:
        SQL connection instance
    """
    if settings.ENV == 'LOCAL':
        logger.info(f"Creating PAT-based SQL connection to {settings.DATABRICKS_HOST} with warehouse {settings.DATABRICKS_WAREHOUSE_ID}")
        return sql.connect(
            server_hostname=settings.DATABRICKS_HOST,
            http_path=f"/sql/1.0/warehouses/{settings.DATABRICKS_WAREHOUSE_ID}",
            access_token=settings.DATABRICKS_TOKEN
        )
    else:
        logger.info(f"Creating credentials-based SQL connection to {settings.DATABRICKS_HOST} with warehouse {settings.DATABRICKS_WAREHOUSE_ID}")
        return sql.connect(
            server_hostname=settings.DATABRICKS_HOST,
            http_path=f"/sql/1.0/warehouses/{settings.DATABRICKS_WAREHOUSE_ID}",
            credentials_provider=lambda: settings.authenticate
        )

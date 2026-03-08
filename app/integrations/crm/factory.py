"""
CRM Client Factory
==================
Creates appropriate CRM client based on configuration.
"""
import os
import logging
from typing import Optional

from .interface import CRMClientInterface
from .mock_client_new import MockCRMClient
from .live_client import LiveCRMClient

logger = logging.getLogger(__name__)


def get_crm_client(mode: Optional[str] = None) -> CRMClientInterface:
    """
    Get CRM client instance based on mode.
    
    Args:
        mode: 'mock' or 'live'. If None, uses CRM_MODE env var (default: 'mock')
        
    Returns:
        CRM client instance (MockCRMClient or LiveCRMClient)
    """
    if mode is None:
        mode = os.getenv('CRM_MODE', 'mock').lower()
    
    if mode == 'mock':
        logger.info("Using MockCRMClient")
        return MockCRMClient()
    elif mode == 'live':
        logger.info("Using LiveCRMClient")
        return LiveCRMClient()
    else:
        logger.warning(f"Unknown CRM_MODE '{mode}', defaulting to mock")
        return MockCRMClient()

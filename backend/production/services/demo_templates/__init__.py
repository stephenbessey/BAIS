"""
BAIS Platform - Demo Template System

This package provides a complete demo template system for generating
BAIS-compliant demonstrations from any business website.
"""

from .orchestrator.demo_workflow import DemoOrchestrator, DemoConfig, DemoType
from .scraper.website_analyzer import WebsiteAnalyzer, BusinessIntelligence
from .generator.schema_generator import SchemaGenerator
from .generator.mcp_server_builder import McpServerBuilder
from .generator.demo_ui_creator import DemoUiCreator
from .generator.acp_config_builder import AcpConfigBuilder
from .commerce.acp_integration_service import AcpIntegrationService, CommerceBridge

__all__ = [
    "DemoOrchestrator",
    "DemoConfig", 
    "DemoType",
    "WebsiteAnalyzer",
    "BusinessIntelligence",
    "SchemaGenerator",
    "McpServerBuilder",
    "DemoUiCreator",
    "AcpConfigBuilder",
    "AcpIntegrationService",
    "CommerceBridge"
]

__version__ = "1.0.0"
__author__ = "BAIS Platform Team"
__email__ = "team@bais.io"

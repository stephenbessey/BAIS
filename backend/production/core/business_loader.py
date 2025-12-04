"""
Business Loader Module
Loads demo businesses from configuration (not hard-coded)
"""

import json
import logging
import os
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger(__name__)


class BusinessLoader:
    """Loads businesses from configuration files"""

    def __init__(self, project_root: Optional[str] = None):
        """Initialize business loader with project root path"""
        if project_root:
            self.project_root = Path(project_root)
        else:
            # Default: 3 levels up from this file
            self.project_root = Path(__file__).parent.parent.parent.parent

        self.config_dir = self.project_root / "backend" / "production" / "config"
        self.customers_dir = self.project_root / "customers"

        logger.info(f"BusinessLoader initialized with project_root: {self.project_root}")

    def load_demo_config(self) -> Dict[str, Any]:
        """Load demo businesses configuration"""
        config_file = self.config_dir / "demo_businesses.json"

        if not config_file.exists():
            logger.warning(f"Demo config not found at {config_file}, using defaults")
            return {
                "demo_businesses": [],
                "auto_load_on_startup": False,
                "auto_load_when_database_empty": False
            }

        try:
            with open(config_file, 'r') as f:
                config = json.load(f)
            logger.info(f"Loaded demo config with {len(config.get('demo_businesses', []))} businesses")
            return config
        except Exception as e:
            logger.error(f"Failed to load demo config: {e}")
            return {
                "demo_businesses": [],
                "auto_load_on_startup": False,
                "auto_load_when_database_empty": False
            }

    def get_enabled_demo_businesses(self) -> List[Dict[str, Any]]:
        """Get list of enabled demo businesses from config"""
        config = self.load_demo_config()
        demo_businesses = config.get("demo_businesses", [])

        # Filter to only enabled businesses
        enabled = [biz for biz in demo_businesses if biz.get("enabled", False)]
        logger.info(f"Found {len(enabled)} enabled demo businesses")
        return enabled

    def load_business_from_file(self, customer_file: str) -> Optional[Dict[str, Any]]:
        """Load a business from a customer JSON file"""
        file_path = self.customers_dir / customer_file

        if not file_path.exists():
            logger.warning(f"Customer file not found: {file_path}")
            return None

        try:
            with open(file_path, 'r') as f:
                customer_data = json.load(f)
            logger.info(f"Loaded business data from {customer_file}")
            return customer_data
        except Exception as e:
            logger.error(f"Failed to load business from {customer_file}: {e}")
            return None

    def convert_to_business_format(self, customer_data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert customer data to standardized business format"""
        # Generate business_id from business_name
        business_name = customer_data.get("business_name", "")
        if not business_name:
            raise ValueError("business_name is required in customer data")

        # Generate URL-friendly business ID
        import re
        business_id = re.sub(r'[^a-z0-9]+', '-', business_name.lower())
        business_id = re.sub(r'^-+|-+$', '', business_id)

        # Create standardized business data
        business_data = {
            "business_id": business_id,
            "business_name": customer_data.get("business_name"),
            "business_type": customer_data.get("business_type"),
            "business_info": customer_data.get("business_info", {}),
            "location": customer_data.get("location", {}),
            "contact_info": customer_data.get("contact_info", {}),
            "services_config": [
                {
                    "id": svc.get("id"),
                    "name": svc.get("name"),
                    "description": svc.get("description"),
                    "category": svc.get("category")
                }
                for svc in customer_data.get("services_config", [])
            ],
            "status": "active",
            "mcp_enabled": True,
            "a2a_enabled": True
        }

        return business_data

    def load_all_demo_businesses(self) -> List[Tuple[str, Dict[str, Any]]]:
        """
        Load all enabled demo businesses from configuration.
        Returns list of tuples: (business_id, business_data)
        """
        enabled_businesses = self.get_enabled_demo_businesses()
        loaded_businesses = []

        for demo_biz in enabled_businesses:
            customer_file = demo_biz.get("customer_file")
            if not customer_file:
                logger.warning(f"Demo business config missing 'customer_file': {demo_biz}")
                continue

            customer_data = self.load_business_from_file(customer_file)
            if not customer_data:
                continue

            try:
                business_data = self.convert_to_business_format(customer_data)
                business_id = business_data["business_id"]
                loaded_businesses.append((business_id, business_data))
                logger.info(f"✅ Loaded demo business: {business_data['business_name']} (ID: {business_id})")
            except Exception as e:
                logger.error(f"Failed to convert business data from {customer_file}: {e}")

        return loaded_businesses

    def should_auto_load(self) -> bool:
        """Check if demo businesses should be auto-loaded on startup"""
        config = self.load_demo_config()
        return config.get("auto_load_on_startup", False)

    def should_load_when_database_empty(self) -> bool:
        """Check if demo businesses should be loaded when database is empty"""
        config = self.load_demo_config()
        return config.get("auto_load_when_database_empty", False)

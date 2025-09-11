import uuid
import hashlib
from datetime import datetime
from fastapi import HTTPException, BackgroundTasks

from ..api_models import BusinessRegistrationRequest, BusinessRegistrationResponse, BusinessStatusResponse
from ..core.database_models import DatabaseManager, BusinessRepository
from ..core.bais_schema_validator import BAISSchemaValidator
from ..utils.schema_factory import BusinessSchemaFactory
# Assume server setup logic exists in a separate module
# from .server_manager import setup_business_servers 

class BusinessService:
    def __init__(self, db_manager: DatabaseManager, background_tasks: BackgroundTasks):
        self.db_manager = db_manager
        self.background_tasks = background_tasks

    def _generate_api_key(self, business_id: str) -> str:
        """Generates a secure API key for a business."""
        data = f"{business_id}:{datetime.utcnow().isoformat()}:{uuid.uuid4()}".encode()
        return hashlib.sha256(data).hexdigest()

    async def register_business(self, request: BusinessRegistrationRequest) -> BusinessRegistrationResponse:
        """Registers a new business, validates its schema, and persists it."""
        schema = BusinessSchemaFactory.create_from_request(request)
        is_valid, issues = BAISSchemaValidator.validate_schema(schema.dict())
        if not is_valid:
            raise HTTPException(status_code=400, detail=f"Invalid business schema: {'; '.join(issues)}")

        api_key = self._generate_api_key(schema.business_info.id)
        
        # need to setup and use a proper database repository
        # For now, we simulate storage and response
        
        # self.background_tasks.add_task(setup_business_servers, schema)

        return BusinessRegistrationResponse(
            business_id=schema.business_info.id,
            status="registered",
            mcp_endpoint=schema.integration.mcp_server.endpoint,
            a2a_endpoint=schema.integration.a2a_endpoint.discovery_url,
            api_keys={"primary": api_key},
            setup_complete=False  # This needs to be updated by the background task
        )

    async def get_business_status(self, business_id: str) -> BusinessStatusResponse:
        """Retrieves the status and metrics for a given business."""
        # This needs to fetch from a database and a monitoring service
        # Simulating the response for now
        return BusinessStatusResponse(
            business_id=business_id,
            name="Example Business",
            status="active",
            services_enabled=1,
            mcp_server_active=True,
            a2a_server_active=True,
            last_updated=datetime.utcnow(),
            metrics={
                "total_interactions": 156,
                "successful_bookings": 23,
                "revenue_today": 2847.50,
                "avg_response_time_ms": 145
            }
        )
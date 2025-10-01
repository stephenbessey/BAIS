"""
BAIS Platform - ACP Manifest Endpoint

Official Agentic Commerce Protocol manifest endpoint for merchant discovery
and capability advertisement as per ACP specification.
"""

from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse

from ...core.database_models import DatabaseManager, Business
from ...services.commerce.acp_official_compliance import OfficialACPIntegrationService
import httpx

# Router
router = APIRouter(prefix="/.well-known", tags=["ACP Manifest"])


@router.get("/commerce-manifest")
async def get_commerce_manifest(
    merchant_id: Optional[str] = None,
    db_manager: DatabaseManager = Depends()
) -> JSONResponse:
    """
    Get ACP commerce manifest for merchant discovery
    
    This endpoint implements the official ACP specification for merchant
    capability advertisement and agent discovery.
    
    Args:
        merchant_id: Optional merchant identifier (defaults to primary merchant)
        
    Returns:
        JSONResponse: ACP-compliant commerce manifest
    """
    try:
        async with httpx.AsyncClient() as http_client:
            acp_service = OfficialACPIntegrationService(db_manager.session, http_client)
            
            # Use provided merchant_id or get default merchant
            if not merchant_id:
                # Get first business as default merchant
                business = db_manager.session.query(Business).first()
                if not business:
                    raise HTTPException(status_code=404, detail="No merchants found")
                merchant_id = str(business.id)
            
            # Generate manifest
            manifest = await acp_service.get_commerce_manifest(merchant_id)
            
            return JSONResponse(
                content=manifest.dict(),
                headers={
                    "Content-Type": "application/json",
                    "Cache-Control": "public, max-age=3600",  # Cache for 1 hour
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "GET, OPTIONS",
                    "Access-Control-Allow-Headers": "Content-Type, Authorization"
                }
            )
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Manifest generation failed: {str(e)}")


@router.get("/commerce-manifest/{merchant_id}")
async def get_merchant_commerce_manifest(
    merchant_id: str,
    db_manager: DatabaseManager = Depends()
) -> JSONResponse:
    """
    Get ACP commerce manifest for specific merchant
    
    Args:
        merchant_id: Merchant identifier
        
    Returns:
        JSONResponse: ACP-compliant commerce manifest
    """
    try:
        async with httpx.AsyncClient() as http_client:
            acp_service = OfficialACPIntegrationService(db_manager.session, http_client)
            manifest = await acp_service.get_commerce_manifest(merchant_id)
            
            return JSONResponse(
                content=manifest.dict(),
                headers={
                    "Content-Type": "application/json",
                    "Cache-Control": "public, max-age=3600",
                    "Access-Control-Allow-Origin": "*"
                }
            )
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Manifest generation failed: {str(e)}")


@router.options("/commerce-manifest")
async def commerce_manifest_options():
    """Handle CORS preflight requests for commerce manifest"""
    return JSONResponse(
        content={},
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization",
            "Access-Control-Max-Age": "3600"
        }
    )


@router.options("/commerce-manifest/{merchant_id}")
async def merchant_commerce_manifest_options(merchant_id: str):
    """Handle CORS preflight requests for merchant commerce manifest"""
    return JSONResponse(
        content={},
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization",
            "Access-Control-Max-Age": "3600"
        }
    )

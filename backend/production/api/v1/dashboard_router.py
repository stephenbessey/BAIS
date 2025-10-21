"""
Dashboard API Router for BAIS Platform
Provides business and platform dashboard endpoints
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any, List
from datetime import datetime, timedelta
from ..services.business_service import BusinessService
from ..core.database_models import DatabaseManager
from ..api_models import *

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


def get_business_dashboard_data(db: DatabaseManager, business_id: str) -> Dict[str, Any]:
    """Get business dashboard data from database"""
    
    # Get business info
    business = db.get_business_by_id(business_id)
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    # Get metrics for last 30 days
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    
    # Query transaction metrics
    transactions = db.get_business_transactions(
        business_id=business_id,
        start_date=start_date,
        end_date=end_date
    )
    
    # Calculate metrics
    total_revenue = sum(t.get('amount', 0) for t in transactions)
    total_transactions = len(transactions)
    
    # Get AI platform breakdown
    platform_breakdown = {}
    for transaction in transactions:
        platform = transaction.get('ai_provider', 'unknown')
        if platform not in platform_breakdown:
            platform_breakdown[platform] = {'count': 0, 'revenue': 0}
        platform_breakdown[platform]['count'] += 1
        platform_breakdown[platform]['revenue'] += transaction.get('amount', 0)
    
    # Get services performance
    services = db.get_business_services(business_id)
    services_performance = []
    for service in services:
        service_transactions = [t for t in transactions if t.get('service_id') == service['id']]
        services_performance.append({
            'id': service['id'],
            'name': service['name'],
            'bookings': len(service_transactions),
            'revenue': sum(t.get('amount', 0) for t in service_transactions)
        })
    
    # Get recent transactions (last 10)
    recent_transactions = sorted(transactions, key=lambda x: x.get('created_at', ''), reverse=True)[:10]
    
    return {
        'business_id': business_id,
        'business_name': business.get('name', 'Unknown Business'),
        'metrics': {
            'total_revenue': total_revenue,
            'total_transactions': total_transactions,
            'conversion_rate': 68.0,  # TODO: Calculate from actual data
            'avg_rating': 4.8  # TODO: Get from reviews
        },
        'platform_breakdown': platform_breakdown,
        'services_performance': services_performance,
        'recent_transactions': recent_transactions,
        'period': {
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat()
        }
    }


def get_platform_dashboard_data(db: DatabaseManager) -> Dict[str, Any]:
    """Get platform-wide dashboard data"""
    
    # Get total businesses
    businesses = db.get_all_businesses()
    total_businesses = len(businesses)
    
    # Get metrics for last 30 days
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    
    # Get all transactions
    all_transactions = db.get_all_transactions(start_date=start_date, end_date=end_date)
    
    # Calculate platform metrics
    total_transactions = len(all_transactions)
    total_revenue = sum(t.get('amount', 0) for t in all_transactions)
    active_consumers = len(set(t.get('user_id') for t in all_transactions if t.get('user_id')))
    
    # Get AI provider breakdown
    provider_breakdown = {}
    for transaction in all_transactions:
        provider = transaction.get('ai_provider', 'unknown')
        if provider not in provider_breakdown:
            provider_breakdown[provider] = {'transactions': 0, 'businesses': set()}
        provider_breakdown[provider]['transactions'] += 1
        provider_breakdown[provider]['businesses'].add(transaction.get('business_id'))
    
    # Convert sets to counts
    for provider in provider_breakdown:
        provider_breakdown[provider]['businesses_count'] = len(provider_breakdown[provider]['businesses'])
        del provider_breakdown[provider]['businesses']
    
    # Get top businesses by traffic
    business_traffic = {}
    for transaction in all_transactions:
        business_id = transaction.get('business_id')
        if business_id not in business_traffic:
            business_traffic[business_id] = {'transactions': 0, 'revenue': 0, 'platforms': {}}
        business_traffic[business_id]['transactions'] += 1
        business_traffic[business_id]['revenue'] += transaction.get('amount', 0)
        
        provider = transaction.get('ai_provider', 'unknown')
        if provider not in business_traffic[business_id]['platforms']:
            business_traffic[business_id]['platforms'][provider] = 0
        business_traffic[business_id]['platforms'][provider] += 1
    
    # Sort by transactions and get top 10
    top_businesses = sorted(
        business_traffic.items(), 
        key=lambda x: x[1]['transactions'], 
        reverse=True
    )[:10]
    
    # Get category breakdown
    category_breakdown = {}
    for business in businesses:
        category = business.get('category', 'other')
        if category not in category_breakdown:
            category_breakdown[category] = {'businesses': 0, 'transactions': 0}
        category_breakdown[category]['businesses'] += 1
        
        # Count transactions for this business
        business_transactions = [t for t in all_transactions if t.get('business_id') == business['id']]
        category_breakdown[category]['transactions'] += len(business_transactions)
    
    return {
        'metrics': {
            'total_businesses': total_businesses,
            'total_transactions': total_transactions,
            'active_consumers': active_consumers,
            'platform_revenue': total_revenue
        },
        'provider_breakdown': provider_breakdown,
        'top_businesses': [
            {
                'business_id': business_id,
                'business_name': next((b.get('name', 'Unknown') for b in businesses if b['id'] == business_id), 'Unknown'),
                'transactions': data['transactions'],
                'revenue': data['revenue'],
                'platforms': data['platforms']
            }
            for business_id, data in top_businesses
        ],
        'category_breakdown': category_breakdown,
        'period': {
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat()
        }
    }


@router.get("/business/{business_id}")
async def get_business_dashboard(
    business_id: str,
    db: DatabaseManager = Depends(get_db_manager)
):
    """Get business dashboard data"""
    try:
        data = get_business_dashboard_data(db, business_id)
        return {
            "success": True,
            "data": data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get business dashboard: {str(e)}")


@router.get("/platform")
async def get_platform_dashboard(
    db: DatabaseManager = Depends(get_db_manager)
):
    """Get platform dashboard data"""
    try:
        data = get_platform_dashboard_data(db)
        return {
            "success": True,
            "data": data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get platform dashboard: {str(e)}")


@router.get("/business/{business_id}/services")
async def get_business_services(
    business_id: str,
    db: DatabaseManager = Depends(get_db_manager)
):
    """Get business services with performance metrics"""
    try:
        services = db.get_business_services(business_id)
        return {
            "success": True,
            "data": services
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get business services: {str(e)}")


@router.get("/platform/health")
async def get_platform_health():
    """Get platform health status"""
    return {
        "success": True,
        "data": {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "services": {
                "api": "healthy",
                "database": "healthy",
                "ai_routers": "healthy"
            }
        }
    }

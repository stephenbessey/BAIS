#!/usr/bin/env python3
"""
BA Integrate - Database Seeding Script
Creates initial data for production deployment
"""

import os
import sys
import asyncio
from datetime import datetime, timezone
from pathlib import Path

# Add the backend directory to the Python path
backend_dir = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

try:
    from production.core.database import get_database
    from production.core.security import hash_password
    from production.models import User, Business, APIKey
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure you're running this from the BAIS directory")
    sys.exit(1)


async def seed_initial_data():
    """Seed the database with initial production data"""
    print("🌱 Starting database seeding...")
    
    try:
        # Get database connection
        db = get_database()
        
        # Create default admin user
        admin_user = await create_admin_user(db)
        print(f"✅ Created admin user: {admin_user.email}")
        
        # Create sample business
        business = await create_sample_business(db)
        print(f"✅ Created sample business: {business.name}")
        
        # Create API key for the business
        api_key = await create_api_key(db, business.id)
        print(f"✅ Created API key: {api_key.key[:8]}...")
        
        print("🎉 Database seeding completed successfully!")
        
    except Exception as e:
        print(f"❌ Error during seeding: {e}")
        sys.exit(1)


async def create_admin_user(db):
    """Create default admin user"""
    admin_email = os.getenv("ADMIN_EMAIL", "admin@baintegrate.com")
    admin_password = os.getenv("ADMIN_PASSWORD", "changeme123!")
    
    # Check if admin user already exists
    existing_user = await db.users.find_one({"email": admin_email})
    if existing_user:
        print(f"⚠️  Admin user {admin_email} already exists")
        return existing_user
    
    # Create admin user
    user_data = {
        "email": admin_email,
        "password_hash": hash_password(admin_password),
        "role": "admin",
        "is_active": True,
        "is_verified": True,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc)
    }
    
    result = await db.users.insert_one(user_data)
    user_data["_id"] = result.inserted_id
    return user_data


async def create_sample_business(db):
    """Create sample business for testing"""
    business_data = {
        "name": "Sample Business",
        "email": "contact@samplebusiness.com",
        "industry": "E-commerce",
        "plan": "professional",
        "is_active": True,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc)
    }
    
    result = await db.businesses.insert_one(business_data)
    business_data["_id"] = result.inserted_id
    return business_data


async def create_api_key(db, business_id):
    """Create API key for business"""
    import secrets
    
    api_key = f"bai_{secrets.token_urlsafe(32)}"
    
    key_data = {
        "business_id": business_id,
        "key": api_key,
        "name": "Production Key",
        "is_active": True,
        "created_at": datetime.now(timezone.utc),
        "expires_at": None  # No expiration
    }
    
    result = await db.api_keys.insert_one(key_data)
    key_data["_id"] = result.inserted_id
    
    # Print the API key (only time it will be shown)
    print(f"🔑 API Key: {api_key}")
    print("⚠️  Save this API key - it won't be shown again!")
    
    return key_data


if __name__ == "__main__":
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    # Run the seeding
    asyncio.run(seed_initial_data())

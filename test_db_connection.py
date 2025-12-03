#!/usr/bin/env python3
"""
Test database connection and table creation
"""

import os
import sys
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent / "backend" / "production"
sys.path.insert(0, str(backend_dir))

def test_database_connection(database_url: str):
    """Test database connection and table creation"""
    print(f"Testing database connection...")
    print(f"Database URL: {database_url[:50]}...")

    try:
        from core.database_models import DatabaseManager, Business

        # Create database manager
        print("\n1. Creating DatabaseManager...")
        db_manager = DatabaseManager(database_url)
        print("✓ DatabaseManager created successfully")

        # Test connection by creating tables
        print("\n2. Creating database tables...")
        db_manager.create_tables()
        print("✓ Tables created successfully")

        # Test session
        print("\n3. Testing database session...")
        with db_manager.get_session() as session:
            # Count businesses
            count = session.query(Business).count()
            print(f"✓ Session working! Current business count: {count}")

        print("\n✅ Database connection test PASSED!")
        return True

    except Exception as e:
        print(f"\n❌ Database connection test FAILED!")
        print(f"Error: {e}")
        import traceback
        print(f"\nFull traceback:\n{traceback.format_exc()}")
        return False

if __name__ == "__main__":
    # Get DATABASE_URL from environment or use provided one
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        print("ERROR: DATABASE_URL not set in environment")
        print("\nUsage:")
        print("  export DATABASE_URL='postgresql://...'")
        print("  python test_db_connection.py")
        sys.exit(1)

    success = test_database_connection(database_url)
    sys.exit(0 if success else 1)

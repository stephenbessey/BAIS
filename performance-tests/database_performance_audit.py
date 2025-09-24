"""
Database Performance Audit
Identifies slow queries and suggests optimizations
"""

import asyncio
from sqlalchemy import text
from backend.production.core.database import get_database_session

class DatabasePerformanceAuditor:
    """Audit database performance"""
    
    async def analyze_slow_queries(self):
        """Analyze slow queries from pg_stat_statements"""
        async with get_database_session() as session:
            # Enable pg_stat_statements if not enabled
            await session.execute(text(
                "CREATE EXTENSION IF NOT EXISTS pg_stat_statements"
            ))
            
            # Get top 10 slowest queries
            result = await session.execute(text("""
                SELECT 
                    query,
                    calls,
                    mean_exec_time,
                    max_exec_time,
                    total_exec_time,
                    rows
                FROM pg_stat_statements
                ORDER BY mean_exec_time DESC
                LIMIT 10
            """))
            
            print("\n" + "="*80)
            print("TOP 10 SLOWEST QUERIES")
            print("="*80 + "\n")
            
            for row in result:
                print(f"Query: {row.query[:100]}...")
                print(f"  Calls: {row.calls}")
                print(f"  Mean Time: {row.mean_exec_time:.2f}ms")
                print(f"  Max Time: {row.max_exec_time:.2f}ms")
                print(f"  Total Time: {row.total_exec_time:.2f}ms")
                print(f"  Rows: {row.rows}")
                print()
    
    async def check_missing_indexes(self):
        """Check for missing indexes"""
        async with get_database_session() as session:
            result = await session.execute(text("""
                SELECT 
                    schemaname,
                    tablename,
                    attname,
                    n_tup_read,
                    n_tup_fetch,
                    idx_scan,
                    idx_tup_read,
                    idx_tup_fetch
                FROM pg_stat_user_tables
                JOIN pg_attribute ON pg_attribute.attrelid = pg_stat_user_tables.relid
                WHERE idx_scan = 0
                AND n_tup_read > 1000
                ORDER BY n_tup_read DESC
                LIMIT 10
            """))
            
            print("\n" + "="*80)
            print("POTENTIAL MISSING INDEXES")
            print("="*80 + "\n")
            
            for row in result:
                print(f"Table: {row.schemaname}.{row.tablename}")
                print(f"  Column: {row.attname}")
                print(f"  Sequential Scans: {row.n_tup_read}")
                print(f"  Recommendation: CREATE INDEX ON {row.tablename}({row.attname});")
                print()
    
    async def check_table_bloat(self):
        """Check for table bloat"""
        async with get_database_session() as session:
            result = await session.execute(text("""
                SELECT
                    schemaname,
                    tablename,
                    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size,
                    n_dead_tup,
                    n_live_tup,
                    ROUND(n_dead_tup::numeric / NULLIF(n_live_tup, 0) * 100, 2) AS dead_ratio
                FROM pg_stat_user_tables
                WHERE n_dead_tup > 1000
                ORDER BY n_dead_tup DESC
                LIMIT 10
            """))
            
            print("\n" + "="*80)
            print("TABLE BLOAT ANALYSIS")
            print("="*80 + "\n")
            
            for row in result:
                print(f"Table: {row.schemaname}.{row.tablename}")
                print(f"  Size: {row.size}")
                print(f"  Dead Tuples: {row.n_dead_tup}")
                print(f"  Live Tuples: {row.n_live_tup}")
                print(f"  Dead Ratio: {row.dead_ratio}%")
                if row.dead_ratio and row.dead_ratio > 20:
                    print(f"  ⚠️  Recommendation: VACUUM ANALYZE {row.tablename};")
                print()

async def main():
    auditor = DatabasePerformanceAuditor()
    await auditor.analyze_slow_queries()
    await auditor.check_missing_indexes()
    await auditor.check_table_bloat()

if __name__ == "__main__":
    asyncio.run(main())

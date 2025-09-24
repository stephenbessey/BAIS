-- ============================================================================
-- DATABASE PERFORMANCE OPTIMIZATIONS
-- ============================================================================

-- 1. Add missing indexes based on query patterns
CREATE INDEX IF NOT EXISTS idx_businesses_type ON businesses(type);
CREATE INDEX IF NOT EXISTS idx_businesses_ap2_enabled ON businesses(ap2_enabled);
CREATE INDEX IF NOT EXISTS idx_bookings_user_id ON bookings(user_id);
CREATE INDEX IF NOT EXISTS idx_bookings_business_id ON bookings(business_id);
CREATE INDEX IF NOT EXISTS idx_bookings_status ON bookings(status);
CREATE INDEX IF NOT EXISTS idx_bookings_created_at ON bookings(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_mandates_user_id ON ap2_mandates(user_id);
CREATE INDEX IF NOT EXISTS idx_mandates_business_id ON ap2_mandates(business_id);
CREATE INDEX IF NOT EXISTS idx_mandates_status ON ap2_mandates(status);
CREATE INDEX IF NOT EXISTS idx_mandates_expires_at ON ap2_mandates(expires_at);

-- 2. Add composite indexes for common query patterns
CREATE INDEX IF NOT EXISTS idx_bookings_user_status ON bookings(user_id, status);
CREATE INDEX IF NOT EXISTS idx_mandates_user_status ON ap2_mandates(user_id, status);

-- 3. Add partial indexes for common filters
CREATE INDEX IF NOT EXISTS idx_bookings_active ON bookings(id) 
    WHERE status IN ('confirmed', 'pending');
CREATE INDEX IF NOT EXISTS idx_mandates_active ON ap2_mandates(id) 
    WHERE status = 'active';

-- 4. Optimize JSON columns
CREATE INDEX IF NOT EXISTS idx_bookings_service_details_gin 
    ON bookings USING gin(service_details);
CREATE INDEX IF NOT EXISTS idx_businesses_integration_gin 
    ON businesses USING gin(integration_config);

-- 5. Add indexes for sorting operations
CREATE INDEX IF NOT EXISTS idx_bookings_created_desc ON bookings(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_mandates_created_desc ON ap2_mandates(created_at DESC);

-- 6. Vacuum and analyze tables
VACUUM ANALYZE businesses;
VACUUM ANALYZE bookings;
VACUUM ANALYZE ap2_mandates;
VACUUM ANALYZE ap2_transactions;

-- 7. Update table statistics
ANALYZE businesses;
ANALYZE bookings;
ANALYZE ap2_mandates;

-- 8. Set appropriate table storage parameters
ALTER TABLE bookings SET (fillfactor = 90);
ALTER TABLE ap2_mandates SET (fillfactor = 90);

-- 9. Enable parallel query execution for large tables
ALTER TABLE bookings SET (parallel_workers = 4);
ALTER TABLE businesses SET (parallel_workers = 2);

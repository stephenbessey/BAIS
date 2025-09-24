#!/bin/bash

# Day 3: OAuth 2.0 & Authentication Security Script
# Comprehensive authentication security testing and validation

set -e

echo "🔒 Starting Day 3: OAuth 2.0 & Authentication Security"
echo "====================================================="

# Create security reports directory
mkdir -p security-reports

# Create authentication security checklist
echo "📋 Creating authentication security checklist..."
cat > security-reports/day3-auth-security.md << 'EOF'
# Authentication Security Audit

## OAuth 2.0 Implementation Review

### JWT Token Security
- [ ] JWT_SECRET_KEY is strong (256+ bits)?
- [ ] JWT algorithm is HS256 or RS256?
- [ ] Token expiration is properly set?
- [ ] Refresh token rotation implemented?
- [ ] Token revocation mechanism exists?

### OAuth 2.0 Flows
- [ ] Authorization Code flow implemented correctly?
- [ ] PKCE (Proof Key for Code Exchange) enabled?
- [ ] State parameter used to prevent CSRF?
- [ ] Redirect URI validation in place?
- [ ] Scope validation implemented?

### Session Management
- [ ] Session timeout configured (< 60 minutes)?
- [ ] Session invalidation on logout?
- [ ] Concurrent session limits?
- [ ] Session fixation prevention?

### Password Security (if applicable)
- [ ] Passwords hashed with bcrypt/argon2?
- [ ] Minimum password length enforced (12+ chars)?
- [ ] Password complexity requirements?
- [ ] Rate limiting on login attempts?
- [ ] Account lockout after failed attempts?

## Security Headers Validation
- [ ] X-Content-Type-Options: nosniff
- [ ] X-Frame-Options: DENY or SAMEORIGIN
- [ ] X-XSS-Protection: 1; mode=block
- [ ] Content-Security-Policy configured
- [ ] Strict-Transport-Security configured

## Issues Found
1. 
2. 
3.

## Remediation Actions
- [ ] 
- [ ] 
EOF

# Run authentication security tests
echo "🧪 Running authentication security tests..."
pytest backend/production/tests/security/test_authentication_security.py -v --tb=short > security-reports/day3-auth-test-results.txt 2>&1

# Test JWT secret strength
echo "🔍 Testing JWT secret strength..."
python -c "
import os
import secrets
from backend.production.core.secrets_manager import get_secrets_manager

try:
    manager = get_secrets_manager()
    jwt_secret = manager.get_jwt_secret()
    
    print(f'JWT Secret Length: {len(jwt_secret)} characters')
    print(f'JWT Secret Strength: {\"Strong\" if len(jwt_secret) >= 32 else \"Weak\"}')
    print(f'Contains Special Chars: {any(c in jwt_secret for c in \"!@#$%^&*()_+-=[]{}|;:,.<>?\")}')
    
    # Generate recommended strong secret
    strong_secret = secrets.token_urlsafe(64)
    print(f'Recommended Strong Secret Length: {len(strong_secret)}')
    
except Exception as e:
    print(f'JWT Secret Test Failed: {e}')
    print('This is expected if JWT_SECRET_KEY environment variable is not set.')
" > security-reports/day3-jwt-secret-test.txt

# Test OAuth configuration
echo "🔍 Testing OAuth configuration..."
python -c "
import os
from backend.production.core.secrets_manager import get_secrets_manager

try:
    manager = get_secrets_manager()
    oauth_creds = manager.get_oauth_credentials()
    
    print('OAuth Configuration Test:')
    for key, value in oauth_creds.items():
        present = bool(value)
        print(f'  {key}: {\"✅ Present\" if present else \"❌ Missing\"}')
        
    if all(oauth_creds.values()):
        print('✅ All OAuth credentials configured')
    else:
        print('❌ Some OAuth credentials missing')
        
except Exception as e:
    print(f'OAuth Configuration Test Failed: {e}')
    print('This is expected if OAuth environment variables are not set.')
" > security-reports/day3-oauth-config-test.txt

# Test authentication service
echo "🔍 Testing authentication service..."
python -c "
import jwt
from datetime import datetime, timedelta
from backend.production.core.constants import SecurityConstants

# Test JWT token creation and validation
try:
    # Create test token
    payload = {
        'sub': 'test_user',
        'exp': datetime.utcnow() + timedelta(hours=1),
        'iat': datetime.utcnow(),
        'iss': SecurityConstants.JWT_ISSUER,
        'aud': SecurityConstants.JWT_AUDIENCE
    }
    
    test_secret = 'test_jwt_secret_for_validation'
    token = jwt.encode(payload, test_secret, algorithm=SecurityConstants.JWT_ALGORITHM)
    
    print('✅ JWT Token Creation Test: PASSED')
    print(f'Token Algorithm: {SecurityConstants.JWT_ALGORITHM}')
    print(f'Token Issuer: {SecurityConstants.JWT_ISSUER}')
    print(f'Token Audience: {SecurityConstants.JWT_AUDIENCE}')
    
    # Test token validation
    decoded = jwt.decode(token, test_secret, algorithms=[SecurityConstants.JWT_ALGORITHM], 
                        audience=SecurityConstants.JWT_AUDIENCE, issuer=SecurityConstants.JWT_ISSUER)
    
    print('✅ JWT Token Validation Test: PASSED')
    print(f'Decoded Subject: {decoded.get(\"sub\")}')
    
except Exception as e:
    print(f'❌ JWT Token Test Failed: {e}')

# Test token expiration
try:
    expired_payload = {
        'sub': 'test_user',
        'exp': datetime.utcnow() - timedelta(hours=1),  # Expired
        'iat': datetime.utcnow() - timedelta(hours=2),
        'iss': SecurityConstants.JWT_ISSUER,
        'aud': SecurityConstants.JWT_AUDIENCE
    }
    
    expired_token = jwt.encode(expired_payload, test_secret, algorithm=SecurityConstants.JWT_ALGORITHM)
    
    try:
        jwt.decode(expired_token, test_secret, algorithms=[SecurityConstants.JWT_ALGORITHM])
        print('❌ Expired Token Test: FAILED (should have been rejected)')
    except jwt.ExpiredSignatureError:
        print('✅ Expired Token Test: PASSED (correctly rejected)')
        
except Exception as e:
    print(f'❌ Expired Token Test Failed: {e}')

" > security-reports/day3-jwt-validation-test.txt

# Test security headers (if server is running)
echo "🔍 Testing security headers..."
cat > security-reports/day3-security-headers-test.txt << 'EOF'
# Security Headers Test

## Expected Security Headers
- X-Content-Type-Options: nosniff
- X-Frame-Options: DENY or SAMEORIGIN
- X-XSS-Protection: 1; mode=block
- Content-Security-Policy: default-src 'self'
- Strict-Transport-Security: max-age=31536000; includeSubDomains (HTTPS only)

## Test Commands (run if server is available)
# curl -I http://localhost:8000/health
# curl -I https://yourdomain.com/health

## Manual Verification Required
- [ ] Check that all security headers are present
- [ ] Verify HSTS is only set for HTTPS endpoints
- [ ] Confirm CSP policy is appropriate for your application
- [ ] Test X-Frame-Options prevents clickjacking

EOF

# Test rate limiting configuration
echo "🔍 Testing rate limiting configuration..."
python -c "
from backend.production.core.constants import SecurityLimits

print('Rate Limiting Configuration:')
print(f'  Default Rate Limit: {SecurityLimits.DEFAULT_RATE_LIMIT_PER_MINUTE} requests/minute')
print(f'  Burst Rate Limit: {SecurityLimits.BURST_RATE_LIMIT_PER_MINUTE} requests/minute')
print(f'  Rate Limit Window: 60 seconds')

# Check if rate limiting is implemented
try:
    from backend.production.core.rate_limiter import RateLimiter
    print('✅ Rate Limiter module found')
except ImportError:
    print('❌ Rate Limiter module not found - implement rate limiting')
    
print('')
print('Rate Limiting Test Recommendations:')
print('1. Test normal request rate (should succeed)')
print('2. Test burst requests (should succeed)')
print('3. Test excessive requests (should be rate limited)')
print('4. Test rate limit reset after window expires')
" > security-reports/day3-rate-limiting-test.txt

# Generate authentication security summary
echo "📊 Generating authentication security summary..."
cat > security-reports/day3-auth-security-summary.md << 'EOF'
# Day 3 Authentication Security Summary

## Test Results

### Authentication Security Tests
- Results: [day3-auth-test-results.txt](day3-auth-test-results.txt)

### JWT Secret Strength Test
- Results: [day3-jwt-secret-test.txt](day3-jwt-secret-test.txt)

### OAuth Configuration Test
- Results: [day3-oauth-config-test.txt](day3-oauth-config-test.txt)

### JWT Validation Test
- Results: [day3-jwt-validation-test.txt](day3-jwt-validation-test.txt)

### Security Headers Test
- Results: [day3-security-headers-test.txt](day3-security-headers-test.txt)

### Rate Limiting Test
- Results: [day3-rate-limiting-test.txt](day3-rate-limiting-test.txt)

## Critical Issues (P0 - Fix Immediately)
- [ ] Review authentication test failures
- [ ] Fix JWT secret strength if weak
- [ ] Implement missing OAuth credentials

## High Priority Issues (P1 - Fix This Week)
- [ ] Implement rate limiting if missing
- [ ] Add security headers if missing
- [ ] Fix authentication flow issues

## Medium Priority Issues (P2 - Fix Before Production)
- [ ] Enhance password security requirements
- [ ] Implement session management improvements
- [ ] Add additional OAuth security features

## Security Recommendations

### JWT Security
1. Use strong JWT secrets (64+ characters)
2. Implement proper token expiration
3. Use secure algorithms (RS256 recommended)
4. Implement token revocation mechanism

### OAuth 2.0 Security
1. Enable PKCE for all OAuth flows
2. Validate redirect URIs strictly
3. Implement proper scope validation
4. Use state parameter for CSRF protection

### Rate Limiting
1. Implement rate limiting on auth endpoints
2. Use different limits for different user types
3. Implement progressive delays for repeated failures
4. Monitor for brute force attempts

### Session Management
1. Use secure session cookies
2. Implement proper session timeout
3. Invalidate sessions on logout
4. Prevent session fixation attacks

## Next Steps
1. Review all test results
2. Fix critical and high priority issues
3. Implement missing security features
4. Document authentication security policies
5. Prepare for AP2 cryptographic validation (Day 4)

EOF

echo "✅ Day 3 authentication security audit completed!"
echo "📁 Reports saved in security-reports/ directory"
echo "🔍 Review the summary: security-reports/day3-auth-security-summary.md"
echo ""
echo "📝 Next steps:"
echo "1. Review authentication test results"
echo "2. Fix any JWT or OAuth configuration issues"
echo "3. Implement rate limiting if missing"
echo "4. Add security headers to responses"
echo "5. Document authentication security policies"

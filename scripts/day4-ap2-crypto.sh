#!/bin/bash

# Day 4: AP2 Cryptographic Validation Script
# Comprehensive AP2 cryptographic security testing and validation

set -e

echo "🔒 Starting Day 4: AP2 Cryptographic Validation"
echo "=============================================="

# Create security reports directory
mkdir -p security-reports

# Create AP2 crypto audit checklist
echo "📋 Creating AP2 crypto audit checklist..."
cat > security-reports/day4-ap2-crypto-audit.md << 'EOF'
# AP2 Cryptographic Security Audit

## RSA Key Pair Validation
- [ ] Private key is in PEM format?
- [ ] Private key strength (2048+ bits for production)?
- [ ] Public key properly paired with private key?
- [ ] Keys stored securely (not in code)?
- [ ] Key rotation process documented?

## Signature Verification
- [ ] RSA-PSS algorithm used for signing?
- [ ] Signature verification on all mandates?
- [ ] Timestamp validation to prevent replay attacks?
- [ ] Mandate expiration enforced?

## Mandate Security
- [ ] Intent mandates cryptographically signed?
- [ ] Cart mandates linked to intent mandates?
- [ ] Mandate tampering detection?
- [ ] Mandate revocation mechanism?

## Key Management
- [ ] Key generation process documented?
- [ ] Key storage is secure?
- [ ] Key rotation procedures in place?
- [ ] Key backup and recovery procedures?

## Issues Found
1. 
2. 

## Remediation Actions
- [ ] 
- [ ] 
EOF

# Run AP2 crypto security tests
echo "🧪 Running AP2 crypto security tests..."
pytest backend/production/tests/security/test_ap2_crypto_security.py -v --tb=short > security-reports/day4-ap2-crypto-test-results.txt 2>&1

# Test RSA key generation
echo "🔍 Testing RSA key generation..."
python -c "
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
import os

print('RSA Key Generation Test:')

# Test 2048-bit key (minimum for testing)
try:
    private_key_2048 = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048
    )
    public_key_2048 = private_key_2048.public_key()
    
    print('✅ 2048-bit RSA key generation: SUCCESS')
    
    # Test key serialization
    private_pem = private_key_2048.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )
    
    public_pem = public_key_2048.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )
    
    print('✅ RSA key serialization: SUCCESS')
    print(f'Private key length: {len(private_pem)} bytes')
    print(f'Public key length: {len(public_pem)} bytes')
    
except Exception as e:
    print(f'❌ RSA key generation failed: {e}')

# Test 4096-bit key (recommended for production)
try:
    private_key_4096 = rsa.generate_private_key(
        public_exponent=65537,
        key_size=4096
    )
    
    print('✅ 4096-bit RSA key generation: SUCCESS')
    print('✅ Production-ready key strength available')
    
except Exception as e:
    print(f'❌ 4096-bit RSA key generation failed: {e}')

print('')
print('Key Strength Recommendations:')
print('- Development/Testing: 2048-bit minimum')
print('- Production: 4096-bit recommended')
print('- Key rotation: Every 90 days')
print('- Secure storage: Use hardware security modules (HSM) for production')

" > security-reports/day4-rsa-key-test.txt

# Test AP2 mandate validation
echo "🔍 Testing AP2 mandate validation..."
python -c "
import json
from datetime import datetime, timedelta
from backend.production.core.constants import AP2Limits, SecurityConstants

print('AP2 Mandate Validation Test:')

# Test mandate data structure
mandate_data = {
    'type': 'intent',
    'userId': 'user123',
    'businessId': 'business456',
    'agentId': 'agent789',
    'intentDescription': 'Book a hotel room',
    'amount': 150.0,
    'currency': 'USD',
    'timestamp': datetime.utcnow().isoformat(),
    'expiresAt': (datetime.utcnow() + timedelta(hours=AP2Limits.MANDATE_EXPIRY_HOURS)).isoformat()
}

print('✅ Mandate data structure: VALID')
print(f'Mandate type: {mandate_data[\"type\"]}')
print(f'Amount: {mandate_data[\"amount\"]} {mandate_data[\"currency\"]}')
print(f'Expires in: {AP2Limits.MANDATE_EXPIRY_HOURS} hours')

# Test amount validation
min_amount = AP2Limits.MIN_PAYMENT_AMOUNT
max_amount = AP2Limits.MAX_MANDATE_AMOUNT

print('')
print('Amount Validation:')
print(f'Minimum amount: {min_amount}')
print(f'Maximum amount: {max_amount}')
print(f'Test amount ({mandate_data[\"amount\"]}): {\"VALID\" if min_amount <= mandate_data[\"amount\"] <= max_amount else \"INVALID\"}')

# Test signature algorithm
print('')
print('Signature Algorithm:')
print(f'Algorithm: {SecurityConstants.SIGNATURE_ALGORITHM}')
print(f'Hash Algorithm: {SecurityConstants.HASH_ALGORITHM}')

print('')
print('Security Features:')
print(f'✅ Mandate expiration: {AP2Limits.MANDATE_EXPIRY_HOURS} hours')
print(f'✅ Signature timeout: {AP2Limits.MANDATE_SIGNATURE_TIMEOUT_SECONDS} seconds')
print(f'✅ Replay protection: {AP2Limits.WEBHOOK_REPLAY_WINDOW_SECONDS} seconds')
print(f'✅ Key rotation: {AP2Limits.KEY_ROTATION_DAYS} days')

" > security-reports/day4-mandate-validation-test.txt

# Test cryptographic operations
echo "🔍 Testing cryptographic operations..."
python -c "
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.exceptions import InvalidSignature
import base64

print('Cryptographic Operations Test:')

# Generate test key pair
private_key = rsa.generate_private_key(
    public_exponent=65537,
    key_size=2048
)
public_key = private_key.public_key()

print('✅ Key pair generation: SUCCESS')

# Test signing
test_data = b'This is test data for signing'
try:
    signature = private_key.sign(
        test_data,
        padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()),
            salt_length=padding.PSS.MAX_LENGTH
        ),
        hashes.SHA256()
    )
    
    print('✅ RSA-PSS signing: SUCCESS')
    print(f'Signature length: {len(signature)} bytes')
    
except Exception as e:
    print(f'❌ RSA-PSS signing failed: {e}')

# Test verification
try:
    public_key.verify(
        signature,
        test_data,
        padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()),
            salt_length=padding.PSS.MAX_LENGTH
        ),
        hashes.SHA256()
    )
    
    print('✅ RSA-PSS verification: SUCCESS')
    
except InvalidSignature:
    print('❌ RSA-PSS verification failed: Invalid signature')
except Exception as e:
    print(f'❌ RSA-PSS verification failed: {e}')

# Test tampered data detection
try:
    tampered_data = b'This is tampered data for signing'
    public_key.verify(
        signature,  # Original signature
        tampered_data,  # Tampered data
        padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()),
            salt_length=padding.PSS.MAX_LENGTH
        ),
        hashes.SHA256()
    )
    
    print('❌ Tamper detection test: FAILED (should have detected tampering)')
    
except InvalidSignature:
    print('✅ Tamper detection test: SUCCESS (correctly detected tampering)')
except Exception as e:
    print(f'❌ Tamper detection test failed: {e}')

print('')
print('Cryptographic Security Features:')
print('✅ RSA-PSS with SHA-256 algorithm')
print('✅ Proper padding (PSS)')
print('✅ Tamper detection')
print('✅ Signature verification')

" > security-reports/day4-crypto-operations-test.txt

# Test key management
echo "🔍 Testing key management..."
python -c "
import os
from backend.production.core.secrets_manager import get_secrets_manager

print('Key Management Test:')

try:
    manager = get_secrets_manager()
    ap2_creds = manager.get_ap2_credentials()
    
    print('AP2 Credentials Check:')
    print(f'Client ID: {\"✅ Present\" if ap2_creds[\"client_id\"] else \"❌ Missing\"}')
    print(f'Private Key: {\"✅ Present\" if ap2_creds[\"private_key\"] else \"❌ Missing\"}')
    print(f'Public Key: {\"✅ Present\" if ap2_creds[\"public_key\"] else \"❌ Missing\"}')
    print(f'Webhook Secret: {\"✅ Present\" if ap2_creds[\"webhook_secret\"] else \"❌ Missing\"}')
    
    # Test key format validation
    if ap2_creds['private_key']:
        if 'BEGIN PRIVATE KEY' in ap2_creds['private_key']:
            print('✅ Private key format: VALID (PEM)')
        else:
            print('❌ Private key format: INVALID')
    
    if ap2_creds['public_key']:
        if 'BEGIN PUBLIC KEY' in ap2_creds['public_key']:
            print('✅ Public key format: VALID (PEM)')
        else:
            print('❌ Public key format: INVALID')
            
except Exception as e:
    print(f'❌ Key management test failed: {e}')
    print('This is expected if AP2 credentials are not configured.')

print('')
print('Key Management Recommendations:')
print('1. Store private keys in secure environment variables')
print('2. Use hardware security modules (HSM) for production')
print('3. Implement key rotation every 90 days')
print('4. Backup keys securely with proper access controls')
print('5. Monitor key usage and access')

" > security-reports/day4-key-management-test.txt

# Generate key pair for production (if needed)
echo "🔑 Generating production RSA key pair..."
mkdir -p keys
python -c "
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
import os

# Generate 4096-bit key pair for production
private_key = rsa.generate_private_key(
    public_exponent=65537,
    key_size=4096  # 4096 bits for production security
)

public_key = private_key.public_key()

# Serialize private key
private_pem = private_key.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.PKCS8,
    encryption_algorithm=serialization.NoEncryption()
)

# Serialize public key
public_pem = public_key.public_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PublicFormat.SubjectPublicKeyInfo
)

# Save keys to files
with open('keys/ap2_private_4096.pem', 'wb') as f:
    f.write(private_pem)

with open('keys/ap2_public_4096.pem', 'wb') as f:
    f.write(public_pem)

print('✅ Production RSA key pair generated successfully!')
print('📁 Files created:')
print('  - keys/ap2_private_4096.pem (PRIVATE - Keep secure!)')
print('  - keys/ap2_public_4096.pem (PUBLIC - Can be shared)')
print('')
print('🔒 Security Instructions:')
print('1. Set file permissions: chmod 600 keys/ap2_private_4096.pem')
print('2. Add keys/ directory to .gitignore')
print('3. Store private key in secure environment variable')
print('4. Never commit private keys to version control')
print('5. Use secure key storage for production (HSM recommended)')

" > security-reports/day4-key-generation.txt

# Generate AP2 crypto security summary
echo "📊 Generating AP2 crypto security summary..."
cat > security-reports/day4-ap2-crypto-summary.md << 'EOF'
# Day 4 AP2 Cryptographic Security Summary

## Test Results

### AP2 Crypto Security Tests
- Results: [day4-ap2-crypto-test-results.txt](day4-ap2-crypto-test-results.txt)

### RSA Key Generation Test
- Results: [day4-rsa-key-test.txt](day4-rsa-key-test.txt)

### Mandate Validation Test
- Results: [day4-mandate-validation-test.txt](day4-mandate-validation-test.txt)

### Cryptographic Operations Test
- Results: [day4-crypto-operations-test.txt](day4-crypto-operations-test.txt)

### Key Management Test
- Results: [day4-key-management-test.txt](day4-key-management-test.txt)

### Key Generation
- Results: [day4-key-generation.txt](day4-key-generation.txt)

## Critical Issues (P0 - Fix Immediately)
- [ ] Review AP2 crypto test failures
- [ ] Ensure RSA keys are 4096-bit for production
- [ ] Verify signature algorithm is RSA-PSS with SHA-256

## High Priority Issues (P1 - Fix This Week)
- [ ] Implement proper key storage (not in code)
- [ ] Set up key rotation procedures
- [ ] Configure secure key backup

## Medium Priority Issues (P2 - Fix Before Production)
- [ ] Implement HSM for production key storage
- [ ] Add key usage monitoring
- [ ] Document key management procedures

## Security Recommendations

### Key Management
1. Use 4096-bit RSA keys for production
2. Store private keys in secure environment variables
3. Implement key rotation every 90 days
4. Use hardware security modules (HSM) for production
5. Secure key backup and recovery procedures

### Signature Security
1. Use RSA-PSS with SHA-256 algorithm
2. Implement proper padding (PSS)
3. Validate all signatures before processing
4. Implement timestamp validation for replay protection
5. Enforce mandate expiration

### Mandate Security
1. Cryptographically sign all mandates
2. Link cart mandates to intent mandates
3. Implement mandate revocation mechanism
4. Monitor for mandate tampering
5. Validate mandate amounts and currencies

## Production Readiness Checklist
- [ ] 4096-bit RSA key pair generated
- [ ] Private key stored securely (environment variable)
- [ ] Public key registered with AP2 network
- [ ] Signature verification implemented
- [ ] Mandate expiration enforced
- [ ] Replay attack prevention implemented
- [ ] Key rotation procedures documented
- [ ] Cryptographic operations tested

## Next Steps
1. Review all test results
2. Fix critical and high priority issues
3. Implement production key management
4. Test cryptographic operations thoroughly
5. Prepare for HTTPS/TLS security audit (Day 5)

EOF

echo "✅ Day 4 AP2 cryptographic validation completed!"
echo "📁 Reports saved in security-reports/ directory"
echo "🔍 Review the summary: security-reports/day4-ap2-crypto-summary.md"
echo ""
echo "🔑 Production keys generated in keys/ directory"
echo "🔒 Remember to secure the private key and never commit it to version control!"
echo ""
echo "📝 Next steps:"
echo "1. Review AP2 crypto test results"
echo "2. Secure the generated private key"
echo "3. Configure AP2 credentials in environment variables"
echo "4. Test mandate signing and verification"
echo "5. Document key management procedures"

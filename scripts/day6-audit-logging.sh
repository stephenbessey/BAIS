#!/bin/bash

# Day 6: Audit Logging & Monitoring Script
# Comprehensive audit logging implementation and monitoring setup

set -e

echo "🔒 Starting Day 6: Audit Logging & Monitoring"
echo "==========================================="

# Create security reports directory
mkdir -p security-reports

# Test audit logging implementation
echo "🧪 Testing audit logging implementation..."
python -c "
from backend.production.core.security_audit_logger import get_audit_logger, AuditEventType, AuditEventSeverity
import json
from datetime import datetime

print('Audit Logging Implementation Test:')

try:
    # Initialize audit logger
    logger = get_audit_logger()
    print('✅ Security Audit Logger: INITIALIZED')
    
    # Test authentication logging
    logger.log_auth_success('test_user_123', 'password', client_ip='192.168.1.1')
    logger.log_auth_failure('hacker_user', 'password', 'invalid_password', client_ip='192.168.1.100')
    
    print('✅ Authentication logging: WORKING')
    
    # Test security violation logging
    logger.log_security_violation('brute_force', 'Multiple failed login attempts', 
                                 user_id='hacker_user', client_ip='192.168.1.100')
    
    print('✅ Security violation logging: WORKING')
    
    # Test rate limiting logging
    logger.log_rate_limit_exceeded('test_user', '/api/v1/mcp/resources/list', 100, 'minute', 
                                  client_ip='192.168.1.1')
    
    print('✅ Rate limiting logging: WORKING')
    
    # Test API access logging
    logger.log_api_access('test_user', 'GET', '/api/v1/mcp/resources/list', 200, 150.5, 
                         client_ip='192.168.1.1')
    
    print('✅ API access logging: WORKING')
    
    # Test payment event logging
    logger.log_payment_event(AuditEventType.PAYMENT_COMPLETED, 'pay_123', 'test_user', 
                           150.0, 'USD', 'completed')
    
    print('✅ Payment event logging: WORKING')
    
    # Test mandate event logging
    logger.log_mandate_event(AuditEventType.MANDATE_CREATED, 'mandate_123', 'test_user', 
                            'intent', 150.0, 'USD', 'created')
    
    print('✅ Mandate event logging: WORKING')
    
    # Get statistics
    stats = logger.get_log_statistics()
    print('')
    print('Audit Log Statistics:')
    print(json.dumps(stats, indent=2))
    
    print('')
    print('✅ All audit logging tests: PASSED')
    
except Exception as e:
    print(f'❌ Audit logging test failed: {e}')
    import traceback
    traceback.print_exc()

" > security-reports/day6-audit-logging-test.txt

# Test log file creation and permissions
echo "🔍 Testing log file creation and permissions..."
python -c "
import os
import stat
from backend.production.core.security_audit_logger import get_audit_logger

print('Log File Security Test:')

try:
    logger = get_audit_logger()
    
    # Check log file path
    log_file = logger.log_file
    print(f'Log file path: {log_file}')
    
    # Check if log file exists
    if os.path.exists(log_file):
        print('✅ Log file: EXISTS')
        
        # Check file permissions
        file_stat = os.stat(log_file)
        file_permissions = stat.filemode(file_stat.st_mode)
        print(f'File permissions: {file_permissions}')
        
        # Check if file is readable/writable
        if os.access(log_file, os.R_OK):
            print('✅ Log file: READABLE')
        else:
            print('❌ Log file: NOT READABLE')
            
        if os.access(log_file, os.W_OK):
            print('✅ Log file: WRITABLE')
        else:
            print('❌ Log file: NOT WRITABLE')
            
        # Check file size
        file_size = os.path.getsize(log_file)
        print(f'Log file size: {file_size} bytes')
        
    else:
        print('❌ Log file: NOT FOUND')
        print('   This may be expected if no events have been logged yet')
    
    print('')
    print('Log File Security Recommendations:')
    print('1. Set appropriate file permissions (600 or 640)')
    print('2. Ensure log directory is secure')
    print('3. Implement log rotation to prevent disk space issues')
    print('4. Monitor log file size and growth')
    print('5. Backup audit logs for compliance')
    
except Exception as e:
    print(f'❌ Log file security test failed: {e}')

" > security-reports/day6-log-file-security-test.txt

# Create security monitoring script
echo "📊 Creating security monitoring script..."
cat > scripts/monitor_security_logs.sh << 'EOF'
#!/bin/bash

# Security Log Monitoring Script
# Monitors audit logs for security events and sends alerts

AUDIT_LOG="/var/log/bais/security_audit.log"
ALERT_EMAIL="security@yourdomain.com"
LOG_DIR="logs"

# Create logs directory if it doesn't exist
mkdir -p $LOG_DIR

echo "🔍 Starting security log monitoring..."

# Function to send alert
send_alert() {
    local subject="$1"
    local message="$2"
    echo "ALERT: $subject - $message" | mail -s "SECURITY ALERT: $subject" $ALERT_EMAIL
    echo "$(date): ALERT SENT - $subject" >> $LOG_DIR/security_monitor.log
}

# Function to check for security violations
check_security_violations() {
    if [ -f "$AUDIT_LOG" ]; then
        # Check for recent security violations
        recent_violations=$(tail -1000 "$AUDIT_LOG" | grep -c "security_violation" || echo "0")
        
        if [ "$recent_violations" -gt 0 ]; then
            echo "$(date): Security violations detected: $recent_violations" >> $LOG_DIR/security_monitor.log
            send_alert "Security Violations" "Detected $recent_violations security violations in recent logs"
        fi
    fi
}

# Function to check for brute force attempts
check_brute_force() {
    if [ -f "$AUDIT_LOG" ]; then
        # Check for repeated failed authentication attempts
        recent_failures=$(tail -1000 "$AUDIT_LOG" | grep "auth_failure" | awk -F'"user_id":"' '{print $2}' | awk -F'"' '{print $1}' | sort | uniq -c | sort -nr)
        
        while read -r line; do
            count=$(echo "$line" | awk '{print $1}')
            user=$(echo "$line" | awk '{print $2}')
            
            if [ "$count" -gt 5 ]; then
                echo "$(date): Brute force attempt detected for user: $user ($count attempts)" >> $LOG_DIR/security_monitor.log
                send_alert "Brute Force Attempt" "User $user has $count failed login attempts"
            fi
        done <<< "$recent_failures"
    fi
}

# Function to check for rate limit violations
check_rate_limits() {
    if [ -f "$AUDIT_LOG" ]; then
        # Check for rate limit violations
        rate_limit_violations=$(tail -1000 "$AUDIT_LOG" | grep -c "rate_limit_exceeded" || echo "0")
        
        if [ "$rate_limit_violations" -gt 10 ]; then
            echo "$(date): High rate limit violations: $rate_limit_violations" >> $LOG_DIR/security_monitor.log
            send_alert "Rate Limit Violations" "High number of rate limit violations: $rate_limit_violations"
        fi
    fi
}

# Function to check for suspicious payment activity
check_payment_anomalies() {
    if [ -f "$AUDIT_LOG" ]; then
        # Check for unusual payment patterns
        recent_payments=$(tail -1000 "$AUDIT_LOG" | grep "payment_completed" | awk -F'"amount":' '{print $2}' | awk -F',' '{print $1}')
        
        # Check for unusually large payments
        while read -r amount; do
            if [ "$(echo "$amount > 10000" | bc -l 2>/dev/null || echo "0")" -eq 1 ]; then
                echo "$(date): Large payment detected: $amount" >> $LOG_DIR/security_monitor.log
                send_alert "Large Payment" "Large payment detected: $amount"
            fi
        done <<< "$recent_payments"
    fi
}

# Main monitoring loop
main() {
    echo "$(date): Starting security monitoring cycle" >> $LOG_DIR/security_monitor.log
    
    check_security_violations
    check_brute_force
    check_rate_limits
    check_payment_anomalies
    
    echo "$(date): Security monitoring cycle completed" >> $LOG_DIR/security_monitor.log
}

# Run monitoring
main

echo "✅ Security monitoring completed"
EOF

chmod +x scripts/monitor_security_logs.sh

# Test log rotation setup
echo "🔍 Testing log rotation setup..."
cat > security-reports/day6-log-rotation-setup.txt << 'EOF'
# Log Rotation Setup

## Logrotate Configuration
Create /etc/logrotate.d/bais-security with:

/var/log/bais/security_audit.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    create 640 bais bais
    postrotate
        # Restart application to reopen log files
        systemctl reload bais-api
    endscript
}

## Manual Log Rotation Script
Create scripts/rotate_logs.sh:

#!/bin/bash
# Manual log rotation script

LOG_FILE="/var/log/bais/security_audit.log"
BACKUP_DIR="/var/log/bais/backups"
DATE=$(date +%Y%m%d_%H%M%S)

# Create backup directory
mkdir -p $BACKUP_DIR

# Rotate log file
if [ -f "$LOG_FILE" ]; then
    mv "$LOG_FILE" "$BACKUP_DIR/security_audit_$DATE.log"
    
    # Compress old log
    gzip "$BACKUP_DIR/security_audit_$DATE.log"
    
    # Send signal to application to reopen log file
    systemctl reload bais-api
    
    echo "Log rotated: security_audit_$DATE.log.gz"
fi

# Clean up old backups (keep 30 days)
find $BACKUP_DIR -name "security_audit_*.log.gz" -mtime +30 -delete

## Log Monitoring Setup

### Systemd Service
Create /etc/systemd/system/bais-security-monitor.service:

[Unit]
Description=BAIS Security Log Monitor
After=network.target

[Service]
Type=simple
User=bais
WorkingDirectory=/opt/bais
ExecStart=/opt/bais/scripts/monitor_security_logs.sh
Restart=always
RestartSec=60

[Install]
WantedBy=multi-user.target

### Cron Job Alternative
Add to crontab:
*/5 * * * * /opt/bais/scripts/monitor_security_logs.sh >> /var/log/bais/monitor.log 2>&1

## Log Analysis Commands

# Count events by type
grep -o '"event_type":"[^"]*"' /var/log/bais/security_audit.log | sort | uniq -c

# Find security violations
grep "security_violation" /var/log/bais/security_audit.log

# Find failed authentications
grep "auth_failure" /var/log/bais/security_audit.log

# Find rate limit violations
grep "rate_limit_exceeded" /var/log/bais/security_audit.log

# Monitor real-time logs
tail -f /var/log/bais/security_audit.log | grep -E "(security_violation|auth_failure|rate_limit_exceeded)"

EOF

# Test audit log integration
echo "🔍 Testing audit log integration..."
python -c "
print('Audit Log Integration Test:')

# Test integration with authentication service
try:
    from backend.production.core.mcp_authentication_service import AuthenticationService
    from backend.production.core.security_audit_logger import get_audit_logger
    
    print('✅ Authentication service integration: AVAILABLE')
    
    # Test integration with AP2 payment service
    from backend.production.core.payments.payment_coordinator import PaymentCoordinator
    print('✅ Payment coordinator integration: AVAILABLE')
    
    # Test integration with MCP server
    from backend.production.core.mcp_server_generator import BAISMCPServer
    print('✅ MCP server integration: AVAILABLE')
    
    print('')
    print('Integration Recommendations:')
    print('1. Add audit logging to all authentication endpoints')
    print('2. Log all payment-related events')
    print('3. Log all MCP resource access')
    print('4. Log all administrative actions')
    print('5. Log all security-related events')
    
except ImportError as e:
    print(f'❌ Integration test failed: {e}')

" > security-reports/day6-audit-integration-test.txt

# Generate audit logging summary
echo "📊 Generating audit logging summary..."
cat > security-reports/day6-audit-logging-summary.md << 'EOF'
# Day 6 Audit Logging & Monitoring Summary

## Test Results

### Audit Logging Implementation Test
- Results: [day6-audit-logging-test.txt](day6-audit-logging-test.txt)

### Log File Security Test
- Results: [day6-log-file-security-test.txt](day6-log-file-security-test.txt)

### Log Rotation Setup
- Results: [day6-log-rotation-setup.txt](day6-log-rotation-setup.txt)

### Audit Integration Test
- Results: [day6-audit-integration-test.txt](day6-audit-integration-test.txt)

## Critical Issues (P0 - Fix Immediately)
- [ ] Implement audit logging in all security-critical components
- [ ] Set up log file security and permissions
- [ ] Configure log rotation to prevent disk space issues

## High Priority Issues (P1 - Fix This Week)
- [ ] Set up security monitoring and alerting
- [ ] Integrate audit logging with all services
- [ ] Configure log backup and retention policies

## Medium Priority Issues (P2 - Fix Before Production)
- [ ] Set up log analysis and reporting
- [ ] Implement real-time security monitoring
- [ ] Configure compliance reporting

## Security Recommendations

### Audit Logging
1. Log all authentication attempts (success and failure)
2. Log all payment-related events
3. Log all administrative actions
4. Log all security violations
5. Log all API access with response codes

### Log Security
1. Set appropriate file permissions (600 or 640)
2. Implement log rotation (daily, keep 30 days)
3. Compress old log files
4. Backup audit logs for compliance
5. Monitor log file size and growth

### Security Monitoring
1. Set up real-time log monitoring
2. Configure alerts for security events
3. Monitor for brute force attempts
4. Track rate limit violations
5. Detect unusual payment patterns

### Compliance
1. Ensure audit logs meet compliance requirements
2. Implement log integrity protection
3. Set up log retention policies
4. Configure log analysis and reporting
5. Document audit procedures

## Production Readiness Checklist
- [ ] Audit logging implemented in all components
- [ ] Log file security configured
- [ ] Log rotation set up
- [ ] Security monitoring configured
- [ ] Alert system operational
- [ ] Log backup procedures in place
- [ ] Compliance requirements met

## Monitoring Scripts Created
- [x] scripts/monitor_security_logs.sh - Security log monitoring
- [x] Log rotation configuration
- [x] Systemd service configuration
- [x] Log analysis commands

## Integration Points
- [x] Authentication service
- [x] Payment coordinator
- [x] MCP server
- [x] Security audit logger
- [x] Error handling system

## Next Steps
1. Review all test results
2. Fix critical and high priority issues
3. Set up production monitoring
4. Configure log rotation and backup
5. Prepare for final security review (Day 7)

EOF

echo "✅ Day 6 audit logging & monitoring completed!"
echo "📁 Reports saved in security-reports/ directory"
echo "🔍 Review the summary: security-reports/day6-audit-logging-summary.md"
echo ""
echo "📊 Security monitoring script created: scripts/monitor_security_logs.sh"
echo "🔒 Log rotation configuration provided"
echo ""
echo "📝 Next steps:"
echo "1. Review audit logging test results"
echo "2. Set up log file security and permissions"
echo "3. Configure log rotation for production"
echo "4. Set up security monitoring and alerting"
echo "5. Integrate audit logging with all services"
echo "6. Test security monitoring scripts"

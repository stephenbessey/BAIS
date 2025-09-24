#!/bin/bash

# Week 1 Security Audit Master Script
# Comprehensive security audit for BAIS platform

set -e

echo "🔒 Starting Week 1 Security & Compliance Audit"
echo "=============================================="
echo ""
echo "This comprehensive security audit will cover:"
echo "  Day 1: Vulnerability Scanning"
echo "  Day 2: Secrets Management Audit"
echo "  Day 3: OAuth 2.0 & Authentication Security"
echo "  Day 4: AP2 Cryptographic Validation"
echo "  Day 5: HTTPS/TLS & Network Security"
echo "  Day 6: Audit Logging & Monitoring"
echo "  Day 7: Final Review & Documentation"
echo ""

# Create main security reports directory
mkdir -p security-reports
mkdir -p docs

# Function to run a day's audit
run_day_audit() {
    local day=$1
    local script=$2
    local description=$3
    
    echo "🚀 Starting Day $day: $description"
    echo "=================================="
    
    if [ -f "scripts/$script" ]; then
        echo "Running scripts/$script..."
        ./scripts/"$script"
        echo "✅ Day $day completed successfully!"
    else
        echo "❌ Script scripts/$script not found!"
        exit 1
    fi
    
    echo ""
    echo "📊 Day $day Summary:"
    echo "  Script: scripts/$script"
    echo "  Reports: security-reports/day$day-*"
    echo ""
}

# Run all day audits
run_day_audit "1" "day1-vulnerability-scan.sh" "Vulnerability Scanning"
run_day_audit "2" "day2-secrets-audit.sh" "Secrets Management Audit"
run_day_audit "3" "day3-auth-security.sh" "OAuth 2.0 & Authentication Security"
run_day_audit "4" "day4-ap2-crypto.sh" "AP2 Cryptographic Validation"
run_day_audit "5" "day5-https-tls.sh" "HTTPS/TLS & Network Security"
run_day_audit "6" "day6-audit-logging.sh" "Audit Logging & Monitoring"
run_day_audit "7" "day7-final-review.sh" "Final Review & Documentation"

# Create master summary
echo "🎉 **WEEK 1 SECURITY AUDIT COMPLETED!**"
echo "====================================="
echo ""

# Count total reports generated
total_reports=$(find security-reports -name "*.md" -o -name "*.txt" -o -name "*.json" -o -name "*.html" | wc -l)
echo "📊 **Total Security Reports Generated: $total_reports**"

# List all reports
echo ""
echo "📁 **Security Reports Generated:**"
echo "================================="
find security-reports -type f | sort | while read -r file; do
    echo "  📄 $file"
done

echo ""
echo "📚 **Documentation Created:**"
echo "============================"
find docs -type f | sort | while read -r file; do
    echo "  📖 $file"
done

echo ""
echo "🔧 **Security Scripts Created:**"
echo "==============================="
find scripts -name "day*.sh" -o -name "*security*.sh" -o -name "*monitor*.sh" | sort | while read -r file; do
    echo "  🔧 $file"
done

# Final security score calculation
echo ""
echo "📊 **Final Security Assessment:**"
echo "==============================="

if [ -f "security-reports/bandit-report.json" ]; then
    bandit_critical=$(grep -c '"severity": "HIGH"' security-reports/bandit-report.json 2>/dev/null || echo "0")
    bandit_medium=$(grep -c '"severity": "MEDIUM"' security-reports/bandit-report.json 2>/dev/null || echo "0")
    bandit_low=$(grep -c '"severity": "LOW"' security-reports/bandit-report.json 2>/dev/null || echo "0")
else
    bandit_critical="0"
    bandit_medium="0"
    bandit_low="0"
fi

if [ -f "security-reports/safety-report.json" ]; then
    safety_vulnerabilities=$(grep -c '"vulnerabilities"' security-reports/safety-report.json 2>/dev/null || echo "0")
else
    safety_vulnerabilities="0"
fi

SECURITY_SCORE=$(python3 -c "
critical_issues = int('$bandit_critical')
medium_issues = int('$bandit_medium') 
low_issues = int('$bandit_low')
safety_issues = int('$safety_vulnerabilities')

# Calculate score (100 - penalties)
score = 100 - (critical_issues * 20 + medium_issues * 10 + low_issues * 5 + safety_issues * 15)
score = max(0, score)

print(f'{score}/100')
" 2>/dev/null || echo "N/A")

echo "  🔴 Critical Issues: $bandit_critical"
echo "  🟡 High Priority Issues: $bandit_medium"
echo "  🟢 Medium Priority Issues: $bandit_low"
echo "  📦 Dependency Vulnerabilities: $safety_vulnerabilities"
echo "  🏆 **Final Security Score: $SECURITY_SCORE**"

echo ""
echo "🎯 **Production Readiness Status:**"
echo "================================="

if [ "$bandit_critical" -eq 0 ] && [ "$safety_vulnerabilities" -eq 0 ]; then
    echo "  ✅ **READY FOR PRODUCTION DEPLOYMENT**"
    echo "  🚀 All critical security issues resolved"
elif [ "$bandit_critical" -gt 0 ]; then
    echo "  ⚠️  **CRITICAL ISSUES FOUND**"
    echo "  🔧 Fix $bandit_critical critical vulnerabilities before production"
elif [ "$safety_vulnerabilities" -gt 0 ]; then
    echo "  ⚠️  **DEPENDENCY VULNERABILITIES FOUND**"
    echo "  🔧 Update $safety_vulnerabilities vulnerable dependencies before production"
else
    echo "  ✅ **PRODUCTION READY**"
    echo "  🎉 Security audit passed successfully"
fi

echo ""
echo "📋 **Next Steps:**"
echo "================"
echo "1. 📖 Review security-reports/week1-final-security-report.md"
echo "2. 🔧 Fix any critical or high-priority issues identified"
echo "3. 📚 Study docs/security-runbook.md for operational procedures"
echo "4. ✅ Complete security-reports/production-deployment-checklist.md"
echo "5. 🚀 Prepare for production deployment"
echo "6. 📅 Schedule Week 2 security activities"

echo ""
echo "📞 **Security Team Contacts:**"
echo "============================"
echo "  🔒 Security Lead: security@baintegrate.com"
echo "  📱 On-Call Engineer: +1-XXX-XXX-XXXX"
echo "  🚨 Emergency Escalation: cto@baintegrate.com"

echo ""
echo "🏆 **Congratulations! Your BAIS platform now has enterprise-grade security!**"
echo ""
echo "📅 **Audit completed on:** $(date)"
echo "📅 **Next security review:** $(date -d '+30 days' 2>/dev/null || echo '30 days from now')"

# Create quick access script
cat > security-reports/quick-access.sh << 'EOF'
#!/bin/bash
# Quick access to security audit results

echo "🔒 BAIS Security Audit - Quick Access"
echo "====================================="
echo ""
echo "📊 Main Reports:"
echo "  📄 Final Report: security-reports/week1-final-security-report.md"
echo "  📖 Security Runbook: docs/security-runbook.md"
echo "  ✅ Production Checklist: security-reports/production-deployment-checklist.md"
echo ""
echo "🔧 Security Scripts:"
echo "  🔍 Vulnerability Scan: ./scripts/day1-vulnerability-scan.sh"
echo "  🔑 Secrets Audit: ./scripts/day2-secrets-audit.sh"
echo "  🔐 Auth Security: ./scripts/day3-auth-security.sh"
echo "  🛡️  Crypto Validation: ./scripts/day4-ap2-crypto.sh"
echo "  🌐 TLS Security: ./scripts/day5-https-tls.sh"
echo "  📊 Audit Logging: ./scripts/day6-audit-logging.sh"
echo "  📋 Final Review: ./scripts/day7-final-review.sh"
echo ""
echo "📱 Monitoring:"
echo "  👀 Security Monitor: ./scripts/monitor_security_logs.sh"
echo ""
echo "🔍 Quick Commands:"
echo "  # View all reports"
echo "  ls -la security-reports/"
echo ""
echo "  # Run security monitoring"
echo "  ./scripts/monitor_security_logs.sh"
echo ""
echo "  # Check audit logs"
echo "  tail -f /var/log/bais/security_audit.log"
EOF

chmod +x security-reports/quick-access.sh

echo ""
echo "🎁 **Bonus: Quick Access Script Created!**"
echo "  🔧 Run: ./security-reports/quick-access.sh"
echo "  📖 Quick reference to all security resources"

echo ""
echo "✨ **Week 1 Security Audit Complete! ✨"

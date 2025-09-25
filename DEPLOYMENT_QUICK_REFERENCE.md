# 🚀 BAIS Platform - Deployment Quick Reference

## ⚡ Quick Deployment Commands

### **1. Staging Deployment**
```bash
./scripts/staging-deployment.sh latest
```

### **2. Acceptance Testing**
```bash
python scripts/acceptance_test_suite.py --url http://staging-api.bais.io --verbose
```

### **3. Monitoring Setup**
```bash
kubectl apply -f scripts/prometheus-alerts.yaml
```

### **4. On-Call Configuration**
```bash
python scripts/oncall-rotation-setup.py
```

### **5. Production Go-Live**
```bash
./scripts/production-golive-checklist.sh
```

---

## 🔍 Quick Health Checks

### **Staging Environment**
```bash
# Check staging deployment
kubectl get pods -n bais-staging

# Test staging API
curl http://staging-api.bais.io/health

# Check staging logs
kubectl logs -n bais-staging deployment/bais-staging
```

### **Production Environment**
```bash
# Check production deployment
kubectl get pods -n bais-production

# Test production API
curl https://api.bais.io/health

# Check production logs
kubectl logs -n bais-production deployment/bais-production
```

---

## 📊 Quick Monitoring

### **Grafana Dashboards**
- **Application Metrics**: https://grafana.bais.com/d/bais-app
- **Database Metrics**: https://grafana.bais.com/d/bais-db
- **Infrastructure**: https://grafana.bais.com/d/bais-infra

### **Alert Status**
```bash
# Check alert status
kubectl get prometheusrules -n monitoring

# Check Alertmanager
kubectl get pods -n monitoring -l app=alertmanager
```

---

## 🚨 Emergency Procedures

### **Service Down**
```bash
# Check pod status
kubectl get pods -n bais-production

# Restart deployment
kubectl rollout restart deployment/bais-production -n bais-production

# Check logs
kubectl logs -n bais-production deployment/bais-production --tail=100
```

### **High Error Rate**
```bash
# Check recent logs
kubectl logs -n bais-production deployment/bais-production --since=5m

# Check metrics
kubectl port-forward svc/bais-production-service 9090:9090 -n bais-production
# Then visit http://localhost:9090/metrics
```

### **Database Issues**
```bash
# Check database pods
kubectl get pods -n bais-production -l app=postgres

# Check database logs
kubectl logs -n bais-production deployment/postgres-production
```

---

## 📞 Quick Contacts

- **Platform Team**: platform@baintegrate.com
- **Security Team**: security@baintegrate.com
- **CTO**: cto@baintegrate.com
- **PagerDuty**: https://baintegrate.pagerduty.com

---

## 🔧 Quick Troubleshooting

### **Common Issues**

#### **Pod Not Starting**
```bash
kubectl describe pod <pod-name> -n bais-production
kubectl logs <pod-name> -n bais-production
```

#### **Service Not Accessible**
```bash
kubectl get svc -n bais-production
kubectl get ingress -n bais-production
```

#### **Database Connection Issues**
```bash
kubectl exec -it <postgres-pod> -n bais-production -- psql -U postgres
```

#### **High Memory Usage**
```bash
kubectl top pods -n bais-production
kubectl describe pod <pod-name> -n bais-production
```

---

## 📋 Quick Checklists

### **Pre-Deployment**
- [ ] Staging tests pass
- [ ] Monitoring alerts configured
- [ ] On-call rotation active
- [ ] SSL certificates valid
- [ ] Backups tested

### **Post-Deployment**
- [ ] Health checks pass
- [ ] Performance metrics normal
- [ ] Error rates acceptable
- [ ] Alerts configured
- [ ] Team notified

---

## 🎯 Performance Targets

| Metric | Target | Critical |
|--------|--------|----------|
| Response Time (p95) | < 200ms | > 500ms |
| Error Rate | < 0.1% | > 1% |
| CPU Usage | < 70% | > 90% |
| Memory Usage | < 80% | > 95% |
| Database Connections | < 80% | > 95% |

---

## 🚀 **READY TO DEPLOY!**

Execute the 5-step deployment sequence for production go-live! 🎉

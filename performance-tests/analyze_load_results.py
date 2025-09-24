"""
Load Test Results Analyzer
Analyzes Locust CSV output and generates performance report
"""

import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

class LoadTestAnalyzer:
    """Analyze load test results"""
    
    def __init__(self, csv_prefix: str):
        self.stats_df = pd.read_csv(f"{csv_prefix}_stats.csv")
        self.failures_df = pd.read_csv(f"{csv_prefix}_failures.csv")
        self.exceptions_df = pd.read_csv(f"{csv_prefix}_exceptions.csv")
    
    def analyze(self):
        """Generate comprehensive analysis"""
        print("=" * 80)
        print("LOAD TEST ANALYSIS REPORT")
        print("=" * 80)
        
        self._analyze_response_times()
        self._analyze_throughput()
        self._analyze_failures()
        self._analyze_percentiles()
        self._check_sla_compliance()
    
    def _analyze_response_times(self):
        """Analyze response times"""
        print("\n📊 RESPONSE TIME ANALYSIS")
        print("-" * 80)
        
        avg_response = self.stats_df['Average Response Time'].mean()
        max_response = self.stats_df['Max Response Time'].max()
        
        print(f"  Average Response Time: {avg_response:.2f}ms")
        print(f"  Maximum Response Time: {max_response:.2f}ms")
        
        if avg_response > 200:
            print(f"  ❌ FAILED: Average exceeds 200ms threshold")
        else:
            print(f"  ✅ PASSED: Average within 200ms threshold")
    
    def _analyze_throughput(self):
        """Analyze request throughput"""
        print("\n📈 THROUGHPUT ANALYSIS")
        print("-" * 80)
        
        total_requests = self.stats_df['Request Count'].sum()
        total_rps = self.stats_df['Requests/s'].sum()
        
        print(f"  Total Requests: {total_requests:,}")
        print(f"  Requests per Second: {total_rps:.2f}")
        
        # Check if meeting target (100+ RPS for payment workflows)
        payment_rps = self.stats_df[
            self.stats_df['Name'].str.contains('Workflow|AP2')
        ]['Requests/s'].sum()
        
        print(f"  Payment Workflow RPS: {payment_rps:.2f}")
        
        if payment_rps >= 100:
            print(f"  ✅ PASSED: Payment workflows > 100 RPS")
        else:
            print(f"  ❌ FAILED: Payment workflows < 100 RPS target")
    
    def _analyze_failures(self):
        """Analyze failures and errors"""
        print("\n❌ FAILURE ANALYSIS")
        print("-" * 80)
        
        total_requests = self.stats_df['Request Count'].sum()
        total_failures = self.stats_df['Failure Count'].sum()
        failure_rate = (total_failures / total_requests * 100) if total_requests > 0 else 0
        
        print(f"  Total Failures: {total_failures:,}")
        print(f"  Failure Rate: {failure_rate:.2f}%")
        
        if failure_rate > 1:
            print(f"  ❌ FAILED: Failure rate exceeds 1% threshold")
        else:
            print(f"  ✅ PASSED: Failure rate within acceptable range")
        
        if not self.failures_df.empty:
            print("\n  Top Failures:")
            for idx, row in self.failures_df.head(5).iterrows():
                print(f"    - {row['Name']}: {row['Occurrences']} occurrences")
    
    def _analyze_percentiles(self):
        """Analyze response time percentiles"""
        print("\n📉 PERCENTILE ANALYSIS")
        print("-" * 80)
        
        for col in ['50%', '66%', '75%', '80%', '90%', '95%', '98%', '99%']:
            if col in self.stats_df.columns:
                p_value = self.stats_df[col].mean()
                print(f"  {col:>5} percentile: {p_value:>8.2f}ms")
        
        # 95th percentile should be < 500ms
        p95 = self.stats_df['95%'].mean() if '95%' in self.stats_df.columns else 0
        if p95 > 500:
            print(f"\n  ⚠️  WARNING: 95th percentile exceeds 500ms")
    
    def _check_sla_compliance(self):
        """Check SLA compliance"""
        print("\n✅ SLA COMPLIANCE CHECK")
        print("-" * 80)
        
        avg_response = self.stats_df['Average Response Time'].mean()
        failure_rate = (self.stats_df['Failure Count'].sum() / 
                       self.stats_df['Request Count'].sum() * 100)
        
        sla_results = {
            "Response Time < 200ms": avg_response < 200,
            "Failure Rate < 1%": failure_rate < 1,
            "99% Uptime": failure_rate < 1  # Simplified check
        }
        
        for check, passed in sla_results.items():
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"  {check:30} {status}")
        
        overall_pass = all(sla_results.values())
        print(f"\n  {'='*80}")
        if overall_pass:
            print(f"  🎉 OVERALL: ALL SLA CHECKS PASSED")
        else:
            print(f"  ⚠️  OVERALL: SOME SLA CHECKS FAILED")
        print(f"  {'='*80}")

# Run analysis
if __name__ == "__main__":
    analyzer = LoadTestAnalyzer("performance-tests/reports/sustained")
    analyzer.analyze()

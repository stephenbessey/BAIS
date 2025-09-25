#!/usr/bin/env python3
"""
BAIS Platform - On-Call Rotation Setup
Configures PagerDuty schedules and escalation policies for production support
"""

import json
import requests
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from enum import Enum
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EscalationLevel(Enum):
    PRIMARY = "primary"
    SECONDARY = "secondary"
    MANAGER = "manager"


@dataclass
class Engineer:
    name: str
    email: str
    phone: str
    timezone: str
    role: str
    pagerduty_user_id: Optional[str] = None


@dataclass
class OnCallSchedule:
    engineer: Engineer
    start_time: datetime
    end_time: datetime
    escalation_level: EscalationLevel


class OnCallRotationManager:
    def __init__(self, pagerduty_api_key: str, slack_webhook_url: str):
        self.pagerduty_api_key = pagerduty_api_key
        self.slack_webhook_url = slack_webhook_url
        self.schedules: List[OnCallSchedule] = []
        self.base_url = "https://api.pagerduty.com"
        self.headers = {
            "Authorization": f"Token token={self.pagerduty_api_key}",
            "Content-Type": "application/json",
            "Accept": "application/vnd.pagerduty+json;version=2"
        }

    def create_rotation_schedule(
        self, 
        engineers: List[Engineer], 
        start_date: datetime,
        rotation_days: int = 7
    ) -> List[OnCallSchedule]:
        """Create a rotating schedule for engineers"""
        schedules = []
        current_date = start_date
        
        for index, engineer in enumerate(engineers):
            schedule = OnCallSchedule(
                engineer=engineer,
                start_time=current_date,
                end_time=current_date + timedelta(days=rotation_days),
                escalation_level=EscalationLevel.PRIMARY
            )
            schedules.append(schedule)
            current_date += timedelta(days=rotation_days)
        
        self.schedules = schedules
        return schedules

    def create_pagerduty_schedule(self, schedule_name: str) -> Dict:
        """Create a PagerDuty schedule"""
        url = f"{self.base_url}/schedules"
        
        schedule_layers = []
        for i, schedule in enumerate(self.schedules):
            layer = {
                "name": f"Layer {i+1} - {schedule.engineer.name}",
                "start": schedule.start_time.isoformat(),
                "rotation_virtual_start": schedule.start_time.isoformat(),
                "rotation_turn_length_seconds": 604800,  # 7 days
                "users": [{
                    "user": {
                        "id": schedule.engineer.pagerduty_user_id,
                        "type": "user_reference"
                    }
                }]
            }
            schedule_layers.append(layer)
        
        payload = {
            "schedule": {
                "type": "schedule",
                "name": schedule_name,
                "time_zone": "UTC",
                "description": "BAIS Platform Production On-Call Rotation",
                "schedule_layers": schedule_layers
            }
        }
        
        logger.info(f"Creating PagerDuty schedule: {schedule_name}")
        response = requests.post(url, headers=self.headers, json=payload)
        response.raise_for_status()
        
        return response.json()

    def create_escalation_policy(self, policy_name: str, schedule_id: str) -> Dict:
        """Create an escalation policy for the schedule"""
        url = f"{self.base_url}/escalation_policies"
        
        escalation_rules = [
            {
                "escalation_delay_in_minutes": 0,
                "targets": [{
                    "id": schedule_id,
                    "type": "schedule_reference"
                }]
            },
            {
                "escalation_delay_in_minutes": 15,
                "targets": [{
                    "id": schedule_id,
                    "type": "schedule_reference"
                }]
            },
            {
                "escalation_delay_in_minutes": 30,
                "targets": [{
                    "type": "user_reference",
                    "id": "MANAGER_USER_ID"  # Replace with actual manager ID
                }]
            }
        ]
        
        payload = {
            "escalation_policy": {
                "type": "escalation_policy",
                "name": policy_name,
                "escalation_rules": escalation_rules,
                "num_loops": 2
            }
        }
        
        logger.info(f"Creating escalation policy: {policy_name}")
        response = requests.post(url, headers=self.headers, json=payload)
        response.raise_for_status()
        
        return response.json()

    def notify_slack_rotation(self):
        """Send rotation update to Slack"""
        current_schedule = self.get_current_oncall()
        
        if not current_schedule:
            logger.warning("No current on-call engineer found")
            return
        
        message = {
            "text": "🚨 On-Call Rotation Update",
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": "📅 BAIS Platform On-Call Schedule"
                    }
                },
                {
                    "type": "section",
                    "fields": [
                        {
                            "type": "mrkdwn",
                            "text": f"*Current On-Call:*\n{current_schedule.engineer.name}"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Contact:*\n{current_schedule.engineer.phone}"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Period:*\n{current_schedule.start_time.strftime('%Y-%m-%d')} to {current_schedule.end_time.strftime('%Y-%m-%d')}"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Timezone:*\n{current_schedule.engineer.timezone}"
                        }
                    ]
                },
                {
                    "type": "divider"
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "*📋 Upcoming Rotation:*"
                    }
                }
            ]
        }
        
        # Add upcoming schedule
        for schedule in self.schedules[:3]:
            message["blocks"].append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"• {schedule.start_time.strftime('%b %d')}: *{schedule.engineer.name}*"
                }
            })
        
        # Add emergency contacts
        message["blocks"].extend([
            {
                "type": "divider"
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*🚨 Emergency Contacts:*\n• Platform Team: platform@baintegrate.com\n• Security Team: security@baintegrate.com\n• CTO: cto@baintegrate.com"
                }
            }
        ])
        
        logger.info("Sending rotation update to Slack")
        response = requests.post(self.slack_webhook_url, json=message)
        response.raise_for_status()

    def get_current_oncall(self) -> Optional[OnCallSchedule]:
        """Get the current on-call engineer"""
        now = datetime.now()
        
        for schedule in self.schedules:
            if schedule.start_time <= now < schedule.end_time:
                return schedule
        
        return None

    def generate_runbook(self) -> Dict:
        """Generate comprehensive runbook for on-call procedures"""
        return {
            "on_call_procedures": {
                "incident_response": [
                    "Acknowledge alert within 5 minutes",
                    "Assess severity and impact using BAIS severity matrix",
                    "Check monitoring dashboards (Grafana)",
                    "Review recent deployments and changes",
                    "Engage additional support if needed",
                    "Update incident status in PagerDuty",
                    "Communicate status to stakeholders"
                ],
                "severity_matrix": {
                    "P1 - Critical": {
                        "description": "Service down, data loss, security breach",
                        "response_time": "5 minutes",
                        "escalation": "Immediate to manager and CTO"
                    },
                    "P2 - High": {
                        "description": "Major feature broken, performance severely degraded",
                        "response_time": "15 minutes",
                        "escalation": "Escalate if not resolved in 30 minutes"
                    },
                    "P3 - Medium": {
                        "description": "Minor feature broken, performance slightly degraded",
                        "response_time": "1 hour",
                        "escalation": "Escalate if not resolved in 4 hours"
                    },
                    "P4 - Low": {
                        "description": "Cosmetic issues, documentation problems",
                        "response_time": "Next business day",
                        "escalation": "No escalation required"
                    }
                },
                "escalation_path": [
                    "Primary on-call: Immediate response (0-5 min)",
                    "Secondary on-call: Escalate if no response (15 min)",
                    "Engineering Manager: Critical incidents (30 min)",
                    "CTO: P1 incidents (1 hour)"
                ],
                "critical_contacts": {
                    "platform_team": "platform@baintegrate.com",
                    "security_team": "security@baintegrate.com",
                    "cto": "cto@baintegrate.com",
                    "customer_support": "support@baintegrate.com"
                },
                "key_resources": [
                    "Grafana: https://grafana.bais.com",
                    "Kibana: https://kibana.bais.com",
                    "Runbooks: https://runbooks.bais.com",
                    "Status Page: https://status.bais.com",
                    "Kubernetes Dashboard: https://k8s.bais.com",
                    "PagerDuty: https://baintegrate.pagerduty.com"
                ]
            },
            "common_incidents": {
                "high_error_rate": {
                    "symptoms": "5xx errors > 1%",
                    "investigation": [
                        "Check application logs in Kibana",
                        "Review database performance metrics",
                        "Check external service status (Stripe, etc.)",
                        "Verify recent deployments and rollbacks",
                        "Check system resource utilization"
                    ],
                    "remediation": [
                        "Rollback if recent deployment caused issues",
                        "Scale up if resource constrained",
                        "Restart affected services",
                        "Engage database team if DB issue",
                        "Contact external service providers if needed"
                    ]
                },
                "service_down": {
                    "symptoms": "Service health check failing",
                    "investigation": [
                        "Check pod status in Kubernetes",
                        "Review container logs for errors",
                        "Verify database connectivity",
                        "Check resource limits and requests",
                        "Verify network connectivity"
                    ],
                    "remediation": [
                        "Restart failed pods",
                        "Scale deployment if needed",
                        "Check and fix configuration issues",
                        "Verify network policies",
                        "Check for resource exhaustion"
                    ]
                },
                "database_issues": {
                    "symptoms": "Slow queries, connection timeouts",
                    "investigation": [
                        "Check database metrics in Grafana",
                        "Review slow query logs",
                        "Check connection pool utilization",
                        "Verify replication status",
                        "Check disk space and I/O"
                    ],
                    "remediation": [
                        "Optimize slow queries",
                        "Increase connection pool size",
                        "Scale database if needed",
                        "Check and fix replication lag",
                        "Clean up old data if disk space low"
                    ]
                },
                "payment_processing_failures": {
                    "symptoms": "High payment failure rate",
                    "investigation": [
                        "Check Stripe API status",
                        "Review payment logs for errors",
                        "Verify webhook delivery",
                        "Check mandate validation",
                        "Review fraud detection rules"
                    ],
                    "remediation": [
                        "Contact Stripe support if API issues",
                        "Fix webhook signature validation",
                        "Update mandate validation rules",
                        "Adjust fraud detection thresholds",
                        "Implement circuit breaker if needed"
                    ]
                }
            },
            "post_incident": {
                "immediate": [
                    "Update all stakeholders on resolution",
                    "Verify all systems are healthy",
                    "Update status page if needed",
                    "Document initial incident details"
                ],
                "within_24_hours": [
                    "Schedule post-mortem meeting",
                    "Gather all relevant logs and metrics",
                    "Identify root cause and contributing factors",
                    "Draft initial incident report"
                ],
                "within_week": [
                    "Conduct post-mortem meeting",
                    "Finalize incident report",
                    "Create action items for improvements",
                    "Update runbooks and procedures",
                    "Implement preventive measures"
                ]
            }
        }

    def export_schedule(self, filename: str):
        """Export schedule and runbook to JSON file"""
        schedule_data = {
            "rotation_schedule": [
                {
                    "engineer": {
                        "name": s.engineer.name,
                        "email": s.engineer.email,
                        "phone": s.engineer.phone,
                        "timezone": s.engineer.timezone,
                        "role": s.engineer.role
                    },
                    "start_time": s.start_time.isoformat(),
                    "end_time": s.end_time.isoformat(),
                    "escalation_level": s.escalation_level.value
                }
                for s in self.schedules
            ],
            "runbook": self.generate_runbook(),
            "created_at": datetime.now().isoformat(),
            "version": "1.0"
        }
        
        with open(filename, 'w') as f:
            json.dump(schedule_data, f, indent=2)
        
        logger.info(f"Schedule and runbook exported to {filename}")

    def create_status_page_integration(self):
        """Create status page integration for incident management"""
        status_page_config = {
            "incident_management": {
                "status_page_url": "https://status.bais.com",
                "components": [
                    {
                        "name": "API",
                        "description": "BAIS API Services",
                        "status": "operational"
                    },
                    {
                        "name": "Database",
                        "description": "PostgreSQL Database",
                        "status": "operational"
                    },
                    {
                        "name": "Cache",
                        "description": "Redis Cache",
                        "status": "operational"
                    },
                    {
                        "name": "Payment Processing",
                        "description": "Stripe Integration",
                        "status": "operational"
                    }
                ],
                "incident_templates": {
                    "service_outage": {
                        "title": "Service Outage - {service_name}",
                        "body": "We are currently experiencing issues with {service_name}. Our team is investigating and will provide updates as they become available.",
                        "severity": "major"
                    },
                    "performance_issues": {
                        "title": "Performance Issues - {service_name}",
                        "body": "We are experiencing performance issues with {service_name}. Some users may experience slower response times.",
                        "severity": "minor"
                    },
                    "maintenance": {
                        "title": "Scheduled Maintenance - {service_name}",
                        "body": "We will be performing scheduled maintenance on {service_name} from {start_time} to {end_time} UTC.",
                        "severity": "maintenance"
                    }
                }
            }
        }
        
        return status_page_config


def setup_oncall_rotation():
    """Main function to set up on-call rotation"""
    # Define engineering team
    engineers = [
        Engineer(
            name="Alice Johnson",
            email="alice@example.com",
            phone="+1-555-0101",
            timezone="America/New_York",
            role="Senior Platform Engineer",
            pagerduty_user_id="USER_ID_ALICE"
        ),
        Engineer(
            name="Bob Smith",
            email="bob@example.com",
            phone="+1-555-0102",
            timezone="America/Los_Angeles",
            role="DevOps Engineer",
            pagerduty_user_id="USER_ID_BOB"
        ),
        Engineer(
            name="Carol Davis",
            email="carol@example.com",
            phone="+1-555-0103",
            timezone="Europe/London",
            role="Site Reliability Engineer",
            pagerduty_user_id="USER_ID_CAROL"
        ),
        Engineer(
            name="David Wilson",
            email="david@example.com",
            phone="+1-555-0104",
            timezone="Asia/Tokyo",
            role="Backend Engineer",
            pagerduty_user_id="USER_ID_DAVID"
        )
    ]
    
    # Initialize rotation manager
    manager = OnCallRotationManager(
        pagerduty_api_key="YOUR_PAGERDUTY_API_KEY",
        slack_webhook_url="YOUR_SLACK_WEBHOOK_URL"
    )
    
    # Create rotation schedule starting from next Monday
    start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    days_until_monday = (7 - start_date.weekday()) % 7
    if days_until_monday == 0:
        days_until_monday = 7
    start_date += timedelta(days=days_until_monday)
    
    manager.create_rotation_schedule(engineers, start_date, rotation_days=7)
    
    try:
        # Create PagerDuty schedule
        schedule_response = manager.create_pagerduty_schedule("BAIS Production On-Call")
        schedule_id = schedule_response['schedule']['id']
        logger.info(f"Created PagerDuty schedule with ID: {schedule_id}")
        
        # Create escalation policy
        policy_response = manager.create_escalation_policy("BAIS Escalation Policy", schedule_id)
        policy_id = policy_response['escalation_policy']['id']
        logger.info(f"Created escalation policy with ID: {policy_id}")
        
        # Send Slack notification
        manager.notify_slack_rotation()
        
        # Export schedule and runbook
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        manager.export_schedule(f"oncall_rotation_schedule_{timestamp}.json")
        
        # Create status page integration
        status_config = manager.create_status_page_integration()
        with open(f"status_page_config_{timestamp}.json", 'w') as f:
            json.dump(status_config, f, indent=2)
        
        logger.info("✅ On-call rotation configured successfully")
        current_oncall = manager.get_current_oncall()
        if current_oncall:
            logger.info(f"📅 Current on-call: {current_oncall.engineer.name}")
        
        logger.info("📋 Next steps:")
        logger.info("1. Update PagerDuty user IDs with actual values")
        logger.info("2. Configure Slack webhook URL")
        logger.info("3. Set up status page integration")
        logger.info("4. Train team on runbook procedures")
        logger.info("5. Test escalation policies")
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to create PagerDuty resources: {e}")
        logger.info("Continuing with local setup...")
        
        # Export schedule and runbook even if PagerDuty fails
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        manager.export_schedule(f"oncall_rotation_schedule_{timestamp}.json")
        
        status_config = manager.create_status_page_integration()
        with open(f"status_page_config_{timestamp}.json", 'w') as f:
            json.dump(status_config, f, indent=2)


if __name__ == "__main__":
    setup_oncall_rotation()

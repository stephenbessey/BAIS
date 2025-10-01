#!/usr/bin/env python3
"""
BAIS Platform - Demo Generation CLI

Command-line interface for generating BAIS demonstrations from business websites.
"""

import asyncio
import argparse
import json
import sys
from pathlib import Path
from typing import Optional

# Add the backend directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend" / "production"))

from services.demo_templates import (
    DemoOrchestrator, DemoConfig, DemoType, 
    WebsiteAnalyzer, BusinessIntelligence
)


async def generate_demo(
    website_url: str,
    demo_type: str = "full_stack",
    output_dir: Optional[str] = None,
    enable_acp: bool = False,
    custom_domain: Optional[str] = None
) -> None:
    """
    Generate a BAIS demo from a business website
    
    Args:
        website_url: URL of the business website to analyze
        demo_type: Type of demo to generate (full_stack, backend_only, frontend_only, commerce_enabled)
        output_dir: Directory to save demo files
        enable_acp: Enable Agentic Commerce Protocol integration
        custom_domain: Custom domain for the demo
    """
    
    print("🚀 BAIS Demo Generation CLI")
    print("=" * 50)
    print(f"Website URL: {website_url}")
    print(f"Demo Type: {demo_type}")
    print(f"ACP Enabled: {enable_acp}")
    if custom_domain:
        print(f"Custom Domain: {custom_domain}")
    print()
    
    try:
        # Configuration
        config = DemoConfig(
            environment="staging",
            include_mock_data=True,
            enable_analytics=True,
            enable_acp=enable_acp,
            custom_domain=custom_domain,
            infrastructure={
                "provider": "docker",
                "auto_cleanup": True,
                "resource_limits": {
                    "cpu": "1",
                    "memory": "2Gi"
                }
            }
        )
        
        # Initialize orchestrator
        async with DemoOrchestrator(config) as orchestrator:
            
            # Generate demo
            demo_type_enum = DemoType(demo_type)
            deployment = await orchestrator.generate_full_demo(
                website_url=website_url,
                demo_type=demo_type_enum
            )
            
            # Save deployment info
            if output_dir:
                output_path = Path(output_dir)
                output_path.mkdir(exist_ok=True)
                
                # Save deployment info
                deployment_info = {
                    "deployment_id": deployment.deployment_id,
                    "demo_url": deployment.demo_url,
                    "admin_panel": deployment.admin_panel,
                    "api_endpoints": deployment.api_endpoints,
                    "documentation": deployment.documentation,
                    "shutdown_command": deployment.shutdown_command,
                    "created_at": deployment.created_at.isoformat(),
                    "metadata": deployment.metadata
                }
                
                with open(output_path / "deployment_info.json", "w") as f:
                    json.dump(deployment_info, f, indent=2)
                
                # Save documentation
                with open(output_path / "README.md", "w") as f:
                    f.write(deployment.documentation)
                
                print(f"📁 Demo files saved to: {output_path}")
            
            # Print results
            print("\n✅ Demo Generation Complete!")
            print("=" * 50)
            print(f"🌐 Demo URL: {deployment.demo_url}")
            print(f"⚙️  Admin Panel: {deployment.admin_panel}")
            print(f"📚 Documentation: {deployment.documentation}")
            print(f"🔧 API Endpoints:")
            for name, url in deployment.api_endpoints.items():
                print(f"   {name}: {url}")
            print(f"🆔 Deployment ID: {deployment.deployment_id}")
            print(f"📅 Created: {deployment.created_at.strftime('%Y-%m-%d %H:%M:%S UTC')}")
            
            print(f"\n🧹 To cleanup this demo:")
            print(f"   {deployment.shutdown_command}")
            
    except Exception as e:
        print(f"❌ Demo generation failed: {str(e)}")
        sys.exit(1)


async def analyze_website(website_url: str) -> None:
    """
    Analyze a business website and display intelligence
    
    Args:
        website_url: URL of the business website to analyze
    """
    
    print("🔍 BAIS Website Analysis")
    print("=" * 50)
    print(f"Website URL: {website_url}")
    print()
    
    try:
        import aiohttp
        
        async with aiohttp.ClientSession() as session:
            analyzer = WebsiteAnalyzer(session)
            intelligence = await analyzer.analyze_business_website(website_url)
            
            print("✅ Website Analysis Complete!")
            print("=" * 50)
            print(f"🏢 Business Name: {intelligence.business_name}")
            print(f"🏷️  Business Type: {intelligence.business_type.value}")
            print(f"📝 Description: {intelligence.description}")
            print(f"📧 Email: {intelligence.contact_info.email or 'Not found'}")
            print(f"📞 Phone: {intelligence.contact_info.phone or 'Not found'}")
            print(f"🌐 Website: {intelligence.contact_info.website or 'Not found'}")
            print(f"📍 Address: {intelligence.contact_info.address or 'Not found'}")
            
            print(f"\n🛍️  Services Found ({len(intelligence.services)}):")
            for i, service in enumerate(intelligence.services, 1):
                print(f"   {i}. {service.name}")
                print(f"      Category: {service.category}")
                print(f"      Type: {service.service_type.value}")
                if service.price:
                    print(f"      Price: ${service.price} {service.currency}")
                print(f"      Description: {service.description}")
                print()
            
            print(f"💰 Pricing Info:")
            if intelligence.pricing_info.min_price:
                print(f"   Price Range: ${intelligence.pricing_info.min_price:.2f} - ${intelligence.pricing_info.max_price:.2f}")
            print(f"   Currency: {intelligence.pricing_info.currency}")
            print(f"   Model: {intelligence.pricing_info.pricing_model or 'Unknown'}")
            
            print(f"\n📊 Analysis Metadata:")
            print(f"   Text Length: {intelligence.metadata.get('text_length', 0):,} characters")
            print(f"   Forms Found: {intelligence.metadata.get('forms_count', 0)}")
            print(f"   Links Found: {intelligence.metadata.get('links_count', 0)}")
            print(f"   Extracted At: {intelligence.extracted_at.strftime('%Y-%m-%d %H:%M:%S UTC')}")
            
    except Exception as e:
        print(f"❌ Website analysis failed: {str(e)}")
        sys.exit(1)


async def list_deployments() -> None:
    """List active demo deployments"""
    
    print("📋 Active Demo Deployments")
    print("=" * 50)
    
    try:
        config = DemoConfig()
        async with DemoOrchestrator(config) as orchestrator:
            deployments = await orchestrator.list_active_deployments()
            
            if not deployments:
                print("No active deployments found.")
                return
            
            for deployment in deployments:
                print(f"🆔 {deployment.deployment_id}")
                print(f"   Business: {deployment.metadata.get('business_name', 'Unknown')}")
                print(f"   Type: {deployment.metadata.get('business_type', 'Unknown')}")
                print(f"   URL: {deployment.demo_url}")
                print(f"   Created: {deployment.created_at.strftime('%Y-%m-%d %H:%M:%S UTC')}")
                print(f"   Components: {', '.join(deployment.metadata.get('components', []))}")
                print()
                
    except Exception as e:
        print(f"❌ Failed to list deployments: {str(e)}")
        sys.exit(1)


async def cleanup_deployment(deployment_id: str) -> None:
    """
    Cleanup a demo deployment
    
    Args:
        deployment_id: ID of the deployment to cleanup
    """
    
    print(f"🧹 Cleaning up deployment: {deployment_id}")
    
    try:
        config = DemoConfig()
        async with DemoOrchestrator(config) as orchestrator:
            success = await orchestrator.cleanup_deployment(deployment_id)
            
            if success:
                print("✅ Deployment cleaned up successfully!")
            else:
                print("❌ Deployment not found or cleanup failed")
                
    except Exception as e:
        print(f"❌ Cleanup failed: {str(e)}")
        sys.exit(1)


def main():
    """Main CLI entry point"""
    
    parser = argparse.ArgumentParser(
        description="BAIS Demo Generation CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate a full-stack demo
  python generate_demo.py generate https://grandhotelstgeorge.com
  
  # Generate a backend-only demo with ACP
  python generate_demo.py generate https://restaurant.com --type backend_only --enable-acp
  
  # Analyze a website
  python generate_demo.py analyze https://business.com
  
  # List active deployments
  python generate_demo.py list
  
  # Cleanup a deployment
  python generate_demo.py cleanup deployment-id-123
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Generate command
    generate_parser = subparsers.add_parser("generate", help="Generate a demo")
    generate_parser.add_argument("website_url", help="Website URL to analyze")
    generate_parser.add_argument(
        "--type", 
        choices=["full_stack", "backend_only", "frontend_only", "commerce_enabled"],
        default="full_stack",
        help="Type of demo to generate"
    )
    generate_parser.add_argument(
        "--output-dir", 
        help="Directory to save demo files"
    )
    generate_parser.add_argument(
        "--enable-acp", 
        action="store_true",
        help="Enable Agentic Commerce Protocol"
    )
    generate_parser.add_argument(
        "--custom-domain",
        help="Custom domain for the demo"
    )
    
    # Analyze command
    analyze_parser = subparsers.add_parser("analyze", help="Analyze a website")
    analyze_parser.add_argument("website_url", help="Website URL to analyze")
    
    # List command
    list_parser = subparsers.add_parser("list", help="List active deployments")
    
    # Cleanup command
    cleanup_parser = subparsers.add_parser("cleanup", help="Cleanup a deployment")
    cleanup_parser.add_argument("deployment_id", help="Deployment ID to cleanup")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Execute commands
    if args.command == "generate":
        asyncio.run(generate_demo(
            website_url=args.website_url,
            demo_type=args.type,
            output_dir=args.output_dir,
            enable_acp=args.enable_acp,
            custom_domain=args.custom_domain
        ))
    elif args.command == "analyze":
        asyncio.run(analyze_website(args.website_url))
    elif args.command == "list":
        asyncio.run(list_deployments())
    elif args.command == "cleanup":
        asyncio.run(cleanup_deployment(args.deployment_id))


if __name__ == "__main__":
    main()

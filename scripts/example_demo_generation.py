#!/usr/bin/env python3
"""
BAIS Platform - Example Demo Generation

This script demonstrates how to use the BAIS Demo Template System
to generate demonstrations for various types of businesses.
"""

import asyncio
import sys
from pathlib import Path

# Add the backend directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend" / "production"))

from services.demo_templates import DemoOrchestrator, DemoConfig, DemoType


async def demo_hotel_integration():
    """Example: Generate a demo for a hotel business"""
    
    print("🏨 Hotel Demo Generation Example")
    print("=" * 50)
    
    config = DemoConfig(
        environment="staging",
        include_mock_data=True,
        enable_analytics=True,
        enable_acp=False  # Hotels typically don't need ACP
    )
    
    async with DemoOrchestrator(config) as orchestrator:
        # Generate demo for Grand Hotel St. George
        deployment = await orchestrator.generate_full_demo(
            website_url="https://grandhotelstgeorge.com",
            demo_type=DemoType.FULL_STACK
        )
        
        print(f"✅ Hotel Demo Generated!")
        print(f"🌐 Demo URL: {deployment.demo_url}")
        print(f"⚙️  Admin Panel: {deployment.admin_panel}")
        print(f"📚 Documentation: {deployment.documentation}")
        
        return deployment


async def demo_restaurant_integration():
    """Example: Generate a demo for a restaurant business"""
    
    print("\n🍽️  Restaurant Demo Generation Example")
    print("=" * 50)
    
    config = DemoConfig(
        environment="staging",
        include_mock_data=True,
        enable_analytics=True,
        enable_acp=False
    )
    
    async with DemoOrchestrator(config) as orchestrator:
        # Generate demo for a restaurant
        deployment = await orchestrator.generate_full_demo(
            website_url="https://example-restaurant.com",
            demo_type=DemoType.FULL_STACK
        )
        
        print(f"✅ Restaurant Demo Generated!")
        print(f"🌐 Demo URL: {deployment.demo_url}")
        print(f"⚙️  Admin Panel: {deployment.admin_panel}")
        
        return deployment


async def demo_retail_integration():
    """Example: Generate a demo for a retail business with ACP"""
    
    print("\n🛍️  Retail Demo Generation Example (with ACP)")
    print("=" * 50)
    
    config = DemoConfig(
        environment="staging",
        include_mock_data=True,
        enable_analytics=True,
        enable_acp=True  # Retail businesses benefit from ACP
    )
    
    async with DemoOrchestrator(config) as orchestrator:
        # Generate commerce-enabled demo for retail
        deployment = await orchestrator.generate_full_demo(
            website_url="https://example-store.com",
            demo_type=DemoType.COMMERCE_ENABLED
        )
        
        print(f"✅ Retail Demo with ACP Generated!")
        print(f"🌐 Demo URL: {deployment.demo_url}")
        print(f"💳 ACP Enabled: Yes")
        print(f"🛒 Commerce Features: Payment processing, order management")
        
        return deployment


async def demo_service_integration():
    """Example: Generate a demo for a professional service business"""
    
    print("\n💼 Professional Service Demo Generation Example")
    print("=" * 50)
    
    config = DemoConfig(
        environment="staging",
        include_mock_data=True,
        enable_analytics=True,
        enable_acp=False
    )
    
    async with DemoOrchestrator(config) as orchestrator:
        # Generate demo for professional services
        deployment = await orchestrator.generate_full_demo(
            website_url="https://example-consulting.com",
            demo_type=DemoType.FULL_STACK
        )
        
        print(f"✅ Professional Service Demo Generated!")
        print(f"🌐 Demo URL: {deployment.demo_url}")
        print(f"📅 Features: Appointment scheduling, consultation booking")
        
        return deployment


async def demo_backend_only():
    """Example: Generate a backend-only demo for API testing"""
    
    print("\n🔧 Backend-Only Demo Generation Example")
    print("=" * 50)
    
    config = DemoConfig(
        environment="staging",
        include_mock_data=True,
        enable_analytics=False,  # No UI for analytics
        enable_acp=False
    )
    
    async with DemoOrchestrator(config) as orchestrator:
        # Generate backend-only demo
        deployment = await orchestrator.generate_full_demo(
            website_url="https://example-business.com",
            demo_type=DemoType.BACKEND_ONLY
        )
        
        print(f"✅ Backend-Only Demo Generated!")
        print(f"🌐 API Base URL: {deployment.demo_url}")
        print(f"📡 MCP Endpoint: {deployment.api_endpoints['mcp']}")
        print(f"🔍 Health Check: {deployment.api_endpoints['health']}")
        
        return deployment


async def demo_frontend_only():
    """Example: Generate a frontend-only demo for UI showcase"""
    
    print("\n🎨 Frontend-Only Demo Generation Example")
    print("=" * 50)
    
    config = DemoConfig(
        environment="staging",
        include_mock_data=True,
        enable_analytics=True,
        enable_acp=False
    )
    
    async with DemoOrchestrator(config) as orchestrator:
        # Generate frontend-only demo
        deployment = await orchestrator.generate_full_demo(
            website_url="https://example-business.com",
            demo_type=DemoType.FRONTEND_ONLY
        )
        
        print(f"✅ Frontend-Only Demo Generated!")
        print(f"🌐 Demo URL: {deployment.demo_url}")
        print(f"🎨 Features: Interactive UI, mock data, demo scenarios")
        
        return deployment


async def cleanup_demos(deployments):
    """Cleanup all generated demos"""
    
    print("\n🧹 Cleaning up demo deployments...")
    print("=" * 50)
    
    config = DemoConfig()
    async with DemoOrchestrator(config) as orchestrator:
        for deployment in deployments:
            try:
                success = await orchestrator.cleanup_deployment(deployment.deployment_id)
                if success:
                    print(f"✅ Cleaned up: {deployment.deployment_id}")
                else:
                    print(f"❌ Failed to cleanup: {deployment.deployment_id}")
            except Exception as e:
                print(f"❌ Error cleaning up {deployment.deployment_id}: {e}")


async def main():
    """Main example function"""
    
    print("🚀 BAIS Demo Template System - Examples")
    print("=" * 60)
    print("This script demonstrates various demo generation scenarios.")
    print("Note: These examples use mock URLs and may not work with real websites.")
    print()
    
    deployments = []
    
    try:
        # Run all examples
        hotel_deployment = await demo_hotel_integration()
        deployments.append(hotel_deployment)
        
        restaurant_deployment = await demo_restaurant_integration()
        deployments.append(restaurant_deployment)
        
        retail_deployment = await demo_retail_integration()
        deployments.append(retail_deployment)
        
        service_deployment = await demo_service_integration()
        deployments.append(service_deployment)
        
        backend_deployment = await demo_backend_only()
        deployments.append(backend_deployment)
        
        frontend_deployment = await demo_frontend_only()
        deployments.append(frontend_deployment)
        
        # Summary
        print("\n📊 Demo Generation Summary")
        print("=" * 50)
        print(f"Total demos generated: {len(deployments)}")
        print(f"Hotel demos: 1")
        print(f"Restaurant demos: 1")
        print(f"Retail demos (with ACP): 1")
        print(f"Service demos: 1")
        print(f"Backend-only demos: 1")
        print(f"Frontend-only demos: 1")
        
        # List all deployments
        print(f"\n📋 All Deployments:")
        for i, deployment in enumerate(deployments, 1):
            print(f"{i}. {deployment.metadata.get('business_name', 'Unknown')} - {deployment.demo_url}")
        
        # Ask user if they want to cleanup
        print(f"\n🧹 Cleanup Options:")
        print(f"1. Cleanup all demos now")
        print(f"2. Keep demos running for testing")
        
        # For demo purposes, we'll cleanup automatically
        cleanup_choice = input("Enter choice (1 or 2): ").strip()
        
        if cleanup_choice == "1":
            await cleanup_demos(deployments)
        else:
            print(f"\n📌 Demos are still running. Use the following commands to cleanup:")
            for deployment in deployments:
                print(f"   {deployment.shutdown_command}")
        
    except Exception as e:
        print(f"❌ Example execution failed: {str(e)}")
        print(f"Cleaning up any partial deployments...")
        if deployments:
            await cleanup_demos(deployments)


if __name__ == "__main__":
    # Run the examples
    asyncio.run(main())

#!/usr/bin/env python3

import asyncio
import json
import sys
import os

# Add the app directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from agents.multi_agent_system import MultiAgentSystem

async def test_multi_agent_system():
    """Test the multi-agent system with a sample action"""
    
    print("🤖 Testing Remedy Bot Multi-Agent System\n")
    
    # Initialize the system
    print("📡 Initializing multi-agent system...")
    system = MultiAgentSystem()
    
    try:
        await system.initialize()
        print("✅ System initialized successfully\n")
    except Exception as e:
        print(f"❌ Failed to initialize system: {e}")
        return
    
    # Test with a sample action
    action = "I decided to quit my job without having another one lined up"
    situation = "I was feeling overwhelmed and stressed at work, my manager was being unreasonable, and I felt like I needed to escape immediately"
    
    print(f"🎯 Testing with sample action:")
    print(f"   Action: {action}")
    print(f"   Situation: {situation}\n")
    
    print("🔄 Running multi-agent analysis...")
    
    try:
        result = await system.analyze_action(
            action_description=action,
            situation_description=situation,
            session_id="test-session-001"
        )
        
        print("✅ Analysis completed successfully!\n")
        
        # Display results
        print("📊 ANALYSIS RESULTS:")
        print("=" * 50)
        
        print(f"\n📝 Summary:")
        print(f"   {result.get('summary', 'No summary available')}")
        
        print(f"\n🎯 Confidence Score: {result.get('confidence_score', 0.0):.2f}")
        print(f"⏱️  Processing Time: {result.get('processing_time_seconds', 0.0):.2f} seconds")
        
        # Show criticism
        criticisms = result.get('criticism', [])
        if criticisms:
            print(f"\n⚠️  Areas of Concern ({len(criticisms)}):")
            for i, criticism in enumerate(criticisms, 1):
                print(f"   {i}. {criticism.aspect} ({criticism.severity})")
                print(f"      {criticism.criticism}")
        
        # Show alternatives
        alternatives = result.get('alternatives', [])
        if alternatives:
            print(f"\n💡 Alternative Actions ({len(alternatives)}):")
            for i, alt in enumerate(alternatives, 1):
                print(f"   {i}. {alt.action}")
                print(f"      Reasoning: {alt.reasoning}")
                print(f"      Difficulty: {alt.difficulty}, Timeline: {alt.timeline}")
        
        # Show research findings
        research = result.get('research_findings', [])
        if research:
            print(f"\n🔬 Research Findings ({len(research)}):")
            for i, finding in enumerate(research, 1):
                print(f"   {i}. [{finding.source_type}] {finding.finding}")
                print(f"      Relevance: {finding.relevance_score:.2f}")
        
        # Show guidance
        guidance = result.get('consequence_guidance', [])
        if guidance:
            print(f"\n🎯 Consequence Guidance ({len(guidance)}):")
            for i, guide in enumerate(guidance, 1):
                print(f"   {i}. {guide.consequence} ({guide.probability} probability)")
                print(f"      Strategy: {guide.mitigation_strategy}")
        
        print("\n" + "=" * 50)
        print("🎉 Test completed successfully!")
        
    except Exception as e:
        print(f"❌ Analysis failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_multi_agent_system())

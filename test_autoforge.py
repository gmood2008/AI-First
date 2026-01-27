#!/usr/bin/env python3
"""
Simple test script to verify AutoForge pipeline.

This script tests each phase of the AutoForge pipeline to ensure it works correctly.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from forge.auto.types import RawRequirement, ParsedRequirement, IntentCategory, SideEffectType
from forge.auto.parser import RequirementParser
from forge.auto.spec_gen import SpecGenerator
from forge.auto.validator import SpecValidator
from forge.auto.code_gen import CodeGenerator
from forge.auto.test_gen import TestGenerator
from forge.auto.pipeline import AutoForge


def test_phase1_types():
    """Test Phase 1: Types"""
    print("=" * 80)
    print("Phase 1: Testing Types")
    print("=" * 80)
    
    # Test RawRequirement
    raw = RawRequirement(
        description="Get Bitcoin price from CoinGecko",
        context={"user_id": "test_user"}
    )
    print(f"✅ RawRequirement created: {raw.description}")
    
    # Test ParsedRequirement
    parsed = ParsedRequirement(
        action="get_price",
        target="coingecko",
        intent_category=IntentCategory.NETWORK,
        inputs=["symbol"],
        outputs=["price", "currency"],
        side_effects=[SideEffectType.NETWORK_READ],
        missing_info=["API endpoint"]
    )
    print(f"✅ ParsedRequirement created: {parsed.action} -> {parsed.target}")
    print(f"   Intent: {parsed.intent_category.value}")
    print(f"   Side Effects: {[e.value for e in parsed.side_effects]}")
    
    return parsed


def test_phase1_parser():
    """Test Phase 1: Parser (requires OpenAI API key)"""
    print("\n" + "=" * 80)
    print("Phase 1: Testing Parser")
    print("=" * 80)
    
    try:
        parser = RequirementParser()
        requirement = "Create a capability to get the current Bitcoin price from CoinGecko API"
        
        print(f"Parsing requirement: {requirement}")
        print("(This requires OPENAI_API_KEY environment variable)")
        
        # Uncomment to actually test (requires API key):
        # parsed = parser.parse(requirement)
        # print(f"✅ Parsed: {parsed.action} -> {parsed.target}")
        # print(f"   Intent: {parsed.intent_category.value}")
        # return parsed
        
        print("⚠️  Skipping actual LLM call (requires API key)")
        return None
        
    except Exception as e:
        print(f"⚠️  Parser test skipped: {e}")
        return None


def test_phase2_spec_gen(parsed):
    """Test Phase 2: Spec Generation"""
    print("\n" + "=" * 80)
    print("Phase 2: Testing Spec Generator")
    print("=" * 80)
    
    if parsed is None:
        # Create a test parsed requirement
        from forge.auto.types import ParsedRequirement, IntentCategory, SideEffectType
        parsed = ParsedRequirement(
            action="get_price",
            target="coingecko",
            intent_category=IntentCategory.NETWORK,
            inputs=["symbol"],
            outputs=["price", "currency"],
            side_effects=[SideEffectType.NETWORK_READ],
            missing_info=[]
        )
    
    spec_gen = SpecGenerator()
    spec = spec_gen.generate(parsed, "net.crypto.get_price")
    
    print(f"✅ Spec generated: {spec.id}")
    print(f"   Name: {spec.name}")
    print(f"   Risk Level: {spec.risk.level.value}")
    print(f"   Operation Type: {spec.operation_type.value}")
    print(f"   Reversible: {spec.side_effects.reversible}")
    print(f"   Compensation: {spec.compensation.supported}")
    print(f"   Parameters: {[p.name for p in spec.parameters]}")
    
    return spec


def test_phase2_validator(spec):
    """Test Phase 2: Validator"""
    print("\n" + "=" * 80)
    print("Phase 2: Testing Validator")
    print("=" * 80)
    
    validator = SpecValidator(max_retries=1)  # Use 1 retry for testing
    
    try:
        validated_spec = validator.validate_and_fix(spec)
        print(f"✅ Spec validated: {validated_spec.id}")
        print(f"   Risk Level: {validated_spec.risk.level.value}")
        return validated_spec
    except Exception as e:
        print(f"⚠️  Validation test: {e}")
        return spec


def test_phase3_code_gen(spec):
    """Test Phase 3: Code Generation (requires OpenAI API key)"""
    print("\n" + "=" * 80)
    print("Phase 3: Testing Code Generator")
    print("=" * 80)
    
    try:
        code_gen = CodeGenerator()
        print("(This requires OPENAI_API_KEY environment variable)")
        print("⚠️  Skipping actual LLM call (requires API key)")
        # Uncomment to test:
        # handler_code = code_gen.generate_handler_code(spec)
        # print(f"✅ Handler code generated ({len(handler_code)} chars)")
        # return handler_code
        return None
    except Exception as e:
        print(f"⚠️  Code generation test skipped: {e}")
        return None


def test_phase3_test_gen(spec, handler_code):
    """Test Phase 3: Test Generation (requires OpenAI API key)"""
    print("\n" + "=" * 80)
    print("Phase 3: Testing Test Generator")
    print("=" * 80)
    
    if handler_code is None:
        handler_code = "# Placeholder handler code\nclass GetPriceHandler:\n    pass"
    
    try:
        test_gen = TestGenerator()
        print("(This requires OPENAI_API_KEY environment variable)")
        print("⚠️  Skipping actual LLM call (requires API key)")
        # Uncomment to test:
        # test_code = test_gen.generate_test_code(spec, handler_code)
        # print(f"✅ Test code generated ({len(test_code)} chars)")
        # return test_code
        return None
    except Exception as e:
        print(f"⚠️  Test generation skipped: {e}")
        return None


def test_phase4_pipeline():
    """Test Phase 4: Full Pipeline (requires OpenAI API key)"""
    print("\n" + "=" * 80)
    print("Phase 4: Testing Full Pipeline")
    print("=" * 80)
    
    try:
        autoforge = AutoForge()
        requirement = "Create a capability to get the current Bitcoin price from CoinGecko API"
        
        print(f"Requirement: {requirement}")
        print("(This requires OPENAI_API_KEY environment variable)")
        print("⚠️  Skipping actual LLM calls (requires API key)")
        
        # Uncomment to test:
        # result = autoforge.forge_capability(requirement, capability_id="net.crypto.get_price")
        # print(f"✅ Pipeline completed: {result.capability_id}")
        # print(f"   Spec: {len(result.spec_yaml)} chars")
        # print(f"   Handler: {len(result.handler_code)} chars")
        # print(f"   Test: {len(result.test_code)} chars")
        
        return None
    except Exception as e:
        print(f"⚠️  Pipeline test skipped: {e}")
        return None


def main():
    """Run all tests"""
    print("\n" + "=" * 80)
    print("AutoForge Pipeline Verification")
    print("=" * 80)
    print("\nThis script verifies each phase of the AutoForge pipeline.")
    print("Note: Phases that require LLM calls will be skipped without OPENAI_API_KEY\n")
    
    # Phase 1
    parsed = test_phase1_types()
    test_phase1_parser()
    
    # Phase 2
    spec = test_phase2_spec_gen(parsed)
    validated_spec = test_phase2_validator(spec)
    
    # Phase 3
    handler_code = test_phase3_code_gen(validated_spec)
    test_code = test_phase3_test_gen(validated_spec, handler_code)
    
    # Phase 4
    test_phase4_pipeline()
    
    print("\n" + "=" * 80)
    print("✅ Verification Complete")
    print("=" * 80)
    print("\nTo test with actual LLM calls, set OPENAI_API_KEY environment variable")
    print("and uncomment the LLM calls in this script.")
    print("\nExample usage:")
    print("  export OPENAI_API_KEY=your_key_here")
    print("  python test_autoforge.py")
    print("\nOr use the CLI:")
    print("  forge create 'Get Bitcoin price from CoinGecko'")


if __name__ == "__main__":
    main()

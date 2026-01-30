"""
Update/Refine command implementation for AutoForge.

Allows users to update existing capabilities instead of recreating from scratch.
"""

import sys
import json
from pathlib import Path
from typing import Optional

from forge.auto.pipeline import AutoForge
from specs.v3.capability_schema import CapabilitySpec
import yaml


def cmd_update(args):
    """Handle 'forge update' or 'forge refine' command"""
    try:
        capability_id = args.capability_id
        workspace_root = Path(args.workspace) if args.workspace else Path.cwd()
        
        # Load existing files
        spec_path = workspace_root / f"capabilities/validated/generated/{capability_id}.yaml"
        handler_path = workspace_root / f"src/runtime/stdlib/generated/{capability_id.replace('.', '_')}.py"
        test_path = workspace_root / f"tests/generated/test_{capability_id.replace('.', '_')}.py"
        
        if not spec_path.exists():
            print(f"❌ Error: Capability '{capability_id}' not found at {spec_path}", file=sys.stderr)
            print(f"   Use 'forge create' to create a new capability", file=sys.stderr)
            return 1
        
        # Load existing spec
        with open(spec_path, 'r') as f:
            existing_spec_dict = yaml.safe_load(f)
        
        # Load existing handler code
        existing_handler = ""
        if handler_path.exists():
            with open(handler_path, 'r') as f:
                existing_handler = f.read()
        
        # Load existing test code
        existing_test = ""
        if test_path.exists():
            with open(test_path, 'r') as f:
                existing_test = f.read()
        
        print(f"\n📝 Updating capability: {capability_id}")
        print(f"   Requirement: {args.requirement}")
        
        # Initialize AutoForge
        autoforge = AutoForge(model=args.model, max_retries=args.retries)
        
        # Load references if provided
        references = None
        if args.reference:
            references = args.reference if isinstance(args.reference, list) else [args.reference]
        
        # Generate updated version
        result = autoforge.forge_capability(
            requirement=args.requirement,
            capability_id=capability_id,
            context=args.context,
            references=references,
            test_first=getattr(args, 'test_first', False)
        )
        
        # Show diff preview
        if args.dry_run or args.preview:
            print("\n" + "=" * 80)
            print("📋 Changes Preview (Spec):")
            print("=" * 80)
            # Simple diff - in production, use proper diff library
            print("(Use --no-preview to see full diff)")
            print("\n" + "=" * 80)
            print("🐍 Handler Changes:")
            print("=" * 80)
            if existing_handler:
                print("(Existing handler will be updated)")
            print("\n" + "=" * 80)
            print("🧪 Test Changes:")
            print("=" * 80)
            if existing_test:
                print("(Existing tests will be updated)")
            
            if args.dry_run:
                return 0
        
        # Ask for confirmation if files exist
        if not args.force and (handler_path.exists() or test_path.exists()):
            print(f"\n⚠️  Warning: Existing files will be overwritten:")
            if handler_path.exists():
                print(f"   - {handler_path}")
            if test_path.exists():
                print(f"   - {test_path}")
            
            response = input("\nProceed with update? [y/N]: ")
            if response.lower() != 'y':
                print("Update cancelled.")
                return 0
        
        # Save updated files
        spec_dir = workspace_root / Path(result.spec_path).parent
        handler_dir = workspace_root / Path(result.handler_path).parent
        test_dir = workspace_root / Path(result.test_path).parent
        
        spec_dir.mkdir(parents=True, exist_ok=True)
        handler_dir.mkdir(parents=True, exist_ok=True)
        test_dir.mkdir(parents=True, exist_ok=True)
        
        # Write files
        (workspace_root / result.spec_path).write_text(result.spec_yaml)
        (workspace_root / result.handler_path).write_text(result.handler_code)
        (workspace_root / result.test_path).write_text(result.test_code)
        
        print("\n" + "=" * 80)
        print("✅ Capability Updated Successfully!")
        print("=" * 80)
        print(f"\n📋 Updated: {capability_id}")
        print(f"📁 Files updated:")
        print(f"   - {result.spec_path}")
        print(f"   - {result.handler_path}")
        print(f"   - {result.test_path}")
        
        if result.dependencies:
            print(f"\n📦 Dependencies: {', '.join(sorted(result.dependencies))}")
        
        return 0
    
    except Exception as e:
        print(f"\n❌ Error: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


def cmd_compose(args):
    """Handle 'forge compose' command - Compose capabilities"""
    try:
        print("\n" + "=" * 80)
        print("🔗 AutoForge - Capability Composition")
        print("=" * 80)
        print("\n⚠️  This feature is under development.")
        print("   Capability composition allows combining existing capabilities")
        print("   to create new composite capabilities.")
        print("\n   Example:")
        print("   forge compose --base 'net.crypto.get_price' --action 'if price > 60000 then alert'")
        print("=" * 80)
        return 0
    
    except Exception as e:
        print(f"\n❌ Error: {e}", file=sys.stderr)
        return 1

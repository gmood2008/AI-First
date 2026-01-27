#!/usr/bin/env python3
"""
Forge CLI - Command-line interface for AI-First Runtime tools.
"""

import sys
import os
import argparse
from pathlib import Path

# Add parent directory to path for imports
project_root = Path(__file__).parent.parent.parent.absolute()

# Change to project root first
os.chdir(project_root)

# Add paths in correct order (src first to avoid tools/forge conflict)
sys.path.insert(0, str(project_root / "src"))
sys.path.insert(0, str(project_root))
# Add tools last to avoid namespace conflicts
if str(project_root / "tools") not in sys.path:
    sys.path.append(str(project_root / "tools"))

# Import forge modules
try:
    from forge.importer.importer import SmartImporter
except ImportError:
    SmartImporter = None  # Optional import

try:
    from forge.auto.pipeline import AutoForge
except ImportError as e:
    print(f"❌ Error importing AutoForge: {e}", file=sys.stderr)
    print("   Make sure you're in the project root directory", file=sys.stderr)
    sys.exit(1)

# Import update and compose commands
try:
    from forge.cli_update import cmd_update, cmd_compose
except ImportError:
    # Fallback if module not found
    def cmd_update(args):
        print("❌ Update command not available", file=sys.stderr)
        return 1
    
    def cmd_compose(args):
        print("❌ Compose command not available", file=sys.stderr)
        return 1

# Import update and compose commands
try:
    from forge.cli_update import cmd_update, cmd_compose
except ImportError:
    # Fallback if module not found
    def cmd_update(args):
        print("❌ Update command not available", file=sys.stderr)
        return 1
    
    def cmd_compose(args):
        print("❌ Compose command not available", file=sys.stderr)
        return 1


def cmd_import(args):
    """Handle 'forge import' command"""
    # Check if this is an external capability import
    if hasattr(args, 'from_claude_skill') and args.from_claude_skill:
        return cmd_import_external(args, 'claude_skill')
    elif hasattr(args, 'from_openai_function') and args.from_openai_function:
        return cmd_import_external(args, 'openai_function')
    elif hasattr(args, 'from_http_api') and args.from_http_api:
        return cmd_import_external(args, 'http_api')
    
    # Original import logic (for code/function imports)
    if SmartImporter is None:
        print("❌ Error: forge.importer not available", file=sys.stderr)
        return 1
    
    try:
        importer = SmartImporter(model=args.model, max_retries=args.retries)
        
        spec, validation, handler_file, test_file = importer.import_from_source(
            source=args.source,
            capability_id=args.id,
            output_dir=args.output,
            function_name=args.function,
            endpoint_path=args.endpoint,
            method=args.method,
            generate_handler=args.generate_handler,
            generate_tests=args.generate_tests,
            dry_run=args.dry_run,
            verbose=args.verbose,
        )
        
        # Print summary
        print("\n" + "=" * 80)
        print("✅ Import completed successfully!")
        print("=" * 80)
        print(f"Capability ID: {spec.meta.id}")
        print(f"Description: {spec.meta.description}")
        print(f"Side Effects: {', '.join(spec.contracts.side_effects) if spec.contracts.side_effects else 'none'}")
        print(f"Requires Confirmation: {spec.contracts.requires_confirmation}")
        print(f"Undo Strategy: {spec.behavior.undo_strategy}")
        
        if validation.warnings:
            print(f"\n⚠️  Warnings: {len(validation.warnings)}")
            for warning in validation.warnings:
                print(f"  - {warning}")
        
        if not args.dry_run:
            print(f"\n📁 Generated files:")
            print(f"  - Spec: {args.output}/{spec.meta.id}.yaml")
            if handler_file:
                print(f"  - Handler: {handler_file}")
            if test_file:
                print(f"  - Tests: {test_file}")
        
        return 0
    
    except Exception as e:
        print(f"\n❌ Error: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


def cmd_import_external(args, adapter_type: str):
    """Handle external capability import (Claude Skill, OpenAI Function, HTTP API)"""
    try:
        from forge.auto.external_importer import ExternalImporter
        
        importer = ExternalImporter(
            model=getattr(args, 'model', 'gpt-4o-mini'),
            provider=getattr(args, 'provider', 'auto')
        )
        
        capability_id = args.id
        if not capability_id:
            print("❌ Error: --id is required for external capability import", file=sys.stderr)
            return 1
        
        output_dir = getattr(args, 'output', 'capabilities/validated/external')
        dry_run = getattr(args, 'dry_run', False)
        
        print("=" * 80)
        print(f"🔄 Importing External Capability: {adapter_type}")
        print("=" * 80)
        print()
        
        if adapter_type == 'claude_skill':
            source = args.from_claude_skill
            api_key = getattr(args, 'api_key', None)
            
            result = importer.import_claude_skill(
                skill_source=source,
                capability_id=capability_id,
                output_dir=output_dir,
                api_key=api_key,
                dry_run=dry_run
            )
        
        elif adapter_type == 'openai_function':
            # Load function definition from source
            import json
            from pathlib import Path
            
            source = args.from_openai_function
            if source.startswith("http"):
                import httpx
                with httpx.Client() as client:
                    response = client.get(source)
                    response.raise_for_status()
                    func_def = response.json()
            else:
                with open(Path(source), 'r') as f:
                    func_def = json.load(f)
            
            # This would need OpenAI Function adapter implementation
            print("⚠️  OpenAI Function import not yet fully implemented", file=sys.stderr)
            return 1
        
        elif adapter_type == 'http_api':
            # Load API definition from source
            import json
            from pathlib import Path
            
            source = args.from_http_api
            if source.startswith("http"):
                import httpx
                with httpx.Client() as client:
                    response = client.get(source)
                    response.raise_for_status()
                    api_def = response.json()
            else:
                with open(Path(source), 'r') as f:
                    api_def = json.load(f)
            
            result = importer.import_http_api(
                api_definition=api_def,
                capability_id=capability_id,
                output_dir=output_dir,
                dry_run=dry_run
            )
        
        # Print summary
        print("\n" + "=" * 80)
        print("✅ External Capability Imported Successfully!")
        print("=" * 80)
        print(f"\n📋 Capability Information:")
        print(f"   ID: {result['capability_id']}")
        print(f"   Name: {result['spec'].name}")
        print(f"   Description: {result['spec'].description}")
        print(f"   Adapter Type: {adapter_type}")
        print(f"   Risk Level: {result['spec'].risk.level.value}")
        print(f"   Supports Undo: No (external capabilities typically don't support undo)")
        
        if not dry_run:
            print(f"\n📁 Generated Files:")
            print(f"   📄 Spec:      {result['spec_path']}")
            if result.get('handler_path'):
                print(f"   🐍 Handler:   {result['handler_path']}")
            if result.get('test_path'):
                print(f"   🧪 Test:      {result['test_path']}")
            
            print(f"\n💡 Next Steps:")
            print(f"   1. Review the generated spec:")
            print(f"      cat {result['spec_path']}")
            print(f"   2. Test the capability:")
            if result.get('test_path'):
                print(f"      pytest {result['test_path']}")
            print(f"   3. Register to runtime (if needed):")
            print(f"      # The capability will be auto-loaded from external/ directory")
        else:
            print("\n📋 Generated Spec (Preview):")
            print("=" * 80)
            print(result['spec_yaml'])
        
        return 0
    
    except Exception as e:
        print(f"\n❌ Error: {e}", file=sys.stderr)
        if getattr(args, 'verbose', False):
            import traceback
            traceback.print_exc()
        return 1


def cmd_create(args):
    """Handle 'forge create' command"""
    try:
        # Check for API key
        import os
        openai_key = os.getenv("OPENAI_API_KEY")
        deepseek_key = os.getenv("DEEPSEEK_API_KEY")
        provider = getattr(args, 'provider', 'auto')
        
        # Auto-detect provider if not specified
        if provider == 'auto':
            if deepseek_key:
                provider = 'deepseek'
            elif openai_key:
                provider = 'openai'
        
        # Check if we have the required API key
        if provider == 'deepseek' and not deepseek_key:
            print("⚠️  Warning: DEEPSEEK_API_KEY not set. LLM operations will fail.", file=sys.stderr)
            print("   Set it with: export DEEPSEEK_API_KEY=your_key_here", file=sys.stderr)
            if not args.dry_run:
                try:
                    response = input("\nContinue anyway? [y/N]: ")
                    if response.lower() != 'y':
                        return 1
                except EOFError:
                    # Non-interactive mode, just continue
                    pass
        elif provider == 'openai' and not openai_key:
            print("⚠️  Warning: OPENAI_API_KEY not set. LLM operations will fail.", file=sys.stderr)
            print("   Set it with: export OPENAI_API_KEY=your_key_here", file=sys.stderr)
            if not args.dry_run:
                try:
                    response = input("\nContinue anyway? [y/N]: ")
                    if response.lower() != 'y':
                        return 1
                except EOFError:
                    # Non-interactive mode, just continue
                    pass
        elif not openai_key and not deepseek_key:
            print("⚠️  Warning: No API key found (OPENAI_API_KEY or DEEPSEEK_API_KEY).", file=sys.stderr)
            print("   Set one with: export DEEPSEEK_API_KEY=your_key_here", file=sys.stderr)
            if not args.dry_run:
                try:
                    response = input("\nContinue anyway? [y/N]: ")
                    if response.lower() != 'y':
                        return 1
                except EOFError:
                    # Non-interactive mode, just continue
                    pass
        
        # Get provider from args or environment
        provider = getattr(args, 'provider', 'auto')
        
        # Initialize AutoForge
        autoforge = AutoForge(
            model=args.model, 
            max_retries=args.retries,
            provider=provider
        )
        
        # Show progress
        print("\n" + "=" * 80)
        print("🔨 AutoForge - Converting Natural Language to Capability")
        print("=" * 80)
        print(f"\n📝 Requirement: {args.requirement}")
        if args.id:
            print(f"🆔 Capability ID: {args.id}")
        print()
        
        if args.verbose:
            print("📊 Starting pipeline...")
            print("   Phase 1: Parsing requirement...")
        
        # Load references if provided
        references = None
        if args.reference:
            references = args.reference if isinstance(args.reference, list) else [args.reference]
        
        # Run pipeline with progress feedback
        import time
        start_time = time.time()
        
        result = autoforge.forge_capability(
            requirement=args.requirement,
            capability_id=args.id,
            context=args.context,
            references=references,
            test_first=getattr(args, 'test_first', False)
        )
        
        elapsed_time = time.time() - start_time
        
        if args.verbose:
            print(f"   ✓ Parsed requirement")
            print(f"   Phase 2: Generating specification...")
            print(f"   ✓ Spec generated")
            print(f"   Phase 3: Validating specification...")
            print(f"   ✓ Validation passed")
            print(f"   Phase 4: Generating handler code...")
            print(f"   ✓ Handler code generated ({len(result.handler_code)} chars)")
            print(f"   Phase 5: Generating test code...")
            print(f"   ✓ Test code generated ({len(result.test_code)} chars)")
            print(f"\n⏱️  Total time: {elapsed_time:.2f}s")
        
        if args.dry_run:
            print("\n" + "=" * 80)
            print("📋 Generated Spec (YAML):")
            print("=" * 80)
            print(result.spec_yaml)
            print("\n" + "=" * 80)
            print("🐍 Generated Handler Code:")
            print("=" * 80)
            print(result.handler_code[:500] + "..." if len(result.handler_code) > 500 else result.handler_code)
            print("\n" + "=" * 80)
            print("🧪 Generated Test Code:")
            print("=" * 80)
            print(result.test_code[:500] + "..." if len(result.test_code) > 500 else result.test_code)
            return 0
        
        # Save files
        workspace_root = Path(args.workspace) if args.workspace else Path.cwd()
        
        # Create directories
        spec_dir = workspace_root / Path(result.spec_path).parent
        handler_dir = workspace_root / Path(result.handler_path).parent
        test_dir = workspace_root / Path(result.test_path).parent
        
        spec_dir.mkdir(parents=True, exist_ok=True)
        handler_dir.mkdir(parents=True, exist_ok=True)
        test_dir.mkdir(parents=True, exist_ok=True)
        
        # Write spec
        spec_file = workspace_root / result.spec_path
        spec_file.write_text(result.spec_yaml)
        
        # Write handler
        handler_file = workspace_root / result.handler_path
        handler_file.write_text(result.handler_code)
        
        # Write test
        test_file = workspace_root / result.test_path
        test_file.write_text(result.test_code)
        
        # Print summary
        print("\n" + "=" * 80)
        print("✅ Capability Forged Successfully!")
        print("=" * 80)
        
        # Capability info
        print(f"\n📋 Capability Information:")
        print(f"   ID: {result.capability_id}")
        print(f"   Name: {result.spec.name}")
        print(f"   Description: {result.spec.description}")
        print(f"   Risk Level: {result.spec.risk.level.value}")
        print(f"   Operation Type: {result.spec.operation_type.value}")
        print(f"   Supports Undo: {'Yes' if result.spec.compensation.supported else 'No'}")
        
        # File info
        print(f"\n📁 Generated Files:")
        print(f"   📄 Spec:      {result.spec_path}")
        print(f"   🐍 Handler:   {result.handler_path}")
        print(f"   🧪 Test:      {result.test_path}")
        
        # Show dependencies if any
        if result.dependencies:
            print(f"\n📦 Detected Dependencies:")
            for dep in sorted(result.dependencies):
                print(f"   • {dep}")
            print(f"\n💡 Add to requirements.txt:")
            print(result.requirements_snippet)
        
        # Next steps
        print(f"\n🚀 Next Steps:")
        print(f"   1. Review the generated code:")
        print(f"      cat {result.handler_path}")
        print(f"   2. Install dependencies (if any):")
        if result.dependencies:
            deps_str = " ".join(sorted(result.dependencies))
            print(f"      pip install {deps_str}")
        print(f"   3. Run tests:")
        print(f"      pytest {result.test_path}")
        print(f"   4. Commit to Git:")
        print(f"      git add {result.spec_path} {result.handler_path} {result.test_path}")
        print(f"      git commit -m 'feat: add {result.capability_id} capability'")
        
        print(f"\n💡 Tip: Use 'forge create --dry-run' to preview before saving")
        print("=" * 80)
        
        return 0
    
    except KeyboardInterrupt:
        print("\n\n⚠️  Operation cancelled by user", file=sys.stderr)
        return 130
    except Exception as e:
        print("\n" + "=" * 80, file=sys.stderr)
        print("❌ Error: Capability Generation Failed", file=sys.stderr)
        print("=" * 80, file=sys.stderr)
        print(f"\n💬 Error Message: {e}", file=sys.stderr)
        
        # Provide helpful suggestions
        error_str = str(e).lower()
        suggestions = []
        
        if "api_key" in error_str or "openai" in error_str:
            suggestions.append("• Set OPENAI_API_KEY environment variable")
            suggestions.append("  export OPENAI_API_KEY=your_key_here")
        
        if "validation" in error_str or "valid spec" in error_str:
            suggestions.append("• Try rephrasing your requirement to be more specific")
            suggestions.append("• Use --verbose to see detailed validation issues")
            suggestions.append("• Check if your requirement involves destructive operations")
            suggestions.append("• Try increasing retries: --retries 5")
        
        if "json" in error_str or "parse" in error_str:
            suggestions.append("• Check your requirement description for special characters")
            suggestions.append("• Try using quotes around your requirement")
            suggestions.append("• Use --verbose to see LLM responses")
        
        if suggestions:
            print(f"\n💡 Suggestions:", file=sys.stderr)
            for suggestion in suggestions:
                print(f"  {suggestion}", file=sys.stderr)
        
        if args.verbose:
            print(f"\n📋 Full Traceback:", file=sys.stderr)
            import traceback
            traceback.print_exc(file=sys.stderr)
        else:
            print(f"\n💡 Run with --verbose for detailed error information", file=sys.stderr)
        
        print("=" * 80, file=sys.stderr)
        return 1


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        prog="forge",
        description="AI-First Runtime development tools",
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # forge import command
    import_parser = subparsers.add_parser(
        "import",
        help="Import external tools as AI-First capabilities",
    )
    
    import_parser.add_argument(
        "source",
        help="Source to import (Python file, code string, OpenAPI spec, or URL)",
    )
    
    import_parser.add_argument(
        "--id",
        required=True,
        help="Capability ID (e.g., 'tools.slack.send_message')",
    )
    
    import_parser.add_argument(
        "--function",
        help="Specific function name to import (for Python sources)",
    )
    
    import_parser.add_argument(
        "--endpoint",
        help="Specific endpoint path to import (for OpenAPI sources)",
    )
    
    import_parser.add_argument(
        "--method",
        choices=["GET", "POST", "PUT", "PATCH", "DELETE"],
        help="HTTP method for endpoint (for OpenAPI sources)",
    )
    
    import_parser.add_argument(
        "--output",
        default="./capabilities",
        help="Output directory for generated files (default: ./capabilities)",
    )
    
    import_parser.add_argument(
        "--generate-handler",
        action="store_true",
        default=True,
        help="Generate handler Python code (default: true)",
    )
    
    import_parser.add_argument(
        "--no-generate-handler",
        action="store_false",
        dest="generate_handler",
        help="Don't generate handler code",
    )
    
    import_parser.add_argument(
        "--generate-tests",
        action="store_true",
        default=True,
        help="Generate test code (default: true)",
    )
    
    import_parser.add_argument(
        "--no-generate-tests",
        action="store_false",
        dest="generate_tests",
        help="Don't generate test code",
    )
    
    import_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show generated spec without writing files",
    )
    
    import_parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Verbose output",
    )
    
    import_parser.add_argument(
        "--model",
        default="gpt-4.1-mini",
        help="LLM model to use for spec generation (default: gpt-4.1-mini)",
    )
    
    import_parser.add_argument(
        "--retries",
        type=int,
        default=3,
        help="Maximum retries for LLM generation (default: 3)",
    )
    
    # forge create command
    create_parser = subparsers.add_parser(
        "create",
        help="Create a new capability from natural language requirement",
    )
    
    create_parser.add_argument(
        "requirement",
        help="Natural language requirement (e.g., 'Create a capability to get Bitcoin price from CoinGecko')",
    )
    
    create_parser.add_argument(
        "--id",
        help="Capability ID (auto-generated if not provided, e.g., 'net.crypto.get_price')",
    )
    
    create_parser.add_argument(
        "--workspace",
        default=".",
        help="Workspace root directory (default: current directory)",
    )
    
    create_parser.add_argument(
        "--context",
        help="Additional context as JSON string (e.g., '{\"user_id\": \"123\"}')",
    )
    
    create_parser.add_argument(
        "--reference",
        "--ref",
        action="append",
        help="Reference file(s) to provide context (can be used multiple times). Supports .md, .py, .txt, .json, .yaml",
    )
    
    create_parser.add_argument(
        "--test-first",
        action="store_true",
        help="Test-Driven Development mode: Generate tests first, then handler code",
    )
    
    create_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show generated files without writing to disk",
    )
    
    create_parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Verbose output",
    )
    
    create_parser.add_argument(
        "--model",
        default="gpt-4o-mini",
        help="LLM model to use (default: gpt-4o-mini)",
    )
    
    create_parser.add_argument(
        "--retries",
        type=int,
        default=3,
        help="Maximum retries for validation (default: 3)",
    )
    
    create_parser.add_argument(
        "--provider",
        choices=["auto", "openai", "deepseek"],
        default="auto",
        help="LLM provider: 'auto' (auto-detect), 'openai', or 'deepseek' (default: auto)",
    )
    
    # forge update/refine command
    update_parser = subparsers.add_parser(
        "update",
        aliases=["refine"],
        help="Update/refine an existing capability",
    )
    
    update_parser.add_argument(
        "capability_id",
        help="Capability ID to update (e.g., 'net.crypto.get_price')",
    )
    
    update_parser.add_argument(
        "requirement",
        help="Updated requirement description",
    )
    
    update_parser.add_argument(
        "--workspace",
        default=".",
        help="Workspace root directory (default: current directory)",
    )
    
    update_parser.add_argument(
        "--context",
        help="Additional context as JSON string",
    )
    
    update_parser.add_argument(
        "--reference",
        "--ref",
        action="append",
        help="Reference file(s) for context",
    )
    
    update_parser.add_argument(
        "--preview",
        action="store_true",
        help="Show diff preview before updating",
    )
    
    update_parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing files without confirmation",
    )
    
    update_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without saving",
    )
    
    update_parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Verbose output",
    )
    
    update_parser.add_argument(
        "--model",
        default="gpt-4o-mini",
        help="LLM model to use (default: gpt-4o-mini)",
    )
    
    update_parser.add_argument(
        "--retries",
        type=int,
        default=3,
        help="Maximum retries for validation (default: 3)",
    )
    
    update_parser.add_argument(
        "--provider",
        choices=["auto", "openai", "deepseek"],
        default="auto",
        help="LLM provider: 'auto' (auto-detect), 'openai', or 'deepseek' (default: auto)",
    )
    
    # forge compose command
    compose_parser = subparsers.add_parser(
        "compose",
        help="Compose new capability from existing ones",
    )
    
    compose_parser.add_argument(
        "--base",
        required=True,
        help="Base capability ID(s) to compose from",
        action="append",
    )
    
    compose_parser.add_argument(
        "--action",
        help="Action/condition to apply (e.g., 'if price > 60000 then alert')",
    )
    
    compose_parser.add_argument(
        "--id",
        help="Capability ID for composed capability",
    )
    
    compose_parser.add_argument(
        "--workspace",
        default=".",
        help="Workspace root directory",
    )
    
    compose_parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Verbose output",
    )
    
    # Parse arguments
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    # Route to command handler
    if args.command == "import":
        return cmd_import(args)
    elif args.command == "create":
        # Parse context if provided
        if args.context:
            import json
            try:
                args.context = json.loads(args.context)
            except json.JSONDecodeError:
                print(f"❌ Error: Invalid JSON in --context: {args.context}", file=sys.stderr)
                return 1
        else:
            args.context = None
        return cmd_create(args)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

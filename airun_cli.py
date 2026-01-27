#!/usr/bin/env python3
"""
AI-First Runtime CLI Wrapper
"""
import sys
import os

# Add tools directory to path
tools_dir = os.path.join(os.path.dirname(__file__), 'tools')
sys.path.insert(0, tools_dir)

from airun.cli import main

if __name__ == "__main__":
    sys.exit(main())

"""
AI-First Runtime Setup Configuration
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read README for long description
readme_path = Path(__file__).parent / "README.md"
long_description = readme_path.read_text(encoding="utf-8") if readme_path.exists() else ""

setup(
    name="ai-first-runtime",
    version="2.0.0",
    author="Manus AI Team",
    author_email="hello@manus.im",
    description="The agentic framework for building safe, reliable, and auditable AI agents",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/gmood2008/ai-first-runtime",
    project_urls={
        "Bug Tracker": "https://github.com/gmood2008/ai-first-runtime/issues",
        "Documentation": "https://github.com/gmood2008/ai-first-runtime/tree/master/docs",
        "Source Code": "https://github.com/gmood2008/ai-first-runtime",
    },
    packages=find_packages(where="src") + ["airun"],
    package_dir={
        "": "src",
        "airun": "tools/airun",
    },
    python_requires=">=3.11",
    install_requires=[
        # Core dependencies would go here
        # For now, keeping it minimal
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "airun=airun.cli:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Software Development :: Libraries :: Application Frameworks",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
    ],
    keywords="ai agents agentic framework undo compliance audit safety",
    license="MIT",
)

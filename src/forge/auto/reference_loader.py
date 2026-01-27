"""
Reference Loader - Loads reference documents and code for context injection.

Supports loading:
- Markdown documents
- Python code files
- Text files
- JSON/YAML configs
"""

from pathlib import Path
from typing import List, Optional, Dict
import re


class ReferenceLoader:
    """
    Load reference materials for context injection.
    
    Supports multiple file types and formats.
    """
    
    def __init__(self):
        """Initialize reference loader"""
        self.supported_extensions = {
            '.md', '.markdown',  # Markdown docs
            '.py', '.pyx',       # Python code
            '.txt',              # Plain text
            '.json', '.yaml', '.yml',  # Config files
            '.rst',              # reStructuredText
        }
    
    def load_references(self, reference_paths: List[str]) -> Dict[str, str]:
        """
        Load multiple reference files.
        
        Args:
            reference_paths: List of file paths to load
        
        Returns:
            Dictionary mapping file paths to their content
        """
        references = {}
        
        for ref_path in reference_paths:
            path = Path(ref_path)
            
            if not path.exists():
                raise FileNotFoundError(f"Reference file not found: {ref_path}")
            
            if path.suffix.lower() not in self.supported_extensions:
                raise ValueError(
                    f"Unsupported file type: {path.suffix}. "
                    f"Supported: {', '.join(self.supported_extensions)}"
                )
            
            content = self._load_file(path)
            references[str(path)] = content
        
        return references
    
    def _load_file(self, path: Path) -> str:
        """Load a single file"""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Add metadata header
            header = f"--- Reference: {path.name} ---\n"
            return header + content
        except UnicodeDecodeError:
            # Try with different encoding
            with open(path, 'r', encoding='latin-1') as f:
                content = f.read()
            header = f"--- Reference: {path.name} (latin-1 encoding) ---\n"
            return header + content
    
    def extract_code_snippets(self, content: str, language: str = "python") -> List[str]:
        """
        Extract code snippets from markdown or text.
        
        Args:
            content: File content
            language: Target language (python, javascript, etc.)
        
        Returns:
            List of code snippets
        """
        snippets = []
        
        # Match code blocks in markdown
        pattern = rf'```{language}\n(.*?)```'
        matches = re.findall(pattern, content, re.DOTALL)
        snippets.extend(matches)
        
        # Match generic code blocks
        pattern = r'```\n(.*?)```'
        matches = re.findall(pattern, content, re.DOTALL)
        snippets.extend(matches)
        
        return snippets
    
    def format_for_prompt(self, references: Dict[str, str]) -> str:
        """
        Format references for inclusion in LLM prompt.
        
        Args:
            references: Dictionary of file paths to content
        
        Returns:
            Formatted string for prompt
        """
        if not references:
            return ""
        
        sections = ["**Reference Materials:**"]
        
        for file_path, content in references.items():
            # Truncate very long files
            max_length = 5000
            if len(content) > max_length:
                content = content[:max_length] + f"\n... (truncated, total {len(content)} chars)"
            
            sections.append(f"\n**File: {Path(file_path).name}**")
            sections.append("```")
            sections.append(content)
            sections.append("```")
        
        return "\n".join(sections)

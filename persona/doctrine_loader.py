"""
Doctrine Loader - Reads and parses YAML doctrine files for ministers and Prime Confident.

Each doctrine file contains:
- role_type: "minister" or "confidant"
- persona.canon: Core worldview and mental models
- doctrine: Purpose, authority, triggers, failure modes, and scope
"""

import os
import yaml
from typing import Dict, Any, Optional
from dataclasses import dataclass


DOCTRINE_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "doctrine", "locked")


@dataclass
class DoctrinalCanon:
    """Parsed doctrine from a YAML file."""
    name: str
    role_type: str  # "minister" or "confidant"
    canon_text: str  # The narrative canon
    purpose: str
    authority_may: list  # What this role is allowed to do
    authority_may_not: list  # What this role cannot do
    triggers_speak: list  # When to speak
    triggers_silent: list  # When to stay silent
    failure_modes: list  # Known failure patterns
    prohibitions: list  # Specific prohibitions
    scope: str  # What this role owns


class DoctrineLoader:
    """Loads and caches doctrine files."""
    
    _cache: Dict[str, DoctrinalCanon] = {}
    
    @classmethod
    def load(cls, domain_name: str) -> Optional[DoctrinalCanon]:
        """Load doctrine for a domain (e.g., 'adaptation', 'risk', 'n')."""
        if domain_name in cls._cache:
            return cls._cache[domain_name]
        
        # Handle special naming cases
        filename_map = {
            "grand_strategist": "grand_strategist.yaml",
            "risk_resources": "risk_resources.yaml",
            "war_mode": "war_mode.yaml",
            "n": "n.yaml",
            "optionality": "optionality.yaml",
            "tribunal": "tribunal.yaml",
        }
        
        filename = filename_map.get(domain_name, f"{domain_name}.yaml")
        filepath = os.path.join(DOCTRINE_PATH, filename)
        
        if not os.path.exists(filepath):
            return None
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            
            if not data:
                return None
            
            # Parse the YAML structure
            canon = DoctrinalCanon(
                name=data.get("name", ""),
                role_type=data.get("role_type", "minister"),
                canon_text=data.get("persona", {}).get("canon", ""),
                purpose=data.get("doctrine", {}).get("purpose", ""),
                authority_may=data.get("doctrine", {}).get("authority", {}).get("may", []),
                authority_may_not=data.get("doctrine", {}).get("authority", {}).get("may_not", []),
                triggers_speak=data.get("doctrine", {}).get("triggers", {}).get("speak", []),
                triggers_silent=data.get("doctrine", {}).get("triggers", {}).get("silent", []),
                failure_modes=data.get("doctrine", {}).get("failure_modes", []),
                prohibitions=data.get("doctrine", {}).get("prohibitions", []),
                scope=data.get("doctrine", {}).get("scope", {}).get("owns", ""),
            )
            
            cls._cache[domain_name] = canon
            return canon
        
        except Exception as e:
            print(f"Error loading doctrine {filename}: {e}")
            return None
    
    @classmethod
    def extract_worldview_keywords(cls, canon_text: str) -> list:
        """Extract key phrases from the canon's core worldview."""
        keywords = []
        if not canon_text:
            return keywords
        
        lines = canon_text.split('\n')
        in_worldview = False
        
        for line in lines:
            if "Core Worldview" in line or "worldview" in line.lower():
                in_worldview = True
                continue
            
            if in_worldview and line.strip().startswith("–"):
                # Extract the statement after the dash
                statement = line.strip()[1:].strip()
                if statement:
                    keywords.append(statement.lower())
            
            if line.strip().startswith("Primary Mental Models"):
                break
        
        return keywords
    
    @classmethod
    def extract_warnings(cls, canon_text: str) -> list:
        """Extract typical warnings from canon."""
        warnings = []
        if not canon_text:
            return warnings
        
        lines = canon_text.split('\n')
        in_warnings = False
        
        for line in lines:
            if "Typical Warnings" in line:
                in_warnings = True
                continue
            
            if in_warnings and line.strip().startswith("–"):
                warning = line.strip()[1:].strip()
                if warning:
                    warnings.append(warning)
            
            if in_warnings and line.strip().startswith("Common Failure"):
                break
        
        return warnings
    
    @classmethod
    def should_speak_based_on_doctrine(cls, canon: DoctrinalCanon, context: Dict[str, Any]) -> bool:
        """Check if a minister should speak based on their doctrine triggers."""
        if not canon or not canon.triggers_speak:
            return True
        
        # Parse trigger keywords to check against context
        for trigger in canon.triggers_speak:
            trigger_lower = trigger.lower()
            
            # Check various context fields for matches
            user_input = context.get("user_input", "").lower()
            domains = [d.lower() for d in context.get("domains", [])]
            
            if trigger_lower in user_input or any(trigger_lower in d for d in domains):
                return True
        
        # If triggers_silent match, return False
        for silencer in canon.triggers_silent:
            silencer_lower = silencer.lower()
            user_input = context.get("user_input", "").lower()
            if silencer_lower in user_input:
                return False
        
        return True

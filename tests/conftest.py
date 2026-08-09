"""Pytest configuration for Study Buddy tests."""
import sys
import os

# Add backend/app to Python path so imports work without installing the package
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

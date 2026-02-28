"""
Entry point for the CrowAgent Streamlit application.
"""
import sys
import os

# Ensure the repository root is in sys.path
sys.path.append(os.path.dirname(__file__))

from app import main

if __name__ == "__main__":
    main.run()

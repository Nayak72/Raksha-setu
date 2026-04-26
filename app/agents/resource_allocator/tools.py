"""
RakshaSetu — Resource Allocator Tools
Re-exports shared tools for resource allocation.
"""

from app.shared.tools import get_shelters, get_available_volunteers, update_assignments

# List of tools available to the Resource Allocator Agent
RESOURCE_ALLOCATOR_TOOLS = [get_shelters, get_available_volunteers, update_assignments]

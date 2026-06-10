"""Adapter layer: identity + storage seams kept thin so providers swap cleanly.

This package is the *only* place that may import provider-specific SDKs
(supabase-py, boto3 with custom endpoints, cognito, etc.). The rest of the
codebase imports the abstract protocols defined here.
"""

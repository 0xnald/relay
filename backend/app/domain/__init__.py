"""Relay domain modules.

Domain models are imported from their defining modules. Keeping this package
initializer free of eager re-exports lets narrow runtimes load only the domain
models they actually use.
"""

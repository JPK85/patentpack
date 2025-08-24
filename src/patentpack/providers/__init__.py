"""
Provider adapters for patentpack.

Each provider module implements the PatentProvider Protocol:
- UsptoProvider  (PatentsView-compatible API)
- EpoProvider    (EPO OPS)

Add new providers by creating a module and wiring it in factory.make_provider().
"""

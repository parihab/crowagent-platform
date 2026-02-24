import overpy

def test_overpy_available():
    # Ensure overpy can be imported and provides a basic API signature
    api = overpy.Overpass()
    assert hasattr(api, "query")
    # The query method itself should be callable (network calls are not performed here)
    import inspect
    assert inspect.isfunction(api.query) or inspect.ismethod(api.query)

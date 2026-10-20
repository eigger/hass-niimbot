"""Central payload examples: run through the shared payload pytest plugin."""


def test_payload_contract_requires_plugin():
    raise AssertionError(
        "Run the shared payload contract; a plain pytest run cannot validate these examples"
    )

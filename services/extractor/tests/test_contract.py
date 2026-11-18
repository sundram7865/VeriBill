from extractor.contract_export import CONTRACT_DIR, SCHEMAS, render


def test_committed_contract_schemas_are_current():
    """If this fails, run `python -m extractor.contract_export` and update the Zod mirror."""
    for name, model in SCHEMAS.items():
        assert (CONTRACT_DIR / name).read_text(encoding="utf-8") == render(model), name

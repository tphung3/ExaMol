"""Test an in-memory store for molecular data"""

from pytest import fixture

from examol.store.db.memory import InMemoryStore
from examol.store.models import MoleculeRecord
from examol.utils.chemistry import get_inchi_key_from_molecule_string


@fixture()
def records() -> list[MoleculeRecord]:
    return [MoleculeRecord.from_identifier(smiles) for smiles in ['C', 'O', 'N']]


def test_store(tmpdir, records):
    # Open the database
    db_path = tmpdir / 'db.json.gz'
    with InMemoryStore(db_path) as store:
        assert len(store) == 0

        # Add the records
        store.update_records(records)
        assert len(store) == 3
        assert MoleculeRecord.from_identifier('C') in store
        assert MoleculeRecord.from_identifier('Br') not in store

    # Load database back in
    with InMemoryStore(db_path) as store:
        assert len(store) == 3

        # Test the make or retrieve
        actual = store[get_inchi_key_from_molecule_string('C')]
        assert store.get_or_make_record('C') is actual  # Gets the same value
        store.get_or_make_record('Br')
        assert len(store) == 4

from pathlib import Path
from rveval.adapters.mock_stateful import MockStatefulAdapter
from rveval.canonical import sha_json
def test_reset_same_initial_state():
    a=MockStatefulAdapter({},Path('.')); s1=a.open_session('case-1',seed=42,arm='A'); s2=a.open_session('case-1',seed=42,arm='B'); assert sha_json(s1.pairing_state())==sha_json(s2.pairing_state())

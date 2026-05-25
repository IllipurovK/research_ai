from memory import Memory
from models import Step

def test_memory_successful_steps():
    m = Memory()
    s1 = Step(step_id=0, description="a", query="a", normalized_query="a", success=True)
    s2 = Step(step_id=1, description="b", query="b", normalized_query="b", success=False)
    m.add_step(s1)
    m.add_step(s2)
    assert len(m.get_successful_steps()) == 1
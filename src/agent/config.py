from langchain_core.stores import InMemoryStore
from langgraph.checkpoint.memory import InMemorySaver

CHECKPOINTER = InMemorySaver()

STORE = InMemoryStore()

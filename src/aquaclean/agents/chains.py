"""The LCEL composition used by both supervisor and specialists via ChatProvider."""

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnableSequence


def structured_chain(model, schema: type, *, wire_schema=None) -> RunnableSequence:
    """Injected chat model; the provider owns construction, retry and usage reporting.

    with_structured_output includes the provider's schema parser. Keeping include_raw
    preserves usage and parser errors; a text parser would destroy this contract.
    """
    prompt = ChatPromptTemplate.from_messages(
        [("system", "{instructions}"), MessagesPlaceholder("messages")]
    )
    return prompt | model.with_structured_output(
        wire_schema or schema, method="json_schema", include_raw=True
    )


def chain_input(messages: list) -> dict:
    system = [text for role, text in messages if role == "system"]
    return {
        "instructions": "\n".join(system),
        "messages": [(role, text) for role, text in messages if role != "system"],
    }

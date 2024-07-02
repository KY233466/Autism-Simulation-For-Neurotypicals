from pydantic import AfterValidator, BaseModel
from typing_extensions import Annotated

from api.schemas.conversation import Messages
from api.schemas.persona import Persona

from . import llm_service as llm


async def generate_message(
    persona: Persona, scenario: str, messages: Messages, extra=""
) -> str:
    def validate_sender(v):
        if v != persona.name:
            raise ValueError(f"Sender must be {persona.name}")
        return v

    class MessageResponse(BaseModel):
        message: str
        sender: Annotated[str, AfterValidator(validate_sender)]

    instr = f"Instructions: {extra}" if extra else ""

    system_prompt = (
        f"{persona.description}\nScenario: {scenario}\n{instr}\nYou are chatting over "
        "text. Keep your messages under 50 words and appropriate for a text "
        "conversation. Keep the conversation going. Return a JSON object with the key "
        "'message' and your message as the value and the key 'sender' with "
        f"'{persona.name}' as the value. Respond ONLY with your next message. Do not "
        "include the previous messages in your response."
    )

    prompt_data = (
        "[CONVERSATION START]"
        if len(messages.root) == 0
        else messages.model_dump_json()
    )

    response = await llm.generate_strict(
        schema=MessageResponse,
        model=llm.MODEL_GPT_4,
        system=system_prompt,
        prompt=prompt_data,
    )

    return response.message
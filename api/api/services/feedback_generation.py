import asyncio
from typing import Annotated

from pydantic import AfterValidator, BaseModel, StringConstraints, TypeAdapter

from api.schemas.conversation import (
    ConversationData,
    FailedCheck,
    Feedback,
    MessageElement,
    UserMessage,
    message_list_adapter,
)
from api.schemas.persona import AgentPersona, UserPersona

from . import llm
from .flow_state.base import FeedbackFlowState, FeedbackFlowStateRef
from .message_generation import generate_message


def _extract_messages_for_feedback(conversation: ConversationData):
    messages = [
        elem.content
        for elem in conversation.elements
        if isinstance(elem, MessageElement)
    ]
    start = 0
    # take all messages since the user's last message
    for i in reversed(range(len(messages) - 2)):
        if not messages[i].user_sent:
            start = i + 1
            break

    return messages[start:]


class FeedbackWithPromptResponse(BaseModel):
    title: Annotated[str, StringConstraints(max_length=50)]
    body: Annotated[str, StringConstraints(max_length=600)]
    misunderstand: str
    clarification: str


async def generate_feedback(
    user: UserPersona,
    conversation: ConversationData,
    state: list[FeedbackFlowState],
) -> Feedback:
    agent = conversation.agent
    messages = _extract_messages_for_feedback(conversation)

    examples = [
        (
            [
                UserMessage(
                    message="I feel like a million bucks today!",
                ),
            ],
            FeedbackWithPromptResponse(
                title="Avoid Similies",
                body=(
                    "Your message relied on Chris understanding the simile 'I feel "
                    "like a million bucks today.' However, figurative language can "
                    "be confusing for autistic individuals, and Chris interpreted it "
                    "literally. To avoid misunderstandings, use more direct language."
                ),
                misunderstand=(
                    "You interpret the similie 'I feel like a million bucks today' "
                    "literally and think that the user won the lottery."
                ),
                clarification=(
                    "Your next message should apologize for using figurative language "
                    "and clarify that you didn't actually win the lottery but are "
                    "feeling really good today. Be direct and avoid figurative "
                    "language."
                ),
            ),
        ),
        (
            [
                UserMessage(
                    message="Break a leg in your performance today!",
                ),
            ],
            FeedbackWithPromptResponse(
                title="Avoid Idioms",
                body=(
                    "Using idioms like 'break a leg' can sometimes be confusing for "
                    "autistic individuals, as they may interpret the phrase literally. "
                    "Taylor interpreted your message literally and thought you wanted "
                    "them to get hurt instead of wishing them good luck. To avoid "
                    "misunderstandings, use clear, direct language."
                ),
                misunderstand=(
                    "You interpret the idiom 'break a leg' literally and think that "
                    "the user wants you to get hurt before your performance."
                ),
                clarification=(
                    "Your next message should apologize for using an idiom and clarify "
                    "that you didn't actually want Taylor to get hurt but were wishing "
                    "them good luck. Be direct and avoid figurative language."
                ),
            ),
        ),
    ]

    system_prompt = (
        "You are a social skills coach. Your task is to provide feedback on the "
        f"ongoing conversation between the user and {agent.name}, who is an "
        f"autistic individual. The conversation is happening over text. Address the "
        "following points in your feedback:\n"
        + "\n".join(f"{fb.prompt}" for fb in state)
        + "\nUse second person pronouns to address the uesr directly. Respond with "
        "a JSON object with the key 'title' containing the title (less than 50 "
        "characters) of your feedback, the key 'body' containing the feedback (less "
        "than 100 words), the key 'misunderstand' directing the autistic individual "
        "to purposefully misunderstand the user's message, and the key 'clarification' "
        "explaining what the user could do to clarify the situation. The "
        "'clarification' should not be a message, but a string that outlines what the "
        "user should do to clarify the misunderstanding. The clarfication should tell "
        "the user to apologize for their mistake and clarify their message. Examples:\n"
        + "\n\n".join(
            [
                f"{message_list_adapter.dump_json(messages).decode()}\n{fb.model_dump_json()}"
                for messages, fb in examples
            ]
        )
    )

    prompt_data = message_list_adapter.dump_json(messages).decode()

    feedback_base = await llm.generate(
        schema=FeedbackWithPromptResponse,
        model=llm.Model.CLAUDE_3_SONNET,
        system=system_prompt,
        prompt=prompt_data,
    )

    all_messages = [
        elem.content
        for elem in conversation.elements
        if isinstance(elem, MessageElement)
    ]

    async def generate_follow_up():
        return await generate_message(
            user_sent=True,
            user=user,
            agent=agent,
            messages=all_messages,
            scenario=conversation.info.scenario,
            instructions=(
                "You follow-up to clarify your previous message. "
                f"{feedback_base.clarification}"
            ),
        )

    async def generate_misunderstand():
        return await generate_message(
            user_sent=False,
            user=user,
            agent=agent,
            messages=all_messages,
            scenario=conversation.info.scenario,
            instructions=(
                f"You misunderstood the user's message. {feedback_base.misunderstand}"
            ),
        )

    follow_up, misunderstand = await asyncio.gather(
        generate_follow_up(), generate_misunderstand()
    )

    return Feedback(
        title=feedback_base.title,
        body=feedback_base.body,
        follow_up=follow_up,
        misunderstanding=misunderstand
    )


async def check_messages(
    user: UserPersona,
    agent: AgentPersona,
    conversation: ConversationData,
    checks: list[tuple[FeedbackFlowStateRef, FeedbackFlowState]],
) -> list[FailedCheck]:
    if not checks:
        return []

    check_names: set[str] = set(check.id for check, _ in checks)

    def validate_failed_check_name(failed_check: str) -> str:
        if failed_check not in check_names:
            raise ValueError(f"Invalid check ID: {failed_check}")

        return failed_check

    class FailedCheckNamed(BaseModel):
        id: Annotated[str, AfterValidator(validate_failed_check_name)]
        offender: str
        reason: str

    class Analysis(BaseModel):
        failed_checks: list[FailedCheckNamed]

    class Check(BaseModel):
        id: str
        check: str

    check_list_adapter = TypeAdapter(list[Check])

    checks_to_do = [Check(id=ref.id, check=check.check) for ref, check in checks]

    user_name = f"{user.name} (the user)" if user.name else "the user"

    system = (
        "You are a social skills coach. Your task is to analyze the following "
        f"conversation between {user_name}, and {agent.name}, who is an autistic "
        f"individual, and determine whether the latest message sent by {user_name} "
        "passes the provided checks. Here is list of checks that you should perform:\n"
        f"{check_list_adapter.dump_json(checks_to_do).decode()}"
        + "\nA check should fail if the user's message does not meets the criteria "
        "described in the check. Provide a JSON object with the key 'failed_checks' "
        "with a list of objects with the keys 'id' containing the semantic ID of the "
        f"check that failed, 'reason' containing the reason why the check failed, and "
        f"'offender' containing '{user_name}. If no checks fail, provide an empty "
        "list. DO NOT perform any checks that are not listed above."
    )

    messages = _extract_messages_for_feedback(conversation)
    prompt_data = message_list_adapter.dump_json(messages).decode()

    result = await llm.generate(
        schema=Analysis,
        model=llm.Model.CLAUDE_3_SONNET,
        system=system,
        prompt=prompt_data,
    )

    failed_checks = [
        FailedCheck(
            source=FeedbackFlowStateRef(id=check.id),
            reason=check.reason,
        )
        for check in result.failed_checks
        if check.offender == user_name
    ]

    return failed_checks

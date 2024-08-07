import asyncio
from uuid import UUID

import numpy as np
from pydantic import BaseModel

from api.schemas.persona import UserBasePersona, UserPersona

from . import llm
from .qa_messages import QaMessage, get_messages_by_user


class Demographics(BaseModel):
    age: str
    occupation: str


async def _extract_demographics(messages: list[QaMessage]) -> Demographics:
    system_prompt = (
        "As a user analyst, your task is to extract demographic information about the "
        "user based on the messages they sent to a chatbot. Start by analyzing "
        "messages sent by the user for any personal details, then use deductive "
        "reasoning to accurately determine their demographic information. Respond like "
        'this: <analysis>[ANALYSIS HERE]</analysis> {"age": "AGE RANGE", "occupation": '
        '"OCCUPATION"}'
    )
    prompt_data = "\n".join([message.message for message in messages])
    demographics = await llm.generate(
        schema=Demographics,
        model=llm.Model.GPT_4,
        system=system_prompt,
        prompt=prompt_data,
    )

    return demographics


# modified from https://arxiv.org/pdf/2305.15498
async def _cluster_messages(
    messages: list[str], epsilon: float, alpha: float, c: int
) -> list[list[int]]:
    message_embeddings = await llm.embed_many(messages)

    clusters = []
    sum_embeddings = []

    for message_index in range(len(messages)):
        max_similarity = -1
        best_cluster_index = None

        for cluster_index in range(len(clusters)):
            avg_embedding = sum_embeddings[cluster_index] / len(clusters[cluster_index])

            similarity = np.dot(avg_embedding, message_embeddings[message_index])

            if similarity > max_similarity:
                max_similarity = similarity
                best_cluster_index = cluster_index

        if best_cluster_index and max_similarity >= epsilon:
            clusters[best_cluster_index].append(message_index)
            sum_embeddings[best_cluster_index] = np.add(
                sum_embeddings[best_cluster_index], message_embeddings[message_index]
            )
        else:
            clusters.append([message_index])
            sum_embeddings.append(message_embeddings[message_index])

    # try to re-merge clusters that are too small
    for i in range(len(clusters)):
        if len(clusters[i]) >= c:
            continue

        avg_embedding = sum_embeddings[i] / len(clusters[i])

        max_similarity = -1
        best_cluster_index = None

        for j in range(i + 1, len(clusters)):
            avg_embedding2 = sum_embeddings[j] / len(clusters[j])

            similarity = np.dot(avg_embedding, avg_embedding2)

            if similarity > max_similarity:
                max_similarity = similarity
                best_cluster_index = j

        if best_cluster_index and max_similarity >= alpha:
            clusters[best_cluster_index].extend(clusters[i])
            sum_embeddings[best_cluster_index] = np.add(
                sum_embeddings[best_cluster_index], sum_embeddings[i]
            )
            clusters[i] = []

    # remove clusters that are still too small
    clusters = [cluster for cluster in clusters if len(cluster) >= c]

    return clusters


async def _get_cluster_topic(cluster: list[str]) -> str | None:
    class ClusterTopicResponse(BaseModel):
        topic: str | None

    system_prompt = (
        "Your task is to identify the primary topic of conversation based on a"
        "list of chatbot questions. Identify this topic as a single noun phrase "
        "that captures the main topics of interest present in the majority of "
        "responses, focusing on subjects, locations, or objects mentioned. Return "
        "a JSON object with the key 'topic' and the identified topic as the value."
        "If no clear topic is identifiable, use a null value."
    )
    prompt_data = "\n".join(cluster)
    response = await llm.generate(
        schema=ClusterTopicResponse,
        model=llm.Model.CLAUDE_3_SONNET,
        system=system_prompt,
        prompt=prompt_data,
    )

    return response.topic


async def _get_cluster_topics(clustered_prompts: list[list[str]]) -> list[str]:
    topics = await asyncio.gather(
        *[_get_cluster_topic(cluster) for cluster in clustered_prompts]
    )
    topics = [topic for topic in topics if topic is not None]

    return topics


async def _get_interests_from_topics(topics: list[str]) -> list[str]:
    class InterestResponse(BaseModel):
        interests: list[str]

    system_prompt = (
        "As an interest analyst, your task is to generate a coherent list of interests "
        "based on a given list of conversation topics. Each interest should be a "
        "single noun phrase, focusing specifically on subjects, locations, or objects. "
        "Do not repeat interests. Respond with a JSON object containing a list of "
        "interests under the key 'interests'."
    )
    prompt_data = "\n".join(topics)
    response = await llm.generate(
        schema=InterestResponse,
        model=llm.Model.GPT_4,
        system=system_prompt,
        prompt=prompt_data,
    )

    return response.interests


async def _extract_interests(messages: list[QaMessage]) -> list[str]:
    responses = [message.response for message in messages]

    clustered_messages_indices = await _cluster_messages(
        responses, epsilon=0.7, alpha=0.3, c=min(len(responses) // 12, 6)
    )

    clustered_prompts = [
        [messages[i].message for i in cluster] for cluster in clustered_messages_indices
    ]

    topics = await _get_cluster_topics(clustered_prompts)
    interests = await _get_interests_from_topics(topics)

    return interests


async def _extract_culture(messages: list[QaMessage]) -> str:
    class CultureResponse(BaseModel):
        culture: str

    system_prompt = (
        "As a culture analyst, your task is to identify the user's cultural background "
        "based on the messages they sent to a chatbot. Analyze the user's language, "
        "references, and topics of conversation to make an educated guess about their "
        "cultural background. Respond with a JSON object containing the key 'culture' "
        "and a description of the user's culture as the value."
    )
    prompt_data = "\n".join([message.message for message in messages])
    response = await llm.generate(
        schema=CultureResponse,
        model=llm.Model.GPT_4,
        system=system_prompt,
        prompt=prompt_data,
    )

    return response.culture


async def _extract_writing_style(messages: list[QaMessage]) -> str:
    class WritingStyleResponse(BaseModel):
        writing_style: str

    system_prompt = (
        "As a writing style analyst, your task is to identify the user's writing style "
        "based on the messages they sent to a chatbot. Analyze the user's sentence "
        "structure, vocabulary, and tone to determine their writing style. Respond "
        "with a JSON object containing the key 'writing_style' and a description of "
        "the user's writing style as the value. Consider the user's tone, vocabulary, "
        "capitalization, punctuation, and message length preferences. Begin with "
        "'Your writing style is...'"
    )

    prompt_data = "\n".join([message.message for message in messages])
    response = await llm.generate(
        schema=WritingStyleResponse,
        model=llm.Model.GPT_4,
        system=system_prompt,
        prompt=prompt_data,
    )

    return response.writing_style


async def _generate_user_persona(user_base: UserBasePersona):
    class PersonaResponse(BaseModel):
        persona: str

    system_prompt = (
        "As a persona generator, your task is to generate a system prompt that will "
        "be used to make ChatGPT embody a persona based on the provided information. "
        "You must include all user details and fill in gaps with logical assumptions. "
        "Respond with a JSON object containing the key 'persona' and the system prompt "
        "as the value. Start with 'You are...'"
    )

    prompt_data = user_base.model_dump_json()

    response = await llm.generate(
        schema=PersonaResponse,
        model=llm.Model.CLAUDE_3_SONNET,
        system=system_prompt,
        prompt=prompt_data,
    )

    return UserPersona(**user_base.model_dump(), description=response.persona)


async def _generate_user_info_base(messages: list[QaMessage]):
    interests, demographics, culture, writing_style = await asyncio.gather(
        _extract_interests(messages),
        _extract_demographics(messages),
        _extract_culture(messages),
        _extract_writing_style(messages),
    )

    user_base = UserBasePersona(
        age=demographics.age,
        occupation=demographics.occupation,
        interests=interests,
        culture=culture,
        writing_style=writing_style,
    )

    return user_base


async def generate_user_info(qa_id: UUID):
    try:
        messages = await get_messages_by_user(qa_id)
    except Exception as e:
        raise RuntimeError("Failed to fetch user messages from endpoint") from e
    user_base = await _generate_user_info_base(messages)
    user_persona = await _generate_user_persona(user_base)

    return user_persona

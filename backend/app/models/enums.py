from enum import Enum


class Sex(str, Enum):
    male = "male"
    female = "female"
    other = "other"
    prefer_not_to_say = "prefer_not_to_say"


class ActivityLevel(str, Enum):
    sedentary = "sedentary"
    light = "light"
    moderate = "moderate"
    active = "active"
    very_active = "very_active"


class HealthGoal(str, Enum):
    weight_loss = "weight_loss"
    weight_gain = "weight_gain"
    weight_maintenance = "weight_maintenance"
    muscle_gain = "muscle_gain"
    medical_diet = "medical_diet"


class ChatSessionType(str, Enum):
    analyse = "analyse"
    compare = "compare"
    rag_chat = "rag_chat"


class ChatRole(str, Enum):
    user = "user"
    assistant = "assistant"
    system = "system"


class RagSourceType(str, Enum):
    """
    Classifies the origin of each RAG chunk for targeted retrieval.

    Why 4 buckets?
    ─────────────
    'knowledge'   — General nutrition science: WHO guidelines, FSSAI rules,
                    macro/micro-nutrient references, food-group recommendations.
                    Injected for every query to ground the model in facts.

    'disease'     — Disease-specific diet rules: "diabetics should limit
                    refined sugar", "hypertension → reduce sodium".
                    Only retrieved when the user's health_profile has a
                    matching disease_tag, keeping prompts lean.

    'user_memory' — Semantic summaries of past conversations for THIS user.
                    Gives the model a lightweight episodic memory without
                    fine-tuning. Retrieved per-user using the user_id FK.

    'label_ocr'   — Extracted and parsed text from nutrition label images.
                    Stored after OCR so the model can compare labels across
                    sessions without re-scanning the same image.

    Separating these allows retrieval filters like:
        WHERE source_type = 'disease' AND disease_tag = 'diabetes'
    so we never pollute a general query with user-private memory chunks,
    and never inject disease-specific rules for healthy users.
    """

    knowledge = "knowledge"
    disease = "disease"
    user_memory = "user_memory"
    label_ocr = "label_ocr"

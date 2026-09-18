from app.a2a.schemas import A2AEnvelope
from app.a2a.signing import sign_envelope


def signed_envelope(envelope: A2AEnvelope, secret: str) -> A2AEnvelope:
    return envelope.model_copy(update={"signature": sign_envelope(envelope, secret)})

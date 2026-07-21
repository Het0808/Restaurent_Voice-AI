"""Deterministic test doubles for retrieval tests."""


class FakeEmbeddings:
    @staticmethod
    def _vector(text: str) -> list[float]:
        lowered = text.lower()
        return [
            float(lowered.count("dairy") + lowered.count("paneer")),
            float(lowered.count("parking")),
            1.0,
        ]

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._vector(text) for text in texts]

    async def embed_query(self, text: str) -> list[float]:
        return self._vector(text)

from openai import AsyncOpenAI

class AiService:
    def __init__(self):
        self.client = AsyncOpenAI(
            base_url="http://localhost:11434/v1",
            api_key="ollama"
        )
        self.model = "phi3:mini"

    async def get_response(self, user_message: str) -> str:
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Ти — армійський бот. Ти допомагаєш діловоду."
                            "Твій стиль: суміш військового гумору та IT-жаргону. "
                            "Відповідай виключно українською мовою"
                            "Відповідай коротко, влучно, іноді використовуй армійський сленг."
                        )
                    },
                    {"role": "user", "content": user_message}
                ],
                temperature=0.3 # Рівень креативності (0.0 - робот, 1.0 - філософ)
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"❌ ШАЇ відключився. Мізки заклинило: {str(e)}"
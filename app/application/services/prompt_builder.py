class PromptBuilder:
    def build_poem_prompt(self, context: dict) -> str:
        """
        Собирает промпт для генерации стихотворения на основе контекста заказа.
        Ожидаемый контекст:
        - occasion: повод (день рождения, свадьба и т.д.)
        - recipient: кому (имя, роль)
        - details: детали (интересы, забавные случаи)
        - style: стиль (по умолчанию юмор)
        """
        occasion = context.get("occasion", "день рождения")
        recipient = context.get("recipient", "друга")
        details = context.get("details", "много радости")
        style = context.get("style", "юмор")

        prompt = (
            f"Напиши веселое и доброе стихотворение на {occasion}.\n"
            f"Получатель: {recipient}.\n"
            f"Ключевые детали, которые нужно включить: {details}.\n"
            f"Стиль: {style}.\n\n"
            "Требования:\n"
            "1. Ровно 3-4 четверостишья.\n"
            "2. Хорошая рифма и ритм.\n"
            "3. Без использования нецензурных слов и грубости.\n"
            "4. Должно быть смешно, но не обидно.\n"
            "5. НЕ используй HTML теги, markdown разметку или blockquote. Только чистый текст стихотворения."
        )
        return prompt
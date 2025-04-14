from transformers import pipeline

class RAGModel:
    def __init__(self):
        """Initialize the RAG model."""
        self.generator = pipeline("text-generation", model="distilgpt2", device="cpu")

    def generate_question_from_text(self, text):
        """
        Generate a single question with 4 selectable answers from the input text.
        :param text: The text to generate a question from.
        :return: A dictionary with the question and 4 answers.
        """
        prompt = f"Generate one multiple-choice question with 4 options (1 correct) based on the following text:\n\n{text}"
        response = self.generator(prompt, max_length=300, num_return_sequences=1)
        generated_text = response[0]['generated_text']

        # Parse response to extract question and answers
        lines = generated_text.strip().split("\n")
        if len(lines) >= 5:
            question = lines[0]
            options = lines[1:5]
            return {
                'question': question,
                'options': options
            }
        else:
            return None

    def generate_questions_from_pages(self, extracted_texts):
        """
        Generate questions based on extracted texts from multiple pages.
        :param extracted_texts: List of text from the pages.
        :return: A list of dictionaries with questions and answers.
        """
        questions = []
        for text in extracted_texts:
            if len(questions) >= 10:  # Limit to 10 questions
                break
            question_data = self.generate_question_from_text(text)
            if question_data:
                questions.append(question_data)
        return questions
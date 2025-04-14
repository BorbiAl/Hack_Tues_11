from transformers import pipeline

class RAGModel:
    def __init__(self):
        """Initialize the RAG model."""
        self.generator = pipeline("text-generation", model="distilgpt2", device="cpu")

    def generate_question_from_text(self, text):
        """
        Generate one multiple-choice question with 4 selectable answers from the input text.
        This function removes the prompt from the generated text, so only the resulting question is returned.
        
        :param text: The input text from which to generate the question.
        :return: A dictionary with the question and its 4 options in Bulgarian.
        """
        prompt = f"Generate one multiple-choice question with 4 options (1 correct) based on the following text in Bulgarian:\n\n{text}"
        response = self.generator(prompt, max_length=300, num_return_sequences=1)
        generated_text = response[0]['generated_text']
        
        # Remove the prompt part from the generated text if it's included.
        if generated_text.startswith(prompt):
            generated_text = generated_text[len(prompt):].strip()
        
        # Further processing: Split the cleaned text into lines and ensure we have at least 5 lines 
        # (first line for the question and next four for the selectable answers)
        lines = [line.strip() for line in generated_text.split("\n") if line.strip()]
        if len(lines) >= 5:
            question = lines[0]
            options = lines[1:5]
            return {
                'question': question,
                'options': options,
            }
        else:
            return None

    def generate_questions_from_pages(self, extracted_texts):
        """
        Generate questions based on extracted texts from multiple pages.
        :param extracted_texts: List of text segments extracted from each page.
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
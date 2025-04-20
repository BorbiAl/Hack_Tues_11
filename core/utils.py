# utils.py

def parse_generated_questions(generated_text):
    """Parse AI-generated text into structured questions."""
    questions = []
    for block in generated_text.split("\n\n"):
        lines = block.split("\n")
        if len(lines) < 5:
            continue
        question = lines[0]
        options = lines[1:5]
        correct_answer = lines[5].split(":")[1].strip() if len(lines) > 5 else None
        questions.append({
            'question': question,
            'options': options,
            'answer': correct_answer
        })
    return questions

import spacy
import pytextrank


class KeywordExtractor:
    def __init__(self):
        # Define undesired keywords (all in lowercase) to filter out overly generic words in the restaurant context
        self.undesired = {
            "food",
            "cuisine",
            "dinner",
            "restaurant"
        }
        # List of allowed proper nouns (can be expanded if needed, currently empty)
        self.allowed_propn = set()
        # Load spaCy's transformer English model and add the PyTextRank pipeline
        self.nlp = spacy.load("en_core_web_trf")
        self.nlp.add_pipe("textrank")

    def filter_phrase(self, phrase):
        if phrase.rank < 0.1:
            return False

        # If the phrase text exactly appears in the undesired list, filter it out
        if phrase.text.lower().strip() in self.undesired:
            return False

        # If the phrase is in the allowed proper noun list, let it pass directly
        if phrase.text.lower().strip() in self.allowed_propn:
            return True

        # Removed filtering logic for job positions (developer/engineer) from the original course recommendation

        # Convert the phrase to a Doc object for tokenization and part-of-speech tagging
        doc_phrase = self.nlp(phrase.text)
        tokens = list(doc_phrase)

        # After removing stop words, check if there are any valid tokens
        filtered_tokens = [token for token in tokens if not token.is_stop]
        if len(filtered_tokens) == 0:
            return False

        # If the phrase contains only one word, only allow it if it is a noun or proper noun
        if len(tokens) == 1:
            if tokens[0].pos_ not in {"NOUN", "PROPN"}:
                return False

        # If more than 50% of the tokens in the phrase are stop words, filter it out
        stop_count = sum(1 for token in tokens if token.is_stop)
        if len(tokens) > 0 and stop_count / len(tokens) > 0.5:
            return False

        # Only keep phrases that contain at least one noun or proper noun
        if not any(token.pos_ in {"NOUN", "PROPN"} for token in tokens):
            return False

        return True

    def refine_phrase(self, phrase):
        """
        Further refine the candidate phrase:
        - Tokenize and remove stop words and some generic words in the restaurant context
          (such as 'some', 'eat', 'have', 'like', 'after', 'food', 'dinner', 'suggestion', 'suggestions')
        - If only one candidate token remains after removal, return that token; otherwise, return the original phrase
        """
        doc_phrase = self.nlp(phrase.text)
        generic_undesired = {"some", "suggestions", "suggestion", "eat", "have", "like", "after", "food", "dinner", "class"}
        candidates = [token.text for token in doc_phrase if not token.is_stop and token.text.lower() not in generic_undesired]
        if len(candidates) == 1:
            return candidates[0]
        return phrase.text

    def extract_keywords(self, prompt: str):
        """
        Input a string prompt, return a list of filtered keywords
        """
        doc = self.nlp(prompt)
        keywords = []
        for phrase in doc._.phrases:
            if self.filter_phrase(phrase):
                refined = self.refine_phrase(phrase)
                keywords.append(refined)
        # Remove duplicates while preserving order
        unique_keywords = list(dict.fromkeys(keywords))
        return unique_keywords


if __name__ == "__main__":
    extractor = KeywordExtractor()
    test_prompts = [
        "I want to eat some american food, like berger.I also want to have some cocktail after dinner. I am near Midtown West, can you give me some suggestion?",
        "I want to try some Italian food, like pizza Margherita. I would also enjoy a glass of red wine after my meal. I'm near South Street Seaport, can you recommend a restaurant?",
        "I'm in the mood for some Mexican cuisine, such as tacos and enchiladas, and I'd love a margarita with dinner. I'm located in the East Village, any suggestions?",
        "I'm looking for a cozy spot in Greenwich Village serving authentic Italian fare—something like a classic pizza Margherita or fresh pasta—and I'd love to unwind with a good glass of red wine afterward."
    ]

    for prompt in test_prompts:
        print("Prompt:", prompt)
        keywords = extractor.extract_keywords(prompt)
        print("Extracted Keywords:", keywords)
        print("-" * 40)

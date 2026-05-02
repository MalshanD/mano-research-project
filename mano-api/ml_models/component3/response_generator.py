"""
Response Generation Engine
Generates empathetic responses based on context and intent
"""

from transformers import AutoTokenizer, AutoModelForSeq2SeqLM, pipeline
import torch
from typing import List, Dict, Optional
import random


class ResponseGenerator:
    """Generates contextual responses for mental health conversations"""

    def __init__(self, model_name: str = "facebook/blenderbot-400M-distill"):
        """
        Initialize response generator
        Uses conversational models like BlenderBot or DialoGPT
        """
        self.device = torch.device('cuda' if torch.cuda.is_available() and torch.cuda.device_count() > 0 else 'cpu')
        print(f"Loading response generation model: {model_name}")
        print(f"Using device: {self.device}")

        try:
            self.tokenizer = AutoTokenizer.from_pretrained(model_name)
            self.model = AutoModelForSeq2SeqLM.from_pretrained(model_name).to(self.device)
            self.model_type = "seq2seq"
        except:
            # Fallback to simpler model
            print("Using fallback conversational pipeline")
            self.conversational = pipeline("conversational", model="microsoft/DialoGPT-medium")
            self.model_type = "dialog"

        self.conversation_history = []

    def generate_response(self, user_input: str, context: Optional[str] = None,
                         max_length: int = 150, temperature: float = 0.7) -> str:
        """
        Generate response based on user input and context

        Args:
            user_input: User's message
            context: Additional context (intent, emotion, etc.)
            max_length: Maximum response length
            temperature: Sampling temperature (higher = more creative)

        Returns:
            Generated response
        """
        if self.model_type == "seq2seq":
            # Prepare input
            if context:
                input_text = f"{context} {user_input}"
            else:
                input_text = user_input

            # Tokenize
            inputs = self.tokenizer(input_text, return_tensors="pt",
                                   max_length=512, truncation=True).to(self.device)

            # Generate
            with torch.no_grad():
                outputs = self.model.generate(
                    inputs["input_ids"],
                    attention_mask=inputs.get("attention_mask"),
                    max_length=max_length,
                    temperature=temperature,
                    do_sample=True,
                    top_p=0.9,
                    pad_token_id=self.tokenizer.eos_token_id
                )

            response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)

        else:
            # Use conversational pipeline
            from transformers import Conversation
            conversation = Conversation(user_input)
            conversation = self.conversational(conversation)
            response = conversation.generated_responses[-1]

        # Add to history
        self.conversation_history.append({
            'user': user_input,
            'bot': response
        })

        return response

    def clear_history(self):
        """Clear conversation history"""
        self.conversation_history = []

    def get_history(self) -> List[Dict]:
        """Get conversation history"""
        return self.conversation_history


class TemplateBasedResponder:
    """Template-based response generation for specific intents"""

    def __init__(self, responses_dict: Dict[str, List[str]]):
        """
        Initialize with response templates

        Args:
            responses_dict: Dictionary mapping intents to response templates
        """
        self.responses = responses_dict

    def get_response(self, intent: str, context: Optional[Dict] = None) -> str:
        """
        Get response for a specific intent

        Args:
            intent: Detected intent
            context: Additional context for personalization

        Returns:
            Response string
        """
        if intent not in self.responses:
            return random.choice(self.responses.get('default',
                ['I understand. Could you tell me more about that?']))

        response_templates = self.responses[intent]
        response = random.choice(response_templates)

        # Personalize if context provided
        if context:
            for key, value in context.items():
                response = response.replace(f"{{{key}}}", str(value))

        return response

    def add_response_template(self, intent: str, template: str):
        """Add a new response template for an intent"""
        if intent not in self.responses:
            self.responses[intent] = []
        self.responses[intent].append(template)


class HybridResponseEngine:
    """
    Hybrid response engine combining template-based and generative approaches
    """

    def __init__(self, responses_dict: Dict[str, List[str]],
                 use_generative: bool = True):
        """
        Initialize hybrid engine

        Args:
            responses_dict: Response templates
            use_generative: Whether to use generative model
        """
        self.template_responder = TemplateBasedResponder(responses_dict)
        self.use_generative = use_generative

        if use_generative:
            try:
                self.generative_responder = ResponseGenerator()
            except Exception as e:
                print(f"Warning: Could not load generative model: {e}")
                self.use_generative = False

    def generate_response(self, user_input: str, intent: str,
                         confidence: float, context: Optional[Dict] = None) -> str:
        """
        Generate response using hybrid approach

        Args:
            user_input: User's message
            intent: Detected intent
            confidence: Confidence score for intent
            context: Additional context

        Returns:
            Generated response
        """
        # Use template-based for high-confidence, known intents
        if confidence > 0.7 and intent in self.template_responder.responses:
            return self.template_responder.get_response(intent, context)

        # Use generative for low-confidence or unknown intents
        elif self.use_generative:
            context_str = ""
            if isinstance(context, dict):
                persona = context.get('persona', '')
                topic = context.get('topic', intent)
                if persona:
                    context_str += f"Persona: {persona}. "
                if topic:
                    context_str += f"Topic: {topic}. "
            elif intent:
                 context_str += f"Intent: {intent}. "
            
            return self.generative_responder.generate_response(user_input, context_str)

        # Fallback to template
        else:
            return self.template_responder.get_response(intent, context)

    def get_conversation_history(self) -> List[Dict]:
        """Get conversation history from generative responder"""
        if self.use_generative:
            return self.generative_responder.get_history()
        return []

    def clear_history(self):
        """Clear conversation history"""
        if self.use_generative:
            self.generative_responder.clear_history()


if __name__ == "__main__":
    print("Response Generation Engine Module")
    print("This module provides template-based and generative response capabilities")

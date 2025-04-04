import anthropic
import logging
from backend.app.core.config import settings

logger = logging.getLogger(__name__)

class AnthropicClient:
    """
    A wrapper for the Anthropic API client.
    """
    def __init__(self, api_key: str):
        if not api_key:
            logger.warning("Anthropic API key is not configured. LLM analysis will fail.")
            # Allow initialization but operations will fail later if key is truly needed and missing.
            # Alternatively, raise ValueError("Anthropic API key is required.")
            self.client = None
        else:
            try:
                self.client = anthropic.AsyncAnthropic(api_key=api_key)
            except Exception as e:
                logger.error(f"Failed to initialize Anthropic client: {e}", exc_info=True)
                self.client = None

    async def get_llm_analysis(
        self,
        prompt: str,
        model_name: str = "claude-3-sonnet-20240229",
        max_tokens: int = 1024,
        system_message: str = "You are an AI assistant specialized in analyzing social media content. Respond ONLY with the requested JSON object.",
    ) -> str:
        """
        Gets analysis from the Anthropic LLM.

        Args:
            prompt: The prompt containing the text and instructions for the LLM.
            model_name: The name of the Claude model to use.
            max_tokens: The maximum number of tokens for the response.
            system_message: A system message to guide the LLM's behavior.

        Returns:
            The raw text response from the LLM, expected to be a JSON string.

        Raises:
            anthropic.APIError: If the API call fails.
            ValueError: If the client was not initialized due to a missing API key.
        """
        if not self.client:
            logger.error("Anthropic client not initialized. Cannot make API call.")
            raise ValueError("Anthropic client is not initialized, likely due to a missing API key.")

        try:
            logger.debug(f"Sending prompt to Anthropic model {model_name}:\n{prompt}")
            message = await self.client.messages.create(
                model=model_name,
                max_tokens=max_tokens,
                system=system_message,
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
            )
            logger.debug(f"Received response from Anthropic: {message}")

            if message.content and isinstance(message.content, list) and message.content[0].text:
                # Assuming the first content block contains the primary response text
                raw_response = message.content[0].text.strip()
                 # Sometimes the model wraps the JSON in ```json ... ```
                if raw_response.startswith("```json"):
                    raw_response = raw_response[7:]
                if raw_response.endswith("```"):
                    raw_response = raw_response[:-3]
                return raw_response.strip()
            else:
                logger.warning("Anthropic response did not contain expected text content.")
                return "{}" # Return empty JSON string on unexpected response format

        except anthropic.APIConnectionError as e:
            logger.error(f"Anthropic API connection error: {e}", exc_info=True)
            raise
        except anthropic.RateLimitError as e:
            logger.error(f"Anthropic API rate limit exceeded: {e}", exc_info=True)
            raise
        except anthropic.APIStatusError as e:
            logger.error(f"Anthropic API status error (Status code: {e.status_code}): {e.response}", exc_info=True)
            raise
        except anthropic.APIError as e:
            logger.error(f"An unexpected Anthropic API error occurred: {e}", exc_info=True)
            raise
        except Exception as e:
            logger.error(f"An unexpected error occurred during LLM analysis: {e}", exc_info=True)
            # Re-raise as a generic exception or a custom one if defined
            raise RuntimeError(f"LLM analysis failed due to an unexpected error: {e}")


# Initialize a singleton client instance
# This assumes settings are loaded globally when the module is imported.
anthropic_client = AnthropicClient(api_key=settings.ANTHROPIC_API_KEY)

# Expose the function directly for easier import
async def get_llm_analysis(
    prompt: str,
    model_name: str = "claude-3-sonnet-20240229",
    max_tokens: int = 1024,
    system_message: str = "You are an AI assistant specialized in analyzing social media content. Respond ONLY with the requested JSON object.",
) -> str:
    """Convenience function to call the singleton client's method."""
    return await anthropic_client.get_llm_analysis(
        prompt=prompt,
        model_name=model_name,
        max_tokens=max_tokens,
        system_message=system_message,
    ) 
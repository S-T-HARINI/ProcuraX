import pytest

try:
    from ollama import chat
except ImportError:
    pytest.skip("ollama python package not installed", allow_module_level=True)

if __name__ == "__main__":
    response = chat(
        model="gemma4:e2b",
        messages=[
            {
                "role": "user",
                "content": "Explain procurement in two sentences."
            }
        ]
    )
    print(response.message.content)
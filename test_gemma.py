from ollama import chat

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
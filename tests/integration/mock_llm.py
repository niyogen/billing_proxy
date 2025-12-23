from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route("/v1/chat/completions", methods=["POST"])
@app.route("/chat/completions", methods=["POST"])
def chat_completions():
    # Log request for debugging if needed
    print("Received request:", request.json)
    
    # Return a fixed mock response matching OpenAI format
    return jsonify({
        "id": "chatcmpl-mock-123",
        "object": "chat.completion",
        "created": 1677652288,
        "model": "gpt-4o",
        "choices": [{
            "index": 0,
            "message": {
                "role": "assistant",
                "content": "This is a mock response from the integration test service."
            },
            "finish_reason": "stop"
        }],
        "usage": {
            "prompt_tokens": 10,
            "completion_tokens": 20,
            "total_tokens": 30
        }
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)

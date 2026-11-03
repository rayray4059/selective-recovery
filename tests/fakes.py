DONE = '{"tool": "done"}'


class FakeLLM:
    model = "fake"
    seed = 0
    temperature = 0.0
    max_tokens = 0

    def __init__(self, replies):
        self.replies = list(replies)
        self.seen = []

    def chat(self, messages, schema=None):
        self.seen.append({"messages": [dict(m) for m in messages], "schema": schema})
        reply = self.replies.pop(0) if self.replies else DONE
        return reply, {"wall_s": 0.0, "prompt_tokens": 1, "completion_tokens": 1, "finish_reason": "stop"}

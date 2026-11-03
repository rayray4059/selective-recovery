import time

from openai import OpenAI


class LLM:
    def __init__(self, url="http://localhost:8080/v1", seed=0, temperature=0.0, max_tokens=2048, client=None):
        self.client = client or OpenAI(base_url=url, api_key="none")
        self.seed = seed
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.model = None

    def chat(self, messages, schema=None):
        if self.model is None:
            self.model = self.client.models.list().data[0].id
        kwargs = {
            "model": self.model, "messages": messages, "temperature": self.temperature,
            "max_tokens": self.max_tokens, "seed": self.seed,
            "extra_body": {"chat_template_kwargs": {"enable_thinking": False}},
        }
        if schema:
            kwargs["response_format"] = {"type": "json_schema", "json_schema": {"name": "reply", "schema": schema}}
        start = time.time()
        resp = self.client.chat.completions.create(**kwargs)
        stats = {
            "wall_s": round(time.time() - start, 2),
            "prompt_tokens": resp.usage.prompt_tokens,
            "completion_tokens": resp.usage.completion_tokens,
            "finish_reason": resp.choices[0].finish_reason,
        }
        return resp.choices[0].message.content or "", stats

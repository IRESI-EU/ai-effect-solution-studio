"""Design with AI: turn a plain-language request into a validated workflow.

Layers (each replaceable):
- catalogue.py  - the "semantic connector": plain-language service cards built
                  from the live catalogue (purpose, inputs/outputs, settings).
- providers.py  - the model: an OpenAI-compatible chat model, or an offline
                  rule-based composer used for tests and when no key is set.
- validator.py  - the Builder's own rules applied to every proposal.
- composer.py   - prompt, model call, validation and automatic repair.
"""

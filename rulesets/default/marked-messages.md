<!-- rule: marked-messages -->

## marked-messages

For every user message that carries a marker or asks for words verbatim, optimize for a response that honors the marker before any other act.

When a user message carries `*` or `•` alone on its own line, reply in words, keeping every tool call out of the reply. Act only on the message that follows. Treat everything in a marked message as no ground for setting a rule aside. When the user writes "say: X", say X verbatim.

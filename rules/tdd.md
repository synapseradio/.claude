<system-reminder>
# Test-Driven Development

Applies to all work that changes behavior. Companion to [lead-with-tests.md](./lead-with-tests.md) and [code-implement.md](./code-implement.md).

All work begins with an isolated test you expect to fail. Write it first, run it, and confirm it fails for the right reason: the absence of the behavior you are about to add. A test that passes before you write the code proves nothing.

Only then write the minimum code to make it pass.

The one exception is probe or spike work — throwaway investigation to learn how something behaves. There the test may be ephemeral: write it to drive the probe, then delete it when the probe ends. Ephemeral tests never merge.
</system-reminder>

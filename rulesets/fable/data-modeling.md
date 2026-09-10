<!-- rule: data-modeling -->

## data-modeling

For every type, data structure, schema, interface signature, or error channel you design or change, in source code or in reasoning about it, optimize for a type that admits only legal states, bought only where it deletes a "should never happen" branch.

Model with product types, sum types, and exhaustive matching. Where a model reaches past them, to GADTs for one, stop and check whether a value check crept back in. Count a newtype wrapper as ergonomics, never as a state removed.

### The runtime check

Treat every runtime check for a state that should never happen as a modeling decision. Write no test for a state the type makes unrepresentable. Where a runtime check, assertion, or throw guards a state that should never happen, ask each move's test, apply the move on a yes, skip it on a no, then model the state out or accept the panic, the runtime failure on that state, knowingly. Where a test must exercise a "should never happen" branch, strengthen the type until the branch disappears. Where strengthening costs more than it pays, write the test guarding the invariant, in place of the type declined. Where a precise type costs too much, use an abstract type with a smart constructor, validated inside, exposing only invariant-preserving methods, with its method set kept closed.

### The five moves

Each move carries a step, an example, and a test question.

Model the positive space. List the legal states and write one constructor per state. For a user reachable by email, phone, or both, write EmailOnly, PhoneOnly, and Both, where two optional fields admit a user reachable by neither. Test it by asking whether you can list the legal states as cases.

Choose the representation for the code at hand. Pick whichever representation serves the code reading it, converting at boundaries. For a time range ordered by construction, use a start time plus a non-negative duration, where two raw timestamps need a check. Test it by asking whether you are defending one true representation.

Let types propagate obligations. Link producers and consumers through the type definition, so a new case makes exhaustive matching report every consumer site. A fourth contact kind added to the union fails every match that lacks it. Test it by asking whether the compiler finds every consumer when a case gets added.

Buy precision where it deletes a panic. Strengthen the type at the site of a "should never happen" throw, and keep the simplest representation at every other site. An email address stays a plain string until code inspects its structure. Test it by asking whether this precision deletes a panic.

Move obligations to whoever can discharge them. Use a required parameter over an optional value, and parse loose input into a precise type once at a boundary and pass it inward. A non-empty list gets parsed at the API edge, where a check returning only a verdict makes every downstream site check again. Test it by asking which side of this boundary can handle the failure.

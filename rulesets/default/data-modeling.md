<!-- rule: data-modeling -->

## data-modeling

For every type, data structure, schema, interface signature, or error channel you design or change, in code or in reasoning about it, optimize for a type that admits only legal states, bought only where it deletes a "should never happen" branch.

Model with product types, sum types, and exhaustive matching.
A model reaches past them, to GADTs for one ? stop and check whether a value check crept back in.
Count a newtype wrapper as ergonomics, with every state it wraps still admitted.

### The runtime check

Treat every runtime check for a state that should never happen as a modeling decision. Test a state only where the type can represent it.
A runtime check, assertion, or throw guards a state that should never happen ? ask each move's test question below (yes ? apply the move : skip it), then model the state out or knowingly accept the panic, the runtime failure on that state.
A test must exercise a "should never happen" branch ? strengthen the type until the branch disappears, at the first rung the gain pays for (a precise type > an abstract type with a smart constructor, validated inside, exposing only invariant-preserving methods, its method set closed > a test guarding the invariant, in place of the declined type).

### The moves

Each move carries a step, an example, and a test question.

Model the positive space. List the legal states, one constructor per state. For a user reachable by email, phone, or both, write EmailOnly, PhoneOnly, and Both, where two optional fields also admit a user with both empty. Test: can you list the legal states as cases?

Choose the representation for the code at hand. Pick whichever serves the code reading it, converting at boundaries. For a time range ordered by construction, use a start time plus a duration of zero or more, where two raw timestamps need a check. Test: would another representation let you delete this check?

Let types propagate obligations. Link producers and consumers through the type definition, so a new case makes exhaustive matching report every consumer site. A fourth contact kind added to the union fails every match that lacks it. Test: could a new case leave a consumer the compiler stays silent about?

Buy precision where it deletes a panic. Strengthen the type at the site of a "should never happen" throw, and keep the simplest representation at every other site. An email address stays a plain string until code inspects its structure. Test: does this precision delete a panic?

Move obligations to whoever can discharge them. Use a required parameter over an optional value, and parse loose input into a precise type once at a boundary, then pass it inward. A non-empty list gets parsed at the API edge, where a check returning only a verdict makes every downstream site check again. Test: can the caller handle this failure where this code cannot?

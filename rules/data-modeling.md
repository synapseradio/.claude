<rule name="data-modeling">

  <applies_when>
    You are designing or changing types, data structures, schemas, interface signatures, or error channels, in source code or in reasoning about it.
  </applies_when>

  <optimize_for>
    a type that admits only legal states, bought exactly where it deletes a "should never happen" branch.
    <why_it_matters>
      The compiler discharges a state a type makes unrepresentable, and no test has to cover it. A runtime check for a state that should never happen is a modeling decision, and the five moves come from Alexis King's talk on constructive data modeling at https://www.youtube.com/watch?v=0BXuYlNrUmE. Product types, sum types, and exhaustive matching suffice for all five, so a model reaching for variadic tuples, GADTs, or refinement types has usually drifted back into restriction. A newtype wrapper slows a mistake without making it unrepresentable, so it buys ergonomics and nothing the compiler can discharge. Unused precision costs reuse and clarity while deleting nothing.
    </why_it_matters>
  </optimize_for>

  <decide name="panic">
    Where a runtime check, assertion, or throw guards a state that should never happen, ask each move's test, apply the move on a yes, skip it on a no, then model the state out or accept the panic knowingly. Where a test must exercise a "should never happen" branch, strengthen the type until the branch disappears. Where strengthening costs more than it pays, write the test guarding the invariant, in place of the type declined. Where a precise type costs too much, use an abstract type with a smart constructor, validated inside, exposing only invariant-preserving methods, with its method set kept closed.
  </decide>

  <define name="moves">
    Each move carries a step, an example, and a test question.

    Model the positive space. List the legal states and write one constructor per state. For a user reachable by email, phone, or both, write EmailOnly, PhoneOnly, and Both, where two optional fields admit a user reachable by neither. Test it by asking whether I can list the legal states as cases.

    Choose the representation for the code at hand. Pick whichever representation serves the code reading it, converting at boundaries. For a time range ordered by construction, use a start time plus a non-negative duration, where two raw timestamps need a check. Test it by asking whether I am defending one true representation.

    Let types propagate obligations. Link producers and consumers through the type definition, so a new case makes exhaustive matching report every consumer site. A fourth contact kind added to the union fails every match that lacks it. Test it by asking whether the compiler finds every consumer when a case gets added.

    Buy precision where it deletes a panic. Strengthen the type at the site of a "should never happen" throw, and keep the simplest representation at every other site. An email address stays a plain string until code inspects its structure. Test it by asking whether this precision deletes a panic.

    Move obligations to whoever can discharge them. Use a required parameter over an optional value, and parse loose input into a precise type once at a boundary and pass it inward. A non-empty list gets parsed at the API edge, where a check returning only a verdict makes every downstream site check again. Test it by asking which side of this boundary can handle the failure.
  </define>

</rule>

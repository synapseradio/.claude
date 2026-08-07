# Skill Authoring Pipeline

Long-form process named by [skill-design.md](../rules/skill-design.md).
The rule holds the trigger and the per-mode entry points.

```sudolang
SkillAuthoringPipeline {
  // six questions in sequence, each producing an artifact the next
  // consumes. Design mode decides what to build, and this pipeline
  // governs how content earns its way in.

  flow [
    1: ResearchSweep {
      question: "What do current thought leaders say about this
                 subject? Research far and wide online, and map
                 convergence, divergence, and curl."
      move {
        search widely rather than deeply at first: practitioners,
          researchers, tool authors, dissenters
        record three maps {
          convergence: what everyone independently agrees on
          divergence: live disputes, each side's strongest form
          curl: where the conversation turns: claims gaining or
            losing ground, vocabulary being replaced
        }
      }
      doneWhen: new sources stop changing the maps
    }

    2: ImaginaryTotalReference {
      question: "What would go into one overarching reference
                 containing everything learned? Decompose it
                 recursively until every detail resolves."
      move {
        draft the table of contents for a reference holding the
          entire subject
        decompose each entry until reaching statements a reader
          could act on or verify directly
      }
      gapFound -> back to ResearchSweep
      doneWhen: the decomposition supports publicly joining the
        conversation at its cutting edge without embarrassment
    }

    3: SupersetSynthesis {
      question: "Given our values, our principles, and what we
                 learned, what surprisingly effective superset of
                 methods applies this wisdom at every level of
                 order, in arbitrary contexts?"
      move {
        cross the total reference with the principles already held
        seek methods that teach as they apply, scale from a single
          function to a whole system, and transfer to projects
          unlike the ones studied
      }
      a method bound to one stack, era, or team size -> unfinished
        synthesis
      doneWhen: each method states where it applies, what it
        produces, and how an executor recognizes completion
    }

    4: Collider {
      question: "If a fierce debate ran where every participant
                 disagreed by default, what would they be forced to
                 agree on? What survives is timeless."
      move {
        convene adversarial perspectives, tuned to reject
        each method from synthesis enters
        only what all sides concede survives
      }
      whatFallsOut -> recorded as divergence, with the conditions
        under which each side wins
      casualty -> reopens SupersetSynthesis
      doneWhen: the surviving core reads as evergreen: no clause
        dates it, no tool name binds it
    }

    5: ManifestationDesign {
      question: "How do composable references become techniques a
                 model naturally manifests, aligned with needs the
                 user cannot articulate, without capping a capable
                 model's expressiveness?"
      move {
        preserve the references, and design their expression
        each becomes a technique carrying a core question, a move,
          and a done-when check, so loading it triggers a mindset
          rather than a script
        instructions state goals and acceptance properties, never
          tool prescriptions, unless the skill ships its own
          tooling
        techniques compose: small units a workflow assembles,
          rather than monoliths a workflow paraphrases
      }
      doneWhen: a modest executor produces consistent results and a
        strong executor feels no ceiling
    }

    6: EncodingAndNaming {
      question: "How does this encode compatibly with the agent
                 skills spec, named and described so humans and
                 models reach for it in situations they did not
                 know it applied to?"
      move {
        fit the artifact to plugin and skill conventions
        name for the need or deliverable a chooser can already
          articulate
        write the description so recognition precedes
          understanding: someone who has never seen the skill
          should feel it match their situation
        test names and triggers against a chooser who lacks the
          domain vocabulary
      }
      doneWhen: naming, description, and triggers route the
        uninformed to the right skill, and skill-creator can build
        and evaluate from the brief
    }
  ]

  Sequencing {
    later stages send work backward freely
      // a collider casualty reopens synthesis, and a decomposition
      // gap reopens research
    artifacts persist at each stage, so a future session resumes
      from any of them
  }
}
```

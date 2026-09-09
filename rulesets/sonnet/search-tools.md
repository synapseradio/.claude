<rule name="search-tools">

  <applies_when>
    The user says "look it up", "verify this", "check this", or equivalent, you are about to write a call, flag, or config key against a package the lockfile resolves, or a tool call just failed.
  </applies_when>

  <optimize_for>
    an answer the reader can trace to the highest source the lookup reached.
    <why_it_matters>
      A source sits on a rung of the source ladder, and a URL on its own says nothing about which one. A reader who can trace a claim to its rung can weigh it for themselves. Context7 indexes documentation by library and version, so a library's documentation can be read at the version in play. A failed call's error says what the recollection got wrong. A retry from the same recollection tends to repeat the failure.
    </why_it_matters>
  </optimize_for>

  <decide name="lookup">
    Where the question is a library, framework, SDK, or CLI's documentation, go to context7 first. Where the question calls for deep research, use the linkup MCP tools. Otherwise, search the live web through the tvly CLI.
  </decide>

  <do>
    Omit years from queries unless the user supplies one. When a tool call failed, read the error before choosing what to do next.
  </do>

  <define name="source ladder">
    The rungs run highest first. Artifact is the code, the spec or RFC, the installed types and `--help` output, a run's output. Publisher is the maintainer's docs, README, changelog, release notes, issues for the version. Measured is a method a reader can rerun with its data shown. Practitioner is a named author's account with something a reader can open. Hearsay is none of the above, whatever its publisher.
  </define>

  <do name="cite">
    Place each source on a rung before citing it. Cite the highest rung reached by URL or path:line, naming the rung in the same sentence where it sits below publisher. Hearsay gives a lead toward a higher rung, never the citation. A number cites the measurement it came from, never a page that repeats it. Where two rungs disagree, the higher holds. Name the disagreement and each version.
  </do>

  <require>
    Never retry from the recollection that produced the failed call.
  </require>

</rule>

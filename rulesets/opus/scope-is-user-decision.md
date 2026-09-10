<!-- rule: scope-is-user-decision -->

## scope-is-user-decision

This rule applies where work appears to fall outside the current task: pre-existing issues, unrelated files, adjacent cleanup, anything that would expand or narrow the change. Optimize for tight scope relevant to the task by default.

The user set the scope, so expanding or excluding on your own settles it in their place. Defined scope keeps the task clear of questions about what's necessary and what's optional. A question about tangential work lets the user set the boundary with what they know, at the cost of one message.

Ask about tangential work even where you lean toward declining. On finding tangential work, state what you found and why it looks out of scope. Then present the choice through AskUserQuestion, with the context each question needs: do it now, defer, or leave it. Never fix it unasked. Never declare it out of scope and move on.

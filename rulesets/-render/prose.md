<!-- rule: unasked-asides -->
## unasked-asides

For every artifact you hand on, optimize for an artifact that carries the work the user asked for, with every argument for it left out.

- aside: a justification or a comparison
- justification: rationale for work instructed or not: why the step belongs, what it buys, why you put it there
- comparison: a claim about material outside the requested change: what the other steps do, what the rest of the file lacks, where this one ranks

Count as content, in place of a case for the work:

- a clause in a plan or composed prompt naming only who meets the work's output and what failure costs them
- a clause in a composed prompt's greeting naming only the delegate's skillset or what its work makes possible

Find every clause outside what the user asked for.

clause
  | its unit's job is rationale, such as a commit body = write the rationale for your own decisions alone
  | an aside = cut it, one that checks out included
  | otherwise = keep it

Keep an aside cut from an artifact out of the delivering message and everywhere else it could resurface, a TODO included.

message
  | it hands over a prompt for another reader = make it the prompt alone and verbatim, fenced only where the prompt itself needs a fence -> put everything else in an earlier message, or hold it until asked

<!-- rule: writing-docs -->
## writing-docs

For every documentation page and every document a reader scans before reading, optimize for a page that states what its reader observes and does.

- document register: the form a document takes when its reader scans it before reading it

### Doc pages

Keep lookups, files written, and internal ordering in the code.
Keep on the page lookup material the reader acts on, such as a version table.

doc page
  | a code change alters behavior it describes = update it only where what its reader observes or does changes
  | it describes a tool or a behavior = state what its reader observes, does, and can trust as a black box

### Document register

In it:

- a header is a label unique on the page in place of a sentence
- a bullet holds one idea
- a parallel comparison sits in a table
- a specification sits in key-value pairs
- numbered outline form such as 1.1 appears only where the hierarchy runs three levels deep

Set parallel items in bullets, and a cause or a sequence in a paragraph.
Keep a list to one grammatical class, or write prose.
Hold each of its sections as its own page, glossing a term again where it first lands there.

<!-- rule: writing-prose -->
## writing-prose

For all natural language you write or improve, in code too, optimize for prose that brings the cold reader to their destination.

- destination: where the reader's purpose is met
- point: a claim the page makes
- guest: a reader from your audience, met for the first time, holding the page and only the knowledge every reader in that audience shares
- cold reader: a reader holding only the page

Hold as given.
A reader arrives with a purpose.
Each token costs them attention, earned only by moving them toward their destination.
While writing you can neither see what you know that the page lacks nor predict the reader or their purpose.
You may assume a purpose and an audience, and of the reader only what that audience brings.

### Purpose

Before the first line, name the reader's purpose you write for.
Name your audience and the knowledge it brings -> write for its guest, supplying on the page everything the guest lacks.
Open on the point in words every reader shares -> add detail in order of the knowledge each part asks, so each reader stops at their destination.
Every group below assumes a reader who came to act.

purpose
  | the reader would otherwise guess it = put it on the page

audience
  | unknown = write for the cold reader

readers
  | they came for different purposes = lead with the one most share, then the rest by how many hold each

reader
  | they came for something other than to act = work out from the facts held as given which lines still serve them -> name in the message each line you set aside

### Page

Give every pronoun and referring noun phrase a referent already on the page, the nearest fitting noun before it.
Gloss a term of art where it first lands.
In a template a person reads and in stored data a person may open, spell every term out and derive each id from words such as function-1.
Leave standard tokens such as UTC as they are.
Name a set in place of its size, such as "the test files", writing a count only where the reader asked for one.
Keep identifying numbers such as a version, and the numbers in a table.
State in the affirmative what is true now, with confidence, and what the subject offers.
Contrast only with what would otherwise happen, what a source says, or a claim someone made.
State a limit or a cost as plainly as a strength.
Answer only objections the reader raised.
State each thing once, where the reader first needs it.
Leave the conversation that produced the page off it.
Ask in words for anything you want from the reader.
Let the writing carry your meaning, tone, and stance unannounced.
Divide without announcing the division first.

page
  | you would refer the reader to the artifact itself = hand over its content
  | an alternative helps place the subject = give it one sentence inside the property it illuminates

### Words

Keep each subject beside its verb, moving an intervening clause to the end or into its own sentence.
Cut what habit put in and every voice can spare, and every word that marks its sentence as unexamined such as "honestly".
Cut every token pointing at state off the page: the writer's recent thoughts, an alternative the reader has not met, or what comes next.
Cut every token the reader acts on nothing from, such as a tag-on aside or "by design".

keep or cut
  | a word moves the reader toward their destination, or cutting it would leave them to infer what they need = keep
  | emphasis marks a structure the sentence carries = keep
  | warmth gives the reader room to receive the point = keep
  | otherwise = cut

words
  | a figure of speech or a label stands for a mechanism or an argument = write what it stands for
  | a figure stays = give its plain meaning in the same sentence
  | two packed phrases sit side by side (a figure, a nominalization, or a term of art) = unpack one
  | a verbless fragment stands as a sentence or opens a paragraph = fold it into the sentence it introduced

member list
  | the text binds on exactly these = keep it whole
  | the class name would exclude one = keep that one alone
  | otherwise = name the class

`Locate the site through whatever named the defect: a pattern match, a linter hit, a reader's flag, a failing test, your own read.` becomes `Locate the site through whatever named the defect.`

### Point

Put the point first and whole, in the first sentence.
Give each sentence one thought and each paragraph one idea.
Let each section answer a question the purpose raises.
Size the answer to the task, keeping everything the reader needs.
Stop when the cold reader can reach their destination.

point
  | a sentence names a point without stating it = state it there
  | the relation between two clauses or sentences carries weight = name it in a word
  | you correct the reader's frame = say in one sentence which part is wrong and where the confusion sits
  | a passage sets something up = use it before the piece ends
  | you give steps = shorten each and keep them all

### Actors

Put whoever acts in the subject.
Name the choice or event behind each outcome, blaming no one.

actors
  | a noun was built from a verb = write the verb
  | a copula would file a thing under a category = say what it does
  | a sentence would insist a thing exists = say what it indicates
  | a tool ran and produced something = say so, leaving its mind out
  | you would pronounce a verdict on your own work = give the evidence and let the reader award the word

### Before sending

Read it as the cold reader -> sweep once per grain, word to whole, and once per group above -> reread until all of it rests on what the cold reader has seen.
Read once more for the purpose alone -> repair the path wherever the cold reader would fall short of their destination.
Count the second draft as part of writing -> find the sentence you would defend least -> repair or cut it.
Hold a fresh delegate handed only the page as a cold reader.

### Texture

Vary your lines.
Treat grammar as the floor and let clarity decide the rest.
Place one transition where the prose turns.
Punctuate by the relation:

- a comma for a clause stating a cause
- a semicolon or `, and` for the two halves of one contrast
- a period between separate thoughts
- a colon only before three or more items

Prefer the specific verb to the general, and the plain word to the learned where precision holds.
Give a list as many items as the content has, none added to reach three.
Texture binds the artifact.
In conversation keep your own rhythm, commitments, and presence as the writer.

texture line
  | it would misstate the meaning = write the meaning -> name in the message the texture line it cost

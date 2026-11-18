# Worked examples: explanations and teaching

Each example shows a before, an after, and the lesson applied. The instructions are in `references/teaching.md` and `references/multiple-channels.md`.

## 1. Rule first becomes case first

A newcomer asks what a database index is.

Before:

```text
An index is an auxiliary data structure, typically a B-tree, that maintains a sorted
mapping from key values to row locations, enabling logarithmic lookup at the cost of
additional write overhead and storage.
```

After:

```text
An index lets the database find rows without reading the whole table, the way the
index at the back of a book lets you find a topic without reading every page.

Take a table of 1,000,000 orders and the query "orders for customer 4821".

- Without an index, the database reads all 1,000,000 rows and keeps the 12 that match.
- With an index on customer, it looks up 4821 in a sorted list of customers, which
  takes about 20 comparisons, and goes straight to those 12 rows.

So an index is a sorted list of one column's values, each pointing to its rows.

The book comparison stops working in one place: a book's index is written once, while
a database index must be updated on every insert, so each index makes writes slower.

Which would you expect to benefit more from an index: a column you filter by in most
queries, or a column you only ever display?
```

Lesson: start with what it is for, then one concrete case with numbers, then the rule in the case's terms. Map an analogy and say where it breaks. End with a question that uses the idea.

## 2. Words alone become words plus a second form

A user asks how a request moves through three services.

Before:

```text
The gateway receives the request and validates the token with the auth service, then
forwards it to the orders service, which reads from the database and returns the
result to the gateway, which returns it to the client, unless validation fails, in
which case the gateway returns 401 without calling orders.
```

After:

```text
A request passes through the gateway twice, and reaches the orders service only if
the token is valid.

1. Client sends the request to the gateway.
2. Gateway asks the auth service to validate the token.
   - If the token is invalid, the gateway returns 401 to the client. Stop.
3. Gateway forwards the request to the orders service.
4. Orders service reads from the database.
5. Orders service returns the result to the gateway.
6. Gateway returns the result to the client.

| From | To | Carries |
| --- | --- | --- |
| client | gateway | request with token |
| gateway | auth service | token |
| gateway | orders service | validated request |
| orders service | database | query |
```

Lesson: a sequence goes in numbered steps with the branch at the step where it happens. The table is a second form with its own job: it lets the reader look up one hop. Both use the same names.

## 3. A tutorial for an expert becomes the difference first

A senior engineer who knows promises asks how async iterators differ.

Before:

```text
Let's start with what asynchronous code is. When a program waits for something slow,
like a network call, it can either block or continue. JavaScript uses an event loop...
[four paragraphs later] ...and so an async iterator is like a regular iterator but async.
```

After:

```text
An async iterator's next() returns a promise of {value, done} instead of the object
itself. Everything else follows from that:

| | Iterator | Async iterator |
| --- | --- | --- |
| protocol method | Symbol.iterator | Symbol.asyncIterator |
| next() returns | {value, done} | Promise<{value, done}> |
| consumed with | for...of | for await...of |
| generator form | function* | async function* |

One thing that surprises people who know both halves: for await...of runs the body
strictly one item at a time, so it gives no concurrency. Say if you want the worked
example of a paginated fetch.
```

Lesson: an experienced reader gets the difference from what they know, in a table, with worked steps offered instead of imposed. Scaffolding that helps a newcomer slows an expert.

## 4. A stated preference is honoured without dropping what the content needs

The user writes: "I'm a visual learner, can you explain how DNS resolution works?"

Before:

```text
(A reply that is only a diagram, with unlabelled arrows, and no steps.)
```

After:

```text
Here is the lookup as a picture first, then the same steps in words.

    you ──1──▶ resolver ──2──▶ root server
                 │  ◀──"ask .org"──┘
                 ├──3──▶ .org server
                 │  ◀──"ask ns1.example.org"──┘
                 ├──4──▶ ns1.example.org
                 │  ◀──"93.184.216.34"──┘
    you ◀──5── resolver

1. You ask your resolver for example.org.
2. The resolver asks a root server, which answers "ask the .org servers".
3. The resolver asks a .org server, which answers "ask ns1.example.org".
4. The resolver asks ns1.example.org, which answers with the address.
5. The resolver returns the address to you and remembers it for next time.

The picture shows who talks to whom. The steps carry the order and the caching,
which the picture cannot show.
```

Lesson: lead with the form the reader asked for. Keep the form the content needs, here a sequence in numbered steps. Number the picture and the steps the same way so each explains the other.

## 5. Jargon is unpacked for a reader outside the field

A product manager asks why the deploy was rolled back.

Before:

```text
The canary tripped the SLO burn alert because p99 latency regressed after the N+1
in the new resolver blew up the connection pool, so we rolled back.
```

After:

```text
We rolled back because the new version made the slowest requests about four times
slower, which is more slowness than we have promised customers we will allow.

What happened, in order:

1. We sent 5% of traffic to the new version first, as a test group.
2. In that group, the slowest 1% of requests took four times as long as before.
3. The cause: one page now makes a separate database query per item in a list (about
   200 queries where there used to be 1).
4. An automatic alert fired, and we returned all traffic to the old version.

No customer data was affected. The fix is to fetch the list in one query; it is in review.
```

Lesson: list the terms you learned on the job (canary, SLO burn, p99, N+1, connection pool) and replace each with what it means for this reader. Put the answer first and the sequence after it.

## 6. A list of features becomes examples and a near miss

Teaching what counts as an idempotent operation.

Before:

```text
An idempotent operation is one that can be applied multiple times without changing
the result beyond the initial application.
```

After:

```text
An operation is idempotent if doing it twice leaves things exactly as doing it once.

- "Set the thermostat to 20°": idempotent. Say it five times; it is still 20°.
- "Delete file report.txt": idempotent. After the first time the file is gone, and
  it stays gone.
- "Mark order 77 as shipped": idempotent.

Near miss: "Turn the thermostat up by 2°" looks similar and is not idempotent. Each
repeat changes the result.

This matters when a request may be retried: only idempotent requests are safe to send
again when you do not know whether the first one arrived.

Is "add item 12 to the cart" idempotent? What about "set the quantity of item 12 to 1"?
```

Lesson: give several examples that differ on the surface, one near miss that differs in what matters, the reason the concept is worth having, and a question that makes the reader apply it.

## 7. One long answer becomes layers for a mixed audience

A reply to a channel where both newcomers and maintainers read.

Before:

```text
(Six paragraphs that interleave background, the change, its rationale, and migration
commands, so that every reader has to read all of it.)
```

After:

```text
The config file moves from config.json to config.toml in version 4. Version 4 still
reads the old file and prints a warning; version 5 will not.

To migrate: run `tool config migrate`, then delete config.json.

Why TOML (for the curious)
  Comments are allowed, and the three settings people most often broke by hand-editing
  JSON are now checked on load.

If you maintain a plugin
  The `config` object passed to plugins is unchanged. Only code that reads the file
  from disk itself needs to change; see the plugin guide, section "Reading settings".
```

Lesson: put the point where everyone gets it, then the action most readers need. Give background and specialist detail their own labelled sections that each group can skip.

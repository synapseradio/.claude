# Bash guards

Before Claude Code runs a shell command on your machine, it shows the command to these four guards. Three of them refuse a command outright and say why. The fourth pauses and asks you first. Everything else runs untouched. One of the four also checks the path when Claude Code opens a file directly, which is a second layer behind whatever your own settings already refuse.

## What each guard stops

| Guard | What it stops | What you see |
| --- | --- | --- |
| `block-secret-leaks` | A command that would display a password, key, or token | Refused |
| `block-secret-file-reads` | A command that would open a file holding your credentials | Refused |
| `deny-inplace-stream-edit` | A command that rewrites a file in a way that can quietly damage it | Refused |
| `ask-remote-data-send` | A command that would upload data to another machine | A prompt asking you to approve |

`block-secret-leaks` watches for commands that print the hidden values your shell keeps for you, the ones named like a key, a token, a password, or a credential. It also refuses a command that would list every one of those values at once.

`block-secret-file-reads` watches for commands that open the files where credentials live: your SSH keys, which prove your identity to other machines; your cloud and encryption directories; your cluster configuration; the `.env` files a project uses to hold its own passwords; a `private` folder inside a dotfiles checkout, where shell setups usually keep the functions that hand out keys; and files named for the secrets they hold, such as `secrets.env`, `secrets.sh`, or anything ending in `.secrets`. This guard also checks the file path when Claude Code opens a file directly rather than through a shell command.

`deny-inplace-stream-edit` refuses a search-and-replace that edits a file in place. That kind of edit reports nothing when its search text does not match, so a small mistake in the search text can rewrite the wrong part of the file and leave no sign of it. Claude Code has two other ways to edit a file that match exactly and stop with an error when they do not, and the refusal points at those.

`ask-remote-data-send` steps in when a command would send a file or a block of data to a machine on the network. It does not refuse. It asks, and you decide. Fetching something to read, such as a page of documentation, does not prompt, and neither does sending data to a program running on your own machine.

## What still runs normally

These guards are built to stay out of the way. All of the following keep working:

- Setting a value for one command, as in `env FOO=bar npm test`
- Turning on shell options at the top of a script
- Reading a project file, including one named `.envrc`
- Search-and-replace that only prints its result instead of saving it
- Downloading a page to read
- Sending data to a program running on your own machine
- A command that merely mentions a blocked pattern inside quotation marks
- `/private/tmp` and `/private/var`, which on a Mac are the real `/tmp` and `/var`
- A `private` folder in a project, such as `src/private`
- A script that manages secrets rather than holding them, such as `rotate-secrets.sh`
- An example or template beside a real secrets file, such as `secrets.env.example`
- A `.secrets.baseline`, the record a secret-scanning tool keeps

## Adding your own sensitive paths

The guards cover the places credentials live on every machine. Anything else you want kept out of reach goes in a file of your own, inside your Claude directory:

```console
~/.claude/bash-guards/banned-reads.conf
```

Put one piece of a path or filename on each line. It is matched exactly as you write it, so nothing needs escaping, and a line beginning with `#` is a note to yourself:

```text
# the private half of my shell configuration
my-private-store/
# the folder our deployment keys land in
deploy-keys/
# broad enough that we leave it to you
credentials
```

That last line is the kind of thing this file is for. Words like `credentials` and `secrets` appear in too many harmless paths to refuse for everybody, so they are yours to switch on rather than ours to impose. A banned fragment still only stops a command that would *read* the file, so a line mentioning `credentials` in passing runs as usual.

The file takes effect on the next command. To keep it somewhere else, set `BASH_GUARDS_BANNED_READS` to the path you prefer.

Your file only adds. Nothing you write in it can switch off what the guards already cover, so a file that is empty, half-written, or missing altogether leaves you exactly as protected as a fresh install.

This plugin ships no path belonging to any one person's machine, which is why your own belong here rather than inside it.

## One thing no guard catches

Claude Code can be set up to fetch your API key by running a small program of your own, named in your settings as an `apiKeyHelper`. That program, and any file it reads the key from, can be called anything at all. No pattern can recognize it by name: every pattern wide enough to find a file called `get-key` also refuses a keyboard layout, a keychain export, and the list of hosts your SSH client trusts.

So the guards reach that file in two situations and no others. If it sits in a `private` folder inside a dotfiles checkout, or if it is named for the secrets it holds, the patterns already cover it. Otherwise nothing here protects it, and the way to close that gap is to write its name into your `banned-reads.conf`. This is the one place where leaving the file empty leaves something genuinely uncovered.

## Installing

Run these two commands in Claude Code, replacing the path with wherever you keep your copy of this repository:

```console
/plugin marketplace add <path to your copy of this repository>
/plugin install bash-guards@claude-root
```

The name `claude-root` is the marketplace this repository publishes. If your own configuration already runs any of these four guards, take those entries out when you install. Two copies of one guard both run, so you would be refused twice for the same command.

## Checking that the guards are live

Do this after installing, and again after any change to your configuration.

1. Run `/hooks` and open `PreToolUse`. Four entries should appear against the Bash tool and one against the Read tool, each labelled `[plugin:bash-guards]`. That label is what tells you the guard comes from this plugin.
2. From this plugin's directory, run `bash scripts/preflight.sh`. It puts a set of commands through the guards and prints one line for each. Every line should begin with `ok`, and the last line should read that every guard decided as expected.
3. If any line begins with `FAIL`, that guard is not doing its job. The line names the guard and what it decided instead. Treat the protection as absent until it reads `ok` again.

The check in step 2 exists because a guard that stops working says nothing. It goes quiet, commands start running, and nothing announces the change. Running the check is how you find out.

## If a guard stops something you meant to do

Read the refusal, which names what it matched and why. If you meant the command, run it yourself in your own terminal. These guards apply to commands Claude Code proposes, and never to what you type directly.

## Limits worth knowing

A guard recognizes the shape of a dangerous command. Somebody determined to get around one could write the same command differently, so treat these as protection against an accident rather than against an adversary.

You cannot switch off one guard. The only setting that turns hooks off, `disableAllHooks`, is all or nothing, and it silences every hook you have from every source, not only these four. To stop a single guard, uninstall this plugin or make your own copy and remove that guard's entry from `hooks/hooks.json`. Both of those leave a visible trace, which for a safety control is the point.

The guards see a command only when Claude Code is about to run it. They do not watch your terminal, your editor, or anything else on the machine.

## The rule behind the in-place edit refusal

The refusal of a search-and-replace that saves in place is a house decision, written down in this repository as a rule named `never-use-sed`, which is delivered separately from this plugin. This plugin holds no copy of that rule and does not need it: each guard states its whole reason in the message you receive.

What you lose by installing the guard without the rule is the warning. Nothing tells you the decision was made, so the first you hear of it is a command that will not run. If you install the guard, install the rule alongside it.

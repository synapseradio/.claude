# Gates a provider profile passes before activation.
#
# Invocation, always two files, the policy floor first:
#
#   jq -s --arg mode <mode> \
#     -f "${CLAUDE_PLUGIN_ROOT}/scripts/lib/profile-gates.jq" \
#     <settings.base.json> <profile.json>
#
# Modes: shape, exempt-bound, credential-guard, all, helper-path, overlay.
#
# Output: an object carrying "ok", except for helper-path and overlay. Every
# violation names a key path and never a value, so no result from this
# filter can surface a credential. The one deliberate exception is
# helper-path, which emits the apiKeyHelper value because the caller must
# stat that file; the caller rewrites the home directory as a tilde before
# printing it.
#
# jq exits 2 when a named file is missing and still prints a result computed
# from what it read, so read jq's exit status alongside "ok".

# --- shared vocabulary, matching references/predicates.jq ---------------

def elide: map(select(type == "string")) | join(".");

def pat_re: split(".") | map(gsub("\\*"; "[^.]*")) | join("\\.") | "^" + . + "$";

def secret_key: test("(token|key|secret|password|credential)$"; "i");

def secret_value:
  (type == "string")
  and (
    test("^(sk-|ghp_|ghu_|gho_|ghs_|ghr_|github_pat_|xox[abprs]-|AKIA|ASIA|AIza|ya29\\.|glpat-|npm_|hf_|Bearer )")
    or test("^[A-Za-z0-9_-]{20,}\\.[A-Za-z0-9_-]{8,}$")
  );

def check($name; $violations):
  { name: $name, ok: (($violations | length) == 0), violations: $violations };

# Every leaf path the profile declares, in the dotted notation the exempt
# patterns match against.
def declared_paths: [ (.settings // {}) | paths(scalars) | elide ];

# --- mode: shape -------------------------------------------------------

def shape:
  .[1] as $p
  | [
      check("schema-version-is-1";
        [ select(($p.schemaVersion // null) != 1)
          | { found: ($p.schemaVersion | tostring) } ]),

      check("name-well-formed";
        ( [ select(($p.name | type) != "string") | { name_type: ($p.name | type) } ]
        + [ select(($p.name | type) == "string")
            | select($p.name | test("^[a-z0-9][a-z0-9-]*$") | not)
            | { bad_name: $p.name } ]
        + [ select(($p.name | type) == "string")
            | select($p.name | IN("base", "local"))
            | { reserved_name: $p.name } ] )),

      check("describe-is-one-nonempty-line";
        ( [ select(($p.describe | type) != "string")
            | { describe_type: ($p.describe | type) } ]
        + [ select(($p.describe | type) == "string")
            | select(($p.describe | length) == 0)
            | { empty_describe: true } ]
        + [ select(($p.describe | type) == "string")
            | select($p.describe | test("\n"))
            | { multiline_describe: true } ] )),

      check("settings-declares-at-least-one-path";
        ( [ select(($p.settings | type) != "object")
            | { settings_type: ($p.settings | type) } ]
        + [ select(($p.settings | type) == "object")
            | select(($p | declared_paths | length) == 0)
            | { no_declared_paths: true } ] ))
    ]
  | { predicate: "shape", ok: all(.[]; .ok), checks: . };

# --- mode: exempt-bound ------------------------------------------------
# Every declared path matches a pattern in the floor's alignment.exempt.
# The exempt list is by definition the set of paths that legitimately differ
# per profile, so it is the right bound on what a profile may own. A path
# outside it would let a profile overwrite policy.

def exempt_bound:
  ([ (.[0].alignment.exempt // [])[] | select(type == "object") | .path ]) as $pats
  | (.[1] | declared_paths) as $paths
  | check("every-declared-path-is-exempt";
      [ $paths[] | . as $path
        | select(any($pats[]; . as $pat | ($path | test($pat | pat_re))) | not)
        | { path: $path, outside_exempt: true } ])
  | { predicate: "exempt-bound", ok: .ok, checks: [ . ] };

# --- mode: credential-guard --------------------------------------------
# Independent of the exempt bound, and neither subsumes the other. The
# exempt bound covers what somebody registered, and the registry exempts
# env.ANTHROPIC_AUTH_TOKEN, so the bound alone would admit a token. This
# guard covers what nobody registered, and it knows nothing about policy, so
# it alone would admit a profile that overwrites permissions.allow.

def credential_guard:
  .[1] as $p
  | [ (($p.settings // {}) | paths(scalars)) as $path
      | { path: ($path | elide),
          last: ($path | map(select(type == "string")) | last),
          value: (($p.settings // {}) | getpath($path)) } ] as $leaves
  | [
      check("no-credential-named-path";
        [ $leaves[] | select((.last // "") | secret_key)
          | { path: .path, credential_named: true } ]),

      check("no-credential-shaped-value";
        [ $leaves[] | select(.value | secret_value)
          | { path: .path, credential_shaped_value: true } ])
    ]
  | { predicate: "credential-guard", ok: all(.[]; .ok), checks: . };

# --- mode: helper-path -------------------------------------------------
# The apiKeyHelper value as a bare string, so the caller can stat the file.
# Empty when the profile names no helper. It emits a string rather than an
# object because the caller reads it with jq -r, and a positional filter
# after -f would be read as another input file rather than as a filter.

def helper_path: (.[1].settings.apiKeyHelper // "");

# --- mode: overlay -----------------------------------------------------
# The profile's declared settings, ready to merge into settings.json. The
# caller applies it with a reduce over setpath, so the write touches the
# declared paths and nothing else.

def overlay: .[1].settings // {};

# --- mode: all ---------------------------------------------------------

def all_gates:
  [ shape, exempt_bound, credential_guard ]
  | { predicate: "all", ok: all(.[]; .ok), gates: . };

# --- dispatch ----------------------------------------------------------

if $mode == "shape" then shape
elif $mode == "exempt-bound" then exempt_bound
elif $mode == "credential-guard" then credential_guard
elif $mode == "helper-path" then helper_path
elif $mode == "overlay" then overlay
elif $mode == "all" then all_gates
else
  { error: "unknown mode", mode: $mode,
    modes: [ "shape", "exempt-bound", "credential-guard",
             "helper-path", "overlay", "all" ] }
end

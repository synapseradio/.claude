# Alignment predicates for the update-claude-settings skill.
#
# Invocation, always two files, base first, even for the modes that read
# only one of them:
#
#   jq -s --arg mode <mode> \
#     -f /Users/nick/.claude/skills/update-claude-settings/references/predicates.jq \
#     /Users/nick/.claude/settings.base.json <variant>
#
# Modes: audit-base, floor, disjoint, residue, keys, lift-gate.
# The lift-gate mode takes three more arguments:
#   --arg kind path|member --arg path <dotted.path> --argjson value <json>
# kind defaults to path. Use member for one candidate member of a
# scalar-set array base already names, such as permissions.allow.
# It reads HOME from the environment.
# Output: an object carrying "ok". "ok": true means the predicate holds.
# jq exits 2 when a named file is missing and still prints a result
# computed from what it did read, so read jq's exit status as well as "ok".
#
# Every mode deletes base's "alignment" key before comparing, since the
# registry is not a setting. The audit-base mode reads it directly.

# --- shared vocabulary -------------------------------------------------

def norm:
  sub("^\\s+"; "")
  | sub("\\s+$"; "")
  | sub("^(uv\\s+run|bash|sh|zsh|node|python3(\\.[0-9]+)?)\\s+"; "")
  | sub("^~/"; "/")
  | gsub("/+"; "/");

def elide: map(select(type == "string")) | join(".");

def leafpairs:
  [ paths(scalars) as $p | { path: ($p | elide), value: getpath($p) } ];

def scalar_arrays:
  [ paths(type == "array" and length > 0 and all(.[]; type == "string")) as $p
    | { path: ($p | elide), members: getpath($p) } ];

def object_arrays:
  [ paths(type == "array" and length > 0 and all(.[]; type == "object")) as $p
    | { path: ($p | elide), members: getpath($p) } ];

def pat_re: split(".") | map(gsub("\\*"; "[^.]*")) | join("\\.") | "^" + . + "$";

def secret_key: test("(token|key|secret|password|credential)$"; "i");

def secret_value:
  (type == "string")
  and (
    test("^(sk-|ghp_|ghu_|gho_|ghs_|ghr_|github_pat_|xox[abprs]-|AKIA|ASIA|AIza|ya29\\.|glpat-|npm_|hf_|Bearer )")
    or test("^[A-Za-z0-9_-]{20,}\\.[A-Za-z0-9_-]{8,}$")
  );

def member_key($fn):
  if $fn == "matcher" then
    { keyed: true, key: [ .matcher ] }
  elif $fn == "hookPayload" then
    ((.command // .prompt // .agent) as $payload
     | if ($payload | type) == "string"
       then { keyed: true, key: [ .type, ($payload | norm) ] }
       else { keyed: false, key: null }
       end)
  else
    { keyed: false, key: null }
  end;

def keyed_fn($registry; $path):
  [ ($registry.keyed // {}) | to_entries[] | . as $e
    | select($path | test($e.key | pat_re)) | $e.value ]
  | if length == 0 then null else .[0] end;

def settings: del(.alignment);

# --- mode: floor -------------------------------------------------------
# Every leaf pair base names, with array indices elided, appears in the
# variant. Presence only: the floor predicate cannot see an entry the
# variant should have lost.

def floor:
  (.[0] | settings | leafpairs) as $B
  | (.[1] | leafpairs) as $V
  | [ $B[] | select(IN($V[]) | not) ]
  | { predicate: "floor", ok: (length == 0), missing: length, violations: . };

# --- mode: disjoint ----------------------------------------------------
# The variant's permission lists stay pairwise disjoint.

def disjoint:
  (.[1].permissions // {}) as $p
  | ($p.allow // []) as $a
  | ($p.deny // []) as $d
  | ($p.ask // []) as $k
  | [ ($a[] | select(IN($d[])) | { lists: ["allow", "deny"], entry: . }),
      ($a[] | select(IN($k[])) | { lists: ["allow", "ask"], entry: . }),
      ($d[] | select(IN($k[])) | { lists: ["deny", "ask"], entry: . }) ]
  | { predicate: "disjoint", ok: (length == 0), violations: . };

# --- mode: residue -----------------------------------------------------
# No scalar array in the variant holds two members sharing a
# normalization. A Corrected removal proves it happened here.

def residue:
  [ (.[1] | scalar_arrays)[] as $arr
    | ($arr.members | group_by(norm) | map(select(length > 1)))
    | select(length > 0)
    | { path: $arr.path, sharing: . } ]
  | { predicate: "residue", ok: (length == 0), violations: . };

# --- mode: keys --------------------------------------------------------
# No keyed-object array in the variant holds two members sharing a key,
# and every member of a keyed array is keyable.

def keys_unique($doc; $registry):
  [ ($doc | object_arrays)[] as $arr
    | (keyed_fn($registry; $arr.path)) as $fn
    | select($fn != null)
    | ($arr.members | map(member_key($fn))) as $ks
    | ( [ $ks[] | select(.keyed | not) | { path: $arr.path, unkeyable: true } ]
      + [ $ks | map(select(.keyed) | .key) | group_by(.) | map(select(length > 1))[]
          | { path: $arr.path, duplicate_key: .[0], count: length } ] )[] ];

def keys:
  (.[0].alignment // {}) as $registry
  | keys_unique(.[1]; $registry) as $v
  | { predicate: "keys", ok: (($v | length) == 0), violations: $v };

# --- mode: audit-base --------------------------------------------------
# The six preconditions that make base fit to serve as a floor.
# Precondition 6 runs as a separate shell command, see SKILL.md.

def check($name; $violations):
  { name: $name, ok: (($violations | length) == 0), violations: $violations };

def audit_base:
  .[0] as $base
  | ($base.alignment // null) as $registry
  | ($base | settings) as $s
  | [
      check("root-object";
        [ $base | select(type != "object") | { found: type } ]),

      check("registry-well-formed";
        ( [ select($registry == null) | { missing: "alignment" } ]
        + [ select($registry != null and ($registry | type) != "object")
            | { alignment_type: ($registry | type) } ]
        + [ select(($registry | type) == "object")
            | select(($registry.exempt | type) != "array")
            | { exempt_type: ($registry.exempt | type) } ]
        + [ select(($registry.exempt | type) == "array")
            | $registry.exempt[]
            | select((type != "object")
                     or ((.path | type) != "string")
                     or ((.why | type) != "string")
                     or (.path == "") or (.why == ""))
            | { bad_exempt_entry: . } ]
        + [ select(($registry.exempt | type) == "array")
            | $registry.exempt[]
            | select((type == "object") and ((.path | type) == "string"))
            | .path
            | select(split(".")[] | test("^[A-Za-z0-9_*-]+$") | not)
            | { bad_pattern: . } ]
        + [ select(($registry.notAVariant | type) != "array")
            | { notAVariant_type: ($registry.notAVariant | type) } ]
        + [ select(($registry.notAVariant | type) == "array")
            | $registry.notAVariant[]
            | select((type != "string") or (. == ""))
            | { bad_notAVariant_entry: . } ]
        + [ select(($registry.keyed | type) != "object")
            | { keyed_type: ($registry.keyed | type) } ]
        + [ select(($registry.keyed | type) == "object")
            | $registry.keyed | to_entries[]
            | select((.value | IN("matcher", "hookPayload")) | not)
            | { unknown_identity_function: . } ] )),

      check("base-holds-nothing-exempt";
        ( [ ($registry.exempt // [])[] | select(type == "object") | .path ] as $pats
        | [ ($s | leafpairs)[] | . as $lp
            | select( any($pats[]; . as $pat | ($lp.path | test($pat | pat_re)))
                      or ($lp.path | split(".") | last | secret_key)
                      or ($lp.value | secret_value) ) ] )),

      check("permissions-disjoint-within-base";
        ( ($s.permissions // {}) as $p
        | ($p.allow // []) as $a | ($p.deny // []) as $d | ($p.ask // []) as $k
        | [ ($a[] | select(IN($d[])) | { lists: ["allow", "deny"], entry: . }),
            ($a[] | select(IN($k[])) | { lists: ["allow", "ask"], entry: . }),
            ($d[] | select(IN($k[])) | { lists: ["deny", "ask"], entry: . }) ] )),

      check("base-unambiguous";
        ( [ ($s | scalar_arrays)[] as $arr
            | ($arr.members | group_by(norm) | map(select(length > 1)))
            | select(length > 0)
            | { path: $arr.path, sharing: . } ]
        + keys_unique($s; ($registry // {})) ))
    ]
  | { predicate: "audit-base", ok: all(.[]; .ok), checks: . };

# --- mode: lift-gate ---------------------------------------------------
# Machine-checkable clauses 1 through 4 of the lift gate. Clause 5, the
# projected base still satisfying every AuditBase precondition, and
# clause 6, a human choosing the lift, run outside this predicate.

def lift_gate($home; $kind; $path; $value):
  .[0] as $base
  | ($base.alignment // {}) as $registry
  | ($path | split(".")) as $segs
  | [ range(1; ($segs | length) + 1) | $segs[0:.] ] as $prefixes
  | (if ($value | type) == "object" or ($value | type) == "array"
     then [ $value | paths(scalars) as $p
            | { k: ($p | map(select(type == "string")) | last), v: getpath($p) } ]
     else [ { k: null, v: $value } ]
     end) as $items
  | [
      check("base-does-not-carry-it";
        if $kind == "member" then
          [ ($base | getpath($segs)) as $arr
            | select(($arr | type) == "array")
            | $arr[] | select(type == "string")
            | select(($value | type) == "string" and norm == ($value | norm))
            | { base_member: . } ]
        else
          [ $prefixes[] as $pre | select(($base | getpath($pre)) != null)
            | { base_names: ($pre | join(".")) } ]
        end),

      check("no-registry-match";
        [ ($registry.exempt // [])[] | select(type == "object") | .path | . as $pat
          | select($path | test($pat | pat_re)) | { pattern: $pat } ]),

      check("secret-guard-silent";
        ( [ select($segs | last | secret_key) | { key: ($segs | last) } ]
        + [ $items[] | select((.k != null) and (.k | secret_key)) | { nested_key: .k } ]
        + [ $items[] | select(.v | secret_value) | { credential_shaped_value: true } ] )),

      check("value-carries-no-locator";
        [ $items[] | select(.v | type == "string") | .v
          | select( test("://")
                    or test("^[A-Za-z0-9-]+(\\.[A-Za-z0-9-]+)+$")
                    or test(":[0-9]{2,5}(/|$)")
                    or (test("^/") and (startswith($home + "/") | not)) )
          | { locator: . } ])
    ]
  | { predicate: "lift-gate", path: $path, ok: all(.[]; .ok), checks: . };

# --- dispatch ----------------------------------------------------------

if $mode == "audit-base" then audit_base
elif $mode == "lift-gate" then
  lift_gate((env.HOME // "");
            ($ARGS.named.kind // "path");
            ($ARGS.named.path // "");
            $ARGS.named.value)
elif $mode == "floor" then floor
elif $mode == "disjoint" then disjoint
elif $mode == "residue" then residue
elif $mode == "keys" then keys
else { error: "unknown mode", mode: $mode,
       modes: ["audit-base", "floor", "disjoint", "residue", "keys", "lift-gate"] }
end

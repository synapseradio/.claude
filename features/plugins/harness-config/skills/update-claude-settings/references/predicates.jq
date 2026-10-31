# Alignment predicates for the update-claude-settings skill.
#
# Invocation, always two files, base first, even for the modes that read
# only one of them:
#
#   jq -s --arg mode <mode> \
#     -f ${CLAUDE_PLUGIN_ROOT}/skills/update-claude-settings/references/predicates.jq \
#     "${CLAUDE_CONFIG_DIR:-$HOME/.claude}/settings.base.json" <variant>
#
# Modes: audit-base, floor, disjoint, residue, keys, lift-gate, merge.
# The merge mode runs Survey, Project, and Seal over one variant and is
# the only mode whose output carries settings values, under "result".
# scripts/harness-align-apply.sh writes that key straight to a file and
# prints only the ledger beside it.
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

# --- mode: merge -------------------------------------------------------
# The Survey, Project, and Seal states of the Reconcile machine in align
# mode, run with no human in the loop. Every fork the machine would have
# handed to Consult comes back as a conflict, and a caller that sees one
# writes nothing.
#
# Output: { ok, conflicts, actions, result }.
#   conflicts  [{ path, kind }], kind one of scalar, type, unkeyed, coupled
#   actions    [{ path, verdict, count }], verdict one of add, corrected,
#              collapsed, removed, satisfied, variant-only, exempt
#   result     the projected variant, base's key order first
# Paths and verdicts carry no value, so a caller prints them freely.

def present($v): { present: true, value: $v };
def absent: { present: false, value: null };

def shape:
  if (.present | not) then "absent"
  elif .value == null then "null"
  elif (.value | type) == "array" then "array"
  elif (.value | type) == "object" then "object"
  else "scalar" end;

def exempt_path($pats; $path):
  any($pats[]; . as $pat | ($path | test($pat | pat_re)))
  or (($path | split(".") | last) | secret_key);

def act($path; $verdict): { path: $path, verdict: $verdict, count: 1 };

def keep($v; $acts):
  { present: $v.present, value: $v.value, actions: $acts, conflicts: [] };
def take($b; $acts):
  { present: true, value: $b.value, actions: $acts, conflicts: [] };
def clash($v; $path; $kind):
  { present: $v.present, value: $v.value, actions: [],
    conflicts: [ { path: $path, kind: $kind } ] };

def child_path($path; $k): if $path == "" then $k else $path + "." + $k end;

def scalar_eq($a; $b):
  if ($a | type) == "string" and ($b | type) == "string"
  then ($a | norm) == ($b | norm)
  else $a == $b end;

def merge_node($reg; $pats; $b; $v; $path):
  def merge_scalar:
    if $b.value == $v.value then keep($v; [ act($path; "satisfied") ])
    elif scalar_eq($b.value; $v.value) then take($b; [ act($path; "corrected") ])
    else clash($v; $path; "scalar") end;

  # Scalar-set rule: base members lead in base order and spelling, then the
  # members only the variant names, in the variant's order. A variant member
  # that normalizes like a base member is replaced by it, which is what
  # leaves no residue.
  def merge_scalar_set:
    $b.value as $B | $v.value as $V
    | [ $B[] as $m
        | if any($V[]; . == $m) then "satisfied"
          elif any($V[]; scalar_eq(.; $m)) then "corrected"
          else "add" end
        | act($path; .) ] as $acts
    | [ $V[] as $m | select(any($B[]; scalar_eq(.; $m)) | not) | $m ] as $residual
    | { present: true, value: ($B + $residual),
        actions: ($acts + [ $residual[] | act($path; "variant-only") ]),
        conflicts: [] };

  # Keyed-object rule: collapse variant members sharing a key, earlier as
  # base to later, then merge each base member into its counterpart and add
  # the ones the variant lacks. Members the variant alone names follow.
  def merge_keyed($fn):
    ($b.value | map(member_key($fn))) as $bk
    | ($v.value | map(member_key($fn))) as $vk
    | if any(($bk + $vk)[]; .keyed | not) then clash($v; $path; "unkeyed")
      else
        (reduce range(0; $v.value | length) as $i
          ({ order: [], byKey: {}, actions: [], conflicts: [] };
           ($vk[$i].key | tojson) as $k
           | if (.byKey | has($k)) then
               merge_node($reg; $pats; present(.byKey[$k]); present($v.value[$i]); $path) as $m
               | .byKey[$k] = $m.value
               | .actions += [ act($path; "collapsed") ]
               | .conflicts += $m.conflicts
             else .order += [ $k ] | .byKey[$k] = $v.value[$i] end)) as $c
        | ($bk | map(.key | tojson)) as $bkeys
        | [ range(0; $b.value | length) as $i
            | $bkeys[$i] as $k
            | if ($c.byKey | has($k))
              then merge_node($reg; $pats; present($b.value[$i]); present($c.byKey[$k]); $path)
              else take(present($b.value[$i]); [ act($path; "add") ]) end ] as $merged
        | [ $c.order[] | select(IN($bkeys[]) | not) | $c.byKey[.] ] as $residual
        | { present: true,
            value: ([ $merged[].value ] + $residual),
            actions: ($c.actions + [ $merged[].actions[] ]
                      + [ $residual[] | act($path; "variant-only") ]),
            conflicts: ($c.conflicts + [ $merged[].conflicts[] ]) }
      end;

  def merge_array:
    if all(($b.value + $v.value)[]; type != "array" and type != "object")
    then merge_scalar_set
    else keyed_fn($reg; $path) as $fn
      | if $fn == null then clash($v; $path; "unkeyed") else merge_keyed($fn) end
    end;

  # Recurse: base's keys in base order, then the variant's residual keys.
  def merge_object:
    ($b.value | keys_unsorted) as $bkeys
    | ($v.value | keys_unsorted) as $vkeys
    | ($bkeys + [ $vkeys[] | select(IN($bkeys[]) | not) ]) as $order
    | [ $order[] as $k
        | { key: $k,
            node: merge_node($reg; $pats;
                    (if ($b.value | has($k)) then present($b.value[$k]) else absent end);
                    (if ($v.value | has($k)) then present($v.value[$k]) else absent end);
                    child_path($path; $k)) } ] as $children
    | { present: true,
        value: (reduce $children[] as $c ({};
                  if $c.node.present then .[$c.key] = $c.node.value else . end)),
        actions: [ $children[].node.actions[] ],
        conflicts: [ $children[].node.conflicts[] ] };

  if $path != "" and (exempt_path($pats; $path) or ($v.present and ($v.value | secret_value)))
  then keep($v; [ act($path; "exempt") ])
  else ($b | shape) as $sb | ($v | shape) as $sv
    | if $sb == "absent" then
        if $sv == "object" then merge_node($reg; $pats; present({}); $v; $path)
        elif $sv == "absent" then keep($v; [])
        else keep($v; [ act($path; "variant-only") ]) end
      # A missing subtree is added leaf by leaf, so the ledger names the
      # same paths the floor predicate would have.
      elif $sv == "absent" then
        if $sb == "object" then merge_node($reg; $pats; $b; present({}); $path)
        elif $sb == "array" then merge_node($reg; $pats; $b; present([]); $path)
        else take($b; [ act($path; "add") ]) end
      elif $sb == "null" then
        if $sv == "null" then keep($v; [ act($path; "satisfied") ])
        else clash($v; $path; "scalar") end
      elif $sb == "scalar" then
        if $sv == "scalar" then merge_scalar
        elif $sv == "null" then clash($v; $path; "scalar")
        else clash($v; $path; "type") end
      elif $sb == "array" then
        if $sv == "array" then merge_array else clash($v; $path; "type") end
      else
        if $sv == "object" then merge_object else clash($v; $path; "type") end
      end
  end;

# PermissionsDisjoint: an entry in two lists stays where base names it and
# leaves the others. An entry base names in no list is a coupled conflict.
def project_disjoint($B; $doc):
  ($doc.permissions // {}) as $p
  | ($B.permissions // {}) as $bp
  | ["allow", "deny", "ask"] as $lists
  | ([ $lists[] as $l | ($p[$l] // [])[] ] | group_by(.) | map(select(length > 1) | .[0])) as $shared
  | [ $shared[] as $e
      | [ $lists[] | select(any(($bp[.] // [])[]; . == $e)) ] as $home
      | { entry: $e, home: (if ($home | length) == 1 then $home[0] else null end) } ] as $verdicts
  | [ $verdicts[] | select(.home == null) | { path: "permissions", kind: "coupled" } ] as $conflicts
  | ($verdicts | map(select(.home != null))) as $moves
  | if ($conflicts | length) > 0 or ($moves | length) == 0
    then { value: $doc, actions: [], conflicts: $conflicts }
    else
      reduce $moves[] as $m ({ value: $doc, actions: [], conflicts: [] };
        reduce ($lists[] | select(. != $m.home)) as $l (.;
          if (.value.permissions[$l] // []) | any(.[]; . == $m.entry)
          then .value.permissions[$l] |= map(select(. != $m.entry))
               | .actions += [ act("permissions." + $l; "removed") ]
          else . end))
    end;

def condense:
  group_by([ .path, .verdict ])
  | map({ path: .[0].path, verdict: .[0].verdict, count: (map(.count) | add) });

def merge:
  (.[0].alignment // {}) as $reg
  | [ ($reg.exempt // [])[] | select(type == "object") | .path ] as $pats
  | (.[0] | settings) as $B
  | merge_node($reg; $pats; present($B); present(.[1]); "") as $m
  | project_disjoint($B; $m.value) as $pj
  | ($m.conflicts + $pj.conflicts) as $conflicts
  | { predicate: "merge",
      ok: (($conflicts | length) == 0),
      conflicts: $conflicts,
      actions: (($m.actions + $pj.actions) | condense),
      result: $pj.value };

# --- dispatch ----------------------------------------------------------

if $mode == "audit-base" then audit_base
elif $mode == "merge" then merge
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
       modes: ["audit-base", "floor", "disjoint", "residue", "keys", "lift-gate", "merge"] }
end

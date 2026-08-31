"""Gen2-owned Repository Construction Facility (G2-00 SS9.1, SS20; SC-23
closure).

Scope, deliberately narrow: local-commit-only. This module wraps Gen1's
real, already-built, production-grade `tenfold.repository_facility.
RepositoryFacility` bound to `tenfold.local_git_transport.
LocalGitRepositoryTransport` (`create_branch`/`read`/`commit` only) --
never re-derived, per G2-00 SS15's "no invariant split across
Python/Rust", the same reuse precedent G2-25's `recovery_takeover.py`
established for `tenfold.recovery.takeover()`. Real GitHub push/PR/merge
authority is explicitly OUT OF SCOPE for this milestone --
`LocalGitRepositoryTransport` itself already refuses
`open_pull_request`/`merge_pull_request` by design, and this module does
not attempt to lift that.

`RepositoryConstructionPropertyQualificationHarness` genuinely exercises
G2-00 SS9.1's 11-property adversarial corpus against the real Facility
operating on a real, disposable, throwaway local git repository (created
fresh per qualification run, never a canonical/production repo) -- this
is Python-only by design (G2-00 SS4: "Python may own: simulation and
analysis"); the critical-gate narrowing this milestone also builds
(`tenfold.gen2.facility.check_critical_gate`, `rust/facility`) is what
Rust independently re-derives, never the harness itself.

The admitted identity fields (`ADMITTED_REPOSITORY_CONSTRUCTION_FACILITY_ID`
etc.) are defined in `tenfold.gen2.facility` itself (the critical gate's
own owning module, avoiding a circular import) and re-exported here for
convenience. This is an identity-metadata match, not a cryptographic
binding to "this exact harness-tested code genuinely ran against a
genuinely disposable repo." That trust boundary is enforced at
construction/qualification time (this harness, permanent tests,
adversarial review, and the Trust Table row's own admission), the same
trust model every other PropertyQualificationRecord/Trust Table row in
this codebase already uses -- disclosed explicitly here since this is
the first time that trust model backs a REAL_MUTATING capability instead
of a read-only or disposable-sandbox one.
"""

from __future__ import annotations

import inspect
import json
import os
import re
import shutil
import subprocess
import tempfile
import time
import types
import weakref
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path

from tenfold.contracts import NodeState, TaskPacket
from tenfold.facility import stable_digest
from tenfold.local_git_transport import (
    LocalGitRepositoryTransport,
    LocalGitTransportError,
    _RegisteredRepository,  # noqa: SLF001 -- genuine safety enforcement; see gen1_wrap_repository_construction_facility's own FROZEN-DATACLASS FINDING
)
from tenfold.ownership import WriteLease
from tenfold.persistence import AssignmentRef, CampaignSnapshot
from tenfold.repository_facility import (
    FacilityError as Gen1RepositoryFacilityError,
    RepositoryFacility,
    RepositoryReceipt,
    RepositoryStateStore,
    repository_ref_resource,
    repository_request_binding,
)

from .facility import (
    ADMITTED_REPOSITORY_CONSTRUCTION_EFFECT_CLASS,
    ADMITTED_REPOSITORY_CONSTRUCTION_FACILITY_GENERATION,
    ADMITTED_REPOSITORY_CONSTRUCTION_FACILITY_ID,
    FacilityAdapterBoundary,
    FacilityContract,
    FacilityIOClass,
    FacilityProperty,
    PropertyQualificationRecord,
    QualificationState,
)

CAMPAIGN_ID = "gen2-sc23-repository-construction-qualification"
NODE_ID = "gen2-sc23-scratch-node"
REPOSITORY_NAME = "scratch"


def _coerce_defaults_attr(raw, expected_type: type, empty_value):
    """SELF-CAUGHT TRUTHINESS-BEFORE-TYPE-CHECK FINDING (review
    finding, PR #86, round 47, P2, Codex, reproduced by the reviewer
    -- "Avoid truthiness check on __kwdefaults__ before type
    validation"): both callers below used to write `func.__defaults__
    or ()` / `func.__kwdefaults__ or {}` -- the `or` operator invokes
    `bool()` on the LEFT operand to decide whether to evaluate the
    right one, and `bool()` dispatches to the object's own `__bool__`
    (or `__len__`) BEFORE either caller's own exact-type check on the
    next line ever ran. `__defaults__`/`__kwdefaults__` are both
    plain, attacker-settable attributes on a function object -- the
    same "any hashable/any object accepted, Python never validates
    it" property already established for `__kwdefaults__`'s KEYS in
    the round-45 finding this docstring's sibling function documents,
    now recurring for the ATTRIBUTE VALUE itself, and for an
    overloaded `__bool__`/`__len__` carrying a malicious side effect
    rather than an overloaded `__lt__`. This helper never calls
    `bool()`, `len()`, or any other implicit-dispatch check on `raw`
    at all: only `is None` (an identity check, never overridable) and
    `type(raw) is expected_type` (the same exact-type discipline used
    everywhere else in this file) ever run, in that order, before
    `raw` is trusted. Returns `(True, normalized_value)` when `raw` is
    genuinely safe to use (`None`, normalized to `empty_value`, or
    already exactly `expected_type`) or `(False, None)` when it is
    neither -- callers decide whether that means raising or simply
    reporting no match, since the two call sites need different
    failure handling."""
    if raw is None:
        return True, empty_value
    if type(raw) is expected_type:
        return True, raw
    return False, None


def _function_defaults_snapshot(func) -> tuple:
    """See `_TRUSTED_TRANSPORT_CLASS_DEFAULTS`'s own module-level
    comment for the round-44 finding this closes. Captures a function's
    `__defaults__` (already an immutable tuple, but copied here so a
    later WHOLESALE reassignment of the tuple itself can't retroactively
    change what THIS reference points to -- the same "capture a
    reference before any tampering is possible" technique used
    throughout this file) and `__kwdefaults__` (a genuinely MUTABLE
    dict) as a sorted tuple of `(name, value)` pairs -- immune to later
    in-place mutation of the dict itself, since a tuple of items is an
    independent snapshot, not a view into the original dict. Both
    attributes are read via `_coerce_defaults_attr` -- see that
    function's own docstring for the round-47 truthiness-before-type-
    check finding this closes.

    SELF-CAUGHT SORT-BEFORE-TYPE-CHECK FINDING (review finding, PR
    #86, round 45, P1, Codex, reproduced by the reviewer -- "Validate
    keyword-default keys before sorting"): `sorted(..., key=lambda
    pair: pair[0])` invokes `__lt__` on the KEYS themselves to
    determine order -- BEFORE any exact-type check on those keys ever
    runs. `__kwdefaults__` accepts ANY hashable object as a key
    (Python never validates it against the function's real parameter
    names), so an attacker-controlled key TYPE with an overloaded
    `__lt__` carrying a malicious SIDE EFFECT (not merely a lying
    comparison RESULT, the round-28 pattern -- an ACTUAL side effect
    that fires the moment `sorted()` calls it) would already have run
    by the time this function's own exact-type checks could reject
    it. Every key's exact type is now verified BEFORE `sorted()` is
    ever called -- `all(type(k) is str for k in kwdefaults)` calls
    only the builtin `type()`, never `<`/`==` on a potentially
    untrusted key, so this check itself cannot be subverted the same
    way."""
    # Called at THIS module's own import time, before
    # `RepositoryConstructionQualificationError` (defined later in
    # this same file) exists yet -- a plain `TypeError` is used for
    # every rejection here instead, matching the fact that this whole
    # function is pure defense-in-depth for a genuinely-defined
    # function's OWN, freshly-created attributes rather than a
    # live-admission rejection.
    defaults_ok, defaults = _coerce_defaults_attr(func.__defaults__, tuple, ())
    if not defaults_ok:
        raise TypeError(f"_function_defaults_snapshot: {func!r}'s __defaults__ is neither None nor a tuple -- refusing to admit")
    kwdefaults_ok, kwdefaults = _coerce_defaults_attr(func.__kwdefaults__, dict, {})
    if not kwdefaults_ok:
        raise TypeError(f"_function_defaults_snapshot: {func!r}'s __kwdefaults__ is neither None nor a dict -- refusing to admit")
    if not all(type(name) is str for name in kwdefaults):
        raise TypeError(f"_function_defaults_snapshot: {func!r}'s __kwdefaults__ has a non-str key -- refusing to admit")
    return (tuple(defaults), tuple(sorted(kwdefaults.items(), key=lambda pair: pair[0])))


def _function_defaults_match(func, captured_snapshot: tuple) -> bool:
    """See `_function_defaults_snapshot`'s own docstring, including
    its own SELF-CAUGHT SORT-BEFORE-TYPE-CHECK FINDING section and
    `_coerce_defaults_attr`'s own SELF-CAUGHT TRUTHINESS-BEFORE-TYPE-
    CHECK FINDING section -- THIS function is the one the round-45
    reviewer's reproduction actually targeted (it runs on
    `func.__kwdefaults__` AFTER admission, the genuinely
    attacker-reachable side of this pair, unlike
    `_function_defaults_snapshot`'s own call against a freshly-defined,
    not-yet-tampered function at import time). Round 28's exact-type
    lesson, replayed here for VALUES too: an attacker-controlled value
    (reachable the moment a default is reassigned) could otherwise
    claim equality with the captured value via an overloaded `__eq__`
    while holding genuinely different content, so every comparison
    checks the CURRENT value's exact type before trusting `==` on it
    at all."""
    captured_defaults, captured_kwdefaults_items = captured_snapshot
    defaults_ok, current_defaults = _coerce_defaults_attr(func.__defaults__, tuple, ())
    if not defaults_ok or len(current_defaults) != len(captured_defaults):
        return False
    for current_value, captured_value in zip(current_defaults, captured_defaults):
        if type(current_value) is not type(captured_value) or current_value != captured_value:
            return False
    kwdefaults_ok, current_kwdefaults = _coerce_defaults_attr(func.__kwdefaults__, dict, {})
    if not kwdefaults_ok:
        return False
    if not all(type(name) is str for name in current_kwdefaults):
        return False
    current_items = tuple(sorted(current_kwdefaults.items(), key=lambda pair: pair[0]))
    if len(current_items) != len(captured_kwdefaults_items):
        return False
    for (current_name, current_value), (captured_name, captured_value) in zip(current_items, captured_kwdefaults_items):
        if (
            type(current_name) is not type(captured_name)
            or current_name != captured_name
            or type(current_value) is not type(captured_value)
            or current_value != captured_value
        ):
            return False
    return True

#: Review finding (PR #86, round 21, P1, Codex, reproduced by the
#: reviewer -- "Bind the transport class implementation before
#: mutation"): every instance-level check so far (rounds 14, 18, 19,
#: 20) validates `vars(transport)` -- the INSTANCE's own `__dict__` --
#: but `LocalGitRepositoryTransport._run = malicious_fn` (assigned on
#: the CLASS, not any particular instance) leaves every instance's own
#: `__dict__` completely untouched; Python's attribute lookup falls
#: through to the class for anything the instance doesn't shadow
#: itself, so the malicious `_run` is what every instance -- including
#: the one genuinely admitted -- actually calls. The reviewer
#: reproduced exactly this passing every existing check, then a
#: fully-authorized `create_branch` invoking the replacement before
#: ever reaching real git. Captured here, at THIS module's own import
#: time -- necessarily before any admission call in every legitimate
#: call path, since a caller must import this module to reach
#: `gen1_wrap_repository_construction_facility` at all -- so
#: `_reject_altered_transport_class_implementation` has a trusted
#: baseline to compare the class's OWN `__dict__` against before every
#: admission and mutation. (This does not defend against an attacker
#: who already has code execution BEFORE this module is ever imported
#: -- the same disclosed, construction-time-review trust model every
#: other check in this file already relies on, not a new category of
#: gap.)
#:
#: ROUND 54 WIDENING (P1, Codex, reproduced by the reviewer -- "Make
#: class-integrity snapshots immutable"): capturing a trust snapshot
#: at import time protects it from a LATER change to the REAL class --
#: but says nothing about the snapshot ITSELF, which was, until this
#: round, an ORDINARY, MUTABLE dict, reachable by any same-process
#: caller that imports this module (`import
#: tenfold.gen2.repository_construction_facility as m`) the SAME way
#: every other module-private name in this file already is. The
#: reviewer reproduced tampering `RepositoryFacility.create_branch`
#: AND updating `_TRUSTED_FACILITY_CLASS_ATTRIBUTES`/
#: `_TRUSTED_FACILITY_CLASS_CODE_OBJECTS` to match, in the SAME
#: attack: `_reject_altered_class_implementation`'s own comparison
#: (`current[name] is not trusted_snapshot[name]`) found both sides
#: equal, since both were set to the identical malicious value --
#: `wrapper.create_branch(None)` then ran the injected method with NO
#: containment, authority, lease, or request-binding validation at
#: all. This is the trust-STORE analogue of every prior round's
#: trust-SUBJECT finding: pinning what a function/class/module
#: REFERENCES protects nothing if the PINS THEMSELVES remain
#: attacker-writable. Fixed (ROUND 54's own attempt; see the ROUND 55
#: WIDENING note immediately below for why `MappingProxyType` itself
#: was NOT the end of this story) by wrapping every trust dict in this
#: file in `types.MappingProxyType` -- a read-only VIEW whose
#: `__setitem__` unconditionally raises `TypeError`, closing the
#: reviewer's exact ENTRY-level mutation as demonstrated at the time.
#:
#: ROUND 55 WIDENING (P1, Codex, reproduced by the reviewer --
#: "Replace mapping proxies with intrinsically immutable snapshots"):
#: `types.MappingProxyType` is a VIEW over a real, separately-
#: referenced backing dict -- blocking `proxy[name] = x` says nothing
#: about the backing dict ITSELF, which remains an ordinary, live
#: Python object the proxy holds a strong reference to, discoverable
#: via `gc.get_referents(proxy)[0]` regardless of how carefully the
#: wrapping is authored (an INHERENT property of the type, not an
#: implementation oversight round 54 could have avoided). The
#: reviewer reproduced exactly that: enumerate the mappingproxy's own
#: referents, mutate the backing dict directly, bypassing
#: `MappingProxyType`'s own guard entirely, since nothing about that
#: guard applies to the dict UNDERNEATH it -- the SAME
#: `RepositoryFacility.create_branch`-plus-matching-trust-update
#: attack round 54 closed for direct mutation, now reopened one layer
#: deeper. Fixed by never persistently storing a dict (proxied or
#: otherwise) as a trust snapshot at all: `_immutable_snapshot`
#: (below) converts every trust structure in this file to a `tuple`
#: of `(key, value)` pairs -- which has NO separate backing structure
#: to discover, since a tuple IS its own elements and supports no
#: in-place mutation whatsoever -- with `_snapshot_as_dict` providing
#: dict-style lookup back ONLY as a fresh, call-scoped local value,
#: never itself stored anywhere persistent. See `_immutable_snapshot`'s
#: own docstring for the full account.
#:
#: DISCLOSED, not fixed, by EITHER round's mechanism: wholesale
#: REBINDING of the MODULE-LEVEL NAME itself --
#: `m._TRUSTED_FACILITY_CLASS_ATTRIBUTES = a_different_tuple` -- remains
#: reachable, the exact same already-disclosed round-27/34
#: reachability fact ("any code holding a reference this module
#: produces can reach anything reachable from it," and importing the
#: module IS such a reference) applied one level further out -- not a
#: new category of gap, and no more fixable here than it is anywhere
#: else in this file. See
#: `test_sc23_wrapper_ignores_a_wholesale_reassigned_trust_dict`'s own
#: docstring for the permanent, executable record of this disclosed
#: limitation.
def _immutable_snapshot(mapping) -> tuple:
    """See `_TRUSTED_TRANSPORT_CLASS_ATTRIBUTES`'s own module-level
    ROUND 55 WIDENING comment for the finding this closes. Converts an
    ordinary mapping into a `tuple` of `(key, value)` pairs -- a
    genuinely, intrinsically immutable structure with no separate
    backing container `gc.get_referents` (or any other introspection)
    could hand back for an attacker to mutate directly, unlike
    `types.MappingProxyType`, which is only ever a VIEW over one."""
    return tuple(mapping.items())


def _snapshot_as_dict(snapshot) -> dict:
    """Companion to `_immutable_snapshot` -- converts one of this
    file's tuple-based trust snapshots back to an ordinary dict for
    convenient lookup, but ONLY ever as a FRESH, LOCAL value scoped to
    the single call that needs it: never stored on `self`, never
    returned to a caller, never assigned to a module-level or
    otherwise long-lived name. A dict that exists only for the
    duration of one function call, referenced by nothing beyond that
    call's own local variables, is not persistently reachable the way
    `MappingProxyType`'s own backing dict was -- there is no
    module-level (or otherwise long-lived) name a same-process caller
    could import and hand to `gc.get_referents` to find it, since it
    is discarded the moment the call returns."""
    return dict(snapshot)


_TRUSTED_TRANSPORT_CLASS_ATTRIBUTES = _immutable_snapshot(dict(vars(LocalGitRepositoryTransport)))
#: Review finding (PR #86, round 37, P1, Codex, reproduced by the
#: reviewer -- "Snapshot method implementations rather than function
#: identities"): `_reject_altered_class_implementation`'s
#: `current[name] is trusted_snapshot[name]` check pins the FUNCTION
#: OBJECT's identity -- but a function object's own `__code__`
#: attribute is itself ordinary, mutable, plain-attribute state, no
#: different in kind from any instance attribute round 14-20 already
#: learned not to trust by identity alone. The reviewer reproduced
#: `LocalGitRepositoryTransport._run.__code__ = malicious.__code__`:
#: the function OBJECT was never replaced (`current[name] is
#: trusted_snapshot[name]` stayed true), only its bytecode was, so the
#: identity check kept passing while a fully-authorized `create_branch`
#: executed the injected body. Captured here, at THIS module's own
#: import time, alongside `_TRUSTED_TRANSPORT_CLASS_ATTRIBUTES` itself
#: -- a SEPARATE reference to the `__code__` OBJECT each trusted
#: function held at that moment, immune to a later reassignment of
#: `func.__code__` for the exact same reason round 36's
#: `_SealedCollaboratorProxy` is immune to a later reassignment of a
#: captured bound method: this dict holds its OWN reference to the
#: original code object, which a later `func.__code__ = other` cannot
#: retroactively change.
_TRUSTED_TRANSPORT_CLASS_CODE_OBJECTS = _immutable_snapshot({name: value.__code__ for name, value in _TRUSTED_TRANSPORT_CLASS_ATTRIBUTES if inspect.isfunction(value)})
#: Review finding (PR #86, round 44, P1, Codex, reproduced by the
#: reviewer -- "Pin function keyword defaults during class checks"):
#: round 37's `__code__` pin closes bytecode mutation, but a
#: function's `__kwdefaults__` (the dict backing keyword-only
#: parameter DEFAULT VALUES) is ITS OWN separate, genuinely mutable
#: dict attribute -- identical in kind to `__code__` being ordinary,
#: mutable, plain-attribute state, just one level further out. The
#: reviewer reproduced `LocalGitRepositoryTransport._run.__kwdefaults__["extra_env"]
#: = {malicious GIT_CONFIG_* overrides}`: neither the function
#: object's identity NOR its `__code__` ever changed, so BOTH existing
#: checks kept passing, while every FUTURE call to `_run` omitting an
#: explicit `extra_env=` argument (the overwhelming majority of real
#: call sites) silently picked up the poisoned default, injecting a
#: malicious `core.hooksPath` override via Git's own
#: `GIT_CONFIG_COUNT`/`GIT_CONFIG_KEY_n`/`GIT_CONFIG_VALUE_n`
#: environment-variable config mechanism during a fully-authorized
#: `create_branch`. Captured here, at THIS module's own import time,
#: as an immutable snapshot (`__defaults__`'s own tuple copied by
#: value; `__kwdefaults__`'s dict converted to a sorted tuple of
#: items) -- immune to later in-place dict mutation for the same
#: reason `_TRUSTED_TRANSPORT_CLASS_CODE_OBJECTS` is immune to a later
#: `func.__code__` reassignment.
_TRUSTED_TRANSPORT_CLASS_DEFAULTS = _immutable_snapshot({name: _function_defaults_snapshot(value) for name, value in _TRUSTED_TRANSPORT_CLASS_ATTRIBUTES if inspect.isfunction(value)})

#: Review finding (PR #86, round 23, P1, Codex, reproduced by the
#: reviewer -- "Seal the delegated RepositoryFacility operations"): the
#: round 14-22 checks comprehensively seal `LocalGitRepositoryTransport`
#: (the object doing the actual git subprocess work), but delegation
#: happens through TWO objects -- `self._facility` (Gen1's real
#: `RepositoryFacility`) is the one `_ContainmentReCheckedRepositoryFacility.
#: create_branch`/`commit`/`read`/`open_pr`/`merge_pr` actually call
#: `.create_branch`/etc. ON. The reviewer reproduced shadowing
#: `facility._facility.create_branch` at the INSTANCE level, exactly
#: the round-14/18 transport attack replayed one layer up: nothing
#: checked `self._facility`'s own instance state at all, so the
#: injected replacement ran instead of the real method -- skipping
#: Gen1's own authority, lease, request-binding, AND every one of this
#: module's transport-integrity checks in one move, since it never
#: even touches the (already thoroughly re-verified) transport.
#: `RepositoryFacility` gets the SAME two-layer defense
#: `LocalGitRepositoryTransport` already has: an instance-attribute
#: allowlist (`_EXPECTED_FACILITY_INSTANCE_ATTRIBUTES`, matching its
#: real `__init__`'s own three data attributes) and a class-
#: implementation pin (`_TRUSTED_FACILITY_CLASS_ATTRIBUTES`), applying
#: the round-18/21 lesson pre-emptively rather than waiting for a
#: predictable round-24 rediscovery of the same pattern one layer
#: deeper. Deliberately NOT pinning `.transport`'s VALUE the way the
#: transport's own four attributes are pinned: a transport swap is
#: legitimate and independently, more thoroughly re-verified by
#: `_current_transport`/`_admitted_state_for` -- pinning it here too
#: would just reject every genuine round-16 swap a second, redundant
#: way.
_TRUSTED_FACILITY_CLASS_ATTRIBUTES = _immutable_snapshot(dict(vars(RepositoryFacility)))
#: See `_TRUSTED_TRANSPORT_CLASS_CODE_OBJECTS`'s own docstring -- the
#: identical round-37 fix, applied symmetrically to `RepositoryFacility`
#: (whose own `create_branch`/`commit`/etc. are equally reachable,
#: equally mutable function objects, and equally protected only by
#: THIS class-implementation check -- `_FrozenClassMeta` guards
#: `_ContainmentReCheckedRepositoryFacility`'s own class, never
#: `RepositoryFacility`'s).
_TRUSTED_FACILITY_CLASS_CODE_OBJECTS = _immutable_snapshot({name: value.__code__ for name, value in _TRUSTED_FACILITY_CLASS_ATTRIBUTES if inspect.isfunction(value)})
#: See `_TRUSTED_TRANSPORT_CLASS_DEFAULTS`'s own module-level comment
#: -- the identical round-44 fix, applied symmetrically to
#: `RepositoryFacility` for the same reason
#: `_TRUSTED_FACILITY_CLASS_CODE_OBJECTS` mirrors
#: `_TRUSTED_TRANSPORT_CLASS_CODE_OBJECTS`.
_TRUSTED_FACILITY_CLASS_DEFAULTS = _immutable_snapshot({name: _function_defaults_snapshot(value) for name, value in _TRUSTED_FACILITY_CLASS_ATTRIBUTES if inspect.isfunction(value)})
_EXPECTED_FACILITY_INSTANCE_ATTRIBUTES = frozenset({"transport", "state", "authority_store"})


def _reject_altered_class_implementation(cls: type, trusted_snapshot: tuple, trusted_code_objects: tuple, trusted_defaults: tuple, label: str) -> None:
    """See `_TRUSTED_TRANSPORT_CLASS_ATTRIBUTES`'s own docstring for
    the round-21 finding this closes, `_TRUSTED_FACILITY_CLASS_ATTRIBUTES`'s
    for the round-23 extension to a second class,
    `_TRUSTED_TRANSPORT_CLASS_CODE_OBJECTS`'s for the round-37
    extension covering in-place `__code__` mutation of an otherwise
    unreplaced function object, `_TRUSTED_TRANSPORT_CLASS_DEFAULTS`'s
    for the round-44 extension covering in-place `__kwdefaults__`/
    `__defaults__` mutation of an otherwise unreplaced, byte-code-
    unchanged function object, and `_immutable_snapshot`'s own for the
    round-55 extension -- `trusted_snapshot`/`trusted_code_objects`/
    `trusted_defaults` now ARRIVE as tuples (converted to local dicts,
    scoped only to this call, via `_snapshot_as_dict`), never a
    persistently-stored dict/mappingproxy this function could be
    handed a lingering reference into. Compares `cls`'s OWN `__dict__`
    (methods, not instance state -- functions compare by identity, so
    any rebinding to a different object is caught) against the
    snapshot taken when this module was first imported; any method
    added, removed, or reassigned is rejected outright. For every
    trusted attribute that is itself a function, ALSO compares its
    CURRENT `__code__` against the code object captured at import
    time (catching a function object whose identity never changed but
    whose underlying bytecode did) AND its current keyword/positional
    DEFAULT VALUES against the snapshot captured at import time
    (catching a function object whose identity AND bytecode never
    changed, but whose default-argument dict did)."""
    trusted_snapshot = _snapshot_as_dict(trusted_snapshot)
    trusted_code_objects = _snapshot_as_dict(trusted_code_objects)
    trusted_defaults = _snapshot_as_dict(trusted_defaults)
    current = dict(vars(cls))
    changed = sorted(set(current) ^ set(trusted_snapshot))
    changed += sorted(
        name
        for name in set(current) & set(trusted_snapshot)
        if current[name] is not trusted_snapshot[name]
    )
    changed += sorted(
        name
        for name in trusted_code_objects
        if name in current and inspect.isfunction(current[name]) and current[name].__code__ is not trusted_code_objects[name]
    )
    changed += sorted(
        name
        for name in trusted_defaults
        if name in current and inspect.isfunction(current[name]) and not _function_defaults_match(current[name], trusted_defaults[name])
    )
    if changed:
        raise RepositoryConstructionQualificationError(
            f"_reject_altered_class_implementation: {label}'s own class implementation no longer matches "
            f"what was admitted at import time ({', '.join(sorted(set(changed)))}), "
            f"breaking the local-commit-only boundary for every instance of the class"
        )


def _reject_altered_transport_class_implementation() -> None:
    """Called at admission and before every mutating or transport-
    delegating call (`create_branch`, `commit`, `read`, `open_pr`,
    `merge_pr` all reach this), since a class-level replacement of
    `open_pull_request`/`merge_pull_request` would otherwise defeat
    the reasoning `open_pr`/`merge_pr` rely on -- that the real,
    unmodified methods unconditionally raise by design. Round 23,
    P1, Codex (see `_admitted_state_for`'s own docstring): MUST run
    before any operation whose dispatch can depend on the transport's
    mutable class -- including a `WeakKeyDictionary` lookup, which
    invokes the transport's own (potentially rebound) `__hash__`/`__eq__`
    internally. The reviewer reproduced replacing `LocalGitRepositoryTransport.__hash__`
    and reaching `_admitted_state_for`'s registry lookup BEFORE this
    check had a chance to reject the class tampering, so the malicious
    `__hash__`'s side effect ran even though the call correctly raised
    moments later. Every call site in this file now runs this check
    first, before touching the transport in any way that could invoke
    a class dunder method on it.

    ROUND 51 WIDENING (see `_TRUSTED_TRANSPORT_CLASS_MODULE_GLOBALS`'s
    own module-level comment for the full finding): also revalidates
    every module-global (and module-attribute) name the transport's
    own methods reference, closing the gap that class-implementation
    pinning alone never covered a method's OWN module dependencies."""
    _reject_altered_class_implementation(LocalGitRepositoryTransport, _TRUSTED_TRANSPORT_CLASS_ATTRIBUTES, _TRUSTED_TRANSPORT_CLASS_CODE_OBJECTS, _TRUSTED_TRANSPORT_CLASS_DEFAULTS, "LocalGitRepositoryTransport")
    _reject_altered_transitive_globals(_TRUSTED_TRANSPORT_CLASS_MODULE_GLOBALS)


def _reject_altered_facility_class_implementation() -> None:
    """See `_TRUSTED_FACILITY_CLASS_ATTRIBUTES`'s own docstring for the
    finding this closes. Called alongside `_reject_altered_transport_class_implementation`
    everywhere `self._facility`'s own methods are about to be invoked."""
    _reject_altered_class_implementation(RepositoryFacility, _TRUSTED_FACILITY_CLASS_ATTRIBUTES, _TRUSTED_FACILITY_CLASS_CODE_OBJECTS, _TRUSTED_FACILITY_CLASS_DEFAULTS, "RepositoryFacility")


#: Review finding (PR #86, round 45, P1, Codex, reproduced by the
#: reviewer -- "Pin delegated methods' global dependencies"): every
#: check so far (rounds 21/23/37/44) pins `RepositoryFacility`/
#: `LocalGitRepositoryTransport`'s OWN class attributes, code objects,
#: and keyword defaults -- but says nothing about the GLOBAL
#: NAMESPACE those classes' methods actually execute WITHIN.
#: `RepositoryFacility._live_mutable` calls `validate_live_task(...)`
#: as an ordinary global-scope name lookup, resolved via
#: `_live_mutable.__globals__['validate_live_task']` -- literally
#: `tenfold.repository_facility.__dict__`, the SAME module namespace
#: `import tenfold.repository_facility; tenfold.repository_facility.validate_live_task
#: = malicious_fn` ordinarily, PUBLICLY rebinds -- no special
#: reachability trick needed at all (unlike round 27/34's disclosed
#: bypasses, which needed SOME cleverness; this needs none, since
#: `tenfold.repository_facility` is a real, intentionally-importable
#: Gen1 module, not a "private" name of THIS module). The reviewer
#: reproduced exactly this: rebind the name, then call `create_branch`
#: with a bare `SimpleNamespace(assignment_id="attacker")` -- no real
#: seal, capability, permission, epoch, or lease at all -- and the
#: malicious replacement ran, skipping EVERY real authority check, so
#: the branch was created regardless.
#:
#: ROUND 46 WIDENING (P1, Codex, reproduced by the reviewer -- "Pin
#: the repository scope predicate before delegation"): round 45's own
#: scoping pass only ever scanned `repository_facility.py`'s IMPORTED
#: names for candidates meeting its OWN stated criterion ("functions
#: whose replacement directly grants unauthorized CAPABILITY"),
#: never its LOCALLY-DEFINED module-level helper functions. The
#: reviewer reproduced rebinding `_path_in_scope` -- defined IN
#: `repository_facility.py` itself, enforcing the EFFECT-REACH
#: boundary for `read`/`commit` -- to `lambda path, scope: True`,
#: then using a legitimately sealed task scoped to `allowed/` to
#: commit `not-allowed/escape.txt`; every existing check (round 45's
#: `validate_live_task`/`validate_task` pins included) passed, and the
#: out-of-scope file landed in Git. Investigating the SAME class of
#: oversight further (not merely fixing the one instance the reviewer
#: demonstrated) found FOUR more locally-defined functions in the
#: identical causal chain, confirmed exploitable the same way:
#: `repository_ref_resource`/`repository_pr_resource` (compute the
#: `resource=` argument `validate_live_task`'s OWN lease-fencing check
#: uses -- a rebind could let a lease held for one resource authorize
#: a write to an entirely different one), `repository_request_binding`
#: (recomputes the EXPECTED request binding from the actual request
#: fields, compared against the task's SEALED binding -- a rebind that
#: ignores its arguments would let ANY request "match" any sealed
#: task, defeating request-binding fencing entirely), and
#: `_file_digests` (feeds `commit`'s own file contents into that same
#: request-binding computation -- a rebind returning constant digests
#: regardless of actual content would let substituted file contents
#: still "match" a binding sealed for different ones). `_path_parts`
#: is `_path_in_scope`'s OWN internal helper -- pinning `_path_in_scope`
#: alone does not protect what it calls internally, the same "one
#: level deeper" concern round 45 already handled for
#: `validate_live_task`/`validate_task`.
#:
#: Fixed the SAME way rounds 21/23/37/44 pin `RepositoryFacility`'s
#: OWN methods, generalized into a single, DATA-DRIVEN check (rather
#: than one hand-written `if` block per name, which is exactly the
#: shape that let round 45's own pass stay incomplete): every trusted
#: global's reference, `__code__`, and `__defaults__`/`__kwdefaults__`
#: are captured once, at THIS module's own import time, into
#: `_TRUSTED_AUTHORITY_VALIDATION_GLOBALS`/
#: `_TRUSTED_AUTHORITY_VALIDATION_FACILITY_MODULE_GLOBALS` (keyed by
#: which REAL module namespace each name is resolved from -- the two
#: differ, since `validate_live_task` calls `validate_task` via
#: `tenfold.facility`'s own namespace, a DIFFERENT module than
#: `tenfold.repository_facility`), and `_reject_altered_authority_validation_globals`
#: loops over both, re-verifying identity/code/defaults on every
#: check -- adding a NEW name to either dict is now the entire cost of
#: covering it, rather than another hand-written comparison block.
#:
#: ROUND 47 WIDENING (P1, Codex, reproduced by the reviewer -- "Pin
#: stable_digest behind request binding" and "Pin canonical_digest
#: behind task validation"): round 46's own pass pinned
#: `repository_request_binding`/`_file_digests`/`validate_task`
#: THEMSELVES but, per THIS docstring's own prior (now-corrected)
#: DISCLOSED SCOPE claim, stopped short of what THOSE functions call
#: internally -- the identical "one level deeper" oversight round 45
#: already fixed once for `validate_live_task`->`validate_task`,
#: recurring for a THIRD and FOURTH name in the SAME causal chain.
#: The reviewer reproduced rebinding `stable_digest` (called
#: internally by `repository_request_binding`/`_file_digests` to
#: compute the digest baked into a task's request binding) to a
#: function that always returns a task's EXISTING, already-sealed
#: binding regardless of its actual argument, then committing
#: DIFFERENT file contents and a DIFFERENT message under that same
#: legitimately sealed task -- the recomputed binding still "matched"
#: the sealed one, and Git stored the substituted bytes. The reviewer
#: separately reproduced rebinding `canonical_digest` (the
#: cryptographic check `validate_task` itself runs to confirm a task
#: genuinely IS what it claims -- `canonical_digest(raw) != claimed`
#: -- more foundational than any single call site) to a function that
#: always matches, then cloning a legitimately narrow-scope task with
#: an EXPANDED scope and a NEW request binding while keeping its
#: ORIGINAL `dispatch_digest` -- the seal check still "passed," and an
#: out-of-scope file was committed. Both are now pinned identically to
#: every other name in these two dicts -- the round-46 data-driven
#: design made this a two-name addition, not a new mechanism.
#:
#: DISCLOSED SCOPE (deliberately NOT recursing further): `RepositoryFacility`'s
#: methods reference several OTHER module-level names too --
#: `FacilityError`, `FacilityEvidence`, `FacilityKind` -- none of
#: which are pinned here. Every name now pinned grants an UNAUTHORIZED
#: CAPABILITY if rebound (skip authorization, forge a lease-resource
#: match, forge a request-binding match, forge a task's own seal
#: check); the remaining unpinned names are exception-class/evidence-
#: container dependencies whose tampering would affect error reporting
#: or evidence bookkeeping, not authorization itself, and recursing
#: into every transitively-referenced name would have no natural
#: stopping point short of the Python standard library itself (`json`,
#: `hashlib`, `dataclasses`) -- not a genuinely closeable scope. The
#: line is drawn at "functions whose replacement grants unauthorized
#: capability," matching this closure's own established practice of
#: narrowing an admitted identity's trust model explicitly rather than
#: chasing an unbounded regress -- and, per round 46's own lesson,
#: applied by genuinely auditing EVERY locally-defined helper in the
#: causal chain, not only the one a reviewer happened to demonstrate.
#: Round 47's own recurrence of the "one level deeper" pattern is a
#: standing reminder that this audit must also trace what EACH pinned
#: name calls internally, not stop at the set of locally-defined
#: functions alone -- named here explicitly so a future round
#: rediscovering the SAME class of gap treats it as confirmation the
#: line above still needs walking outward, not as a new surprise.
_REPOSITORY_FACILITY_MODULE_GLOBALS = RepositoryFacility.create_branch.__globals__


def _tenfold_owned_function(value: object) -> bool:
    """See `_capture_transitive_authority_globals`'s own docstring for
    the round-48 finding this closes. True only for a plain Python
    function genuinely defined somewhere under this codebase's own
    `tenfold` package -- the principled boundary for how far that
    function's transitive-closure walk recurses. A standard-library
    function (`dataclasses.is_dataclass`), a builtin
    (`hashlib.sha256`), a module object (`json`), or a class
    (`FacilityError`) all return `False` here -- each is still pinned
    by IDENTITY at the one level a trusted function directly
    references it, just never recursed INTO, matching this closure's
    own long-standing DISCLOSED SCOPE reasoning that the standard
    library has no natural recursion stopping point short of the
    library itself."""
    if not inspect.isfunction(value):
        return False
    module_name = getattr(value, "__module__", None) or ""
    return module_name == "tenfold" or module_name.startswith("tenfold.")


#: Review finding (PR #86, round 47, P1, Codex, reproduced by the
#: reviewer -- "Pin stable_digest behind request binding" and "Pin
#: canonical_digest behind task validation") and round 48, P1, Codex,
#: reproduced by the reviewer -- "Pin the digest functions'
#: transitive globals": round 46's own fix pinned
#: `repository_request_binding`/`_file_digests`/`validate_task`
#: THEMSELVES, but not what THOSE functions call internally; round
#: 47's own fix then pinned `stable_digest`/`canonical_digest`
#: THEMSELVES, but not what THEY call internally either -- the SAME
#: "pinning a function's own identity/code does not protect what it
#: calls" lesson, recurring for a FIFTH time. `repository_request_binding`
#: (and `_file_digests`) call `stable_digest` internally to compute
#: the digest baked into the request binding; `validate_task`'s own
#: seal check (`canonical_digest(raw) != claimed`) is the
#: cryptographic verification that a task genuinely IS what it claims
#: to be at all; both `stable_digest` and `canonical_digest`
#: themselves call `sha256` (via a plain `from hashlib import sha256`
#: in their own respective modules) to actually compute that digest.
#: Round 47 reproduced rebinding the digest functions THEMSELVES;
#: round 48 reproduced rebinding `tenfold.facility.sha256` instead,
#: leaving `stable_digest` itself untouched (so round 47's own pin
#: kept passing) while `stable_digest`'s OWN call to `sha256` resolved
#: the replacement -- a constructor returning a task's existing
#: request binding regardless of the actual content hashed -- letting
#: a sealed task commit substituted bytes and message, the recomputed
#: binding still "matching."
#:
#: Given this is the FIFTH recurrence of manually adding one more
#: name after a reviewer demonstrates it, the fix this round is a
#: change in KIND, not another name added to a tuple:
#: `_capture_transitive_authority_globals` (below) genuinely WALKS
#: each root function's own `__code__.co_names` for every name that
#: resolves in ITS `__globals__`, capturing it, and -- if that
#: referenced value is itself a locally-owned function
#: (`_tenfold_owned_function`) -- recursing into it the SAME way,
#: transitively, memoized so a name reachable via more than one path
#: is captured exactly once. This closes the `sha256` gap
#: automatically (and its exact sibling in `canonical_digest`'s own
#: `tenfold.contracts` module, not separately demonstrated by the
#: reviewer but found and closed via the SAME established
#: self-auditing discipline before considering this round closed) and
#: closes any FUTURE one-level-deeper rediscovery of this same shape
#: without another round being needed at all -- provided the newly
#: reachable name is still genuinely local, first-party code; see
#: `_tenfold_owned_function`'s own docstring for where that boundary
#: is deliberately drawn and why.
#: Round 56: sentinel distinguishing "genuinely absent" from "present
#: but happens to be `None`" for `inspect.getattr_static`'s own
#: `default` parameter, used wherever this file needs to check
#: attribute PRESENCE on a class without ever triggering descriptor
#: dispatch (unlike `hasattr`, which invokes `__get__` the same way
#: `getattr` does).
_LEAF_ATTRIBUTE_ABSENT = object()


def _leaf_attribute_roots(func) -> list:
    """SELF-CAUGHT FINDING (review finding, PR #86, round 51, P1,
    Codex, reproduced by the reviewer -- "Snapshot mutable attributes
    of captured modules"): a module captured as an identity-only leaf
    (`sqlite3`, `json`, ...) has its OWN attributes verified by
    NOTHING -- `current is trusted_value` only checks that the MODULE
    OBJECT itself was never rebound; it says nothing about whether one
    of that module's OWN attributes was mutated in place afterward.
    The reviewer reproduced assigning `sqlite3.connect = malicious`
    directly (the `sqlite3` module reference itself untouched, so the
    round-50 fix's own identity check kept passing) while `_connect`'s
    own body -- unchanged, still code-pinned -- resolved the tampered
    `.connect` attribute the moment it ran.

    A module's own `__dict__` is an ordinary globals-shaped namespace
    (exactly what `_capture_transitive_authority_globals` already
    walks for a REGULAR module's top-level names), so the fix is not a
    new mechanism: for one function's `__code__.co_names`, this finds
    every name that resolves to a MODULE in that function's
    `__globals__`, then pairs it with every OTHER co_name that is a
    genuine attribute of that SAME module (`sqlite3`/`connect`, for a
    body that calls `sqlite3.connect(...)`) -- returning
    `(module.__dict__, attr_name)` pairs that feed directly back into
    `_capture_transitive_authority_globals` as additional roots.
    Bounded the same way the rest of this file's transitive walks are:
    only attributes THIS SAME function's own bytecode actually
    references are ever pinned, never a module's full, unbounded
    attribute surface.

    ROUND 52 WIDENING (originally `_module_attribute_roots`, renamed
    here -- review finding, PR #86, round 52, P1, Codex, reproduced by
    the reviewer -- "Pin mutable attributes on captured classes"): the
    round-51 version only ever checked `inspect.ismodule(candidate)`
    -- a CLASS captured as an identity-only leaf (`pathlib.Path`) has
    the IDENTICAL exposure a module does, and was skipped by this
    branch entirely. The reviewer reproduced `Path.is_symlink = lambda
    self: False` after admission: `Path` itself was never rebound, so
    an identity check on `Path` alone would keep passing regardless,
    while every `git_dir.is_symlink()` containment check anywhere in
    this file resolves the tampered method the moment it runs, letting
    a symlinked `.git/refs/heads` escape detection during a fully
    authorized `create_branch`.

    ROUND 53 WIDENING (P1, Codex, reproduced by the reviewer -- "Pin
    concrete pathlib classes before containment scans"): the round-52
    fix above only ever captured a class's OWN `__dict__` entry for a
    name -- but `Path(...)` never actually returns a `Path` instance;
    `Path.__new__` dispatches to a PLATFORM-SPECIFIC concrete subclass
    (`PosixPath`/`WindowsPath`), which can carry its OWN,
    independently overridable attribute for any name otherwise
    inherited from `Path`. Worse, an attacker CREATING a brand-new
    override where none existed before (exactly what the reviewer
    reproduced: `type(Path()).is_symlink = lambda self: False`,
    assigning directly onto `PosixPath`/`WindowsPath`, which had NO
    `is_symlink` entry of its own beforehand) leaves nothing in that
    subclass's OWN `__dict__` to compare against at capture time --
    even a subclass-`__dict__`-aware version of the round-52 fix would
    have found nothing to pin, since the entry simply didn't exist
    yet. `Path` itself remains byte-for-byte untouched throughout, so
    the round-52 check (and the round-51 module-identity check it's
    modeled on) both keep passing while every instance's own
    `.is_symlink()` call resolves the new override via ordinary MRO
    lookup. Fixed by capturing the MRO-RESOLVED value
    (`getattr(concrete_cls, attr_name)`, not
    `concrete_cls.__dict__.get(attr_name)`) for `candidate` itself AND
    every class reachable via `candidate.__subclasses__()`,
    transitively (side-effect-free -- never constructs an instance,
    just introspects already-loaded subclasses) -- the actual,
    effective implementation any instance of that concrete class will
    really call, regardless of WHERE in its own MRO the override
    lands. `_capture_transitive_authority_globals`'s own lookup (see
    that function's own docstring) now branches on whether a captured
    namespace is a real dict-like object (module/class `__dict__`,
    unchanged) or a CLASS ITSELF (this new case, verified via
    `getattr`), so this needed no separate verification mechanism --
    only a second kind of root and a small extension to the ONE
    existing lookup used everywhere. This naturally subsumes round
    52's own fix rather than merely adding to it: `candidate` itself
    is the first node this new walk visits, so `Path`'s own attribute
    is covered exactly as before, now alongside every concrete
    subclass.

    ROUND 55 WIDENING (P1, Codex, reproduced by the reviewer -- "Pin
    the Path factory's runtime concrete class"): the round-53 fix
    above enumerates CURRENTLY-loaded subclasses via
    `candidate.__subclasses__()` -- but `Path.__new__` does not
    discover its concrete class that way at all: its own body reads
    `cls = WindowsPath if os.name == 'nt' else PosixPath`, an ordinary
    `LOAD_GLOBAL` resolved fresh, on every call, via
    `Path.__new__.__globals__` (`pathlib`'s own module namespace).
    Round 53's own snapshot pins whatever concrete class OBJECT was
    reachable via `__subclasses__()` AT IMPORT TIME -- it says nothing
    about whether the NAME `pathlib.PosixPath`/`pathlib.WindowsPath`
    ITSELF was later REBOUND to point at an entirely different class.
    The reviewer reproduced exactly that: rebind `pathlib.PosixPath`
    to a brand-new subclass overriding `is_symlink`, so every FUTURE
    `Path(...)` construction returns an instance of the NEW class --
    round 53's own pin, still faithfully verifying the OLD `PosixPath`
    object's own `is_symlink`, has nothing to say about it. Fixed by
    tracing one level further: for every class visited in the
    subclass walk, ALSO walk every function directly defined on that
    class (`Path.__new__`, in particular) for its OWN
    `__code__.co_names`, adding `(func.__globals__, referenced_name)`
    as an additional root for each -- discovering
    `pathlib.PosixPath`/`pathlib.WindowsPath` (and `os`, already
    covered) automatically, the exact same transitive-closure
    technique this file already uses for ordinary functions, now
    applied to a class's OWN methods too rather than stopping at its
    attribute VALUES."""
    referenced = func.__code__.co_names
    pairs = []
    for name in referenced:
        candidate = func.__globals__.get(name)
        if inspect.ismodule(candidate):
            for attr_name in referenced:
                if attr_name != name and hasattr(candidate, attr_name):
                    pairs.append((candidate.__dict__, attr_name))
        elif isinstance(candidate, type):
            stack = [candidate]
            seen = {candidate}
            while stack:
                cls = stack.pop()
                for attr_name in referenced:
                    # Round 56 (see `_leaf_attribute_namespace_get`'s
                    # own ROUND 56 WIDENING docstring section): plain
                    # `hasattr` invokes descriptor `__get__` the same
                    # way plain `getattr` does, so even this
                    # DISCOVERY-phase existence check could trigger a
                    # malicious descriptor's side effect (not merely a
                    # lying comparison result). `getattr_static`
                    # checks presence without ever invoking `__get__`.
                    if attr_name != name and inspect.getattr_static(cls, attr_name, _LEAF_ATTRIBUTE_ABSENT) is not _LEAF_ATTRIBUTE_ABSENT:
                        pairs.append((cls, attr_name))
                for method in vars(cls).values():
                    # `__new__` (the exact method `Path`'s own
                    # concrete-class dispatch lives in) is stored as a
                    # `staticmethod` WRAPPER object in a class's own
                    # `__dict__`, not a plain function -- unwrap
                    # static/classmethod descriptors to reach the real
                    # underlying function, or this walk silently never
                    # sees `__new__`'s own body at all.
                    if isinstance(method, (staticmethod, classmethod)):
                        method = method.__func__
                    if inspect.isfunction(method):
                        for inner_name in method.__code__.co_names:
                            if inner_name in method.__globals__:
                                pairs.append((method.__globals__, inner_name))
                for subclass in cls.__subclasses__():
                    if subclass not in seen:
                        seen.add(subclass)
                        stack.append(subclass)
    return pairs


def _leaf_attribute_namespace_get(namespace, name):
    """Round 53: reads one name from a captured-leaf NAMESPACE, which
    is either an ordinary dict-like object (a module's or class's own
    `__dict__`, unchanged since round 51/52 -- read via plain key
    lookup, seeing only what that SPECIFIC object directly defines
    itself) or a CLASS OBJECT itself (`_leaf_attribute_roots`'s new
    concrete-subclass entries) -- read via MRO-resolved attribute
    lookup, seeing the actual binding any real instance of that class
    would resolve to, from wherever in its own MRO it's actually
    defined. Shared by `_capture_transitive_authority_globals`'s own
    capture step and `_transitive_global_entry_matches`'s own
    verification, so both read a given namespace identically.

    ROUND 56 WIDENING (P1, Codex, reproduced by the reviewer --
    "Avoid descriptor dispatch while validating class leaves"): the
    round-53/55 versions read the class branch via plain `getattr`,
    which -- for ANY attribute that is a DESCRIPTOR (an object
    implementing `__get__`, which every plain function already is) --
    INVOKES that descriptor's `__get__` rather than returning the raw
    binding stored in the class's own MRO. The reviewer reproduced
    installing a CUSTOM descriptor on the concrete `Path` subclass
    whose `__get__` inspects its `obj` argument and returns
    DIFFERENTLY depending on the caller: `descriptor.__get__(None,
    cls)` (CLASS-level access, exactly what `getattr(cls, name)`
    performs, and exactly what this verification used) returned the
    ORIGINALLY-ADMITTED `is_symlink` function, so every identity
    comparison kept passing -- while `descriptor.__get__(instance,
    cls)` (INSTANCE-level access, what REAL code performs via
    `git_dir.is_symlink()`) returned a function that always reports
    `False`. Fixed by reading the class branch via
    `inspect.getattr_static` instead -- the SAME descriptor-free,
    MRO-walking read this file already uses elsewhere for exactly
    this reason (see `_capture_collaborator_relied_upon_attributes`'s
    own use of it) -- which returns the RAW object actually stored at
    that point in the MRO, invoking no `__get__` at all: a malicious
    descriptor is itself the value compared, correctly differing by
    identity from the originally-captured plain function, with no
    separate "reject descriptors" step needed beyond the SAME
    identity check every other leaf already receives."""
    if isinstance(namespace, type):
        return inspect.getattr_static(namespace, name, None)
    return namespace.get(name)


def _leaf_attribute_namespace_label(namespace) -> str:
    """Round 53: companion to `_leaf_attribute_namespace_get` for
    error-message purposes -- a module's own `__name__` (unchanged),
    or a CLASS's own `__qualname__` for the new class-object
    namespace kind, which has no `__name__` KEY of its own to `.get`."""
    if isinstance(namespace, type):
        return getattr(namespace, "__qualname__", "<unknown class>")
    return namespace.get("__name__", "<unknown module>")




def _capture_transitive_authority_globals(roots: tuple) -> tuple:
    """Walks outward from each `(globals_dict, name)` root pin,
    following every name a trusted function's own `__code__.co_names`
    references that actually resolves in that function's `__globals__`
    -- recursing further only while the referenced value is itself
    `_tenfold_owned_function`-owned (see that function's own docstring
    for why recursion stops there). Returns an `_immutable_snapshot`
    (round 54/55 -- see `_TRUSTED_TRANSPORT_CLASS_ATTRIBUTES`'s own
    module-level ROUND 54/55 WIDENING comments for the findings this
    closes) of a dict keyed by
    `(id(globals_dict), name)` -> `(globals_dict, name, value,
    code_or_None, defaults_or_None)` -- `code_or_None`/
    `defaults_or_None` are populated only for entries that are
    themselves locally-owned functions (subject to the SAME identity/
    code/defaults check `_reject_altered_class_implementation` uses
    elsewhere in this file); every other captured value (a stdlib
    function, a builtin, a module, a class, ...) is verified by
    IDENTITY alone -- see `_leaf_attribute_roots`'s own docstring
    for the round-51/52 findings that identity-alone is not enough for
    a MODULE or CLASS specifically, and how this walk also captures its
    OWN referenced attributes for exactly that reason. Memoized by
    `(id(globals_dict), name)` so a name reachable via more than one
    path in the walk is captured exactly once, and so mutually- or
    self-referential functions cannot cause unbounded recursion."""
    captured: dict = {}
    stack = list(roots)
    while stack:
        globals_dict, name = stack.pop()
        key = (id(globals_dict), name)
        if key in captured:
            continue
        value = _leaf_attribute_namespace_get(globals_dict, name)
        if _tenfold_owned_function(value):
            captured[key] = (globals_dict, name, value, value.__code__, _function_defaults_snapshot(value))
            for referenced_name in value.__code__.co_names:
                if referenced_name in value.__globals__:
                    stack.append((value.__globals__, referenced_name))
            stack.extend(_leaf_attribute_roots(value))
        else:
            captured[key] = (globals_dict, name, value, None, None)
    # Round 54/55 (see `_TRUSTED_TRANSPORT_CLASS_ATTRIBUTES`'s own
    # module-level ROUND 54/55 WIDENING comments): every structure
    # this function's own callers store as a module-level trust
    # baseline gets the SAME intrinsically-immutable treatment -- done
    # here, once, so every current and future caller of this function
    # is covered automatically, rather than remembering to wrap the
    # result at each of the (currently four) call sites individually.
    return _immutable_snapshot(captured)


def _transitive_global_entry_matches(entry: tuple) -> bool:
    """See `_capture_transitive_authority_globals`'s own docstring for
    the entry shape this verifies against. Shared verification logic
    for one `(globals_dict, name, trusted_value, trusted_code,
    trusted_defaults)` entry: `True` when the CURRENT live binding
    still matches what was captured -- identity (plus `__code__`/
    defaults, for entries that are themselves locally-owned
    functions) -- `False` otherwise. Round 50 (see
    `_capture_collaborator_relied_upon_attributes`'s own ROUND 50
    WIDENING docstring section) extracted this from
    `_reject_altered_authority_validation_globals`'s own inline check
    so the collaborator-instance mechanism could reuse the EXACT same
    verification, rather than maintaining a second, independently
    drifting copy of it."""
    globals_dict, name, trusted_value, trusted_code, trusted_defaults = entry
    current = _leaf_attribute_namespace_get(globals_dict, name)
    if trusted_code is not None:
        return (
            current is trusted_value
            and inspect.isfunction(current)
            and current.__code__ is trusted_code
            and _function_defaults_match(current, trusted_defaults)
        )
    return current is trusted_value


def _reject_altered_transitive_globals(trusted: tuple) -> None:
    """Shared verification loop, used by every caller of
    `_capture_transitive_authority_globals` that wants a simple
    "raise on the first mismatch" check rather than the collaborator-
    instance mechanism's own more specific error message: re-reads
    every entry FRESH via `_transitive_global_entry_matches` and
    raises `RepositoryConstructionQualificationError` naming the
    entry's own originating module (`globals_dict["__name__"]`) and
    name on the first one that no longer matches. `trusted` is one of
    this file's `_immutable_snapshot` tuples (round 55) -- a tuple of
    `((id, name), entry)` pairs, iterated directly, never converted to
    a dict at all here since only the VALUES are needed."""
    for _key, entry in trusted:
        if not _transitive_global_entry_matches(entry):
            globals_dict, name = entry[0], entry[1]
            label = _leaf_attribute_namespace_label(globals_dict)
            raise RepositoryConstructionQualificationError(
                f"_reject_altered_transitive_globals: {label}'s own {name} binding "
                f"no longer matches what was admitted at import time, breaking the "
                f"local-commit-only boundary"
            )


_TRUSTED_AUTHORITY_VALIDATION_GLOBALS = _capture_transitive_authority_globals(tuple(
    (_REPOSITORY_FACILITY_MODULE_GLOBALS, name)
    for name in (
        "validate_live_task",
        "_path_in_scope",
        "_path_parts",
        "repository_ref_resource",
        "repository_pr_resource",
        "repository_request_binding",
        "_file_digests",
        "stable_digest",
    )
))
_FACILITY_MODULE_GLOBALS = _REPOSITORY_FACILITY_MODULE_GLOBALS["validate_live_task"].__globals__
_TRUSTED_AUTHORITY_VALIDATION_FACILITY_MODULE_GLOBALS = _capture_transitive_authority_globals(tuple(
    (_FACILITY_MODULE_GLOBALS, name)
    for name in ("validate_task", "canonical_digest")
))

#: Review finding (PR #86, round 51, P1, Codex, reproduced by the
#: reviewer -- "Pin transport methods' module globals"):
#: `_TRUSTED_TRANSPORT_CLASS_ATTRIBUTES`/`_CODE_OBJECTS`/`_DEFAULTS`
#: (rounds 21/37/44) pin `LocalGitRepositoryTransport`'s own class
#: attributes/code/defaults -- but, unlike `RepositoryFacility` (whose
#: effect-bearing dependencies are already covered transitively via
#: `_TRUSTED_AUTHORITY_VALIDATION_GLOBALS`'s own roots -- confirmed by
#: self-audit: every module-global name any `RepositoryFacility`
#: method's own code references is either already a root or an
#: already-disclosed exception-class/evidence-container dependency),
#: the transport NEVER had ANY module-globals coverage at all. The
#: reviewer reproduced rebinding `tenfold.local_git_transport.subprocess`
#: after admission: every existing transport check (class attributes,
#: code objects, defaults) kept passing, since `subprocess` itself was
#: never a class attribute -- it's an ordinary module-level global
#: `_run`'s own body resolves via `_run.__globals__`. Fixed the same
#: way `_TRUSTED_AUTHORITY_VALIDATION_GLOBALS` covers
#: `RepositoryFacility`'s authority-validation chain, seeded from
#: EVERY function `LocalGitRepositoryTransport` itself defines (there
#: is no narrower "authority validation" subset to curate here -- the
#: transport's methods ARE the effect-bearing surface) rather than a
#: hand-picked list, so a future method added to the class is covered
#: automatically rather than needing its own round.
_TRUSTED_TRANSPORT_CLASS_MODULE_GLOBALS = _capture_transitive_authority_globals(tuple(
    (value.__globals__, referenced_name)
    for _name, value in _TRUSTED_TRANSPORT_CLASS_ATTRIBUTES
    if inspect.isfunction(value)
    for referenced_name in value.__code__.co_names
    if referenced_name in value.__globals__
) + tuple(
    (module_dict, attr_name)
    for _name, value in _TRUSTED_TRANSPORT_CLASS_ATTRIBUTES
    if inspect.isfunction(value)
    for module_dict, attr_name in _leaf_attribute_roots(value)
))


def _reject_altered_authority_validation_globals() -> None:
    """See `_capture_transitive_authority_globals`'s own module-level
    comment for the round-45/46/47/48 findings this closes. Re-reads
    every trusted name FRESH from its real, live module namespace
    (never a cached reference of our own) and compares identity (plus
    `__code__`/defaults, for entries that are themselves locally-owned
    functions) against what was captured at this module's own import
    time, exactly mirroring `_reject_altered_class_implementation`'s
    own layered check, one axis further out -- looping over the
    transitive closure of both root trust dicts instead of one
    hand-written comparison per name. Each entry's own originating
    module name (`globals_dict["__name__"]`) is used in the error
    message directly, rather than a single label per root dict, since
    the transitive walk now reaches more than one real module from
    each root (`tenfold.facility` AND `tenfold.contracts`, in
    particular). Delegates to the shared `_reject_altered_transitive_globals`
    (round 51), rather than its own independent copy of this same
    loop."""
    for trusted in (_TRUSTED_AUTHORITY_VALIDATION_GLOBALS, _TRUSTED_AUTHORITY_VALIDATION_FACILITY_MODULE_GLOBALS):
        _reject_altered_transitive_globals(trusted)


@dataclass(frozen=True)
class _RepositoryConstructionFacilityIdentity:
    facility_id: str
    facility_generation: int
    adapter_boundary: FacilityAdapterBoundary
    effect_class: str


#: Convenience grouping of the admitted-identity fields `tenfold.gen2.
#: facility` owns (see the imports above) -- built from those constants,
#: never a second, independent source of truth.
ADMITTED_REPOSITORY_CONSTRUCTION_FACILITY_IDENTITY = _RepositoryConstructionFacilityIdentity(
    facility_id=ADMITTED_REPOSITORY_CONSTRUCTION_FACILITY_ID,
    facility_generation=ADMITTED_REPOSITORY_CONSTRUCTION_FACILITY_GENERATION,
    adapter_boundary=FacilityAdapterBoundary.REPOSITORY,
    effect_class=ADMITTED_REPOSITORY_CONSTRUCTION_EFFECT_CLASS,
)


def _neutralize_hooks_for_every_registered_repository(transport: LocalGitRepositoryTransport) -> "dict[str, _EstablishedHooksNeutralization]":
    """Review finding (PR #84, round 8, reproduced-in-principle by the
    reviewer): `build_disposable_local_git_facility` only neutralized
    hooks for the ONE repository it itself freshly creates -- this
    generic wrapper, the advertised reusable G2-28+ entry point, had no
    such protection for a caller-supplied `LocalGitRepositoryTransport`
    registered against a DIFFERENT, possibly pre-existing repository
    (which could already carry a real, malicious/legacy
    `reference-transaction` hook). Genuinely neutralizes hooks (the
    same `core.hooksPath` redirect, real and durable, repo-local git
    config) for EVERY repository the given transport has registered,
    not only a disposable one this module happens to have built.
    `LocalGitRepositoryTransport` exposes no public API for its
    registered-repository roots (by design, matching its own minimal,
    read/mutate-only interface) -- accessing `_repositories` here is a
    deliberate, documented exception, justified by a genuine safety
    requirement with no other real avenue, not mere convenience.

    SYMLINK FINDING (review finding, PR #84, round 9, reproduced by the
    reviewer): the original fixed-name `.git/tenfold-gen2-no-hooks`
    directory used `mkdir(parents=True, exist_ok=True)`, which silently
    FOLLOWS a pre-existing symlink planted at that exact, predictable
    path rather than failing -- if `.git/tenfold-gen2-no-hooks` were
    already a symlink to a directory containing a real
    `reference-transaction` hook, `git config core.hooksPath` would
    point AT that attacker-controlled hook, and the hook WOULD fire,
    defeating the entire neutralization this function exists to
    provide. Fixed by never using a predictable, fixed name at all:
    `tempfile.mkdtemp` under the repository's own real (symlink-
    checked) `.git` directory creates a genuinely fresh,
    unpredictably-named directory every call, so there is no fixed
    path for a pre-planted symlink to occupy; the redirect is then
    applied through `LocalGitRepositoryTransport._run` (real,
    argv-list `subprocess.run`, no shell) rather than a second, ad-hoc
    `subprocess.run` call.

    Returns the `{name: _EstablishedHooksNeutralization}` mapping it
    established, so a caller (see `_hooks_neutralization_still_intact`)
    can later confirm -- CHEAPLY, no subprocess spawn -- that
    neutralization is still in place before paying for a fresh
    `mkdtemp` + `git config` call again."""
    established: dict[str, _EstablishedHooksNeutralization] = {}
    for name, registered in transport._repositories.items():  # noqa: SLF001 -- genuine safety enforcement; see docstring
        repo_root = registered.root
        git_dir = repo_root / ".git"
        if git_dir.is_symlink() or not git_dir.is_dir():
            raise RepositoryConstructionQualificationError(
                f"_neutralize_hooks_for_every_registered_repository: {repo_root} has no real, non-symlink .git directory"
            )
        no_hooks_dir = Path(tempfile.mkdtemp(prefix="tenfold-gen2-no-hooks-", dir=str(git_dir)))
        # Self-caught bug (round 17): a plain `git config
        # core.hooksPath <value>` REFUSES to run at all when the key
        # already has multiple values ("cannot overwrite multiple
        # values with a single value") -- exactly the state a round-15
        # `--add`-based attack leaves behind. `--replace-all` genuinely
        # replaces EVERY existing value with the single trusted one,
        # succeeding regardless of how many stale/malicious entries
        # were already present.
        transport._run(name, "config", "--replace-all", "core.hooksPath", str(no_hooks_dir))  # noqa: SLF001 -- see docstring
        config_path = git_dir / "config"
        established[name] = _EstablishedHooksNeutralization(no_hooks_dir, config_path.read_text(encoding="utf-8", errors="strict"))
    # Review finding (PR #86, round 44, P1, Codex, reproduced by the
    # reviewer -- "Freeze the hook-neutralization snapshot"): round
    # 43 wrapped `instance_state` in `types.MappingProxyType` but left
    # this SIBLING `_AdmittedTransportState` field -- `no_hooks_dirs`
    # -- as a plain, mutable dict. Each individual
    # `_EstablishedHooksNeutralization` record is already
    # `frozen=True`, so its OWN fields can't be reassigned via
    # ordinary syntax -- but the OUTER dict entry can still be
    # REPLACED WHOLESALE (`no_hooks_dirs[name] =
    # _EstablishedHooksNeutralization(unrelated_dir, malicious_config_text)`),
    # a dict-item assignment, never an attribute assignment on the
    # frozen record, so nothing about ITS freeze applies. The reviewer
    # reproduced exactly this against an enumerated, unrelated
    # admission (the same already-disclosed round-34/42 reachability),
    # poisoning `_hooks_neutralization_still_intact`'s own baseline so
    # it accepted an attacker's `core.hooksPath` as unchanged. Wrapped
    # here, at the one place this mapping is ever constructed (used by
    # BOTH the admission-time call site and the per-mutation
    # re-neutralization call site in `_revalidate_transport_integrity`),
    # so every caller gets the same genuinely read-only view.
    return types.MappingProxyType(established)


@dataclass(frozen=True)
class _EstablishedHooksNeutralization:
    no_hooks_dir: Path
    #: The COMPLETE, exact byte content of `.git/config` immediately
    #: after `git config core.hooksPath <no_hooks_dir>` wrote it --
    #: see `_hooks_neutralization_still_intact`'s own docstring for
    #: why exact-content comparison, not substring matching or
    #: git-config-semantics parsing, is what this actually needs.
    config_snapshot: str


def _hooks_neutralization_still_intact(transport: LocalGitRepositoryTransport, established: "dict[str, _EstablishedHooksNeutralization]") -> bool:
    """Performance finding (PR #86, round 14): re-running the full
    `_neutralize_hooks_for_every_registered_repository` (a fresh
    `mkdtemp` plus a real `git config` subprocess spawn, per
    registered repository) before EVERY mutation is genuinely
    expensive -- measured roughly 280x the cost of the containment
    scan alone (subprocess spawn dominates, especially so under this
    platform's own process-creation/AV-scanning overhead) -- and, run
    unconditionally on every mutation across a qualification harness
    making hundreds of them, turned a ~80 second test suite into a
    ~65 minute one. This performs the COMMON-case check for free: read
    `.git/config`'s raw text directly (no subprocess at all) and
    confirm the exact `no_hooks_dir` path `_neutralize_hooks_for_every_registered_repository`
    established is still referenced there, and that the directory
    itself still exists as a real, non-symlinked, EMPTY-of-hooks
    directory. Only when this returns `False` (nothing was tampered
    with) does the caller pay for the expensive full re-neutralization
    again -- preserving the exact same security property (hooks
    genuinely neutralized before every mutation) at a fraction of the
    cost in the overwhelmingly common case where nothing changed
    between mutations.

    SUBSTRING-MATCH FINDING (review finding, PR #86, round 15, P1,
    reproduced independently by both reviewers): the original version
    of this check searched for `no_hooks_dir`'s own path text as a
    SUBSTRING of `.git/config`'s raw content -- which is fooled by
    anything that keeps the trusted text present WITHOUT it being the
    actual EFFECTIVE value git uses. Codex reproduced `git config
    --add core.hooksPath <malicious>` (git's own `--add` APPENDS a
    second `hooksPath` entry rather than replacing the first; git uses
    the LAST one) still containing the original trusted path text,
    while the ACTIVE value became the attacker's. CodeRabbit
    reproduced appending the trusted path as a `# comment` line after
    setting a malicious active value -- also still "present" as a
    substring while never actually being used. Correctly interpreting
    git-config's own semantics (comments, duplicate keys, last-value-
    wins, quoting/escaping) well enough to defend against every such
    trick would mean re-deriving a real INI-with-git's-own-dialect
    parser here -- a correctness-critical undertaking exactly the kind
    this codebase avoids re-deriving (G2-00 SS15). This does something
    provably simpler and stronger instead: it never tries to
    UNDERSTAND the config file's meaning at all. It captures the
    COMPLETE, exact byte content of `.git/config` immediately after
    `_neutralize_hooks_for_every_registered_repository` itself wrote
    it (`_EstablishedHooksNeutralization.config_snapshot`), and now
    requires the CURRENT content to be BYTE-IDENTICAL to that snapshot
    -- ANY change at all (an appended entry, a comment, a reordered
    line, anything) fails the cheap check and forces the genuine,
    expensive re-neutralization. Since identical bytes parse
    identically under git's own (or any) config reader, this is
    airtight against every trick that fools a substring or naive-parse
    check, without this code needing to correctly reimplement git's
    own config grammar at all."""
    for name, registered in transport._repositories.items():  # noqa: SLF001 -- see _neutralize_hooks_for_every_registered_repository's own docstring
        snapshot = established.get(name)
        if snapshot is None:
            return False
        git_dir = registered.root / ".git"
        if git_dir.is_symlink() or not git_dir.is_dir():
            return False
        if snapshot.no_hooks_dir.is_symlink() or not snapshot.no_hooks_dir.is_dir():
            return False
        try:
            if any(snapshot.no_hooks_dir.iterdir()):
                # Something was planted directly inside the neutralized
                # directory itself (e.g. a reference-transaction file)
                # WITHOUT changing core.hooksPath -- the path reference
                # alone is not enough; the directory must also still be
                # genuinely empty.
                return False
        except OSError:
            return False
        config_path = git_dir / "config"
        if config_path.is_symlink() or not config_path.is_file():
            return False
        try:
            current_config_text = config_path.read_text(encoding="utf-8", errors="strict")
        except OSError:
            return False
        if current_config_text != snapshot.config_snapshot:
            return False
    return True


def _find_unsafe_git_storage_entry(root: Path) -> Path | None:
    """Walks `root` with `os.walk(..., followlinks=False)` (never
    descending into a symlinked subdirectory, so this always terminates
    even under a symlink cycle) and returns the first UNSAFE entry
    (file OR directory) found anywhere beneath it, or `None` if none
    exists. `root` itself is checked first, separately, since
    `os.walk` never reports its own starting path.

    DANGLING-SYMLINK ORDERING FINDING (review finding, PR #84, round
    13, Major, CWE-59, reproduced by the reviewer): the original
    version checked `root.exists()` BEFORE `root.is_symlink()` --
    `Path.exists()` follows a symlink and returns `False` for a
    DANGLING one (whose target does not exist yet), so a dangling
    symlink was silently treated as "nothing here" and skipped
    entirely. The reviewer reproduced planting a dangling symlink at
    `.git/config` before registration; a LATER write through it (e.g.
    hook neutralization's own `git config core.hooksPath`) would then
    create the external target file, a genuine escape this check was
    supposed to prevent. `is_symlink()` never follows the link (it
    inspects the directory entry itself via `lstat`, which does not
    require the target to exist), so it is now checked FIRST,
    unconditionally, before any existence check.

    HARD-LINK FINDING (review finding, PR #84, round 13, P1, reproduced
    by the reviewer): symlink detection alone misses a HARD-linked
    file -- `.git/logs/refs/heads/main` hard-linked to an external
    file is not a symlink at all (`is_symlink()` is `False` for it),
    yet writing through EITHER path mutates the SAME underlying data,
    since both names reference the identical inode. The reviewer
    reproduced `commit()`'s own real reflog append landing in the
    external file through such a hard link. Regular files (never
    directories -- hard links to directories are not supported on the
    filesystems this code targets) are now also rejected when their
    real link count exceeds 1, meaning some OTHER directory entry
    genuinely references the same data."""
    if root.is_symlink():
        return root
    if not root.exists():
        return None
    if root.is_file() and root.stat().st_nlink > 1:
        return root
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        base = Path(dirpath)
        for entry_name in dirnames:
            candidate = base / entry_name
            if candidate.is_symlink():
                return candidate
        for entry_name in filenames:
            candidate = base / entry_name
            if candidate.is_symlink():
                return candidate
            if candidate.stat().st_nlink > 1:
                return candidate
    return None


def _reject_symlinked_git_storage_for_every_registered_repository(transport: LocalGitRepositoryTransport) -> None:
    """Review finding (PR #84, round 10, P1, reproduced by the reviewer):
    `LocalGitRepositoryTransport.__init__` only checks that the
    repository ROOT itself is not a symlink -- it never checks whether
    `.git`'s own INTERNAL storage directories are symlinked elsewhere.
    If `.git/objects` were a symlink to a directory outside the
    registered repository root, every blob/tree/commit object
    `commit_files` writes (via `git hash-object -w`) would land at that
    EXTERNAL location instead -- a real, reproduced escape of the
    admitted identity's own local-commit-only EFFECT_REACH boundary
    (writes are supposed to stay within the registered repository, not
    merely within whatever `.git` happens to reference).

    NESTED-SYMLINK FINDING (review finding, PR #84, round 11, P1,
    reproduced independently by two reviewers): checking only whether
    `.git/objects` and `.git/refs` THEMSELVES are symlinks still admits
    a repository with a symlinked DESCENDANT further down -- both
    reviewers reproduced `git update-ref` following a symlinked
    `.git/refs/heads` and `git hash-object -w` following a symlinked
    object fan-out directory (`.git/objects/<2-char-prefix>`), each
    landing the real write outside the registered repository despite
    `.git/objects`/`.git/refs` themselves being genuine, non-symlinked
    directories. `_find_symlink_beneath` now walks the COMPLETE
    `objects` and `refs` subtrees (never following a symlink it finds,
    so a cycle cannot cause unbounded recursion) and rejects admission
    if ANY entry anywhere beneath either one is a symlink, for ANY
    registered repository -- mirroring the same no-symlinks-followed
    discipline `LocalGitRepositoryTransport` itself already applies to
    the repository root.

    METADATA-PATH FINDING (review finding, PR #84, round 12, P1,
    reproduced by the reviewer): `objects` and `refs` are not the only
    Git-internal paths the admitted operations write to. The reviewer
    reproduced `create_branch`'s own real `update-ref` call writing the
    new branch's REFLOG entry through a symlinked `.git/logs/refs/heads`
    into an external directory, and separately showed a symlinked
    `.git/config` would let hook neutralization's own `git config
    core.hooksPath` write land externally too. `logs` (a directory) and
    `config` (a single file) are now scanned the same way -- `logs`
    recursively via `_find_unsafe_git_storage_entry` (which also
    correctly rejects `config` itself being a symlink, its very first
    check, without needing a directory walk).

    See `_find_unsafe_git_storage_entry`'s own docstring for the round
    13 dangling-symlink-ordering and hard-link findings this function
    inherits automatically, since it delegates the actual walk/check
    logic there.

    `.GIT`-ITSELF FINDING (review finding, PR #86, round 14, P1,
    reproduced by the reviewer): every prior round scanned `.git`'s
    OWN internal paths (`objects`/`refs`/`logs`/`config`) but never
    re-checked `.git` itself -- if the ENTIRE `.git` directory were
    replaced with a symlink to an external directory AFTER admission,
    `git_dir / "objects"` etc. resolve INTO that external directory's
    own, ordinary-looking subpaths, and the walk below finds nothing
    to object to there. The reviewer reproduced this scan passing and
    a subsequent `create_branch` writing into the external directory
    through the swapped `.git`. `git_dir` itself is now checked first,
    directly (matching `_neutralize_hooks_for_every_registered_repository`'s
    own existing `git_dir.is_symlink()` guard, which this function had
    never independently carried)."""
    for name, registered in transport._repositories.items():  # noqa: SLF001 -- genuine safety enforcement; see docstring
        git_dir = registered.root / ".git"
        if git_dir.is_symlink():
            raise RepositoryConstructionQualificationError(
                f"_reject_symlinked_git_storage_for_every_registered_repository: "
                f"{name}'s .git directory itself is a symlink, escaping the registered repository root"
            )
        # COMMONDIR FINDING (review finding, PR #86, round 20, P1,
        # Codex, reproduced by the reviewer): git's own repository
        # layout lets `.git/commondir` redirect where the EFFECTIVE
        # objects/refs/logs/hooks storage actually lives (normally used
        # for linked worktrees) -- entirely independent of whether
        # `objects`/`refs`/`logs`/`config` under THIS `.git` are
        # themselves clean. The reviewer reproduced this scan and the
        # hooks-integrity check both passing, followed by a real
        # `create_branch` writing the new ref into the external
        # directory `commondir` pointed at rather than the registered
        # repository's own `.git`. Same "detect presence, don't
        # interpret" philosophy as `_reject_alternate_git_config_sources`
        # -- a genuinely admitted, from-scratch, single-worktree
        # repository has no legitimate reason to carry a `commondir`
        # file at all, so its mere presence is rejected outright rather
        # than resolving what it points at.
        if (git_dir / "commondir").exists():
            raise RepositoryConstructionQualificationError(
                f"_reject_symlinked_git_storage_for_every_registered_repository: "
                f"{name}'s .git directory declares a commondir file -- rejected outright rather than "
                f"resolving the effective common directory it redirects to"
            )
        for internal in ("objects", "refs", "logs", "config"):
            found = _find_unsafe_git_storage_entry(git_dir / internal)
            if found is not None:
                raise RepositoryConstructionQualificationError(
                    f"_reject_symlinked_git_storage_for_every_registered_repository: "
                    f"{name}'s .git/{internal} contains a symlink or hard link ({found}), escaping the registered repository root"
                )
        _reject_alternate_git_config_sources(name, git_dir)


#: Self-caught bug (round 16): a trailing `\b` here would require a
#: WORD boundary immediately after "include" -- but "includeIf" has no
#: such boundary ("e" and "I" are both word characters), so `\binclude\b`
#: silently failed to match `[includeIf "..."]` at all. No trailing
#: boundary is needed: matching the literal prefix "[include" catches
#: both `[include]` and `[includeIf ...]` correctly.
_INCLUDE_SECTION_HEADER = re.compile(r"^\s*\[include", re.MULTILINE | re.IGNORECASE)

#: Case-insensitive substring match, deliberately not a precise parse
#: -- see `_reject_alternate_git_config_sources`'s own docstring for
#: why "detect presence, don't interpret" is the whole point here.
_WORKTREE_CONFIG_MENTION = re.compile(r"worktreeconfig", re.IGNORECASE)


def _reject_alternate_git_config_sources(name: str, git_dir: Path) -> None:
    """Review finding (PR #86, round 16, P1): git's config resolution
    reads `.git/config` -- but also `[include]`/`[includeIf "..."]`
    directives WITHIN it (fixed earlier this round), AND, when
    `extensions.worktreeConfig` is enabled, a SEPARATE
    `.git/config.worktree` file that takes precedence over the local
    `[core]` section for exactly this kind of setting. Round 17,
    reproduced by the reviewer (Git 2.43.0): with
    `extensions.worktreeConfig=true` and a malicious `core.hooksPath`
    in `.git/config.worktree`, `_hooks_neutralization_still_intact`
    still reported the local file's own bytes as unchanged (correctly
    -- they were), while the ACTUAL effective hooksPath came from the
    higher-precedence worktree file entirely outside what
    `.git/config` reveals; re-neutralization only ever rewrote the
    lower-priority local value, never touching the file that actually
    mattered.

    This is genuinely the SAME category of problem as the include
    directive, just a different git mechanism -- and re-deriving git's
    own complete config-resolution engine (every scope, every
    precedence rule, every extension) to correctly interpret each one
    is a losing battle where every fix invites the next variant (G2-00
    SS15's "no re-derivation" principle, and simple pragmatism, both
    argue against it). The philosophy stays the same as round 16: make
    the check robust BY CONSTRUCTION -- detect the mere PRESENCE of a
    mechanism this identity's own disposable, single-worktree,
    from-scratch repositories have no legitimate reason to use, and
    reject it outright, rather than trying to correctly interpret what
    it would resolve to. Rejects if `.git/config.worktree` exists at
    all (regardless of content), OR if `.git/config`'s own text even
    MENTIONS `worktreeConfig` (case-insensitive substring, not a
    precise key/value parse -- deliberately conservative: a
    false-positive rejection here costs nothing for a repository that
    genuinely has no reason to reference it at all)."""
    worktree_config_path = git_dir / "config.worktree"
    if worktree_config_path.exists():
        raise RepositoryConstructionQualificationError(
            f"_reject_alternate_git_config_sources: {name} has a .git/config.worktree file -- "
            f"rejected outright rather than resolving its effective value"
        )
    config_path = git_dir / "config"
    if config_path.is_symlink() or not config_path.is_file():
        return  # handled by the caller's own symlink/hard-link check
    try:
        config_text = config_path.read_text(encoding="utf-8", errors="strict")
    except OSError:
        return
    if _INCLUDE_SECTION_HEADER.search(config_text):
        raise RepositoryConstructionQualificationError(
            f"_reject_alternate_git_config_sources: {name}'s .git/config declares an [include]/[includeIf] section -- "
            f"rejected outright rather than resolving its effective value"
        )
    if _WORKTREE_CONFIG_MENTION.search(config_text):
        raise RepositoryConstructionQualificationError(
            f"_reject_alternate_git_config_sources: {name}'s .git/config mentions worktreeConfig -- "
            f"rejected outright rather than resolving its effective value"
        )


#: Review finding (PR #86, round 37, P1, Codex, reproduced by the
#: reviewer -- "Resolve Git independently of caller-controlled PATH"):
#: round 36's `_reject_untrusted_transport_git_executable` re-resolved
#: `shutil.which("git")` FRESH, at admission time, as its "independent"
#: ground truth -- but `shutil.which` walks `PATH`, itself ordinary,
#: caller-controlled process environment state, no more independent
#: than `transport._git` itself. The reviewer reproduced prepending a
#: shell shim's directory to `PATH` AFTER importing this module but
#: BEFORE constructing the transport: `LocalGitRepositoryTransport.__init__`'s
#: own `shutil.which("git")` call and round 36's validation call both
#: resolve the SAME poisoned `PATH` to the SAME malicious path, so the
#: "independent" check just compared the tampered value against
#: itself and passed.
#:
#: Resolved exactly ONCE, here, at THIS module's own import time --
#: the same trust boundary `_TRUSTED_TRANSPORT_CLASS_ATTRIBUTES` and
#: every other import-time snapshot in this file already rely on: a
#: caller must import this module to reach
#: `gen1_wrap_repository_construction_facility` at all, so `PATH`
#: tampering that happens (as the reviewer's own reproduction does)
#: AFTER import but before construction/admission no longer has any
#: effect on this ALREADY-CAPTURED value -- `_reject_untrusted_transport_git_executable`
#: now compares `transport._git` against THIS constant, never a fresh
#: `shutil.which` call, so a transport constructed under a
#: post-import-poisoned `PATH` resolves to a DIFFERENT `_git` value
#: than this trusted baseline and is correctly rejected. (This does
#: not defend against an attacker who already controls `PATH` BEFORE
#: this module is ever imported -- the same disclosed,
#: construction-time-review trust model `_TRUSTED_TRANSPORT_CLASS_ATTRIBUTES`'s
#: own docstring already names, not a new category of gap.)
_TRUSTED_GIT_EXECUTABLE = (lambda resolved: str(Path(resolved).resolve()) if resolved else None)(shutil.which("git"))
#: Review finding (PR #86, round 38, P1, Codex, reproduced by the
#: reviewer -- "Verify the Git executable rather than only its path"):
#: `_TRUSTED_GIT_EXECUTABLE` closes PATH-resolution tampering (round
#: 37), but pins only the PATHNAME -- when that path resolves to a
#: caller-writable location (a common, ordinary case: a user-local
#: git install, a venv-bundled one, many CI images), a caller can
#: leave `_git`'s STRING value completely untouched while replacing
#: the FILE'S OWN CONTENT at that same path, in place, at any point
#: after import or admission. The reviewer reproduced exactly this:
#: importing and admitting through a real, delegating git shim, then
#: overwriting that SAME file afterward with a side-effecting
#: replacement -- every existing check (pathname pinning, exact-type,
#: instance-value pinning) kept passing, since none of them ever read
#: the file's own bytes, only compared the unchanged path STRING.
#: Hashed here, at THIS module's own import time -- the file's
#: content, not merely its location, becomes part of the trusted
#: baseline every other import-time snapshot in this file already
#: establishes.
_TRUSTED_GIT_EXECUTABLE_DIGEST = sha256(Path(_TRUSTED_GIT_EXECUTABLE).read_bytes()).hexdigest() if _TRUSTED_GIT_EXECUTABLE else None

#: Review finding (PR #86, round 52, P1, Codex, reproduced by the
#: reviewer -- "Pin mutable attributes on captured classes"): the
#: round-51 module-attribute walk only ever checked
#: `inspect.ismodule(candidate)` -- a CLASS captured as an identity-
#: only leaf has the identical exposure, and was skipped entirely
#: (see `_leaf_attribute_roots`'s own ROUND 52 WIDENING docstring
#: section for the mechanism fix itself). The reviewer reproduced
#: `Path.is_symlink = lambda self: False` after admission: `Path`
#: itself was never rebound, so an identity check on `Path` alone
#: would keep passing regardless, while every `git_dir.is_symlink()`
#: containment check in this file's own symlink-escape scanning
#: (`_find_unsafe_git_storage_entry`/
#: `_neutralize_hooks_for_every_registered_repository`, confirmed by
#: self-audit to be the only two of this module's OWN functions that
#: reference `Path` and a containment-check method -- `is_symlink`/
#: `is_dir`/`is_file`/`exists`/`stat` -- together; `_hooks_neutralization_still_intact`/
#: `_reject_alternate_git_config_sources`/
#: `_reject_symlinked_git_storage_for_every_registered_repository`
#: also call these same methods on `Path` INSTANCES, but never
#: reference the `Path` CLASS directly themselves -- pinning `Path`'s
#: own attributes via the two functions that DO is sufficient, since
#: `Path.is_symlink` is a single, shared, class-level attribute
#: regardless of which call site resolves it) resolves the tampered
#: method the moment it runs, letting a symlinked `.git/refs/heads`
#: escape detection during a fully authorized `create_branch`.
#: Fixed the SAME way `_TRUSTED_TRANSPORT_CLASS_MODULE_GLOBALS`
#: covers the transport's own methods: seeded from these two
#: Gen2-owned containment functions' own module-level references
#: (their names are genuine globals in THIS module's own namespace,
#: exactly like any other root used elsewhere in this file), reusing
#: `_capture_transitive_authority_globals` directly -- which, since
#: these two functions are themselves `_tenfold_owned_function`-owned,
#: ALSO pins their own identity/code/defaults, the same protection
#: every other root in this file's trust dicts already receives.
_TRUSTED_CONTAINMENT_SCAN_MODULE_GLOBALS = _capture_transitive_authority_globals(tuple(
    (globals(), name)
    for name in ("_find_unsafe_git_storage_entry", "_neutralize_hooks_for_every_registered_repository")
))


def _reject_untrusted_transport_git_executable(transport: LocalGitRepositoryTransport) -> None:
    """See `_TRUSTED_GIT_EXECUTABLE`/`_TRUSTED_GIT_EXECUTABLE_DIGEST`'s
    own module-level comments for the round-36/37/38 findings this
    closes. `LocalGitRepositoryTransport.__init__` itself only ever
    resolves `_git` two ways: an explicit `git_executable` constructor
    argument (confirmed, by a full-codebase search, never used
    anywhere in this repository -- there is no legitimate scenario
    today that needs it), or `shutil.which("git")` resolved to an
    absolute path -- so, unlike `_author_name`/`_author_email`
    (free-form strings with no independently-derivable "correct"
    value) or `_repositories` (legitimately varies per admission,
    supplied by the caller), `_git` DOES have a genuine, PATH- and
    content-independent ground truth this function checks against.
    Called both at admission AND on every per-mutation revalidation
    (`_revalidate_transport_integrity`, not merely once at admission)
    -- a pathname-only check would need only one pass, but a
    CONTENT check must be repeated every time, since the file at a
    caller-writable path can be replaced again at any later moment;
    re-hashing here narrows that residual window to the same
    TOCTOU-class, disclosed-and-accepted race round 14 already
    established, rather than leaving it open indefinitely."""
    current_git = transport._git  # noqa: SLF001 -- genuine safety enforcement, mirrors _reject_altered_transport_instance_state's own established pattern
    # Round 28's exact-type lesson, replayed here: an attacker-controlled
    # `str` subclass with a lying `__eq__`/`__ne__` could otherwise claim
    # equality with the expected value while holding different content.
    if type(current_git) is not str:
        raise RepositoryConstructionQualificationError(
            f"_reject_untrusted_transport_git_executable: transport._git is not a plain str "
            f"(got {type(current_git).__name__}) -- refusing to trust it as this admission's baseline"
        )
    if _TRUSTED_GIT_EXECUTABLE is None or current_git != _TRUSTED_GIT_EXECUTABLE:
        raise RepositoryConstructionQualificationError(
            f"_reject_untrusted_transport_git_executable: transport._git ({current_git!r}) does not match "
            f"the git executable resolved at this module's own import time ({_TRUSTED_GIT_EXECUTABLE!r}) -- "
            f"refusing to trust it as this admission's baseline"
        )
    try:
        current_digest = sha256(Path(current_git).read_bytes()).hexdigest()
    except OSError as exc:
        raise RepositoryConstructionQualificationError(
            f"_reject_untrusted_transport_git_executable: could not read transport._git ({current_git!r}) "
            f"to verify its content ({exc}) -- refusing to trust it as this admission's baseline"
        ) from exc
    if _TRUSTED_GIT_EXECUTABLE_DIGEST is None or current_digest != _TRUSTED_GIT_EXECUTABLE_DIGEST:
        raise RepositoryConstructionQualificationError(
            f"_reject_untrusted_transport_git_executable: the file at transport._git ({current_git!r}) no "
            f"longer matches the content hashed at this module's own import time -- the executable has been "
            f"replaced in place, refusing to trust it as this admission's baseline"
        )


#: Review finding (PR #86, round 36, P1, Codex, reproduced by the
#: reviewer -- "Seal caller-retained collaborators before mutation"):
#: round 29 pinned `facility.authority_store` by IDENTITY (rejecting a
#: SWAPPED reference) and round 32 denied delegating it through the
#: wrapper at all (rejecting a caller who only holds the wrapper from
#: ever reaching it) -- but neither addresses a caller who never
#: needed the wrapper to reach `authority_store` in the first place:
#: whoever called `gen1_wrap_repository_construction_facility` genuinely
#: constructed this object and, by the ordinary rules of passing a
#: mutable Python object as an argument, still holds their OWN
#: reference to it after this function returns. The reviewer
#: reproduced reassigning THAT retained reference's `read` method
#: in place (`rig.authority_store.read = malicious_fn`) -- since the
#: object's IDENTITY never changed, round 29's `is` check kept
#: passing, while `RepositoryFacility._live_mutable`'s real call to
#: `self.authority_store.read(...)` (via Gen1's own `validate_live_task`)
#: invoked the malicious replacement mid-`create_branch`, moving
#: `.git/refs/heads` externally and installing a symlink before the
#: actual git mutation, with an authorized `create_branch` still
#: returning a successful receipt -- a deterministic sibling of the
#: round-29 finding, reached without ever touching the wrapper at all.
#:
#: Unlike round 27/34's genuinely unfixable "any code holding ANY
#: object this module produced can reach anything reachable from it"
#: limitation, this one has a real, complete fix: a Python bound
#: method captures its underlying function AT THE MOMENT it is read
#: off an instance (`bound = obj.method`) -- reassigning an attribute
#: on the ORIGINAL object afterward (`obj.method = malicious_fn`) has
#: ZERO effect on an already-captured bound method, since the
#: reassignment only changes what a FUTURE `obj.method` lookup would
#: return, not what the already-created `MethodType` object refers
#: to. `RepositoryFacility` is now handed a proxy that captures
#: `authority_store.read` at THIS admission, and only ever calls that
#: captured, tamper-immune reference -- never `self.authority_store`
#: freshly looked up, which is what let the caller's later mutation
#: reach Gen1's real dispatch in the first place. The proxy is never
#: returned to any caller (it lives only as `RepositoryFacility`'s own
#: `.authority_store` instance attribute, and the wrapper's
#: `__getattr__` already denies delegating that name at all -- round
#: 32), so nothing external ever gets a chance to tamper with the
#: proxy itself.
#:
#: ROUND 36->38 REVERSAL: `state_store` was ORIGINALLY left
#: deliberately unsealed here, reasoning that
#: `RepositoryConstructionPropertyQualificationHarness`'s own
#: legitimate `put_receipt` crash-simulation pattern needed a mutable
#: `state`. Round 38, P1, Codex, reproduced by the reviewer -- "Seal
#: the caller-retained state store" -- proved that reasoning
#: insufficient: `state.claim_writer`/`state.receipt` (methods the
#: harness never touches) are EQUALLY reachable via a caller-retained
#: reference, and `RepositoryFacility.create_branch` calls
#: `self.state.claim_writer(...)` in the SAME post-containment-scan,
#: pre-git-mutation window `self.authority_store.read(...)` (round 36)
#: already demonstrated. The reviewer reproduced replacing
#: `claim_writer` with a callback planting an external symlink,
#: exactly the round-29/36 pattern replayed for a THIRD collaborator
#: method. `state` is now sealed identically to `authority_store` --
#: see `_STATE_STORE_CAPTURED_METHODS` below -- and the harness's own
#: crash-simulation need is met through `_SealedCollaboratorProxy`'s
#: own `_inject_fault_for_qualification_harness`, an explicit,
#: narrowly-scoped seam reachable ONLY via `_admitted_state_for`'s
#: module-private registry lookup (the SAME trust boundary this
#: module's own internal code already relies on everywhere else, not
#: a new, general-purpose unsealing mechanism) -- never by directly
#: reassigning an attribute on the caller-retained original object,
#: which is precisely the pattern this fix closes.
_AUTHORITY_STORE_CAPTURED_METHODS = ("read",)
#: See the ROUND 36->38 REVERSAL comment above. `RepositoryFacility`
#: itself only ever calls five of these methods on `self.state`
#: (confirmed by grep against `src/tenfold/repository_facility.py`):
#: `receipt`/`put_receipt` (idempotency bookkeeping), `acquire_writer`/
#: `release_writer` (the wrapper's own allowlisted delegated methods),
#: and `claim_writer` (the reviewer's own reproduction target).
#: `writer` is ALSO captured, even though `RepositoryFacility` never
#: calls it itself -- this module's own property-qualification harness
#: legitimately calls it, via the SAME `_admitted_state_for` registry
#: access every other module-internal read in this file already uses,
#: to independently confirm real, durable writer-lock state (not to
#: dispatch through Gen1's own authority checks).
#:
#: ROUND 48 WIDENING (P1, Codex, reproduced by the reviewer -- "Seal
#: transitive state-store method lookups"): capturing `claim_writer`
#: (and the rest) pins THAT method's own identity/code -- but every
#: one of `RepositoryStateStore`'s captured methods internally calls
#: `self._connect()`, an ORDINARY instance-attribute lookup on the
#: SAME caller-retained `state_store` object our captured bound
#: methods' `__self__` still points at. Round 36/38's own fix only
#: ever protected against the CALLER reassigning one of the CAPTURED
#: names on that object (`state_store.claim_writer = ...`) -- it says
#: nothing about the caller instead giving that object a NEW instance
#: attribute for a name a captured method relies on internally
#: (`state_store._connect = ...`), which Python's ordinary attribute
#: resolution (instance `__dict__` checked before the class) will
#: happily let shadow the real class method the next time OUR
#: captured `claim_writer` executes `self._connect()` -- the SAME
#: "pinning a function's own identity does not protect what it calls"
#: lesson already applied to module globals (rounds 45-47), now
#: applied to a caller-retained COLLABORATOR INSTANCE's own attribute
#: namespace instead of a module's. The reviewer reproduced exactly
#: this: assign a malicious `_connect` on the retained `state_store`
#: after admission, then watch an authorized `create_branch` pass
#: every existing revalidation, invoke the callback post-containment-
#: scan, and write the branch ref externally.
#:
#: Fixed generally (see `_capture_collaborator_relied_upon_attributes`'s
#: own docstring): every captured method's OWN code is walked for
#: further `self.<name>()`-shaped calls, transitively, and
#: `_SealedCollaboratorProxy.__getattr__` now also rejects any access
#: once the retained source object's OWN instance `__dict__` has
#: gained an entry for any name a captured method relies on
#: internally -- not merely re-verifying the captured names
#: themselves, the same widening in kind as the globals-closure fix.
#:
#: ROUND 49 WIDENING (P1, Codex, reproduced by the reviewer -- "Pin
#: transitive collaborator class methods"): the round-48 fix above
#: only ever checked the INSTANCE `__dict__` for a shadowing entry --
#: it never revalidated the CLASS-level binding of a transitively-
#: relied-upon name at all. The reviewer reproduced rebinding
#: `RepositoryStateStore._connect` directly on the CLASS (not the
#: instance): no instance shadow exists, so round 48's own check found
#: nothing wrong, while the already-captured, code-pinned
#: `claim_writer` still resolved `self._connect` fresh on every call
#: -- straight to the tampered class attribute. Fixed by ALSO
#: capturing each transitively-relied-upon name's own
#: identity/`__code__`/defaults, read directly off the class at
#: construction time, and revalidating the CURRENT class-level binding
#: against that capture on every access -- exactly mirroring how the
#: top-level captured names are already protected, one level further
#: out. This is the SAME "one level deeper" lesson recurring for a
#: SIXTH time, now within this closure's own OWN round-48 fix itself
#: -- a standing reminder that a transitive-closure mechanism must
#: cover every axis a captured entity can be tampered through (here:
#: both the instance's own attributes AND the class's), not just the
#: first one a reviewer happens to demonstrate.
#:
#: ROUND 50 WIDENING (P1, Codex, reproduced by the reviewer -- "Pin
#: collaborator methods' module dependencies"): rounds 48/49 together
#: cover the instance and class AXES for a transitively-relied-upon
#: name, but a relied-upon method's own body can ALSO reference an
#: ordinary MODULE-level global -- `RepositoryStateStore._connect`
#: calls `sqlite3.connect(...)`, where `sqlite3` is resolved via
#: `_connect.__globals__`, a THIRD namespace entirely, distinct from
#: both the instance and the class. The reviewer reproduced rebinding
#: `tenfold.repository_facility.sqlite3` itself: `_connect` remains
#: byte-for-byte untouched, so rounds 48/49's own checks find nothing
#: wrong, while `_connect`'s own body resolves the tampered name the
#: moment it runs -- the SEVENTH recurrence of "pinning a function's
#: own identity does not protect what it calls," and confirmation
#: that a transitive-closure mechanism protecting a caller-retained
#: OBJECT needs the SAME module-globals coverage this file's own
#: `_capture_transitive_authority_globals` already gives
#: `RepositoryFacility`'s authority-validation call chain. Fixed by
#: reusing that EXACT mechanism rather than a third, independently
#: maintained walk: `_capture_collaborator_relied_upon_attributes` now
#: also collects every module-global name a relied-upon method's code
#: references and hands it to `_capture_transitive_authority_globals`
#: directly, verified via the SAME shared
#: `_transitive_global_entry_matches` helper
#: `_reject_altered_authority_validation_globals` uses.
_STATE_STORE_CAPTURED_METHODS = ("receipt", "put_receipt", "acquire_writer", "release_writer", "claim_writer", "writer")

#: Review finding (PR #86, round 51, P1, Codex, reproduced by the
#: reviewer -- "Pin the admitted state store's storage identity"):
#: rounds 48-50 together seal every axis a captured METHOD can be
#: tampered through (instance shadow, class rebind, module-global
#: rebind) -- but `RepositoryStateStore.path`, an ordinary DATA
#: attribute set once in `__init__` and never reassigned by any of
#: this class's own methods, was never checked at all. `path`
#: determines which physical durable SQLite file every captured
#: method actually reads and writes -- reassigning it after admission
#: silently redirects the ENTIRE writer-ownership ledger to a
#: different backing store, with every method/class/module identity
#: check still passing (nothing about `path` itself is a method,
#: class attribute, or module global). The reviewer reproduced
#: acquiring a branch writer as one owner, reassigning
#: `state_store.path` to a second, independently-initialized
#: database, then acquiring the SAME branch as a second owner through
#: the wrapper -- the mutable-writer ownership record was silently
#: bypassed, since the second acquisition read/wrote an entirely
#: different, empty ledger.
#:
#: Fixed via a NEW, narrower mechanism (see
#: `_SealedCollaboratorProxy`'s own `immutable_data_attributes`
#: parameter) rather than widening any of the method-focused ones
#: above: an EXPLICIT, curated allowlist of data-attribute names
#: (mirroring how `_STATE_STORE_CAPTURED_METHODS` itself is curated,
#: not a blanket "pin every instance attribute" default) -- a blanket
#: default would incorrectly reject `_MutableAuthorityStore`'s own
#: `.snapshot` reassignment, a genuine, load-bearing capability this
#: module's own qualification harness relies on to simulate campaign
#: progression between scenarios (see
#: `RepositoryConstructionPropertyQualificationHarness`), so ONLY
#: `state_store`'s `path` -- confirmed, via this same class's own
#: source, to never be legitimately reassigned after construction --
#: is pinned; `authority_store`'s own proxy construction passes none.
_STATE_STORE_IMMUTABLE_DATA_ATTRIBUTES = ("path",)


#: Review finding (PR #86, round 41 -- an independently-launched
#: adversarial re-review, run because Codex's review quota was
#: exhausted again for this round, filling the same role with the
#: same "real repro or it doesn't count" discipline): `_captured`/
#: `_captured_code` (round 36/40) were declared `__slots__` members --
#: ordinary, directly-named instance attributes. `getattr(proxy,
#: "_captured")` resolves via the slot descriptor and NEVER reaches
#: `__getattr__` at all (`__getattr__` only fires when normal
#: attribute lookup FAILS), so the round-40 code-pinning check --
#: which lives inside `__getattr__` -- never ran for direct access to
#: the backing dict itself. The reviewer reproduced `proxy._captured`
#: returning the real dict, then mutating an entry in place
#: (`proxy._captured["read"] = other_bound_method`) -- since this is a
#: `dict.__setitem__` call, not an attribute-set on the PROXY, the
#: proxy's own `__setattr__` override (which only intercepts
#: assignment on `self`) never fires either. This is the SAME lesson
#: round 31 already learned for the OUTER wrapper
#: (`_ContainmentReCheckedRepositoryFacility`): a `__getattr__`-based
#: allowlist is only as sealed as the set of REAL instance attributes
#: is empty -- any genuinely-declared attribute, however named, is
#: reachable by ordinary `getattr`/`.` access regardless of what
#: `__getattr__` does, since `__getattr__` is a fallback, never an
#: interception point for existing attributes. Round 31's fix for the
#: wrapper was moving ALL state into the module-private,
#: wrapper-keyed `_ADMITTED_TRANSPORT_STATE` registry so the wrapper
#: itself carries NO instance attribute beyond `__weakref__`. Applied
#: here identically: `_SealedCollaboratorProxy` now carries NO
#: instance attribute beyond `__weakref__` either -- the captured
#: callables/code objects live only in this module-private,
#: proxy-keyed registry, populated by `__init__` AFTER `self` exists.
#: Reaching this registry at all still requires the SAME already-
#: disclosed round-34 `sys.modules`-introspection boundary every other
#: module-private name in this file already accepts -- this fix closes
#: the TRIVIAL, one-line `proxy._captured` access, not that
#: underlying, structurally unfixable reachability fact. Round 42 (see
#: `_AdmittedTransportState`'s own docstring for the full account)
#: further demonstrated that a single, process-global registry like
#: this one is ENUMERABLE, not merely look-up-able by one's own key --
#: reaching it via ANY admission grants enumeration of EVERY live
#: proxy's captured state, including one belonging to an unrelated
#: caller. `_SealedCollaboratorProxy._inject_fault_for_qualification_harness`'s
#: own docstring documents this consequence for this specific
#: registry; not a new reachability fact, but a stronger, previously
#: undemonstrated one.
_SEALED_PROXY_CAPTURED_STATE: "weakref.WeakKeyDictionary[_SealedCollaboratorProxy, tuple[dict, dict, object, dict, dict, dict]]" = weakref.WeakKeyDictionary()
#: Sentinel for `_SealedCollaboratorProxy.__getattr__`'s own
#: `immutable_data_attributes` check (round 51): `getattr(source,
#: attr_name, ...)` needs a default distinguishable from any REAL
#: attribute value (including `None`) for the case where the
#: attribute was deleted entirely after admission -- a plain module-
#: level `object()` can never legitimately equal, nor share the exact
#: type of, any value this file itself ever captures.
_SEALED_PROXY_MISSING_DATA_ATTRIBUTE = object()


def _capture_collaborator_relied_upon_attributes(source_cls: type, method_names: tuple[str, ...]) -> tuple[dict, dict]:
    """See `_STATE_STORE_CAPTURED_METHODS`'s own module-level ROUND 48
    WIDENING comment for the finding this closes. Starting from the
    names `_SealedCollaboratorProxy` was asked to capture, walks each
    one's OWN `__code__.co_names` for further names that resolve to a
    plain function defined on `source_cls` -- a `self.<name>()`-shaped
    call candidate -- and recurses into those transitively, exactly
    the same transitive-closure technique
    `_capture_transitive_authority_globals`'s own module-level globals
    walk uses (see that name's own module-level comment), applied here
    to a class's own attribute namespace instead of a module's
    `__globals__`. `inspect.getattr_static` is used throughout so this
    walk never triggers a descriptor, property, or `__getattr__` of
    its own -- a purely structural read, invoking none of the
    (potentially attacker-influenced) code it is inspecting, the same
    discipline this file applies everywhere it inspects untrusted
    objects. Bounded the same way the globals walk is bounded: a
    referenced name that is NOT itself a plain function defined on
    this class (a stdlib collaborator method, a builtin, an instance
    attribute set only in `__init__`, ...) is not a further recursion
    candidate -- there is no natural stopping point short of the
    standard library itself, the same line this file's own DISCLOSED
    SCOPE sections already draw elsewhere.

    ROUND 49 WIDENING (P1, Codex, reproduced by the reviewer -- "Pin
    transitive collaborator class methods"): the round-48 version of
    this function returned only a set of NAMES, and
    `_SealedCollaboratorProxy` used it solely to check whether
    `source`'s own INSTANCE `__dict__` had gained a shadowing entry --
    it never verified the CLASS-level binding itself. The reviewer
    reproduced rebinding `RepositoryStateStore._connect` directly on
    the CLASS (not the instance): `vars(source)` shows nothing
    (there's no instance-level shadow at all), while the already-
    captured, code-pinned `claim_writer` still resolves `self._connect`
    fresh on every call -- straight to the tampered class attribute.
    This function now ALSO captures each relied-upon name's
    `(value, __code__, defaults snapshot)`, read off the class at THIS
    proxy's own construction time -- returned in the FIRST dict, keyed
    by name, so `_SealedCollaboratorProxy` can revalidate the CURRENT
    class-level binding's identity/code/defaults on every access,
    exactly mirroring how the top-level captured names are already
    protected via `captured_code`, one level further out.

    ROUND 50 WIDENING (P1, Codex, reproduced by the reviewer -- "Pin
    collaborator methods' module dependencies"): rounds 48/49 together
    protect a relied-upon method against being shadowed on the
    instance OR rebound on the class -- but say nothing about a NAME
    THAT METHOD ITSELF references at MODULE scope. `RepositoryStateStore
    ._connect` calls `sqlite3.connect(...)`, where `sqlite3` is an
    ordinary module-level global in `tenfold.repository_facility`
    (`import sqlite3`), resolved via `_connect.__globals__` -- a
    COMPLETELY different namespace than either the instance or the
    class. The reviewer reproduced rebinding
    `tenfold.repository_facility.sqlite3` to a module-like object
    whose `connect` plants an external symlink: `_connect` itself
    (identity, code, defaults) is untouched, so rounds 48/49's own
    checks find nothing wrong, while `_connect`'s own body resolves
    the tampered `sqlite3` name the moment it runs. This is the exact
    module-globals problem `_capture_transitive_authority_globals`
    already solves for `RepositoryFacility`'s own authority-validation
    call chain -- so rather than re-implementing it, THIS function now
    also collects every module-global name each relied-upon method's
    `__code__.co_names` references (that resolves in that method's OWN
    `__globals__`) as an additional root, and hands the complete set
    to `_capture_transitive_authority_globals` itself -- returned as
    the SECOND dict, in the exact shape that function already
    produces, so `_SealedCollaboratorProxy` can revalidate it with the
    SAME shared `_transitive_global_entry_matches` helper
    `_reject_altered_authority_validation_globals` uses, rather than a
    third independently-maintained copy of that check.

    ROUND 51 WIDENING (P1, Codex, reproduced by the reviewer --
    "Snapshot mutable attributes of captured modules"): the round-50
    fix above pins a module like `sqlite3` by IDENTITY -- but that
    says nothing about whether one of THAT module's OWN attributes
    (`sqlite3.connect`) was mutated in place afterward, with the
    module reference itself untouched. Fixed by ALSO collecting
    `_leaf_attribute_roots(func)` for each relied-upon method, the
    exact same helper `_capture_transitive_authority_globals`'s own
    internal walk now uses for the identical reason.

    Deliberately EXCLUDES `method_names` themselves from the returned
    per-class-method dict (though they are still walked, to discover
    what THEY call): those top-level names are already fully protected
    by `_SealedCollaboratorProxy`'s own bound-method capture and
    `__func__.__code__` pin (rounds 36/40) -- calling the already-
    captured bound method never re-resolves `source.<name>` again, so
    neither an instance-level shadow nor a class-level rebind of one of
    THOSE specific names (exactly what rounds 36/38's own regression
    tests deliberately reproduce, as the now-safe case those fixes
    close) is itself tampering. Only a name discovered ONE STEP OR
    MORE beyond the roots is a genuine instance of the round-48/49/50
    gap, since those are resolved fresh, on `self` or on the method's
    own module namespace, every time a captured method actually runs."""
    relied_upon_methods: dict = {}
    global_roots: dict = {}
    stack = list(method_names)
    seen: set = set()
    while stack:
        name = stack.pop()
        if name in seen:
            continue
        seen.add(name)
        func = inspect.getattr_static(source_cls, name, None)
        if not inspect.isfunction(func):
            continue
        relied_upon_methods[name] = (func, func.__code__, _function_defaults_snapshot(func))
        for referenced_name in func.__code__.co_names:
            if referenced_name not in seen:
                candidate = inspect.getattr_static(source_cls, referenced_name, None)
                if inspect.isfunction(candidate):
                    stack.append(referenced_name)
            if referenced_name in func.__globals__:
                global_roots[(id(func.__globals__), referenced_name)] = (func.__globals__, referenced_name)
        for module_dict, attr_name in _leaf_attribute_roots(func):
            global_roots[(id(module_dict), attr_name)] = (module_dict, attr_name)
    for name in method_names:
        relied_upon_methods.pop(name, None)
    relied_upon_globals = _capture_transitive_authority_globals(tuple(global_roots.values()))
    # Round 54/55 (see `_TRUSTED_TRANSPORT_CLASS_ATTRIBUTES`'s own
    # module-level ROUND 54/55 WIDENING comments): this dict is ALSO a
    # trust baseline (`_SealedCollaboratorProxy.__getattr__` compares
    # against it on every access), so it gets the same intrinsically-
    # immutable treatment as every other one in this file, for the
    # identical reason -- `relied_upon_globals` is already immutable,
    # since `_capture_transitive_authority_globals` itself now returns
    # one.
    return _immutable_snapshot(relied_upon_methods), relied_upon_globals


class _SealedCollaboratorProxy:
    """See `_AUTHORITY_STORE_CAPTURED_METHODS`'s own module-level
    comment for the round-36 finding this closes. Captures the exact
    bound methods named in `method_names`, read off `source` at
    construction time, and exposes ONLY those -- never `source`
    itself, never any other attribute. Immutable after construction
    (`__setattr__` always raises); `__slots__` carries no writable
    surface at all beyond `__weakref__` -- see
    `_SEALED_PROXY_CAPTURED_STATE`'s own module-level comment for why
    the captured collections themselves live in a module-private
    registry rather than as named instance attributes.

    SECOND-LAYER FIX (review finding, PR #86, round 40, P1, Codex,
    reproduced by the reviewer -- "Snapshot collaborator code objects
    before delegation"): capturing a BOUND METHOD (`bound =
    getattr(source, name)`) is immune to the caller's retained
    reference being REASSIGNED (`source.method = malicious_fn` only
    shadows the descriptor for FUTURE lookups on that instance,
    leaving an already-captured bound method's `__func__` pointing at
    the original class function -- round 36's own reasoning). It is
    NOT immune to that SAME underlying function object having its OWN
    `__code__` mutated in place: `bound.__func__` -- the unbound
    function actually stored on the collaborator's CLASS, not a
    per-instance copy -- is SHARED by every bound method obtained from
    every instance of that class, including this proxy's own captured
    one. The reviewer reproduced
    `state_store.claim_writer.__func__.__code__ = malicious.__code__`
    on the caller's retained reference: since `state_store.claim_writer.__func__`
    IS `type(state_store).claim_writer`, the SAME object this proxy's
    captured bound method also delegates through, the mutation reached
    a fully-authorized `create_branch` mid-dispatch, exactly the
    round-14/29/36/38 deterministic-TOCTOU pattern, this time inside
    the very mechanism (round 36's sealing) built to close it.

    Fixed the SAME way round 37 closed the identical exposure for
    `LocalGitRepositoryTransport`/`RepositoryFacility`: each captured
    bound method's `__func__.__code__` is separately pinned, at THIS
    proxy's own construction time, into a second captured-code mapping
    -- a later `func.__code__ = other` reassignment cannot
    retroactively change what that separately-held reference points
    to. `__getattr__` re-verifies the CURRENT `__func__.__code__`
    against the pinned reference on EVERY access (not merely once at
    construction), since Gen1's own dispatch always reaches this proxy
    via a fresh `self.state.claim_writer(...)`-style attribute lookup
    each call -- matching round 38's "a content check must be repeated
    every time" lesson, now for code-object identity rather than file
    content.

    THIRD-LAYER FIX (review finding, PR #86, round 48, P1, Codex,
    reproduced by the reviewer -- "Seal transitive state-store method
    lookups"; see `_capture_collaborator_relied_upon_attributes`'s own
    docstring and `_STATE_STORE_CAPTURED_METHODS`'s own ROUND 48
    WIDENING comment for the full account): rounds 36/40 protect the
    CAPTURED names themselves against reassignment/in-place code
    mutation, but every captured method still executes with `self`
    bound to the ORIGINAL, caller-retained `source` object -- and any
    OTHER name that method calls via ordinary `self.<name>()` is
    resolved FRESH, on the live `source` instance, every time it
    executes; nothing captured at construction protects that lookup.
    The reviewer reproduced giving the retained `source` a NEW
    instance attribute for a name `claim_writer` relies on internally
    (`_connect`), shadowing the real class method the next time our
    already-captured, code-pinned `claim_writer` ran.

    FOURTH-LAYER FIX (review finding, PR #86, round 49, P1, Codex,
    reproduced by the reviewer -- "Pin transitive collaborator class
    methods"): the round-48 fix above only ever checked `source`'s own
    INSTANCE `__dict__` for a shadowing entry -- it never revalidated
    the CLASS-level binding of a transitively-relied-upon name at all.
    The reviewer reproduced rebinding `RepositoryStateStore._connect`
    on the CLASS itself: no instance shadow exists, so the round-48
    check found nothing wrong, while the already-captured, code-pinned
    `claim_writer` still resolved `self._connect` fresh on every call
    -- straight to the tampered class attribute. Fixed by ALSO
    capturing, once at construction, each transitively-relied-upon
    name's `(value, __code__, defaults snapshot)` read directly off
    the class (see `_capture_collaborator_relied_upon_attributes`'s
    own docstring), and revalidating the CURRENT class-level binding's
    identity/code/defaults on every access -- exactly mirroring how
    the top-level captured names are already protected via
    `captured_code`, one level further out.

    FIFTH-LAYER FIX (review finding, PR #86, round 50, P1, Codex,
    reproduced by the reviewer -- "Pin collaborator methods' module
    dependencies"; see `_capture_collaborator_relied_upon_attributes`'s
    own ROUND 50 WIDENING docstring section for the full account):
    rounds 48/49 together protect a relied-upon method against being
    shadowed on the instance or rebound on the class, but a method's
    OWN body can also reference an ordinary MODULE-level global
    (`RepositoryStateStore._connect` calls `sqlite3.connect(...)`,
    where `sqlite3` is resolved via `_connect.__globals__` -- a
    completely different namespace than either the instance or the
    class). The reviewer reproduced rebinding
    `tenfold.repository_facility.sqlite3` itself: `_connect` remains
    byte-for-byte untouched, so rounds 48/49's own checks find nothing
    wrong, while `_connect`'s own body resolves the tampered name the
    moment it runs. Fixed by ALSO capturing the transitive closure of
    every module-global name a relied-upon method's code references --
    reusing `_capture_transitive_authority_globals` itself (the exact
    module-globals mechanism the `RepositoryFacility` authority-
    validation chain already uses) rather than a third, independently
    maintained walk -- and revalidating it on every access with the
    SAME shared `_transitive_global_entry_matches` helper
    `_reject_altered_authority_validation_globals` uses. All three
    checks (instance shadow, class rebind, module-global rebind) are
    checked fresh on every access, the same "repeat the check every
    time" discipline as the top-level code-object pin.

    SIXTH-LAYER FIX (review finding, PR #86, round 51, P1, Codex,
    reproduced by the reviewer -- "Pin the admitted state store's
    storage identity"; see `_STATE_STORE_IMMUTABLE_DATA_ATTRIBUTES`'s
    own module-level comment for the full account): every fix above
    seals a captured METHOD's own tampering surface -- none of them
    say anything about an ordinary DATA attribute the collaborator
    holds. `RepositoryStateStore.path` determines which physical
    durable file every captured method reads/writes; reassigning it
    is neither a method shadow, a class rebind, nor a module-global
    rebind, so nothing above catches it. Fixed via a new, EXPLICITLY
    curated `immutable_data_attributes` parameter (deliberately NOT a
    blanket "pin every instance attribute" default -- see
    `_STATE_STORE_IMMUTABLE_DATA_ATTRIBUTES`'s own comment for why a
    blanket default would break `_MutableAuthorityStore`'s own
    legitimate `.snapshot` reassignment): each named attribute's exact
    type and value are captured once at construction, and revalidated
    -- type first, matching round 28's exact-type-before-`==`
    discipline used throughout this file -- on every access."""

    __slots__ = ("__weakref__",)

    def __init__(self, source: object, method_names: tuple[str, ...], label: str, immutable_data_attributes: tuple[str, ...] = ()) -> None:
        captured = {}
        captured_code = {}
        for name in method_names:
            bound = getattr(source, name)
            if not callable(bound):
                raise RepositoryConstructionQualificationError(
                    f"_SealedCollaboratorProxy: {label}.{name} is not callable -- refusing to admit"
                )
            captured[name] = bound
            func = getattr(bound, "__func__", None)
            if func is not None:
                captured_code[name] = func.__code__
        relied_upon_methods, relied_upon_globals = _capture_collaborator_relied_upon_attributes(type(source), method_names)
        data_snapshot = {attr_name: (type(getattr(source, attr_name)), getattr(source, attr_name)) for attr_name in immutable_data_attributes}
        # Round 54/55 (see `_TRUSTED_TRANSPORT_CLASS_ATTRIBUTES`'s own
        # module-level ROUND 54/55 WIDENING comments): `data_snapshot`
        # is ALSO a trust baseline `__getattr__` compares live state
        # against on every access, and (unlike `captured`/
        # `captured_code`) is NEVER legitimately mutated after
        # construction -- `_inject_fault_for_qualification_harness`'s
        # own sanctioned escape hatch only ever writes to `captured`/
        # `captured_code`, so ONLY this one gets the intrinsically-
        # immutable treatment here; the other two must stay genuinely
        # mutable for that harness to keep working.
        _SEALED_PROXY_CAPTURED_STATE[self] = (captured, captured_code, source, relied_upon_methods, relied_upon_globals, _immutable_snapshot(data_snapshot))

    def __getattr__(self, name):
        captured, captured_code, source, relied_upon_methods, relied_upon_globals, data_snapshot = _SEALED_PROXY_CAPTURED_STATE[self]
        try:
            bound = captured[name]
        except KeyError:
            raise AttributeError(
                f"_SealedCollaboratorProxy: {name} was not captured at admission -- only the exact "
                f"methods RepositoryFacility genuinely calls on this collaborator are exposed"
            ) from None
        if name in captured_code:
            func = getattr(bound, "__func__", None)
            if func is None or func.__code__ is not captured_code[name]:
                raise RepositoryConstructionQualificationError(
                    f"_SealedCollaboratorProxy: {name}'s underlying implementation no longer matches "
                    f"what was captured at admission time -- the collaborator's method was mutated in place"
                )
        source_vars = vars(source)
        source_cls = type(source)
        for relied_name, (trusted_value, trusted_code, trusted_defaults) in relied_upon_methods:
            if relied_name in source_vars:
                raise RepositoryConstructionQualificationError(
                    f"_SealedCollaboratorProxy: the collaborator's own instance now defines "
                    f"{relied_name!r}, shadowing a class method one of its captured methods "
                    f"relies on internally via self.<name>() -- refusing to dispatch"
                )
            current = inspect.getattr_static(source_cls, relied_name, None)
            if (
                current is not trusted_value
                or not inspect.isfunction(current)
                or current.__code__ is not trusted_code
                or not _function_defaults_match(current, trusted_defaults)
            ):
                raise RepositoryConstructionQualificationError(
                    f"_SealedCollaboratorProxy: the collaborator's own class no longer defines "
                    f"{relied_name!r} as what was captured at admission time -- a method one of "
                    f"its captured methods relies on internally via self.<name>() was mutated"
                )
        for _key, entry in relied_upon_globals:
            if not _transitive_global_entry_matches(entry):
                globals_dict, global_name = entry[0], entry[1]
                label = _leaf_attribute_namespace_label(globals_dict)
                raise RepositoryConstructionQualificationError(
                    f"_SealedCollaboratorProxy: {label}'s own {global_name} binding no longer "
                    f"matches what was captured at admission time -- a module dependency one of "
                    f"its captured methods relies on internally was rebound"
                )
        for attr_name, (trusted_type, trusted_value) in data_snapshot:
            current_value = getattr(source, attr_name, _SEALED_PROXY_MISSING_DATA_ATTRIBUTE)
            if type(current_value) is not trusted_type or current_value != trusted_value:
                raise RepositoryConstructionQualificationError(
                    f"_SealedCollaboratorProxy: the collaborator's own {attr_name!r} data attribute "
                    f"no longer matches what was captured at admission time -- refusing to dispatch"
                )
        return bound

    def __setattr__(self, name: str, value: object) -> None:
        raise AttributeError("_SealedCollaboratorProxy instances are immutable after construction")

    def __delattr__(self, name: str) -> None:
        raise AttributeError("_SealedCollaboratorProxy instances are immutable after construction")

    def _inject_fault_for_qualification_harness(self, name: str, replacement) -> None:
        """See the ROUND 36->38 REVERSAL comment on
        `_AUTHORITY_STORE_CAPTURED_METHODS` for why this exists:
        `RepositoryConstructionPropertyQualificationHarness`'s own
        genuine crash/recovery scenarios need to substitute ONE
        captured method mid-scenario (simulating a crash-before-persist
        in `put_receipt`, for instance) without reopening the
        caller-retained-reference gap round 36/38 close. Reachable
        only by code that already holds a direct reference to a
        `_SealedCollaboratorProxy` object -- which means going through
        `_SEALED_PROXY_CAPTURED_STATE`'s module-private registry, since
        neither the wrapper's `__getattr__` (round 32/36) nor any
        caller-retained reference to the ORIGINAL `state_store`/
        `authority_store` can reach it. Not a general-purpose unsealing
        mechanism -- a narrowly named, explicitly test-labeled escape
        hatch for this module's own internal harness.

        CORRECTION (review finding, PR #86, round 42): this docstring
        previously claimed the reference had to be "THIS proxy object,"
        implying only the harness's OWN proxy was reachable this way --
        that was an overclaim, corrected here. Round 42's own finding
        (see `_AdmittedTransportState`'s docstring for the full
        account) demonstrated that `_SEALED_PROXY_CAPTURED_STATE`,
        being a single process-global registry, is ENUMERABLE by
        anyone who reaches the module via the already-disclosed round-
        34 boundary -- meaning this method is callable against ANY
        LIVE proxy reached this way, not only one the caller was
        legitimately handed. This is the SAME already-disclosed
        reachability fact, not a new category; there is no
        code-level way to distinguish "the trusted harness is calling
        this" from "an attacker who enumerated their way here is
        calling this" without a fragile caller-identity heuristic this
        codebase deliberately avoids (see this file's own "detect
        presence, don't interpret" philosophy). Disclosed, not fixed."""
        if not callable(replacement):
            raise RepositoryConstructionQualificationError(
                f"_SealedCollaboratorProxy._inject_fault_for_qualification_harness: replacement for {name!r} is not callable"
            )
        captured, captured_code, _source, _relied_upon_methods, _relied_upon_globals, _data_snapshot = _SEALED_PROXY_CAPTURED_STATE[self]
        if name not in captured:
            raise AttributeError(
                f"_SealedCollaboratorProxy._inject_fault_for_qualification_harness: {name!r} was not captured at admission"
            )
        captured[name] = replacement
        # The harness's replacement is a deliberately, knowingly
        # different implementation -- not a tampered original -- so
        # the round-40 code-object pin for THIS name no longer
        # applies; `__getattr__` skips the check for any name absent
        # from the captured-code mapping.
        captured_code.pop(name, None)


def gen1_wrap_repository_construction_facility(transport, state_store, authority_store) -> "_ContainmentReCheckedRepositoryFacility":
    """Thin constructor around real `tenfold.repository_facility.
    RepositoryFacility` -- never re-derived. Returns a
    `_ContainmentReCheckedRepositoryFacility` (see its own docstring
    and this function's MUTATION-TIME CONTAINMENT FINDING note below),
    a transparent wrapper observably identical to the raw
    `RepositoryFacility` for every use site except the two mutating
    methods it re-validates containment before.

    SCOPE NOTE (review finding, PR #84, P1): this function's own
    SIGNATURE requires no live Gen1 Foreman, campaign state, or
    authority owner -- `transport`/`state_store`/`authority_store` are
    all caller-injected. It is the genuine, reusable, Gen2-owned
    production entry point: a future G2-28+ orchestrator supplying its
    OWN Gen2-owned `CampaignAuthorityStore` implementation (matching
    `_MutableAuthorityStore`'s Protocol, not this disposable
    qualification-only stand-in) and a real repository transport would
    use this SAME function, unmodified. `RepositoryFacility`'s own
    internal admission logic still calls Gen1's real
    `validate_live_task` -- an explicit, sanctioned reuse of the
    qualified ALGORITHM (G2-00 SS15: "no invariant split across
    Python/Rust"), the same precedent G2-25's
    `run_real_gen2_recovery_takeover` established for
    `tenfold.recovery.takeover()`; Gen2 owning the DECISION means Gen2
    supplies and controls the authority DATA this algorithm operates
    over, not that Gen2 must reimplement the algorithm itself.

    Today, the ONLY caller in this codebase is
    `build_disposable_local_git_facility` (SC-23's own qualification
    rig) -- there is no G2-28 production caller yet because G2-28 does
    not exist yet; building one is explicitly out of this closure's
    scope (see `docs/gen2/G2-27-SC23-closure-review-record.md`, "Does
    not enable"). This is disclosed here so a future G2-28 author
    starts from this function, not a re-derivation of it.

    TRANSPORT BOUNDARY (review finding, PR #84, round 6, P1): the
    returned `RepositoryFacility`'s public `open_pr`/`merge_pr` methods
    delegate directly to whatever `transport` is supplied -- Gen1's own
    `RepositoryFacility` class has no opinion about which transport it
    is given. Without a genuine check here, a future caller could
    supply a remote-capable transport and perform real push/PR/merge
    effects while still claiming the local-commit-only admitted
    identity, silently breaking that identity's own scope guarantee.
    This is now genuinely enforced: `transport` MUST be a real
    `LocalGitRepositoryTransport` instance, whose own
    `open_pull_request`/`merge_pull_request` already, unconditionally
    raise `LocalGitTransportError` by design -- so this identity's
    local-commit-only scope is enforced at the ONE point in code where
    it actually can be, not merely documented.

    EXACT-TYPE FINDING (review finding, PR #84, round 13, P1,
    reproduced by the reviewer): `isinstance` accepts any SUBCLASS of
    `LocalGitRepositoryTransport` too -- the reviewer reproduced a
    subclass overriding `commit_files`/`open_pull_request`/
    `merge_pull_request` with real remote or out-of-domain effects,
    still passing the `isinstance` check and receiving the
    local-commit-only admitted identity. The check now requires the
    EXACT class (`type(transport) is LocalGitRepositoryTransport`),
    binding to the one qualified implementation rather than anything
    merely claiming compatibility with it.

    MUTATION-TIME CONTAINMENT FINDING (review finding, PR #84, round
    13, P1, reproduced by the reviewer): the symlink/hard-link
    containment scan above runs exactly ONCE, before this function
    returns -- nothing re-validated containment before each
    SUBSEQUENT mutation. The reviewer reproduced admitting a clean
    repository, THEN replacing `.git/refs/heads` with an
    external-directory symlink AFTER admission, then a later
    `create_branch` call following that newly-planted symlink: the
    admitted identity's own EFFECT_REACH boundary held only at
    construction time, not for the Facility's actual operating
    lifetime. The returned object is now a `_ContainmentReCheckedRepositoryFacility`
    that re-runs the SAME real containment check immediately before
    EVERY mutating call (`create_branch`, `commit`), delegating to the
    real, unmodified `RepositoryFacility` only after it passes --
    genuinely closing the window between admission and each individual
    mutation, not merely at construction.

    ROUND 14 FOLLOW-UP FINDINGS (review findings, PR #86, all
    reproduced by the reviewer(s)): the round 13 per-mutation re-check
    above closed the FILESYSTEM-containment window but left three
    further, related gaps open -- see `_reject_instance_overridden_transport_methods`
    and `_ContainmentReCheckedRepositoryFacility`'s own docstrings for
    the full accounts:
    - the per-mutation re-check never re-verified `.git` itself (fixed
      in `_reject_symlinked_git_storage_for_every_registered_repository`
      directly, see its own docstring);
    - the per-mutation re-check never re-applied hook neutralization,
      so a `.git/config` change restoring `core.hooksPath` to an
      external hook AFTER admission would still fire on the next
      mutation (now re-applied on every `create_branch`/`commit`, not
      only at construction);
    - the exact-type check only binds the CLASS -- an INSTANCE can
      still shadow a real class method with its own `__dict__` entry
      (`transport.open_pull_request = malicious_fn`), which
      `isinstance`/`type(...) is ...` cannot detect at all (now
      genuinely rejected, at admission and before every mutating or
      transport-delegating call)."""
    if type(transport) is not LocalGitRepositoryTransport:
        raise RepositoryConstructionQualificationError(
            f"gen1_wrap_repository_construction_facility: transport must be a real LocalGitRepositoryTransport "
            f"(local-commit-only, per this identity's own admitted scope) -- got {type(transport).__name__}"
        )
    _reject_altered_transport_class_implementation()
    # Round 23 (see `_TRUSTED_FACILITY_CLASS_ATTRIBUTES`'s own
    # docstring): defense-in-depth parallel to the transport check
    # above -- `RepositoryFacility` itself is constructed fresh a few
    # lines below and so cannot yet carry an INSTANCE-level shadow,
    # but its CLASS could already be tampered with before this
    # function ever runs, the same class of risk the transport check
    # above already covers.
    _reject_altered_facility_class_implementation()
    # Round 45 (see `_TRUSTED_VALIDATE_LIVE_TASK`'s own module-level
    # comment): checked alongside the class-implementation checks
    # above, at BOTH admission and every per-mutation revalidation --
    # a rebound `validate_live_task`/`validate_task` is exactly the
    # same class of pre-admission or post-admission tampering those
    # checks already guard against, just reached through a function's
    # `__globals__` rather than a class's own `__dict__`.
    _reject_altered_authority_validation_globals()
    # Round 52 (see `_TRUSTED_CONTAINMENT_SCAN_MODULE_GLOBALS`'s own
    # module-level comment): checked alongside the checks above, at
    # BOTH admission and every per-mutation revalidation -- a rebound
    # `Path.is_symlink` (or any other module/class dependency this
    # module's own symlink-escape scanning relies on) is exactly the
    # same class of pre-admission or post-admission tampering those
    # checks already guard against, just reached through THIS module's
    # own containment-scan functions rather than Gen1's.
    _reject_altered_transitive_globals(_TRUSTED_CONTAINMENT_SCAN_MODULE_GLOBALS)
    _reject_instance_overridden_transport_methods(transport)
    # Round 36 (see `_reject_untrusted_transport_git_executable`'s own
    # docstring): must run BEFORE `established_instance_state` is ever
    # captured below, and before hook neutralization actually executes
    # `_git` -- otherwise a pre-admission tampered value gets blessed
    # as the trusted baseline instead of being rejected outright.
    _reject_untrusted_transport_git_executable(transport)
    # `dict(vars(transport))` only copies the OUTER __dict__ -- the
    # value at `_repositories` would still be the SAME mutable dict
    # object `transport._repositories` itself, so a later in-place
    # mutation (`transport._repositories[name] = ...`) would silently
    # mutate this "established" snapshot too, defeating the whole
    # point (self-caught while re-verifying the round-19 regression
    # test against this round's consolidation). `_repositories` is
    # copied independently; `_git`/`_author_name`/`_author_email` are
    # plain immutable strings, so no further copying is needed there.
    established_instance_state = dict(vars(transport))  # noqa: SLF001 -- genuine safety enforcement; see _reject_altered_transport_instance_state's own docstring
    # FROZEN-DATACLASS FINDING (review finding, PR #86, round 25, P1,
    # Codex, reproduced by the reviewer -- "Snapshot registered
    # repository records by value"): copying the OUTER `_repositories`
    # dict (above) is not enough -- its VALUES are still the SAME
    # `_RegisteredRepository` object references as `transport._repositories`
    # itself. `@dataclass(frozen=True)` only blocks NORMAL attribute
    # assignment; it does NOT stop `object.__setattr__(registered,
    # "root", other_root)`, a well-known way to bypass a frozen
    # dataclass's own immutability. The reviewer reproduced exactly
    # this: mutate a shared `_RegisteredRepository`'s `root`/`device`/
    # `inode` fields in place via `object.__setattr__`, which changes
    # BOTH the live transport's view AND this snapshot simultaneously
    # (they're the same object), so `_reject_altered_transport_instance_state`'s
    # equality check still trivially passes -- comparing the mutated
    # object to itself -- while a subsequent `create_branch` wrote into
    # the now-different, unadmitted repository the fields pointed at.
    # Fixed by constructing BRAND NEW `_RegisteredRepository` instances
    # holding copies of the primitive field values (`Path`/`int`/`int`,
    # all themselves immutable) -- genuinely independent objects a
    # live-record mutation cannot reach.
    # DEEP-IMMUTABILITY FINDING (review finding, PR #86, round 43, P1,
    # Codex, reproduced by the reviewer -- "Make admission snapshots
    # deeply immutable"): round 42 made `_AdmittedTransportState`
    # `frozen=True`, which blocks `admitted.instance_state = new_dict`
    # -- but freezing a dataclass only seals its OWN field REFERENCES,
    # never the CONTENTS of a plain, mutable `dict` one of those
    # fields happens to point at. The reviewer reproduced enumerating
    # the registry (the same already-disclosed round-34/42
    # reachability) to reach an unrelated VICTIM admission, then
    # mutating `victim_admitted.instance_state["_repositories"]`
    # in place to redirect BOTH the victim's live transport
    # registration AND this "established" snapshot to the SAME
    # external clone -- since both sides of
    # `_reject_altered_transport_instance_state`'s comparison were
    # poisoned consistently, the check still "passed," and a fully
    # authorized `create_branch` landed in the attacker's clone while
    # the genuinely admitted repository stayed untouched. Fixed by
    # wrapping BOTH the nested `_repositories` dict and the outer
    # `established_instance_state` dict itself in
    # `types.MappingProxyType` -- a genuinely read-only VIEW, not a
    # copy that could itself be discarded; since no other reference to
    # the underlying mutable dicts is ever retained past this point,
    # this is the only handle anyone (attacker or legitimate code)
    # ever has to this state again, and every write through it raises
    # `TypeError` outright.
    established_instance_state["_repositories"] = types.MappingProxyType({
        name: _RegisteredRepository(registered.root, registered.device, registered.inode)
        for name, registered in established_instance_state["_repositories"].items()
    })
    established_instance_state = types.MappingProxyType(established_instance_state)
    _reject_symlinked_git_storage_for_every_registered_repository(transport)
    established_no_hooks_dirs = _neutralize_hooks_for_every_registered_repository(transport)
    # Round 36/38 (see `_AUTHORITY_STORE_CAPTURED_METHODS`'s own
    # module-level comment for the full "ROUND 36->38 REVERSAL"
    # account): `RepositoryFacility` is handed sealed proxies capturing
    # both `authority_store.read` and `state_store`'s five methods at
    # THIS admission, never the raw collaborators themselves -- immune
    # to either caller's own retained reference being mutated in place
    # afterward.
    sealed_authority_store = _SealedCollaboratorProxy(authority_store, _AUTHORITY_STORE_CAPTURED_METHODS, "authority_store")
    sealed_state_store = _SealedCollaboratorProxy(state_store, _STATE_STORE_CAPTURED_METHODS, "state_store", _STATE_STORE_IMMUTABLE_DATA_ATTRIBUTES)
    facility = RepositoryFacility(transport, sealed_state_store, sealed_authority_store)
    # Round 22/24 (see `_AdmittedTransportState`'s own docstring): this
    # trusted state -- including `facility` itself, the genuine
    # instance every dispatch method delegates to (round 24) -- is
    # registered in the module-private `_ADMITTED_TRANSPORT_STATE`
    # registry, NOT passed into the wrapper's own constructor -- a
    # caller holding only the returned facility has no attribute path
    # to reach or overwrite any of it.
    #
    # WRAPPER-KEYED FINDING (review finding, PR #86, round 25, Minor,
    # CodeRabbit -- "Bind admission state to each wrapper"): keying by
    # `transport` meant re-admitting the SAME transport object (as a
    # real recovery/takeover scenario legitimately does, with a
    # DIFFERENT `RepositoryStateStore`/facility) silently OVERWROTE the
    # first admission's registry entry -- a later call on the FIRST,
    # still-held wrapper would then use the SECOND admission's facility
    # and state. The registry is now keyed by the WRAPPER instance
    # itself (constructed first, below), which is unique per admission
    # call by construction -- see `_admitted_state_for`'s own updated
    # docstring for why hashing the wrapper carries none of round 23's
    # transport-hashing risk.
    wrapper = _ContainmentReCheckedRepositoryFacility(facility, transport)
    _ADMITTED_TRANSPORT_STATE[wrapper] = _AdmittedTransportState(
        facility, established_instance_state, established_no_hooks_dirs,
        established_facility_state=facility.state,
        established_facility_authority_store=facility.authority_store,
    )
    return wrapper


#: Review finding (PR #86, round 18, P1, reproduced by the reviewer):
#: rounds 14-15 sealed a growing list of specific PUBLIC method names
#: (`resolve_ref`, `read_file`, `create_branch`, `commit_files`,
#: `open_pull_request`, `merge_pull_request`) one at a time, ending
#: with "the full set Codex originally named." The reviewer then
#: reproduced shadowing `transport._run` instead -- the PRIVATE helper
#: every one of those public methods actually delegates its real
#: subprocess work through -- passing every named-method check while
#: still performing an out-of-repository write before ever reaching
#: git. Enumerating known-dangerous method names is a losing pattern
#: for exactly the same reason the git-config findings were: it is a
#: fragile allowlist-of-the-wrong-shape that invites the next variant
#: (any OTHER private helper today, or one added to
#: `LocalGitRepositoryTransport` -- a Gen1-owned, evolving module --
#: tomorrow). Replaced with the inverse, comprehensive check: a
#: genuinely unmodified `LocalGitRepositoryTransport` instance's own
#: `__dict__` contains EXACTLY the four data attributes its real
#: `__init__` sets (`_git`, `_author_name`, `_author_email`,
#: `_repositories` -- confirmed empirically, not assumed) and NOTHING
#: else; any additional instance attribute at all -- a shadowed public
#: method, a shadowed private helper, or literally anything else --
#: is rejected outright, without needing to name it in advance.
_EXPECTED_TRANSPORT_INSTANCE_ATTRIBUTES = frozenset({"_git", "_author_name", "_author_email", "_repositories"})


def _reject_instance_overridden_attributes(obj: object, expected_attributes: frozenset, label: str) -> None:
    """See `_reject_instance_overridden_transport_methods`'s own
    docstring for the round-14/18 finding this originally closed for
    `LocalGitRepositoryTransport`, and `_TRUSTED_FACILITY_CLASS_ATTRIBUTES`'s
    for the round-23 extension to `RepositoryFacility`. A genuinely
    unmodified instance's own `__dict__` contains EXACTLY its class's
    real `__init__` data attributes and nothing else; this rejects if
    it carries anything beyond that, whatever it is called (a shadowed
    public method, a shadowed private helper, or literally anything
    else)."""
    unexpected = sorted(set(vars(obj)) - expected_attributes)
    if unexpected:
        raise RepositoryConstructionQualificationError(
            f"_reject_instance_overridden_attributes: {label} instance carries unexpected instance "
            f"attributes beyond its own __init__ ({', '.join(unexpected)}), breaking the local-commit-only boundary"
        )


def _reject_instance_overridden_transport_methods(transport: LocalGitRepositoryTransport) -> None:
    """Review finding (PR #86, round 14, P1, reproduced by the
    reviewer): an exact-type check (`type(transport) is
    LocalGitRepositoryTransport`) only binds the CLASS -- Python allows
    assigning a plain function directly onto an INSTANCE's own
    `__dict__`, which shadows the class's real method for that
    instance alone (`transport.open_pull_request = malicious_fn`),
    completely invisible to any class-identity check. The reviewer
    reproduced exactly this: the exact-type check passed, but
    `facility.open_pr(...)` still invoked the injected, remote-capable
    override instead of `LocalGitRepositoryTransport`'s own real
    method (which unconditionally raises by design). Rounds 15 and 18
    (see `_EXPECTED_TRANSPORT_INSTANCE_ATTRIBUTES`'s own comment)
    showed enumerating specific method names -- public OR private --
    to seal is a losing, ever-growing battle."""
    _reject_instance_overridden_attributes(transport, _EXPECTED_TRANSPORT_INSTANCE_ATTRIBUTES, "LocalGitRepositoryTransport")


def _reject_instance_overridden_facility_methods(facility: object) -> None:
    """See `_TRUSTED_FACILITY_CLASS_ATTRIBUTES`'s own docstring for the
    round-23 finding this closes -- the same instance-shadowing attack
    `_reject_instance_overridden_transport_methods` closes for the
    transport, applied to the inner, real `RepositoryFacility` this
    module delegates to. `facility` deliberately untyped, matching
    `gen1_wrap_repository_construction_facility`'s own established
    reasoning for why an explicit `RepositoryFacility` annotation would
    itself be an undisclosed live-Gen1-authority reference."""
    _reject_instance_overridden_attributes(facility, _EXPECTED_FACILITY_INSTANCE_ATTRIBUTES, "RepositoryFacility")


def _reject_altered_facility_collaborators(
    facility: object,
    established_state: object,
    established_authority_store: object,
) -> None:
    """Review finding (PR #86, round 29, P1, Codex, reproduced by the
    reviewer -- "Pin the delegated facility's collaborator values"):
    `_reject_instance_overridden_facility_methods` validates attribute
    NAMES only -- `state`/`authority_store` are themselves two of the
    three expected names, so reassigning what they POINT AT (a
    malicious delegating object) after admission was invisible to that
    check, the SAME underlying gap round 19's "Pin registered
    repository identities at admission" already closed for the
    transport's `_repositories`, one collaborator over.

    The reviewer's exploit was sharper than a simple swap-and-read,
    though: `RepositoryFacility.create_branch`'s own real
    implementation calls `self.authority_store` (via `_live_mutable`
    -> `validate_live_task`) BEFORE the actual git mutation, but AFTER
    `_revalidate_transport_integrity`'s own containment scan has
    already run and returned. A malicious `authority_store` whose
    `read()` (or whatever real method Gen1's authority validation
    calls) has a SIDE EFFECT -- moving `.git/refs/heads` outside the
    repository and replacing it with a symlink -- fires DETERMINISTICALLY
    in that window, every time, not merely as a probabilistic race: by
    the time `self.transport.create_branch(...)` actually writes, the
    symlink is already in place, even though the EARLIER scan found
    nothing wrong (because the tampering had not happened yet). This
    is a STRICTLY WORSE, deterministic sibling of the round-14 TOCTOU
    finding (a race against a background process) -- but unlike that
    genuinely-unfixable race, THIS window is closed by a concrete,
    complete fix: `state`/`authority_store` are set exactly ONCE by
    `RepositoryFacility.__init__` and never legitimately reassigned
    anywhere in Gen1's own code afterward (unlike `.transport`, which
    round 16 established CAN be legitimately swapped and is
    independently, more thoroughly re-verified elsewhere) -- so pinning
    them by IDENTITY (never by equality, which would reopen round 28's
    attacker-controlled-equality risk; `is` never dispatches to
    `__eq__`/`__ne__` at all) and checking BEFORE every delegating call
    closes this specific exploit completely: the swap is caught before
    `admitted.facility.create_branch`/etc. is ever invoked, so the
    malicious collaborator's callback never gets a chance to run."""
    changed = []
    if facility.state is not established_state:
        changed.append("state")
    if facility.authority_store is not established_authority_store:
        changed.append("authority_store")
    if changed:
        raise RepositoryConstructionQualificationError(
            f"_reject_altered_facility_collaborators: RepositoryFacility's own state/authority_store "
            f"no longer match what was admitted at construction time ({', '.join(changed)}) -- rejecting "
            f"before delegation so a swapped collaborator's own callback never gets a chance to run"
        )


def _reject_altered_transport_instance_state(
    transport: LocalGitRepositoryTransport,
    established_instance_state: dict,
) -> None:
    """Review finding (PR #86, round 19, Major, CodeRabbit -- "Pin
    registered repository identities at admission"): round 18's
    instance-attribute allowlist validates attribute NAMES only --
    `_repositories` is itself one of the four expected names, so
    replacing what it POINTS AT (a different, independently clean
    `_RegisteredRepository`) was invisible to that check.
    `LocalGitRepositoryTransport._repo` only checks a registration's
    internal self-consistency against ITSELF, not against what was
    actually admitted, so a swapped registration passed every existing
    check and a later `create_branch`/`commit` silently operated on a
    repository that was never scanned for symlinked git storage or
    hook neutralization.

    Review finding (PR #86, round 20, P1, Codex, reproduced by the
    reviewer -- "Bind allowed transport attribute values"): the
    round-19 fix pinned `_repositories`' VALUES but left `_git`,
    `_author_name`, and `_author_email` covered by name only. The
    reviewer reproduced reassigning `transport._git` to a malicious
    executable after admission -- still one of the four allowed
    NAMES, so the round-18/19 checks stayed silent, and the injected
    executable ran (in place of the real `git` binary) the next time
    `_run` used `self._git` during a fully-authorized `create_branch`.

    Both are the same underlying gap: an allowlist of attribute NAMES
    proves nothing about the VALUES behind them. Generalized once,
    covering all four: `established_instance_state` is a snapshot of
    `vars(transport)` -- names AND values -- taken at admission time
    (after `_reject_instance_overridden_transport_methods` has already
    confirmed the incoming instance carries no unexpected names), and
    every mutation now re-verifies `vars(transport)` is EXACTLY that
    snapshot -- no attribute added, removed, or reassigned to a
    different value, whatever its name.

    ATTACKER-CONTROLLED EQUALITY FINDING (review finding, PR #86,
    round 28, P1, Codex, reproduced by the reviewer -- "Reject
    transport values with overloaded equality"): `current[name] !=
    established_instance_state[name]` dispatches through WHICHEVER
    operand's type implements `__ne__`/`__eq__` -- and `current[name]`
    is exactly the value a caller may have just reassigned. The
    reviewer reproduced assigning `transport._git` a `str` SUBCLASS
    (a new, genuine TYPE with its own `__ne__` defined in its class
    body -- Python's special-method dispatch for operators always goes
    through the TYPE, never an instance `__dict__`, so this is a real
    subclass, not an instance-level monkeypatch of `__ne__`, which
    would not participate in `!=` dispatch at all) that always claims
    `!= -> False` regardless of its actual content, which then held a
    malicious executable path: the comparison "passed" the check while
    the value had genuinely changed, and the injected executable ran
    (in place of the real `git` binary) during a fully-authorized
    `create_branch`. Confirmed empirically. Every comparison in this
    function is now preceded by an EXACT-type check (`type(x) is str`,
    never `isinstance`, which also accepts subclasses) on the
    CURRENT (potentially attacker-controlled) value before trusting
    ANY comparison operator on it -- a genuine, unmodified `str`'s own
    `__eq__`/`__ne__` are fixed, C-implemented, non-overridable-per-
    instance methods, so once the exact type is confirmed, the
    comparison itself is safe. `_repositories`' values are handled the
    same way, one level deeper (see `_registered_repositories_match`'s
    own docstring), rather than trusting `_RegisteredRepository`'s own
    dataclass-generated `__eq__` (or a dict's own `!=`) to dispatch
    safely without first confirming every operand's exact type."""
    current = vars(transport)
    unexpected_or_missing = sorted(set(current) ^ set(established_instance_state))
    if unexpected_or_missing:
        raise RepositoryConstructionQualificationError(
            f"_reject_altered_transport_instance_state: transport instance attributes no longer match "
            f"the set admitted at construction time ({', '.join(unexpected_or_missing)}), "
            f"breaking the local-commit-only boundary"
        )
    changed = sorted(
        name
        for name in established_instance_state
        if not _trusted_transport_value_matches(name, current[name], established_instance_state[name])
    )
    if changed:
        raise RepositoryConstructionQualificationError(
            f"_reject_altered_transport_instance_state: transport instance attribute value(s) changed "
            f"since construction time ({', '.join(changed)}) -- rejecting the same as a symlinked git directory"
        )


def _trusted_transport_value_matches(name: str, current_value, established_value) -> bool:
    """See `_reject_altered_transport_instance_state`'s own ATTACKER-
    CONTROLLED EQUALITY FINDING docstring. `established_value` is
    always genuinely trustworthy (captured immediately after the real
    `LocalGitRepositoryTransport.__init__` ran, before any tampering
    could occur -- its own constructor always assigns a real `str` via
    `str(Path(...).resolve())`), so only `current_value` -- read FRESH
    before each mutation, potentially already tampered with -- needs
    its exact type verified before any comparison operator on it is
    trusted."""
    if name == "_repositories":
        return _registered_repositories_match(current_value, established_value)
    return type(current_value) is str and current_value == established_value


def _registered_repositories_match(current: object, established: dict) -> bool:
    """See `_reject_altered_transport_instance_state`'s own ATTACKER-
    CONTROLLED EQUALITY FINDING docstring. Rather than trusting a bare
    `current != established` dict comparison (which would dispatch
    through `dict.__eq__`, itself comparing each VALUE via `==` --
    exactly the same attacker-controlled-equality risk one level
    deeper, this time via `_RegisteredRepository`'s own
    dataclass-generated `__eq__` or a malicious non-`_RegisteredRepository`
    object entirely), every field of every registration is manually,
    exact-type-checked before being compared at all."""
    if type(current) is not dict or set(current) != set(established):
        return False
    for name, established_registered in established.items():
        current_registered = current[name]
        if type(current_registered) is not _RegisteredRepository:
            return False
        if (
            type(current_registered.root) is not type(established_registered.root)
            or current_registered.root != established_registered.root
            or type(current_registered.device) is not int
            or current_registered.device != established_registered.device
            or type(current_registered.inode) is not int
            or current_registered.inode != established_registered.inode
        ):
            return False
    return True


@dataclass(frozen=True)
class _AdmittedTransportState:
    """Review finding (PR #86, round 42 -- an independently-launched
    adversarial re-review, run because Codex's review quota was
    exhausted a third time): round 34's own disclosure ("no
    interpreter-level mechanism can make a name defined in this
    module genuinely unreachable from code that already holds a
    reference to ANY object this module produced") establishes that
    `_ADMITTED_TRANSPORT_STATE` itself is reachable this way -- but
    that disclosure only ever demonstrated READING one's OWN entry.
    The reviewer went further: since `_ADMITTED_TRANSPORT_STATE` is a
    single, PROCESS-GLOBAL registry holding every LIVE admission (a
    real, anticipated coexistence -- round 25's own recovery/takeover
    scenario legitimately keeps two admissions of the same transport
    alive at once), a caller who reaches the module via ANY admission
    they hold can ENUMERATE the registry's keys and reach every OTHER,
    UNRELATED admission too -- including one belonging to a completely
    different caller who handed the attacker nothing at all. This
    class was previously a PLAIN (non-frozen) dataclass, so once an
    unrelated entry was reached this way, EVERY field --
    `facility`/`instance_state`/`no_hooks_dirs`/
    `established_facility_state`/`established_facility_authority_store`
    -- was trivially reassignable via ordinary syntax, no bypass
    technique needed at all: `other_admitted.facility =
    attacker_facility` genuinely redirected the VICTIM's own,
    perfectly ordinary `create_branch` calls to attacker-controlled
    output, a complete cross-identity compromise reached without the
    attacker ever holding a reference to the victim's wrapper.

    The REACHABILITY half of this (enumerating the registry at all) is
    NOT a new gap -- it is the SAME already-disclosed round-34 fact,
    now demonstrated with a materially stronger consequence
    (cross-identity compromise, not merely self-inspection) than its
    original text named. The MUTABILITY half -- that a reached entry's
    fields could be reassigned via ORDINARY syntax with zero further
    effort -- IS a genuine, fixable gap, closed here: `frozen=True`
    rejects ordinary field reassignment outright (`FrozenInstanceError`),
    the same defensive posture already used elsewhere in this file for
    advertised-immutable state. The ONE legitimate internal mutation
    site (`_revalidate_transport_integrity` refreshing
    `no_hooks_dirs` after hook re-neutralization) now uses
    `object.__setattr__` explicitly, the established, narrowly-scoped
    escape hatch for module-private code that needs to mutate what an
    external caller must not. `object.__setattr__` bypassing
    `frozen=True` for an attacker who ALSO reaches an unrelated entry
    remains the SAME disclosed, unfixable low-level-bypass class rounds
    25/27/39/41 already established -- narrowing the EASY, ordinary-
    syntax attack this round demonstrated, not claiming to close every
    conceivable path.

    Review finding (PR #86, round 22, P1, Codex, reproduced by the
    reviewer -- "Keep the admission snapshot caller-independent"): the
    round 19/20 fix (`_reject_altered_transport_instance_state`) is
    only as trustworthy as the snapshot it compares against -- and
    that snapshot (`established_instance_state`) was stored as a plain
    instance attribute on the WRAPPER, `self._established_instance_state`.
    Any caller holding the returned `facility` object can simply
    OVERWRITE the "trusted" baseline to match whatever tampering they
    just did to the real transport, defeating the comparison entirely
    without needing to touch the transport's class at all. The
    reviewer reproduced exactly this: reassign `transport._git`, then
    also reassign `facility._established_instance_state["_git"]` to
    the same value, and the check trivially still "matches." The same
    is true of `established_no_hooks_dirs`
    (`self._established_no_hooks_dirs`): a caller-poisoned baseline
    there would make `_hooks_neutralization_still_intact` report a
    malicious `.git/config` as unchanged, silently skipping
    re-neutralization.

    Fixed by moving BOTH pieces of admission-time trusted state OUT of
    any attribute reachable through the `facility` object graph
    entirely, into `_ADMITTED_TRANSPORT_STATE` below -- a private,
    MODULE-level registry the wrapper instance itself carries no
    reference to. A caller holding only `facility` cannot reach it
    through any attribute access on that object; doing so would
    require importing this module directly and reaching into its own
    private globals, a fundamentally more privileged action than
    anything reachable through the facility's own public surface (the
    same disclosed trust model as the round-21 "attacker with code
    execution before this module is imported" limitation, not a new
    category of gap).

    Review finding (PR #86, round 24, P1, Codex, reproduced by the
    reviewer -- "Verify the inner facility identity before delegation"):
    the round-23 fix sealed `self._facility`'s own instance-attribute
    NAMES, but every dispatch method still called `self._facility.<method>`
    directly -- a plain, caller-mutable wrapper attribute. The reviewer
    reproduced replacing `self._facility` WHOLESALE with a different
    object whose `__dict__` merely matched the round-23 allowlist's
    SHAPE (same attribute names), which the name-only check accepts
    since it never verifies the object's actual type or identity;
    `create_branch`/`commit` then invoked THAT object's own,
    attacker-controlled methods, skipping every one of Gen1's real
    authority/lease/request-binding checks entirely. `facility` (the
    genuine, originally-constructed `RepositoryFacility` instance) is
    now ALSO carried in this registry entry -- every dispatch method
    (`create_branch`/`commit`/`read`/`open_pr`/`merge_pr`) delegates to
    `admitted.facility`, this immutable registry-sourced reference,
    never to `self._facility` -- so no amount of cleverness reassigning
    `self._facility` can affect what actually gets called. `self._facility`
    remains in use only for `__getattr__`'s non-security-sensitive
    delegation (`state`/`authority_store`/`acquire_writer`/
    `release_writer`).

    Review finding (PR #86, round 25, Minor, CodeRabbit -- "Bind
    admission state to each wrapper"): registering this state keyed by
    `transport` meant re-admitting the SAME transport object (as a
    real recovery/takeover scenario legitimately does, with a
    DIFFERENT `RepositoryStateStore`/facility) silently OVERWROTE the
    FIRST admission's entry, so a later call on the FIRST, still-held
    wrapper would use the SECOND admission's facility and state. Fixed
    by keying `_ADMITTED_TRANSPORT_STATE` by the WRAPPER instance
    itself (see its own docstring below) instead -- unique per
    admission call by construction, so two admissions of the same
    transport can never collide. `_current_transport` no longer needs
    to read `self._facility.transport` to DISCOVER a lookup key at
    all; `admitted.facility.transport` is read directly instead, once
    `admitted` itself is already in hand.

    Review finding (PR #86, round 29, P1, Codex, reproduced by the
    reviewer -- "Pin the delegated facility's collaborator values"):
    round 24 pinned `facility` ITSELF against wholesale replacement,
    but never pinned WHAT `facility.state`/`facility.authority_store`
    themselves point at -- `_reject_instance_overridden_facility_methods`
    checks names only. The reviewer reproduced swapping
    `facility.authority_store` for a malicious delegating object whose
    `read()` callback (invoked by Gen1's own real authority validation,
    mid-`create_branch`, AFTER the containment scan but BEFORE the
    actual git mutation) moves `.git/refs/heads` outside the repository
    and replaces it with a symlink -- deterministically, not as a race.
    `established_facility_state`/`established_facility_authority_store`
    capture the genuine, originally-constructed collaborators (see
    `_reject_altered_facility_collaborators`'s own docstring for the
    full account), checked by IDENTITY before every delegating call."""

    facility: object
    instance_state: dict
    no_hooks_dirs: "dict[str, _EstablishedHooksNeutralization]"
    established_facility_state: object
    established_facility_authority_store: object


#: Keyed by WRAPPER instance IDENTITY (round 25 -- see
#: `_AdmittedTransportState`'s own docstring for the collision finding
#: that motivated moving off transport-keying), a `WeakKeyDictionary`
#: so a wrapper that is later garbage-collected doesn't leak its
#: registry entry forever. Hashing the wrapper carries none of round
#: 23's transport-hashing risk: `_ContainmentReCheckedRepositoryFacility`
#: is this module's OWN class (never Gen1-owned), uses the default,
#: identity-based `object.__hash__`/`__eq__` (never overridden), and
#: -- since round 25's `__slots__` fix -- cannot have either rebound at
#: the INSTANCE level either; only importing this module's own private
#: class directly and rebinding at the CLASS level could affect it,
#: the same disclosed "attacker with code execution before this module
#: is imported"-equivalent threshold every other class-level check in
#: this file already accepts as out of scope.
_ADMITTED_TRANSPORT_STATE: "weakref.WeakKeyDictionary" = weakref.WeakKeyDictionary()


def _admitted_state_for(wrapper: "_ContainmentReCheckedRepositoryFacility") -> _AdmittedTransportState:
    admitted = _ADMITTED_TRANSPORT_STATE.get(wrapper)
    if admitted is None:
        raise RepositoryConstructionQualificationError(
            "_admitted_state_for: no admission-time state found for this wrapper instance -- "
            "it was never admitted through gen1_wrap_repository_construction_facility"
        )
    return admitted


class _FrozenClassMeta(type):
    """Review finding (PR #86, round 26, P1, Codex, reproduced by the
    reviewer -- "Seal the wrapper class dispatch surface"): round 25's
    `__slots__` fix blocks INSTANCE-level shadowing
    (`facility.create_branch = malicious_fn`) but does nothing to stop
    CLASS-level rebinding -- `type(facility).create_branch = malicious_fn`
    reaches the SAME class object every instance shares, and Python
    classes are, by default, fully mutable from the outside. The
    reviewer correctly disproved this file's own earlier reasoning
    (that class-level tampering "would require importing this module
    directly," the disclosed-limitation boundary every OTHER
    class-level check in this file relies on): `type(facility)` hands
    ANY caller merely holding the returned wrapper a direct class
    reference, no import needed at all -- a fundamentally weaker,
    more available attack than the one that boundary was drawn around.

    Unlike `LocalGitRepositoryTransport`/`RepositoryFacility` (Gen1-owned
    classes this module cannot modify, where a REACTIVE
    snapshot-comparison check -- `_reject_altered_class_implementation`
    -- is the best available option, run by THIS wrapper's own code
    before delegating to them), `_ContainmentReCheckedRepositoryFacility`
    is THIS module's OWN class. A reactive check could never have
    worked here regardless: if `create_branch` itself were
    successfully replaced, no code inside it would ever run to notice
    -- the same "no hook point from within" problem round 25 already
    identified for instance-level shadowing, replaying one level up.
    Since this class is Gen2-owned, a PROACTIVE, structural fix is
    possible instead: this metaclass makes the class object itself
    reject any attribute assignment or deletion after it is defined,
    closing the entire class of attack at the language level, the same
    kind of guarantee `__slots__` already gives at the instance level.

    SECURITY NOTE -- DISCLOSED LIMITATION (review finding, PR #86,
    round 27, P1/Major, Codex and CodeRabbit, both independently
    reproduced by the reviewers): `__setattr__`/`__delattr__` above
    only intercept Python's NORMAL attribute-assignment SYNTAX
    (`SomeClass.attr = x`, which is sugar for
    `type(SomeClass).__setattr__(SomeClass, "attr", x)` -- virtual
    dispatch through the metaclass's own MRO). Calling
    `type.__setattr__(SomeClass, "attr", x)` EXPLICITLY sidesteps that
    dispatch entirely, invoking the base implementation directly --
    confirmed empirically:
    `type.__setattr__(type(facility), "create_branch", malicious_fn)`
    succeeds and the next `facility.create_branch(...)` call runs the
    replacement, unconditionally. This is a FUNDAMENTAL property of
    Python's object model, not a defect in this metaclass or a gap
    that a cleverer metaclass could close: `type.__setattr__` is the
    ROOT implementation every class ultimately inherits (directly or
    through its metaclass chain), it is always PUBLICLY reachable as a
    builtin, and no override anywhere in the MRO can prevent a caller
    from invoking a LESS-derived implementation of the same dunder by
    name -- exactly the same structural bypass round 25's
    `object.__setattr__`-defeats-`@dataclass(frozen=True)` finding
    already demonstrated for INSTANCE-level freezing, replaying here
    for CLASS-level freezing. The REACTIVE snapshot-comparison approach
    (`_reject_altered_class_implementation`) that protects the
    Gen1-owned `LocalGitRepositoryTransport`/`RepositoryFacility`
    classes remains fully sound against this exact technique (verified
    empirically) -- it detects the CURRENT state regardless of HOW it
    was mutated, so bypassing `__setattr__` changes nothing about
    whether it gets caught. But that same reactive pattern could never
    have protected THIS wrapper's own dispatch methods regardless of
    round 26's implementation choice: if `create_branch` itself is
    successfully replaced, by ANY technique, no code inside it --
    including a hypothetical check -- would ever run to notice. There
    is consequently no further code-level fix available inside this
    single Python process. Matching CodeRabbit's own explicit
    suggestion ("narrow the documented attacker model" when the
    alternative -- protecting the boundary outside the interpreter,
    e.g. OS-level process isolation or a capability-sandboxed
    subprocess -- is a materially different, separately-deliberated
    undertaking, not a rewrite of this module): the admitted
    local-commit-only identity's trust model is explicitly narrowed
    here to a caller using Python's NORMAL attribute-access surface
    (ordinary syntax, `getattr`/`setattr` builtins, `__slots__`-aware
    reflection) -- not one deliberately invoking a base dunder
    implementation by name to route around virtual dispatch. This is
    the SAME category of trust boundary this module's own top-level
    docstring already discloses for the admitted identity generally
    ("construction/qualification time... review discipline... the same
    trust model every other PropertyQualificationRecord/Trust Table
    row in this codebase already uses"), not a new kind of gap --
    disclosed explicitly here because this is the first round where
    that boundary was concretely, empirically probed rather than
    assumed. See `test_sc23_wrapper_class_freeze_cannot_defend_against_a_direct_type_setattr_bypass`
    for the permanent, executable record of this disclosed limitation.

    SECURITY NOTE -- DISCLOSED LIMITATION, WIDENED (review finding, PR
    #86, round 37, P1, Codex, reproduced by the reviewer -- "Protect
    wrapper methods' mutable code objects"): the round-27 narrowing
    above excluded "invoking a base dunder implementation by name to
    route around virtual dispatch" -- but the reviewer found a bypass
    that needs NEITHER `type.__setattr__` NOR any dunder trick at all:
    `type(facility).create_branch.__code__ = malicious.__code__`. This
    is ORDINARY attribute assignment, using NORMAL Python syntax, on a
    plain `function` OBJECT -- `__code__` is just one more mutable
    attribute a `function` instance carries, exactly like any other
    object's mutable state, and this metaclass's own `__setattr__`
    override only ever intercepts assignment ON THE CLASS
    (`SomeClass.attr = x`); it has no way to intercept, and no
    jurisdiction over, an assignment on some OTHER object the class
    happens to hold a reference to as one of its attribute VALUES.
    Confirmed empirically: the reassignment succeeds without raising,
    and the next `facility.create_branch(None)` call runs the injected
    bytecode with none of the real method's containment, authority, or
    lease checks -- worse than round 27's own bypass, since this one
    falls squarely INSIDE the trust model round 27 already narrowed to
    ("ordinary syntax... not a new kind of gap"), not outside it.

    Round 37's OTHER finding this same round (see
    `_TRUSTED_TRANSPORT_CLASS_CODE_OBJECTS`'s own docstring) shows the
    identical `__code__`-mutation technique IS genuinely defensible
    for `LocalGitRepositoryTransport`/`RepositoryFacility` -- because a
    SEPARATE, EARLIER function (`_revalidate_transport_integrity`)
    exists and can snapshot-compare their code objects BEFORE ever
    delegating to them. THIS wrapper's own dispatch methods have no
    such earlier checkpoint: `create_branch` IS the function whose
    code gets replaced, so by the time it starts running, the
    malicious bytecode is what is already executing -- the same
    "no hook point from within" structural fact round 25/26 already
    established, replaying a third time for a third kind of mutable
    state (instance `__dict__` shadowing, then class-attribute
    rebinding, now a function object's own `__code__`). There is
    consequently no further code-level fix available inside this
    single Python process; the admitted identity's trust model is
    narrowed once more, explicitly, to also exclude a caller mutating
    the `__code__` (or `__defaults__`/`__closure__`/`__globals__`) of
    any function object reachable from the returned wrapper -- the
    same materially different, separately-deliberated undertaking
    (protecting the boundary outside the interpreter) round 27's own
    disclosure already named, not a new kind of gap. See
    `test_sc23_wrapper_dispatch_method_code_object_cannot_be_defended_against_in_process`
    for the permanent, executable record of this disclosed
    limitation."""

    def __setattr__(cls, name, value):
        raise AttributeError(
            f"cannot reassign {name!r} on frozen class {cls.__name__} -- "
            f"class-level tampering is rejected outright, not merely detected"
        )

    def __delattr__(cls, name):
        raise AttributeError(
            f"cannot delete {name!r} on frozen class {cls.__name__} -- "
            f"class-level tampering is rejected outright, not merely detected"
        )


def _current_transport(wrapper: "_ContainmentReCheckedRepositoryFacility") -> LocalGitRepositoryTransport:
    """Review finding (PR #86, round 16, P1, reproduced by the
    reviewer): `RepositoryFacility.create_branch`/`commit` internally
    use `self.transport` (Gen1's own, plain, mutable attribute), not
    any static reference remembered elsewhere. The reviewer reproduced
    reassigning the real facility's own `.transport` to an injected
    object AFTER admission, silently redirecting every subsequent
    mutation. This function reads `.transport` FRESH from the TRUSTED
    facility reference and re-verifies the exact-type check against
    whatever is CURRENTLY there -- so a swap to anything that is not a
    genuine, unmodified `LocalGitRepositoryTransport` is rejected
    outright.

    Round 24 (P1, Codex -- "Check the facility class before reading
    transport"): the read above is only safe once `RepositoryFacility`'s
    own class implementation is confirmed unmodified FIRST, since a
    class-level `__getattribute__` replacement runs the moment ANY
    attribute is read off a genuine instance -- the reviewer reproduced
    exactly this, with the eventual rejection coming too late to
    prevent the side effect.

    Round 25 (see `_ADMITTED_TRANSPORT_STATE`'s own docstring): this
    function used to read `wrapper._facility.transport` -- a plain,
    caller-mutable wrapper attribute -- purely to DISCOVER a registry
    lookup key, which round 24's "Verify the inner facility identity
    before delegation" finding showed was itself an attack surface (a
    wholesale-swapped `_facility` impersonating the right shape). Now
    that the registry is keyed by the WRAPPER itself, `_admitted_state_for(wrapper)`
    needs no bootstrap read at all -- `admitted.facility` (the
    immutable, registry-sourced reference) is read directly, closing
    that entire class of attack rather than merely type-checking
    around it.

    Round 33, P1, Codex, reproduced by the reviewer -- "Stop returning
    the raw transport from the wrapper": this was formerly an INSTANCE
    METHOD (`wrapper._current_transport()`) -- and a leading underscore
    is purely convention, not enforcement (the same lesson rounds 30/31
    already established for instance ATTRIBUTES, now replaying for
    METHODS): the reviewer reproduced calling
    `facility._current_transport()` directly, obtaining the RAW,
    unguarded transport with none of `_revalidate_transport_integrity`'s
    OWN, further checks ever running. A method DEFINED ON THE CLASS is
    always reachable via normal attribute lookup regardless of naming
    -- `__getattr__`'s allowlist (round 33, CodeRabbit) never even gets
    a chance to run for it, since normal lookup finds it FIRST. Moved
    OUT of the class entirely, into this module-level function taking
    `wrapper` as an explicit parameter: there is no attribute named
    `_current_transport` on the wrapper AT ALL anymore, so
    `facility._current_transport` now falls through to `__getattr__`,
    which correctly denies it (not on the allowlist) -- the SAME
    structural fix `__slots__` (round 25) already gave instance
    attributes, now applied to what were previously instance methods.

    SECURITY NOTE -- DISCLOSED LIMITATION (review finding, PR #86,
    round 34, P1, Codex, reproduced by the reviewer -- "Stop module
    helpers from returning the raw transport"): moving this function
    to module scope closes the ORDINARY-ATTRIBUTE-LOOKUP path (round
    33's own finding), but a leading underscore on a MODULE-LEVEL name
    is, just like everywhere else in Python, convention ONLY -- `from
    module import _private_name` has ALWAYS worked, with no way to
    disable it. The reviewer reproduced exactly that: importing this
    function by name and calling `_current_transport(facility)`
    directly. Verified this is WORSE than even that, independently of
    the reviewer's own reproduction: a caller holding ONLY the returned
    `facility` object, with NO explicit import of anything from this
    module at all, can STILL reach this function purely through
    standard-library introspection every Python object exposes by
    construction --
    `sys.modules[type(facility).__module__]._current_transport(facility)`
    -- confirmed empirically. `type(obj).__module__` is a builtin,
    unavoidable property; `sys.modules` is the standard, always-populated
    registry of every module Python has ever loaded (which this one
    necessarily has been, for `facility` to exist at all); once the
    MODULE object is in hand, every one of its top-level names --
    function or otherwise, underscore-prefixed or not -- is an ordinary
    attribute, reachable exactly like any other. This is NOT a new
    category of gap: it is the SAME fundamental property of Python's
    object model already disclosed in round 27 (`type.__setattr__`
    bypassing a metaclass's own `__setattr__`) -- no interpreter-level
    mechanism can make a name defined in this module genuinely
    unreachable from code that already has a reference to ANY object
    this module produced, short of enforcing the boundary OUTSIDE the
    interpreter entirely (OS-level process isolation, a
    capability-sandboxed subprocess), the same materially different,
    separately-deliberated undertaking round 27's own disclosure named.
    Also verified: replacing this module-level function with a CLOSURE
    captured at admission time would not help either -- the closure
    itself would need to live somewhere reachable by the wrapper's own
    methods, which reduces to either an instance attribute (round
    30/31's already-closed, but structurally analogous, losing battle)
    or the SAME module-level reachability this finding just
    demonstrated. There is consequently no further code-level fix
    available. See
    `test_sc23_current_transport_cannot_be_fully_hidden_from_module_introspection`
    for the permanent, executable record of this disclosed limitation,
    matching round 27's `_FrozenClassMeta` precedent exactly."""
    admitted = _admitted_state_for(wrapper)
    _reject_altered_facility_class_implementation()
    # Round 45 (see `_TRUSTED_VALIDATE_LIVE_TASK`'s own module-level
    # comment): re-checked on EVERY revalidation, not merely once at
    # admission -- a `validate_live_task`/`validate_task` rebinding
    # that happens AFTER admission is exactly what the reviewer's own
    # reproduction targeted.
    _reject_altered_authority_validation_globals()
    # Round 52 (see `_TRUSTED_CONTAINMENT_SCAN_MODULE_GLOBALS`'s own
    # module-level comment): re-checked on EVERY revalidation, not
    # merely once at admission -- a `Path.is_symlink` rebinding that
    # happens AFTER admission is exactly what the reviewer's own
    # reproduction targeted.
    _reject_altered_transitive_globals(_TRUSTED_CONTAINMENT_SCAN_MODULE_GLOBALS)
    current = admitted.facility.transport
    _reject_altered_transport_class_implementation()
    if type(current) is not LocalGitRepositoryTransport:
        raise RepositoryConstructionQualificationError(
            f"_current_transport: facility.transport is no longer a real LocalGitRepositoryTransport "
            f"(local-commit-only, per this identity's own admitted scope) -- got {type(current).__name__}"
        )
    return current


def _revalidate_transport_integrity(wrapper: "_ContainmentReCheckedRepositoryFacility") -> "_AdmittedTransportState":
    """Renamed from `_revalidate_before_mutation` (round 22, Codex --
    "Revalidate delegated reads before invoking transport"): `read` is
    not a mutation, but it still delegates through the transport's own
    `_run` helper just like `create_branch`/`commit` do -- the reviewer
    reproduced a class-level `_run` replacement performing an
    out-of-repository write during a fully-authorized `read`, entirely
    bypassing the round 14-21 checks because `read` was never wrapped
    at all, only ever reaching `self._facility.read` via plain
    `__getattr__` delegation. The name no longer implies "mutation
    only."

    Round 33, P1, Codex, reproduced by the reviewer -- "Fully
    revalidate transport state before open_pr": `open_pr`/`merge_pr`
    used to run only `_reject_instance_overridden_transport_methods`
    (a NAME-only check), reasoning that `LocalGitRepositoryTransport`'s
    own real `open_pull_request`/`merge_pull_request` unconditionally
    raise by design, so nothing further could matter. That reasoning
    was INCOMPLETE: `RepositoryFacility.open_pr`/`merge_pr` call
    `self.transport.resolve_ref(...)` BEFORE ever reaching the
    transport's own `open_pull_request`/`merge_pull_request` -- and
    `resolve_ref` itself uses `_run`/`self._git`, which a `_git`
    VALUE change (round 20/28's finding) can compromise regardless of
    what the eventual transport call does. The reviewer reproduced a
    fully authorized `open_pr` invoking a replacement executable during
    `resolve_ref`, an external side effect occurring BEFORE the real
    local transport eventually rejected PR creation. Fixed by
    UNIFYING all five dispatch methods (`create_branch`/`commit`/
    `read`/`open_pr`/`merge_pr`) onto this SAME, fully comprehensive
    check -- closing the entire CLASS of "we assumed a narrower risk
    profile for open_pr/merge_pr" mistakes at once, rather than adding
    yet another special-cased partial check.

    Also moved OUT of the class entirely (see `_current_transport`'s
    own docstring for the identical round-33 finding this function was
    equally exposed to, as a directly-callable instance method) into
    this module-level function taking `wrapper` as an explicit
    parameter -- `_current_transport`'s own class-implementation check
    runs before ever reading `admitted.facility.transport`, and the
    registry lookup below is keyed by `wrapper` itself (round 25),
    which needs no such ordering care at all -- both centralized in
    ONE place instead of duplicated at every call site."""
    transport = _current_transport(wrapper)
    # Round 38 (see `_TRUSTED_GIT_EXECUTABLE_DIGEST`'s own docstring):
    # a pathname-only check needed only one pass, at admission -- a
    # CONTENT check must be repeated every time, since the file at a
    # caller-writable path can be replaced again at any later moment.
    _reject_untrusted_transport_git_executable(transport)
    admitted = _admitted_state_for(wrapper)
    _reject_instance_overridden_facility_methods(admitted.facility)
    _reject_altered_facility_collaborators(admitted.facility, admitted.established_facility_state, admitted.established_facility_authority_store)
    # `_reject_altered_transport_instance_state`'s key-set check is a
    # strict superset of `_reject_instance_overridden_transport_methods`
    # (the established snapshot's own key set is always exactly
    # `_EXPECTED_TRANSPORT_INSTANCE_ATTRIBUTES`, since it was captured
    # only after that check already passed at admission), plus it
    # additionally pins every attribute's VALUE -- so one call here
    # covers both without redundancy.
    _reject_altered_transport_instance_state(transport, admitted.instance_state)
    _reject_symlinked_git_storage_for_every_registered_repository(transport)
    # Performance finding (PR #86, round 14): only pay for a fresh
    # mkdtemp + git-config subprocess spawn per registered repository
    # when the cheap, subprocess-free check finds neutralization
    # genuinely disturbed -- see `_hooks_neutralization_still_intact`'s
    # own docstring. The refreshed dirs are written back into the SAME
    # registry entry (never a wrapper attribute -- see
    # `_AdmittedTransportState`'s own docstring for why).
    if not _hooks_neutralization_still_intact(transport, admitted.no_hooks_dirs):
        # Round 42 (see `_AdmittedTransportState`'s own docstring):
        # `frozen=True` now rejects ordinary field reassignment --
        # this IS the one legitimate, module-private site that needs
        # to refresh `no_hooks_dirs`, so it uses `object.__setattr__`
        # explicitly, the same narrowly-scoped escape hatch this
        # file's other frozen/sealed constructs already reserve for
        # their own internal setup.
        object.__setattr__(admitted, "no_hooks_dirs", _neutralize_hooks_for_every_registered_repository(transport))
    return admitted


class _ContainmentReCheckedRepositoryFacility(metaclass=_FrozenClassMeta):
    """Gen2-owned, transparent wrapper around a real, unmodified
    `RepositoryFacility` -- see `gen1_wrap_repository_construction_facility`'s
    own MUTATION-TIME CONTAINMENT FINDING and ROUND 14 FOLLOW-UP
    FINDINGS docstrings for why this exists.

    ONLY `acquire_writer`/`release_writer` delegate via `__getattr__`
    (round 33 -- see `_ALLOWED_DELEGATED_ATTRIBUTES`'s own docstring
    for why this is an ALLOWLIST, not a denylist): they are METHODS on
    `RepositoryFacility` itself, never exposing a raw collaborator
    object, and touch only lock bookkeeping, never the transport. All
    five real dispatch methods (`create_branch`/`commit`/`read`/
    `open_pr`/`merge_pr` -- unified as of round 33, see
    `_revalidate_transport_integrity`'s own docstring for why
    `open_pr`/`merge_pr` no longer get a narrower check) call the SAME
    module-level `_revalidate_transport_integrity(self)` first, which
    re-runs the real containment scan, the class- and instance-level
    transport-identity checks, the class- and instance-level checks on
    the DELEGATED `RepositoryFacility` itself (round 23 -- see
    `_TRUSTED_FACILITY_CLASS_ATTRIBUTES`'s own docstring), the
    collaborator-identity pin (round 29), AND re-applies hook
    neutralization, before delegating to `admitted.facility` (round 24
    -- see `_AdmittedTransportState`'s own docstring), the immutable,
    registry-sourced `RepositoryFacility` reference. `_current_transport`/
    `_revalidate_transport_integrity` themselves are module-level
    FUNCTIONS, not methods on this class (round 33 -- see
    `_current_transport`'s own docstring for why a leading underscore
    on a METHOD is exactly as unenforced as it is on an attribute).

    Review finding (PR #86, round 25, P1, Codex, reproduced by the
    reviewer -- "Seal the returned wrapper's own dispatch methods"):
    every check above protects the DELEGATED transport and facility --
    but nothing protected THIS wrapper's own dispatch methods. The
    reviewer reproduced `facility.create_branch = malicious_fn`
    (an INSTANCE-level shadow directly on the returned wrapper): Python
    resolves that override without ever calling this class's real
    `create_branch` at all, so NONE of the checks above ever run --
    there is no hook point from WITHIN this class's own code to catch
    an attack that bypasses this class's own code entirely. `__slots__`
    (below) closes this at the language level rather than reactively:
    with no per-instance `__dict__` and a slot set containing only
    `_facility`/`_transport` (plus `__weakref__`, needed because round
    25's `_ADMITTED_TRANSPORT_STATE` re-keying now makes THIS class the
    `WeakKeyDictionary`'s key type, and `__slots__` disables weak-
    referenceability by default unless explicitly included -- self-
    caught when the first version without it failed every admission
    with `TypeError: cannot create weak reference to
    '_ContainmentReCheckedRepositoryFacility' object`), `facility.create_branch
    = malicious_fn` raises `AttributeError` outright -- there is no
    dict for such an override to live in, and slots reserve storage
    only for the names actually declared.

    Review finding (PR #86, round 26, P1, Codex, reproduced by the
    reviewer -- "Seal the wrapper class dispatch surface"): `__slots__`
    only blocks INSTANCE-level shadowing -- `type(facility).create_branch
    = malicious_fn` rebinds the method on the CLASS itself, reachable
    from ANY caller holding `facility` via the built-in `type()`, no
    import required. See `_FrozenClassMeta`'s own docstring for the
    metaclass-based fix (`metaclass=_FrozenClassMeta` above), which
    makes such a reassignment raise `AttributeError` at the attempt,
    the same language-level guarantee `__slots__` gives at the
    instance level, now also at the class level.

    Review finding (PR #86, round 30, P1, Codex, reproduced by the
    reviewer -- "Hide the raw transport from wrapper callers"):
    `_transport` was itself a declared slot -- meaning `facility._transport`
    was directly, PUBLICLY readable by ANY caller holding the wrapper,
    handing them the RAW, unguarded `LocalGitRepositoryTransport`
    instance. The reviewer reproduced calling
    `facility._transport.create_branch(...)` directly: since this
    bypasses the WRAPPER's own dispatch methods entirely, NONE of this
    class's containment, hooks, class-implementation, instance-state,
    or facility-collaborator checks ever ran -- there was never
    anything to bypass in the technical sense (no override, no
    tampering), the raw object was simply handed out, unguarded,
    alongside the checked ones. Investigating WHY `_transport` was a
    slot at all: it was write-only leftover bookkeeping from before
    round 25's redesign (`_current_transport` caching its own return
    value) -- nothing in this class, or anywhere else in this module,
    ever READS `self._transport` (confirmed empirically via a full
    grep of every `._transport` reference before removing it). Fixed
    by removing it entirely, from `__slots__` and from every
    assignment -- there being no slot means `facility._transport`
    raises `AttributeError` outright, closing this the same
    comprehensive way round 25's `__slots__` fix closed instance-level
    method shadowing: not by hiding a value better, but by genuinely
    having nothing left to hide.

    Review finding (PR #86, round 31, P1, Codex, reproduced by the
    reviewer -- "Block delegated access to the raw transport"): round
    30 closed `facility._transport`, but missed the TWO remaining,
    equally direct paths to the SAME raw object -- `_facility` was
    ITSELF still a declared slot, so `facility._facility` was directly
    readable (slots are never "private," underscore naming is purely
    convention, not enforcement -- this is precisely how every round
    22-30 regression TEST in this file reaches in to plant its own
    attack in the first place, a capability this closure record never
    connected to also being a genuine, unprivileged caller's escape
    hatch), handing out the WHOLE inner `RepositoryFacility` -- its own
    real, entirely unguarded `create_branch`/`commit`/`read`/`open_pr`/
    `merge_pr` methods included, none of which carry ANY of this
    module's containment/hooks/authority checks. And even without
    `_facility` directly, `__getattr__`'s blanket delegation exposed
    `facility.transport` too, since `RepositoryFacility` (Gen1's own
    class) itself exposes `transport` as a PUBLIC, unprefixed
    attribute -- the reviewer reproduced calling
    `facility.transport.create_branch(...)` directly, identical in
    effect to round 30's `facility._transport` leak. **Fixed,
    comprehensively rather than by naming individual leaks**: `_facility`
    is removed from `__slots__` entirely (mirroring round 30's own
    `_transport` removal) -- the wrapper instance now carries NO
    attribute at all beyond `__weakref__`, with EVERY piece of real
    state living only in the module-private, wrapper-keyed
    `_ADMITTED_TRANSPORT_STATE` registry. `__getattr__` now reads
    `_admitted_state_for(self).facility` (never a `self.` attribute)
    for its delegation target, AND explicitly denies `"transport"`
    outright -- the one Gen1-exposed name that would otherwise still
    leak the raw object through this same delegation path.
    `state`/`authority_store` remain delegated (their own methods stay
    non-git-mutating, the same already-disclosed scope every prior
    round accepted), and `facility._facility` now correctly raises
    `AttributeError`, since `getattr(admitted.facility, "_facility")`
    finds nothing -- `RepositoryFacility` has no such attribute on
    itself.

    Review finding (PR #86, round 39 -- an independently-launched
    adversarial re-review, run because Codex's own review quota was
    exhausted for this round, filling the same role with the same
    "real repro or it doesn't count" discipline): every check above
    protects THIS class's own class object (`_FrozenClassMeta`) and
    its instances' `__dict__` (`__slots__`) -- but neither protects
    the instance's `__class__` SLOT itself. `facility.__class__ =
    SomeAttackerDefinedClass` is ORDINARY Python syntax (no dunder
    tricks, no `__code__` mutation, no module-private introspection)
    that CPython permits whenever the target class has a
    structurally compatible memory layout -- trivially satisfied by
    an attacker replicating this class's own `__slots__ =
    ("__weakref__",)` layout. This reassignment reaches `type()` for
    every future method lookup WITHOUT ever calling
    `_FrozenClassMeta.__setattr__` (which only fires for assignment
    ON the class object, not on an instance's `__class__` attribute)
    and without touching any function's `__code__` (so round 37's
    disclosed, genuinely unfixable wrapper-method limitation does not
    apply here -- this needed neither of that finding's mechanisms).
    Reproduced: after `facility.__class__ = _MaliciousFacility`, the
    wrapper's own `create_branch` genuinely became the attacker's
    replacement, with the real `create_branch`'s implementation and
    the original class object entirely untouched. A plain
    instance-level `__setattr__`/`__delattr__` override (below)
    intercepts `__class__` reassignment via NORMAL syntax exactly like
    any other instance attribute set, since it dispatches through
    `type(obj).__setattr__` the same way -- confirmed empirically that
    adding it blocks the exact reproduction above. This is the SAME
    "always raise" pattern `_FrozenClassMeta` already uses one level
    up for the class object; now also applied one level down, for the
    instance.

    SECURITY NOTE -- DISCLOSED LIMITATION (review finding, PR #86,
    round 41 -- another independently-launched adversarial re-review,
    filling the same role while Codex's quota was exhausted a second
    time): round 39's own text above originally claimed this fix was
    "genuinely fixable," unlike rounds 27/34/37's disclosed bypasses --
    that claim was WRONG, and this note corrects it. The round-39
    `__setattr__` override is reached only through VIRTUAL DISPATCH,
    exactly like `_FrozenClassMeta.__setattr__` one level up -- calling
    the ROOT implementation directly, `object.__setattr__(facility,
    "__class__", _MaliciousFacility)`, sidesteps it entirely, the
    IDENTICAL structural bypass round 27 already disclosed for the
    class-level freeze, now confirmed to apply equally to the
    instance-level one. Reproduced: `type(facility)` becomes the
    attacker's class and `create_branch` is fully replaced, with none
    of `_revalidate_transport_integrity`'s checks ever running --
    `object.__setattr__` is the root implementation every class
    ultimately inherits, always publicly reachable as a builtin, and
    no override anywhere in the MRO can prevent a caller from invoking
    a LESS-derived implementation of the same dunder by name (round
    27's own reasoning, unchanged one level down). There is
    consequently no further code-level fix available inside this
    single Python process; the admitted identity's trust model is
    narrowed the same way round 27's already is, to a caller using
    Python's NORMAL attribute-access surface, not one deliberately
    invoking a base dunder implementation by name to route around
    virtual dispatch. See
    `test_sc23_wrapper_instance_freeze_cannot_defend_against_a_direct_object_setattr_bypass`
    for the permanent, executable record of this disclosed limitation,
    matching round 27's own precedent for the identical bypass one
    level up."""

    __slots__ = ("__weakref__",)

    def __setattr__(self, name: str, value: object) -> None:
        raise AttributeError(
            f"_ContainmentReCheckedRepositoryFacility: cannot set {name!r} on an admitted instance -- "
            f"instance-level tampering (including __class__ reassignment) is rejected outright"
        )

    def __delattr__(self, name: str) -> None:
        raise AttributeError(
            f"_ContainmentReCheckedRepositoryFacility: cannot delete {name!r} on an admitted instance -- "
            f"instance-level tampering is rejected outright"
        )

    def __init__(self, facility, transport: LocalGitRepositoryTransport) -> None:
        # Round 22 (see `_AdmittedTransportState`'s own docstring):
        # `established_no_hooks_dirs`/`established_instance_state` are
        # deliberately NOT stored here -- any attribute on `self` is
        # reachable (and mutable) by any caller holding this object,
        # which is exactly what let the round-22 finding poison the
        # trusted baseline. They live only in the module-private
        # `_ADMITTED_TRANSPORT_STATE` registry, populated by
        # `gen1_wrap_repository_construction_facility` before this
        # wrapper is ever constructed.
        #
        # Round 30/31 (see this class's own docstring): `transport` and
        # `facility` are, likewise, no longer stored on `self` AT ALL
        # -- `self` carries no instance attribute whatsoever beyond the
        # `__weakref__` slot `__slots__` itself requires. Both
        # parameters stay, unused within `__init__` itself, only
        # because `gen1_wrap_repository_construction_facility` already
        # passes them positionally and changing that call site's arity
        # is not otherwise warranted; `facility` is registered directly
        # into `_ADMITTED_TRANSPORT_STATE` by the caller, not by this
        # constructor.
        pass

    #: Review finding (PR #86, round 33, Major, CodeRabbit -- "Restrict
    #: delegated attributes to an explicit allowlist"): rounds 31/32
    #: built a DENY-list (`transport`/`state`/`authority_store` -- the
    #: SPECIFIC names those two rounds' reviewers happened to
    #: reproduce). The reviewer's own reproduction script proved a
    #: deny-list is STRUCTURALLY THE WRONG SHAPE, the same lesson round
    #: 18 already learned for the transport's own instance-attribute
    #: check ("enumerating specific... names... is a losing,
    #: ever-growing battle"): `wrapper.__dict__` was NOT on the deny
    #: list, so `getattr(self, "__dict__")` fell through to
    #: `__getattr__` and returned `admitted.facility.__dict__` -- the
    #: REAL `RepositoryFacility`'s OWN instance dict, containing
    #: `transport`/`state`/`authority_store` UNFILTERED, completely
    #: bypassing the deny-list without naming any denied attribute at
    #: all. Only TWO names have any genuine, in-codebase reason to be
    #: delegated at all -- `acquire_writer`/`release_writer`, METHODS on
    #: `RepositoryFacility` ITSELF that never expose a raw collaborator
    #: object and touch only lock bookkeeping, never the transport --
    #: so this is now an ALLOW-list instead: every OTHER name, known or
    #: not yet discovered, is rejected by default.
    _ALLOWED_DELEGATED_ATTRIBUTES = frozenset({"acquire_writer", "release_writer"})

    def __getattr__(self, name):
        if name not in self._ALLOWED_DELEGATED_ATTRIBUTES:
            raise AttributeError(
                f"_ContainmentReCheckedRepositoryFacility.{name}: this attribute is not delegated -- "
                f"use create_branch/commit/read/open_pr/merge_pr instead, which revalidate before delegating"
            )
        # Review finding (PR #86, round 35, P1, Codex, reproduced by
        # the reviewer -- "Revalidate allowlisted writer methods
        # before delegation"): `acquire_writer`/`release_writer` were
        # delegated via a bare `getattr(admitted.facility, name)`,
        # never calling `_revalidate_transport_integrity` the way all
        # five dispatch methods do. The reviewer reproduced rebinding
        # `RepositoryFacility.acquire_writer` at the CLASS level, then
        # calling `facility.acquire_writer(...)` -- the injected
        # method ran and returned successfully, entirely bypassing
        # `_reject_altered_facility_class_implementation`, even though
        # that exact same tampering is rejected by every one of the
        # other five delegated methods. Fixed by running the SAME
        # full revalidation here before returning the bound method --
        # matching every other delegation path in this class rather
        # than special-casing these two as "lock bookkeeping only,
        # nothing to check."
        admitted = _revalidate_transport_integrity(self)
        return getattr(admitted.facility, name)

    def create_branch(self, *args, **kwargs):
        # Round 24 (see `_AdmittedTransportState`'s own docstring):
        # delegates to `admitted.facility` -- the immutable,
        # registry-sourced reference -- never to `self._facility`,
        # which a caller can freely reassign. Round 33 (see
        # `_revalidate_transport_integrity`'s own docstring): all FIVE
        # dispatch methods now call the SAME, fully comprehensive
        # check, unifying what used to be a narrower check for
        # `open_pr`/`merge_pr`.
        admitted = _revalidate_transport_integrity(self)
        return admitted.facility.create_branch(*args, **kwargs)

    def commit(self, *args, **kwargs):
        admitted = _revalidate_transport_integrity(self)
        return admitted.facility.commit(*args, **kwargs)

    def read(self, *args, **kwargs):
        admitted = _revalidate_transport_integrity(self)
        return admitted.facility.read(*args, **kwargs)

    def open_pr(self, *args, **kwargs):
        admitted = _revalidate_transport_integrity(self)
        return admitted.facility.open_pr(*args, **kwargs)

    def merge_pr(self, *args, **kwargs):
        admitted = _revalidate_transport_integrity(self)
        return admitted.facility.merge_pr(*args, **kwargs)


class _MutableAuthorityStore:
    """Gen2-owned, disposable, in-memory `CampaignAuthorityStore` stand-in
    -- Python-only simulation/harness infrastructure (G2-00 SS4: "Python
    may own: simulation and analysis"), never a re-derivation of Gen1's
    real authority-checking logic. `validate_live_task` remains genuinely
    called, unmodified, against whatever snapshot this store currently
    holds; the harness only controls which snapshot that is."""

    def __init__(self, snapshot: CampaignSnapshot) -> None:
        self.snapshot = snapshot

    def read(self, campaign_id: str) -> CampaignSnapshot:
        return self.snapshot


@dataclass
class DisposableRepositoryConstructionRig:
    facility: _ContainmentReCheckedRepositoryFacility
    transport: LocalGitRepositoryTransport
    authority_store: _MutableAuthorityStore
    repository: str
    initial_sha: str
    repo_root: Path
    #: The real, on-disk SQLite receipts database path -- durable across
    #: a fresh `RepositoryStateStore`/`RepositoryFacility` instance, so a
    #: genuine takeover scenario can reconstruct state from disk rather
    #: than merely reusing the same in-memory objects.
    state_db_path: Path


def _run_git(root: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True)


def list_branches(rig: DisposableRepositoryConstructionRig) -> tuple[str, ...]:
    """Real, Gen2-owned branch-enumeration capability for this identity.

    Review finding (PR #84, round 2): Gen1's real `RepositoryFacility`
    exposes NO enumeration operation at all (`create_branch`/`read`/
    `commit`/`open_pr`/`merge_pr`/`acquire_writer`/`release_writer`
    only), and neither does `LocalGitRepositoryTransport`. A production
    caller of the admitted Facility genuinely could not enumerate its
    own mutation domain -- so `ENUMERATION_COMPLETENESS` cannot be
    honestly exercised by bypassing the Facility with raw git calls
    that a real caller would never have access to. This function makes
    enumeration a genuine, disclosed, Gen2-owned addition this specific
    identity's Facility interface provides (operating through the same
    real transport-bound repository, never a re-derivation of Gen1's
    own admission/mutation logic) -- the harness below uses THIS
    function, not an ad-hoc bypass, as the qualified observation path."""
    output = subprocess.run(["git", "-C", str(rig.repo_root), "for-each-ref", "--format=%(refname:short)", "refs/heads"], check=True, capture_output=True, text=True).stdout.split()
    return tuple(sorted(output))


def tree_files_at(rig: DisposableRepositoryConstructionRig, sha: str) -> frozenset[str]:
    """Real, Gen2-owned tree-enumeration capability -- same rationale as
    `list_branches` (review finding, PR #84, round 5): checking a
    single requested blob's content does not prove the COMPLETE
    resulting tree equals the requested parent-plus-patch; an
    unexpected extra file (or a missing one) would pass a single-blob
    check while still being a genuine reconciliation failure."""
    output = subprocess.run(["git", "-C", str(rig.repo_root), "ls-tree", "-r", "--name-only", sha], check=True, capture_output=True, text=True).stdout.split()
    return frozenset(output)


def tree_entries_at(rig: DisposableRepositoryConstructionRig, sha: str) -> frozenset[tuple[str, str, str]]:
    """Review finding (PR #84, round 8, reproduced by the reviewer):
    `tree_files_at` alone compares only PATH NAMES, not content -- a
    commit that corrupts an existing file's content while keeping the
    same path SET (e.g. silently rewriting `README.md` while adding the
    requested new file) would still pass a names-only comparison. This
    returns `(path, mode, blob_sha)` triples (via real `git ls-tree -r`,
    which reports each entry's own mode and blob object hash) so
    callers can compare the COMPLETE tree -- paths, content, AND mode
    -- against the expected parent-plus-patch tree.

    MODE FINDING (review finding, PR #84, round 10, P1, reproduced by
    the reviewer): the original two-element `(path, blob_sha)` tuple
    discarded each entry's MODE -- a commit that changed an existing
    file's mode (e.g. `README.md` from `100644` to `100755`, an
    executable-bit flip) while keeping the same path and blob would
    still compare equal under a names-and-content-only check. Mode is
    now included so a mode-only change is genuinely detected too."""
    output = subprocess.run(["git", "-C", str(rig.repo_root), "ls-tree", "-r", sha], check=True, capture_output=True, text=True).stdout.splitlines()
    entries: set[tuple[str, str, str]] = set()
    for line in output:
        # "<mode> <type> <blob-sha>\t<path>"
        meta, path = line.split("\t", 1)
        mode, _entry_type, blob_sha = meta.split()
        entries.add((path, mode, blob_sha))
    return frozenset(entries)


def real_commit_parent(rig: DisposableRepositoryConstructionRig, sha: str) -> str | None:
    """Review finding (PR #84, round 12, P1, reproduced by the
    reviewer): a complete-tree match alone does not prove the landed
    commit is genuinely a CHILD of the requested `expected_head` -- a
    faulty (or adversarial) `commit_files` could replace the landed
    commit with an unrelated ROOT commit (no parent, or the wrong
    parent) that merely happens to carry the exact expected tree,
    silently corrupting the branch's real history while still passing
    a tree-only check. Returns the real first-parent SHA via `git
    rev-parse <sha>^`, or `None` if `sha` has no parent (a root
    commit) -- a reconciling caller must confirm this equals the
    original `expected_head` before treating the mutation as genuinely
    matching what was requested."""
    result = subprocess.run(["git", "-C", str(rig.repo_root), "rev-parse", f"{sha}^"], capture_output=True, text=True)
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def real_commit_message(rig: DisposableRepositoryConstructionRig, sha: str) -> str:
    """Companion to `real_commit_parent`: returns the EXACT, real commit
    message stored in the commit object (via `git cat-file -p`, taking
    everything after the header/body blank-line separator -- unlike
    `git log --format=%B`, which appends its own extra trailing
    newline not present in the stored object)."""
    raw = subprocess.run(["git", "-C", str(rig.repo_root), "cat-file", "-p", sha], check=True, capture_output=True, text=True).stdout
    _header, _separator, message = raw.partition("\n\n")
    return message


def build_disposable_local_git_facility(tmp_dir: Path) -> DisposableRepositoryConstructionRig:
    """Real (if disposable) local git mutation, never a canonical/
    production repository: a fresh, throwaway repo under `tmp_dir`,
    created and destroyed per qualification run."""
    repo_root = tmp_dir / "scratch-repo"
    repo_root.mkdir()
    _run_git(repo_root, "init", "-b", "main")
    _run_git(repo_root, "config", "user.name", "tenfold-gen2-sc23")
    _run_git(repo_root, "config", "user.email", "tenfold-gen2-sc23@local.invalid")
    # Review finding (PR #84, round 4): the real `git update-ref` calls
    # create_branch/commit_files internally make (via
    # LocalGitRepositoryTransport) fire repository-controlled hooks
    # (e.g. reference-transaction) regardless of any file-path scope
    # check -- a genuinely unbounded external-effect vector no scope
    # check can contain, confirmed reproducible by the reviewer.
    # core.hooksPath is a repo-local git config setting; redirecting it
    # to a fresh, permanently-empty directory genuinely, durably
    # disables every hook for this repository's entire lifetime,
    # including operations made through LocalGitRepositoryTransport
    # (whose own environment sandboxing does not otherwise touch
    # hooksPath).
    no_hooks_dir = tmp_dir / "no-hooks"
    no_hooks_dir.mkdir()
    _run_git(repo_root, "config", "core.hooksPath", str(no_hooks_dir))
    (repo_root / "README.md").write_text("gen2 sc23 disposable scratch repository\n", encoding="utf-8")
    _run_git(repo_root, "add", "README.md")
    _run_git(repo_root, "commit", "-m", "initial")

    transport = LocalGitRepositoryTransport({REPOSITORY_NAME: repo_root})
    initial_sha = transport.resolve_ref(REPOSITORY_NAME, "main")

    state_db_path = tmp_dir / "repo-state.db"
    state_store = RepositoryStateStore(str(state_db_path))
    snapshot = _empty_snapshot(campaign_generation=1, foreman_epoch=1)
    authority_store = _MutableAuthorityStore(snapshot)

    facility = gen1_wrap_repository_construction_facility(transport, state_store, authority_store)
    return DisposableRepositoryConstructionRig(facility, transport, authority_store, REPOSITORY_NAME, initial_sha, repo_root, state_db_path)


def _empty_snapshot(
    *,
    campaign_generation: int,
    foreman_epoch: int,
    node_state: NodeState = NodeState.RUNNING,
    assignments: tuple[AssignmentRef, ...] = (),
    leases: tuple[WriteLease, ...] = (),
) -> CampaignSnapshot:
    return CampaignSnapshot(
        campaign_id=CAMPAIGN_ID,
        campaign_generation=campaign_generation,
        campaign_digest="0" * 64,
        blueprint_generation=1,
        blueprint_digest="0" * 64,
        matrix_generation=1,
        matrix_digest="0" * 64,
        campaign_payload="{}",
        foreman_epoch=foreman_epoch,
        node_states=((NODE_ID, node_state.value),),
        assignments=assignments,
        leases=leases,
    )


def _file_digests(files: dict[str, bytes]) -> dict[str, str]:
    """Independently recomputes what `RepositoryFacility.commit`'s own
    real request-binding digest will be, mirroring its own private
    `_file_digests` (`stable_digest(data.hex())` -- JSON-encodes the hex
    string, sorted/compact-separated, before hashing) -- a legitimate
    caller must know its own request ahead of sealing the dispatching
    task, since `request_binding` fences the task to one exact,
    pre-known request."""
    return {path: sha256(json.dumps(data.hex(), sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest() for path, data in sorted(files.items())}


def _dispatch(
    rig: DisposableRepositoryConstructionRig,
    *,
    assignment_id: str,
    attempt: int,
    campaign_generation: int,
    foreman_epoch: int,
    lease_epoch: int,
    lease_generation: int,
    resource: str,
    request_binding: str,
    require_lease: bool = True,
    # `_path_in_scope`'s own semantics: an EMPTY scope tuple matches
    # NOTHING (the for-loop never runs); `("",)` -- a scope entry whose
    # own parts are empty -- is what genuinely means "every path is in
    # scope." Default here is full access; the EFFECT_REACH scenario
    # passes a genuinely narrow scope to prove escape-detection.
    scope: tuple[str, ...] = ("",),
) -> TaskPacket:
    """Builds one genuinely-sealed dispatch (task + matching active lease
    + durable assignment + snapshot) and sets it as the rig's current
    authority state -- the same real fencing fields Gen1's own
    `validate_live_task` independently checks (campaign generation,
    Foreman epoch, durable assignment, lease ownership/fencing token)."""
    lease = WriteLease(
        lease_id=f"lease-{assignment_id}",
        campaign_id=CAMPAIGN_ID,
        campaign_generation=campaign_generation,
        epoch=lease_epoch,
        generation=lease_generation,
        owner_lane=assignment_id,
        namespace="gen2-sc23-scratch",
        surfaces=(resource,),
        resources=(resource,),
        active=True,
    )
    task = TaskPacket(
        task_id=f"task-{assignment_id}",
        campaign_id=CAMPAIGN_ID,
        campaign_generation=campaign_generation,
        node_id=NODE_ID,
        assignment_id=assignment_id,
        attempt=attempt,
        objective="sc23-repository-construction-qualification",
        scope=scope,
        capabilities=(RepositoryFacility.write_capability, RepositoryFacility.read_capability),
        permissions=("write", "read"),
        evidence_obligations=(),
        stop_conditions=(),
        reporting_officer="sc23-closure",
        source_binding="gen2-sc23-scratch-source",
        foreman_epoch=foreman_epoch,
        lease_id=lease.lease_id if require_lease else "",
        lease_epoch=lease_epoch if require_lease else 0,
        lease_generation=lease_generation if require_lease else 0,
        request_binding=request_binding,
    ).sealed()

    assignment = AssignmentRef(
        assignment_id=assignment_id,
        task_id=task.task_id,
        node_id=NODE_ID,
        attempt=attempt,
        status="active",
        dispatch_digest=task.dispatch_digest,
    )
    rig.authority_store.snapshot = _empty_snapshot(
        campaign_generation=campaign_generation,
        foreman_epoch=foreman_epoch,
        assignments=(assignment,),
        leases=(lease,) if require_lease else (),
    )
    return task


class RepositoryConstructionQualificationError(RuntimeError):
    pass


@dataclass(frozen=True)
class RepositoryConstructionScenarioResult:
    scenario_id: str
    property: FacilityProperty
    state: QualificationState
    evidence_refs: tuple[str, ...]
    detail: str
    bound_description: str | None = None


class RepositoryConstructionPropertyQualificationHarness:
    """Runs G2-00 SS9.1's adversarial corpus against a real
    `RepositoryFacility` operating on a real, disposable local git
    repository. One real scenario per `FacilityProperty` -- never a
    printed checklist."""

    def __init__(self, rig: DisposableRepositoryConstructionRig):
        self.rig = rig

    def run_duplicate_key_scenario(self) -> RepositoryConstructionScenarioResult:
        # create_branch's own fence (base_ref must still resolve to
        # expected_base_sha) does not move as a result of branching, so a
        # genuine identical retry reaches the real idempotent-receipt
        # path, unlike commit (whose own fence is the branch's own head,
        # which the operation itself moves).
        request = {"operation_id": "op-duplicate-key", "repository": self.rig.repository, "branch": "sc23/duplicate-key", "owner": "assign-dup", "base_ref": "main", "expected_base_sha": self.rig.initial_sha}
        binding = repository_request_binding("create_branch", **request)
        resource = repository_ref_resource(self.rig.repository, request["branch"])

        task1 = _dispatch(self.rig, assignment_id="assign-dup", attempt=1, campaign_generation=1, foreman_epoch=1, lease_epoch=1, lease_generation=1, resource=resource, request_binding=binding)
        receipt1 = self.rig.facility.create_branch(task1, repository=request["repository"], branch=request["branch"], owner=request["owner"], base_ref=request["base_ref"], expected_base_sha=request["expected_base_sha"], operation_id=request["operation_id"], foreman_epoch=1)

        task2 = _dispatch(self.rig, assignment_id="assign-dup", attempt=2, campaign_generation=1, foreman_epoch=1, lease_epoch=1, lease_generation=1, resource=resource, request_binding=binding)
        receipt2 = self.rig.facility.create_branch(task2, repository=request["repository"], branch=request["branch"], owner=request["owner"], base_ref=request["base_ref"], expected_base_sha=request["expected_base_sha"], operation_id=request["operation_id"], foreman_epoch=1)

        idempotent = receipt1 == receipt2
        state = QualificationState.QUALIFIED if idempotent else QualificationState.UNQUALIFIED
        return RepositoryConstructionScenarioResult("duplicate-key", FacilityProperty.DUPLICATE_KEY_BEHAVIOR, state, ("create-branch-twice-same-operation-id",), f"idempotent={idempotent}")

    def run_idempotency_two_sided_scenario(self) -> RepositoryConstructionScenarioResult:
        # The other side of idempotency: reusing an operation_id with a
        # genuinely DIFFERENT request must be rejected, not silently
        # accepted as "the same retry."
        request = {"operation_id": "op-idempotency", "repository": self.rig.repository, "branch": "sc23/idempotency", "owner": "assign-idem", "base_ref": "main", "expected_base_sha": self.rig.initial_sha}
        binding1 = repository_request_binding("create_branch", **request)
        resource = repository_ref_resource(self.rig.repository, request["branch"])
        task1 = _dispatch(self.rig, assignment_id="assign-idem", attempt=1, campaign_generation=1, foreman_epoch=1, lease_epoch=1, lease_generation=1, resource=resource, request_binding=binding1)
        self.rig.facility.create_branch(task1, repository=request["repository"], branch=request["branch"], owner=request["owner"], base_ref=request["base_ref"], expected_base_sha=request["expected_base_sha"], operation_id=request["operation_id"], foreman_epoch=1)

        other_branch = "sc23/idempotency-different"
        other_request = {**request, "branch": other_branch}
        binding2 = repository_request_binding("create_branch", **other_request)
        other_resource = repository_ref_resource(self.rig.repository, other_branch)
        task2 = _dispatch(self.rig, assignment_id="assign-idem", attempt=2, campaign_generation=1, foreman_epoch=1, lease_epoch=1, lease_generation=1, resource=other_resource, request_binding=binding2)
        rejected = False
        try:
            self.rig.facility.create_branch(task2, repository=other_request["repository"], branch=other_request["branch"], owner=other_request["owner"], base_ref=other_request["base_ref"], expected_base_sha=other_request["expected_base_sha"], operation_id=request["operation_id"], foreman_epoch=1)
        except Gen1RepositoryFacilityError:
            rejected = True
        state = QualificationState.QUALIFIED if rejected else QualificationState.UNQUALIFIED
        return RepositoryConstructionScenarioResult("idempotency-reused-operation-id-different-request", FacilityProperty.IDEMPOTENCY, state, ("reused-operation-id-different-branch-rejected",), f"rejected={rejected}")

    def run_stale_expected_head_non_occurrence_scenario(self) -> RepositoryConstructionScenarioResult:
        request = {"operation_id": "op-non-occurrence", "repository": self.rig.repository, "branch": "sc23/non-occurrence", "owner": "assign-nonocc", "base_ref": "main", "expected_base_sha": self.rig.initial_sha}
        binding = repository_request_binding("create_branch", **request)
        resource = repository_ref_resource(self.rig.repository, request["branch"])
        task = _dispatch(self.rig, assignment_id="assign-nonocc", attempt=1, campaign_generation=1, foreman_epoch=1, lease_epoch=1, lease_generation=1, resource=resource, request_binding=binding)
        self.rig.facility.create_branch(task, repository=request["repository"], branch=request["branch"], owner=request["owner"], base_ref=request["base_ref"], expected_base_sha=request["expected_base_sha"], operation_id=request["operation_id"], foreman_epoch=1)
        branch_sha = self.rig.transport.resolve_ref(self.rig.repository, request["branch"])

        # Deliberately WRONG expected_head (not merely "used to be
        # current" -- a fabricated SHA that never matches the branch's
        # real current head), proving the fence rejects any mismatch, not
        # only a specific stale-but-once-valid value.
        wrong_head = "0" * 40
        commit_request = {"operation_id": "op-non-occurrence-commit", "repository": self.rig.repository, "branch": request["branch"], "owner": "assign-nonocc", "expected_head": wrong_head, "files": _file_digests({"nonocc.txt": b"x"}), "message": "should not land\n"}
        commit_binding = repository_request_binding("commit", **commit_request)
        commit_task = _dispatch(self.rig, assignment_id="assign-nonocc", attempt=2, campaign_generation=1, foreman_epoch=1, lease_epoch=1, lease_generation=1, resource=resource, request_binding=commit_binding)
        rejected = False
        try:
            self.rig.facility.commit(commit_task, repository=self.rig.repository, branch=request["branch"], owner="assign-nonocc", expected_head=wrong_head, files={"nonocc.txt": b"x"}, message="should not land\n", operation_id="op-non-occurrence-commit", foreman_epoch=1)
        except Gen1RepositoryFacilityError:
            rejected = True
        genuinely_unmoved = self.rig.transport.resolve_ref(self.rig.repository, request["branch"]) == branch_sha
        state = QualificationState.QUALIFIED if (rejected and genuinely_unmoved) else QualificationState.UNQUALIFIED
        return RepositoryConstructionScenarioResult("stale-expected-head-non-occurrence", FacilityProperty.NON_OCCURRENCE_SIGNAL, state, ("wrong-expected-head-commit-rejected", "branch-genuinely-unmoved"), f"rejected={rejected} genuinely_unmoved={genuinely_unmoved}")

    def run_enumeration_falsification_scenario(self) -> RepositoryConstructionScenarioResult:
        request = {"operation_id": "op-enum", "repository": self.rig.repository, "branch": "sc23/enum", "owner": "assign-enum", "base_ref": "main", "expected_base_sha": self.rig.initial_sha}
        binding = repository_request_binding("create_branch", **request)
        resource = repository_ref_resource(self.rig.repository, request["branch"])
        task = _dispatch(self.rig, assignment_id="assign-enum", attempt=1, campaign_generation=1, foreman_epoch=1, lease_epoch=1, lease_generation=1, resource=resource, request_binding=binding)
        self.rig.facility.create_branch(task, repository=request["repository"], branch=request["branch"], owner=request["owner"], base_ref=request["base_ref"], expected_base_sha=request["expected_base_sha"], operation_id=request["operation_id"], foreman_epoch=1)
        tracked_writer = _admitted_state_for(self.rig.facility).facility.state.writer(self.rig.repository, request["branch"])

        # Out-of-band ref, created directly via raw git (a real caller
        # would not have this authority; simulating an attacker/foreign
        # process, not the Facility itself) -- mirrors LocalSandboxFacility's
        # own attach_out_of_band falsification-detection pattern.
        _run_git(self.rig.repo_root, "branch", "sc23/out-of-band", self.rig.initial_sha)
        # Detection goes through this identity's own genuine,
        # Gen2-owned enumeration capability (list_branches), not a
        # bypass of the admitted Facility (review finding, PR #84).
        enumerated_refs = list_branches(self.rig)

        detected_in_raw_enumeration = "sc23/out-of-band" in enumerated_refs
        not_conflated_as_facility_tracked = _admitted_state_for(self.rig.facility).facility.state.writer(self.rig.repository, "sc23/out-of-band") is None
        genuinely_tracked = tracked_writer == task.assignment_id
        ok = detected_in_raw_enumeration and not_conflated_as_facility_tracked and genuinely_tracked
        state = QualificationState.QUALIFIED if ok else QualificationState.UNQUALIFIED
        return RepositoryConstructionScenarioResult(
            "enumeration-falsification",
            FacilityProperty.ENUMERATION_COMPLETENESS,
            state,
            ("out-of-band-branch-created-then-enumerated", "facility-tracked-writer-not-conflated"),
            f"detected={detected_in_raw_enumeration} not_conflated={not_conflated_as_facility_tracked} tracked={genuinely_tracked}",
        )

    def run_observation_semantics_scenario(self) -> RepositoryConstructionScenarioResult:
        read_request = {"request_id": "req-observe", "repository": self.rig.repository, "path": "README.md", "ref": "main", "expected_sha": self.rig.initial_sha}
        binding = repository_request_binding("read", **read_request)
        resource = repository_ref_resource(self.rig.repository, "main")
        task = _dispatch(self.rig, assignment_id="assign-observe", attempt=1, campaign_generation=1, foreman_epoch=1, lease_epoch=1, lease_generation=1, resource=resource, request_binding=binding, require_lease=False)
        content, _evidence = self.rig.facility.read(task, repository=self.rig.repository, path="README.md", ref="main", expected_sha=self.rig.initial_sha, request_id="req-observe", foreman_epoch=1)
        genuine_read = content == b"gen2 sc23 disposable scratch repository\n"

        stale_request = {"request_id": "req-observe-stale", "repository": self.rig.repository, "path": "README.md", "ref": "main", "expected_sha": "0" * 40}
        stale_binding = repository_request_binding("read", **stale_request)
        stale_task = _dispatch(self.rig, assignment_id="assign-observe", attempt=2, campaign_generation=1, foreman_epoch=1, lease_epoch=1, lease_generation=1, resource=resource, request_binding=stale_binding, require_lease=False)
        rejected = False
        try:
            self.rig.facility.read(stale_task, repository=self.rig.repository, path="README.md", ref="main", expected_sha="0" * 40, request_id="req-observe-stale", foreman_epoch=1)
        except Gen1RepositoryFacilityError:
            rejected = True
        ok = genuine_read and rejected
        state = QualificationState.QUALIFIED if ok else QualificationState.UNQUALIFIED
        return RepositoryConstructionScenarioResult("observation-semantics", FacilityProperty.OBSERVATION_SEMANTICS, state, ("genuine-read-matches-content", "stale-expected-sha-rejected"), f"genuine_read={genuine_read} rejected={rejected}")

    def run_effect_reach_scenario(self) -> RepositoryConstructionScenarioResult:
        request = {"operation_id": "op-reach", "repository": self.rig.repository, "branch": "sc23/reach", "owner": "assign-reach", "base_ref": "main", "expected_base_sha": self.rig.initial_sha}
        binding = repository_request_binding("create_branch", **request)
        resource = repository_ref_resource(self.rig.repository, request["branch"])
        task = _dispatch(self.rig, assignment_id="assign-reach", attempt=1, campaign_generation=1, foreman_epoch=1, lease_epoch=1, lease_generation=1, resource=resource, request_binding=binding)
        self.rig.facility.create_branch(task, repository=request["repository"], branch=request["branch"], owner=request["owner"], base_ref=request["base_ref"], expected_base_sha=request["expected_base_sha"], operation_id=request["operation_id"], foreman_epoch=1)

        # A genuinely narrow declared scope ("allowed/" only) and a
        # write attempt outside it -- exercises the real scope-boundary
        # comparison (target prefix vs. allowed prefix), not merely the
        # separate ".."-traversal special case.
        escaping_files = {"not-allowed/escape.txt": b"escape"}
        commit_request = {"operation_id": "op-reach-commit", "repository": self.rig.repository, "branch": request["branch"], "owner": "assign-reach", "expected_head": self.rig.initial_sha, "files": _file_digests(escaping_files), "message": "escape\n"}
        commit_binding = repository_request_binding("commit", **commit_request)
        commit_task = _dispatch(self.rig, assignment_id="assign-reach", attempt=2, campaign_generation=1, foreman_epoch=1, lease_epoch=1, lease_generation=1, resource=resource, request_binding=commit_binding, scope=("allowed",))
        rejected = False
        try:
            self.rig.facility.commit(commit_task, repository=self.rig.repository, branch=request["branch"], owner="assign-reach", expected_head=self.rig.initial_sha, files=escaping_files, message="escape\n", operation_id="op-reach-commit", foreman_epoch=1)
        except Gen1RepositoryFacilityError:
            rejected = True

        # Review finding (PR #84, round 4, reproduced by the reviewer):
        # `git update-ref` (invoked internally by create_branch/
        # commit_files) fires repository-controlled hooks (e.g.
        # reference-transaction) regardless of any file-path scope
        # check -- a genuinely unbounded external-effect vector no
        # scope check can contain. A positive control first proves the
        # hook mechanism itself is real (a genuinely separate,
        # throwaway repo WITHOUT hooksPath neutralization, where the
        # same hook genuinely fires), then confirms the admitted
        # Facility's own real create_branch call against THIS rig's
        # repository (which has core.hooksPath redirected at
        # construction time) does not trigger it.
        if not self._git_supports_reference_transaction_hook():
            raise RepositoryConstructionQualificationError(
                "the installed git toolchain does not support the reference-transaction hook (needs Git >= 2.28) -- "
                "cannot genuinely qualify EFFECT_REACH's hook-neutralization control on this environment; this is a "
                "real toolchain limitation, not evidence that neutralization is broken or unnecessary"
            )
        hook_mechanism_confirmed_real = self._probe_reference_transaction_hook_fires_without_neutralization()
        hooks_neutralized_on_admitted_repository = self._probe_reference_transaction_hook_does_not_fire_on_rig()

        ok = rejected and hook_mechanism_confirmed_real and hooks_neutralized_on_admitted_repository
        state = QualificationState.QUALIFIED if ok else QualificationState.UNQUALIFIED
        return RepositoryConstructionScenarioResult(
            "effect-reach",
            FacilityProperty.EFFECT_REACH,
            state,
            ("out-of-scope-commit-path-rejected", "reference-transaction-hook-mechanism-confirmed-real", "hooks-genuinely-neutralized-on-the-admitted-repository"),
            f"rejected={rejected} hook_mechanism_confirmed_real={hook_mechanism_confirmed_real} hooks_neutralized_on_admitted_repository={hooks_neutralized_on_admitted_repository}",
        )

    _REFERENCE_TRANSACTION_HOOK_SCRIPT = "#!/bin/sh\necho fired > \"$MARKER_PATH\"\nexit 0\n"

    def _install_reference_transaction_hook(self, hooks_dir: Path, marker_path: Path) -> None:
        hooks_dir.mkdir(parents=True, exist_ok=True)
        hook_path = hooks_dir / "reference-transaction"
        hook_path.write_text(self._REFERENCE_TRANSACTION_HOOK_SCRIPT, encoding="utf-8")
        hook_path.chmod(0o755)
        _ = marker_path  # documents intent; the marker path is passed via MARKER_PATH env at invocation time

    @staticmethod
    def _git_supports_reference_transaction_hook() -> bool:
        """Review finding (PR #84, round 6, CodeRabbit): the
        `reference-transaction` hook was only added in real Git 2.28
        (2020). On an older git toolchain the hook mechanism genuinely
        does not exist, so the positive-control probe would correctly
        never fire -- an environment/toolchain limitation, not evidence
        that neutralization is broken. Detected explicitly so
        `run_effect_reach_scenario` can raise a clear, honest error
        instead of silently reporting a wrong-reason UNQUALIFIED."""
        output = subprocess.run(["git", "--version"], check=True, capture_output=True, text=True).stdout.strip()
        match = re.search(r"(\d+)\.(\d+)\.(\d+)", output)
        if not match:
            return False
        major, minor, _patch = (int(x) for x in match.groups())
        return (major, minor) >= (2, 28)

    def _probe_reference_transaction_hook_fires_without_neutralization(self) -> bool:
        """Positive control: a genuinely separate, throwaway repository
        (never `self.rig`'s own), with NO `core.hooksPath` redirect,
        proving the reference-transaction hook mechanism itself is real
        -- not merely assumed."""
        with tempfile.TemporaryDirectory(prefix="tenfold-gen2-sc23-hook-probe-") as probe_dir_str:
            probe_dir = Path(probe_dir_str)
            probe_repo = probe_dir / "probe-repo"
            probe_repo.mkdir()
            marker_path = probe_dir / "hook-fired-marker.txt"
            _run_git(probe_repo, "init", "-b", "main")
            _run_git(probe_repo, "config", "user.name", "tenfold-gen2-sc23-probe")
            _run_git(probe_repo, "config", "user.email", "tenfold-gen2-sc23-probe@local.invalid")
            self._install_reference_transaction_hook(probe_repo / ".git" / "hooks", marker_path)
            (probe_repo / "README.md").write_text("probe\n", encoding="utf-8")
            _run_git(probe_repo, "add", "README.md")
            env = {**os.environ, "MARKER_PATH": str(marker_path)}
            subprocess.run(["git", "-C", str(probe_repo), "commit", "-m", "initial"], check=True, capture_output=True, env=env)
            return marker_path.exists()

    def _probe_reference_transaction_hook_does_not_fire_on_rig(self) -> bool:
        """Confirms the admitted Facility's own repository (hooks
        neutralized via `core.hooksPath` at construction time) does not
        trigger a real hook, via a genuine Facility-driven create_branch
        call -- not a raw, bypassing git invocation."""
        marker_path = self.rig.repo_root.parent / "rig-hook-fired-marker.txt"
        if marker_path.exists():
            marker_path.unlink()
        # core.hooksPath already redirects away from .git/hooks for this
        # repo; installing the script there is a genuine negative
        # control confirming redirection, not merely absence of a hook.
        self._install_reference_transaction_hook(self.rig.repo_root / ".git" / "hooks", marker_path)

        probe_request = {"operation_id": "op-hook-probe", "repository": self.rig.repository, "branch": "sc23/hook-probe", "owner": "assign-hook-probe", "base_ref": "main", "expected_base_sha": self.rig.initial_sha}
        binding = repository_request_binding("create_branch", **probe_request)
        resource = repository_ref_resource(self.rig.repository, "sc23/hook-probe")
        task = _dispatch(self.rig, assignment_id="assign-hook-probe", attempt=1, campaign_generation=1, foreman_epoch=1, lease_epoch=1, lease_generation=1, resource=resource, request_binding=binding)

        os.environ["MARKER_PATH"] = str(marker_path)
        try:
            self.rig.facility.create_branch(task, repository=probe_request["repository"], branch="sc23/hook-probe", owner="assign-hook-probe", base_ref="main", expected_base_sha=self.rig.initial_sha, operation_id="op-hook-probe", foreman_epoch=1)
        finally:
            os.environ.pop("MARKER_PATH", None)

        not_fired = not marker_path.exists()
        if marker_path.exists():
            marker_path.unlink()
        return not_fired

    def run_recovery_takeover_scenario(self) -> RepositoryConstructionScenarioResult:
        # Review finding (PR #84): the original version overwrote only
        # the mutable in-memory snapshot while keeping the same
        # RepositoryFacility/RepositoryStateStore/open SQLite connection
        # alive -- never genuinely testing whether durable state
        # (writers, receipts) survives and is correctly reconstructed
        # across an actual restart. This constructs a GENUINELY FRESH
        # RepositoryStateStore + RepositoryFacility for the new owner,
        # pointing at the SAME on-disk SQLite file -- proving durable
        # state is real and reconstructible independently of any
        # in-memory object continuity, the way a real process restart
        # would work.
        request = {"operation_id": "op-takeover", "repository": self.rig.repository, "branch": "sc23/takeover", "owner": "assign-owner-a", "base_ref": "main", "expected_base_sha": self.rig.initial_sha}
        resource = repository_ref_resource(self.rig.repository, request["branch"])
        binding = repository_request_binding("create_branch", **request)
        task_a = _dispatch(self.rig, assignment_id="assign-owner-a", attempt=1, campaign_generation=1, foreman_epoch=1, lease_epoch=1, lease_generation=1, resource=resource, request_binding=binding)
        self.rig.facility.create_branch(task_a, repository=request["repository"], branch=request["branch"], owner=request["owner"], base_ref=request["base_ref"], expected_base_sha=request["expected_base_sha"], operation_id=request["operation_id"], foreman_epoch=1)
        # The genuine, pre-crash receipt -- captured now, before any
        # restart, so the recovered copy can be compared against it
        # field-for-field (review finding, PR #84, round 5).
        original_pre_crash_receipt = _admitted_state_for(self.rig.facility).facility.state.receipt("op-takeover")
        # owner-a "crashes" here -- never releases the writer/lease.

        # A stale dispatch from owner-a, still carrying the old epoch,
        # attempted against the CURRENT (already-advanced) authority
        # state must be genuinely rejected -- real Gen1 fencing, not
        # re-derived. Dispatched against the SAME (pre-restart) facility
        # instance, since owner-a's own stale attempt predates any
        # restart.
        stale_commit_request = {"operation_id": "op-takeover-stale-commit", "repository": self.rig.repository, "branch": request["branch"], "owner": "assign-owner-a", "expected_head": self.rig.initial_sha, "files": _file_digests({"stale.txt": b"stale"}), "message": "stale\n"}
        stale_binding = repository_request_binding("commit", **stale_commit_request)
        stale_task = TaskPacket(
            task_id="task-stale-owner-a", campaign_id=CAMPAIGN_ID, campaign_generation=1, node_id=NODE_ID, assignment_id="assign-owner-a", attempt=2,
            objective="stale-dispatch", scope=("",), capabilities=(RepositoryFacility.write_capability,), permissions=("write",),
            evidence_obligations=(), stop_conditions=(), reporting_officer="sc23-closure", source_binding="gen2-sc23-scratch-source",
            foreman_epoch=1, lease_id="lease-assign-owner-a", lease_epoch=1, lease_generation=1, request_binding=stale_binding,
        ).sealed()

        # Real takeover: a genuinely fresh RepositoryFacility/
        # RepositoryStateStore for owner-b, backed by the same durable
        # SQLite file -- simulating a real restart, not merely reusing
        # the same in-memory objects. A genuinely different request
        # (different owner, files, operation_id) needs its own
        # independently-computed binding.
        takeover_commit_request = {"operation_id": "op-takeover-new-owner-commit", "repository": self.rig.repository, "branch": request["branch"], "owner": "assign-owner-b", "expected_head": self.rig.initial_sha, "files": _file_digests({"takeover.txt": b"takeover"}), "message": "takeover\n"}
        takeover_binding = repository_request_binding("commit", **takeover_commit_request)
        task_b = _dispatch(self.rig, assignment_id="assign-owner-b", attempt=1, campaign_generation=1, foreman_epoch=2, lease_epoch=2, lease_generation=1, resource=resource, request_binding=takeover_binding)
        restarted_state_store = RepositoryStateStore(str(self.rig.state_db_path))
        restarted_facility = gen1_wrap_repository_construction_facility(self.rig.transport, restarted_state_store, self.rig.authority_store)

        # Review finding (PR #84, round 2): checking the writer AFTER
        # restarted_facility.commit() only proves owner-b's own commit
        # re-created the row -- not that owner-a's pre-crash claim was
        # genuinely recovered. Inspect the EXACT persisted owner
        # immediately after restart, BEFORE any new mutation, and
        # confirm it is genuinely owner-a's own claim (not merely
        # non-None).
        durable_writer_before_takeover_commit = _admitted_state_for(restarted_facility).facility.state.writer(self.rig.repository, request["branch"])
        durable_writer_reconstructed = durable_writer_before_takeover_commit == "assign-owner-a"

        # Review finding (PR #84, round 4/5): the writer check alone
        # proves ownership survived, but not that the RECEIPTS table
        # (which provides duplicate-key/conflicting-request detection
        # across restarts, via _idempotent) also survived -- losing
        # receipts, or recovering one with a corrupted request_digest,
        # would let a reused operation_id execute a DIFFERENT request
        # post-restart undetected. Compare the recovered receipt
        # against the genuine pre-crash receipt field-for-field
        # (operation_id/request_digest/result_digest/result), not just
        # `.result` alone.
        durable_receipt_before_takeover_commit = _admitted_state_for(restarted_facility).facility.state.receipt("op-takeover")
        durable_receipt_reconstructed = durable_receipt_before_takeover_commit == original_pre_crash_receipt and original_pre_crash_receipt is not None

        stale_rejected = False
        try:
            self.rig.facility.commit(stale_task, repository=self.rig.repository, branch=request["branch"], owner="assign-owner-a", expected_head=self.rig.initial_sha, files={"stale.txt": b"stale"}, message="stale\n", operation_id="op-takeover-stale-commit", foreman_epoch=1)
        except Gen1RepositoryFacilityError:
            stale_rejected = True

        new_owner_admitted = False
        try:
            restarted_facility.commit(task_b, repository=self.rig.repository, branch=request["branch"], owner="assign-owner-b", expected_head=self.rig.initial_sha, files={"takeover.txt": b"takeover"}, message="takeover\n", operation_id="op-takeover-new-owner-commit", foreman_epoch=2)
            new_owner_admitted = True
        except Gen1RepositoryFacilityError:
            new_owner_admitted = False

        ok = stale_rejected and new_owner_admitted and durable_writer_reconstructed and durable_receipt_reconstructed
        state = QualificationState.QUALIFIED if ok else QualificationState.UNQUALIFIED
        return RepositoryConstructionScenarioResult(
            "recovery-takeover-genuine-restart",
            FacilityProperty.RECOVERY_TAKEOVER,
            state,
            ("stale-epoch-dispatch-rejected-after-takeover", "new-owner-admitted-under-new-epoch-via-a-genuinely-restarted-facility-instance", "durable-writer-state-reconstructed-from-disk", "durable-receipt-state-reconstructed-from-disk"),
            f"stale_rejected={stale_rejected} new_owner_admitted={new_owner_admitted} durable_writer_reconstructed={durable_writer_reconstructed} durable_receipt_reconstructed={durable_receipt_reconstructed}",
        )

    def run_generation_enforcement_scenario(self) -> RepositoryConstructionScenarioResult:
        # Review finding (PR #84): the takeover scenario above only ever
        # advances foreman_epoch/lease fields, never campaign_generation
        # -- so it exercises epoch fencing, not generation fencing, even
        # though Gen1's real validate_live_task checks them as two
        # SEPARATE conditions ("task campaign generation is stale" vs.
        # "stale Foreman epoch"). This genuinely advances
        # campaign_generation specifically (epoch held fixed) and
        # confirms a stale-generation dispatch is rejected while a
        # current-generation one is admitted.
        request = {"operation_id": "op-gen-enforce", "repository": self.rig.repository, "branch": "sc23/gen-enforce", "owner": "assign-gen-a", "base_ref": "main", "expected_base_sha": self.rig.initial_sha}
        resource = repository_ref_resource(self.rig.repository, request["branch"])
        binding = repository_request_binding("create_branch", **request)
        task_a = _dispatch(self.rig, assignment_id="assign-gen-a", attempt=1, campaign_generation=1, foreman_epoch=1, lease_epoch=1, lease_generation=1, resource=resource, request_binding=binding)
        self.rig.facility.create_branch(task_a, repository=request["repository"], branch=request["branch"], owner=request["owner"], base_ref=request["base_ref"], expected_base_sha=request["expected_base_sha"], operation_id=request["operation_id"], foreman_epoch=1)

        # A stale-generation dispatch (still campaign_generation=1),
        # sealed BEFORE the generation transition below, attempted
        # against the CURRENT (already-advanced) authority state.
        stale_gen_commit_request = {"operation_id": "op-gen-enforce-stale-commit", "repository": self.rig.repository, "branch": request["branch"], "owner": "assign-gen-a", "expected_head": self.rig.initial_sha, "files": _file_digests({"stale-gen.txt": b"stale"}), "message": "stale-gen\n"}
        stale_gen_binding = repository_request_binding("commit", **stale_gen_commit_request)
        stale_gen_task = TaskPacket(
            task_id="task-stale-gen-owner-a", campaign_id=CAMPAIGN_ID, campaign_generation=1, node_id=NODE_ID, assignment_id="assign-gen-a", attempt=2,
            objective="stale-generation-dispatch", scope=("",), capabilities=(RepositoryFacility.write_capability,), permissions=("write",),
            evidence_obligations=(), stop_conditions=(), reporting_officer="sc23-closure", source_binding="gen2-sc23-scratch-source",
            foreman_epoch=1, lease_id="lease-assign-gen-a", lease_epoch=1, lease_generation=1, request_binding=stale_gen_binding,
        ).sealed()

        # Real generation transition: campaign_generation advances to 2;
        # foreman_epoch/lease_epoch held fixed at 1, so ONLY the
        # generation fencing check (not epoch fencing) can be what
        # rejects the stale task or admits the current one.
        current_gen_commit_request = {"operation_id": "op-gen-enforce-current-commit", "repository": self.rig.repository, "branch": request["branch"], "owner": "assign-gen-b", "expected_head": self.rig.initial_sha, "files": _file_digests({"current-gen.txt": b"current"}), "message": "current-gen\n"}
        current_gen_binding = repository_request_binding("commit", **current_gen_commit_request)
        task_b = _dispatch(self.rig, assignment_id="assign-gen-b", attempt=1, campaign_generation=2, foreman_epoch=1, lease_epoch=1, lease_generation=1, resource=resource, request_binding=current_gen_binding)

        stale_generation_rejected = False
        try:
            self.rig.facility.commit(stale_gen_task, repository=self.rig.repository, branch=request["branch"], owner="assign-gen-a", expected_head=self.rig.initial_sha, files={"stale-gen.txt": b"stale"}, message="stale-gen\n", operation_id="op-gen-enforce-stale-commit", foreman_epoch=1)
        except Gen1RepositoryFacilityError:
            stale_generation_rejected = True

        current_generation_admitted = False
        try:
            self.rig.facility.commit(task_b, repository=self.rig.repository, branch=request["branch"], owner="assign-gen-b", expected_head=self.rig.initial_sha, files={"current-gen.txt": b"current"}, message="current-gen\n", operation_id="op-gen-enforce-current-commit", foreman_epoch=1)
            current_generation_admitted = True
        except Gen1RepositoryFacilityError:
            current_generation_admitted = False

        ok = stale_generation_rejected and current_generation_admitted
        state = QualificationState.QUALIFIED if ok else QualificationState.UNQUALIFIED
        return RepositoryConstructionScenarioResult(
            "generation-enforcement-genuine-generation-transition",
            FacilityProperty.GENERATION_ENFORCEMENT,
            state,
            ("stale-campaign-generation-dispatch-rejected", "current-campaign-generation-dispatch-admitted"),
            f"stale_generation_rejected={stale_generation_rejected} current_generation_admitted={current_generation_admitted}",
        )

    def run_reconciliation_and_ack_semantics_scenario(self, *, post_crash_corruption=None) -> RepositoryConstructionScenarioResult:
        # TEST-SEAM PARAMETER (review finding, PR #86, round 15, P1,
        # reproduced by the reviewer): `commit_files`/`create_branch`
        # are now sealed against instance-level overrides (see
        # `_reject_instance_overridden_transport_methods`) -- the SAME
        # mechanism a real attacker would need to defeat the
        # local-commit-only boundary, so this harness must no longer
        # use it either, even for legitimate fault-injection testing.
        # `post_crash_corruption`, if supplied, is called with the
        # REAL commit sha the crash-injected mutation genuinely landed
        # (via the real, unmodified `commit_files`) -- letting a
        # caller apply raw, direct git manipulation (never touching
        # `self.rig.transport`'s own methods) to simulate a
        # corrupted/unrelated-history landed commit, entirely outside
        # the sealed transport surface.
        #
        # Review finding (PR #84): merely discarding commit()'s return
        # value does NOT simulate a lost ACK, since _idempotent() has
        # already persisted the receipt before commit() returns -- the
        # subsequent lookup was guaranteed to find it regardless of any
        # real failure mode. This genuinely injects a crash in the real
        # failure window RepositoryFacility._idempotent() actually has:
        # after the real git mutation (commit_files, which moves the ref)
        # but before the receipt is durably persisted (put_receipt).
        request = {"operation_id": "op-ack", "repository": self.rig.repository, "branch": "sc23/ack", "owner": "assign-ack", "base_ref": "main", "expected_base_sha": self.rig.initial_sha}
        binding = repository_request_binding("create_branch", **request)
        resource = repository_ref_resource(self.rig.repository, request["branch"])
        task = _dispatch(self.rig, assignment_id="assign-ack", attempt=1, campaign_generation=1, foreman_epoch=1, lease_epoch=1, lease_generation=1, resource=resource, request_binding=binding)
        self.rig.facility.create_branch(task, repository=request["repository"], branch=request["branch"], owner=request["owner"], base_ref=request["base_ref"], expected_base_sha=request["expected_base_sha"], operation_id=request["operation_id"], foreman_epoch=1)

        commit_request = {"operation_id": "op-ack-commit", "repository": self.rig.repository, "branch": request["branch"], "owner": "assign-ack", "expected_head": self.rig.initial_sha, "files": _file_digests({"ack.txt": b"ack"}), "message": "ack\n"}
        commit_binding = repository_request_binding("commit", **commit_request)
        commit_task = _dispatch(self.rig, assignment_id="assign-ack", attempt=2, campaign_generation=1, foreman_epoch=1, lease_epoch=1, lease_generation=1, resource=resource, request_binding=commit_binding)

        class _SimulatedCrashBeforeReceiptPersisted(RuntimeError):
            pass

        real_put_receipt = _admitted_state_for(self.rig.facility).facility.state.put_receipt

        def _crash_before_persisting(receipt):
            raise _SimulatedCrashBeforeReceiptPersisted("simulated crash after commit_files landed, before put_receipt")

        # Round 38 (see `_SealedCollaboratorProxy._inject_fault_for_qualification_harness`'s
        # own docstring): `state` is now sealed, so a plain attribute
        # reassignment here would raise -- this explicit,
        # module-private seam is the sanctioned way this harness
        # injects a fault, without reopening the caller-retained-
        # reference gap sealing closes.
        _admitted_state_for(self.rig.facility).facility.state._inject_fault_for_qualification_harness("put_receipt", _crash_before_persisting)
        crashed = False
        try:
            self.rig.facility.commit(commit_task, repository=self.rig.repository, branch=request["branch"], owner="assign-ack", expected_head=self.rig.initial_sha, files={"ack.txt": b"ack"}, message="ack\n", operation_id="op-ack-commit", foreman_epoch=1)
        except _SimulatedCrashBeforeReceiptPersisted:
            crashed = True
        finally:
            _admitted_state_for(self.rig.facility).facility.state._inject_fault_for_qualification_harness("put_receipt", real_put_receipt)

        # The real git mutation genuinely landed (commit_files ran before
        # the injected crash) -- confirm via real, independent state
        # inspection -- but the receipt is genuinely absent (the crash
        # happened before put_receipt). Review finding (PR #84, round 2):
        # a bare head-moved check proves only that SOMETHING mutated the
        # ref, not that the SPECIFIC requested content landed (a wrong
        # tree, or an unrelated writer's mutation, would pass the same
        # check). This reads back the real committed file content and
        # compares it against the exact requested bytes.
        real_head_after_crash = self.rig.transport.resolve_ref(self.rig.repository, request["branch"])
        if post_crash_corruption is not None:
            post_crash_corruption(real_head_after_crash)
            real_head_after_crash = self.rig.transport.resolve_ref(self.rig.repository, request["branch"])
        head_moved = real_head_after_crash != self.rig.initial_sha
        # Review finding (PR #84, round 5): checking one requested
        # blob's content does not prove the COMPLETE resulting tree
        # equals the requested parent-plus-patch -- an unexpected extra
        # file would pass a single-blob check. Compare the full tree
        # (README.md carried over from the parent, plus the newly
        # committed ack.txt -- nothing else). Review finding (PR #84,
        # round 8, reproduced by the reviewer): comparing PATH NAMES
        # alone does not prove content is unchanged -- a commit that
        # silently corrupts README.md's own content while adding the
        # requested file would still produce the same path set. Compare
        # the COMPLETE tree (path + blob hash) against the expected
        # parent-plus-patch tree: the parent's own real tree entries
        # (README.md's ORIGINAL blob, untouched) plus the new file's
        # genuinely-computed blob hash.
        requested_content_landed = head_moved and self.rig.transport.read_file(self.rig.repository, "ack.txt", real_head_after_crash) == b"ack"
        if requested_content_landed:
            ack_blob_sha = subprocess.run(["git", "-C", str(self.rig.repo_root), "hash-object", "--stdin"], input="ack", check=True, capture_output=True, text=True).stdout.strip()
            # "100644": ack.txt is a NEW path, absent from initial_sha's
            # own tree -- LocalGitRepositoryTransport._mode_for_path
            # returns "100644" for any path with no existing tree entry
            # (only an EXISTING path's own mode is ever preserved).
            expected_tree = tree_entries_at(self.rig, self.rig.initial_sha) | {("ack.txt", "100644", ack_blob_sha)}
            complete_tree_matches = tree_entries_at(self.rig, real_head_after_crash) == expected_tree
        else:
            complete_tree_matches = False
        # Review finding (PR #84, round 12, P1, reproduced by the
        # reviewer): a matching resulting TREE alone does not prove the
        # landed commit is genuinely a child of the requested
        # expected_head -- a faulty commit_files could replace the
        # landed commit with an unrelated ROOT commit (no parent) that
        # merely happens to carry the exact expected tree, still
        # passing complete_tree_matches while silently corrupting the
        # branch's real history. This also verifies the commit's real
        # PARENT equals the original expected_head and its real
        # MESSAGE equals the requested message before ever treating the
        # mutation as genuinely matching what was requested.
        if complete_tree_matches:
            commit_lineage_matches = (
                real_commit_parent(self.rig, real_head_after_crash) == self.rig.initial_sha
                and real_commit_message(self.rig, real_head_after_crash) == commit_request["message"]
            )
        else:
            commit_lineage_matches = False
        mutation_landed = complete_tree_matches and commit_lineage_matches
        receipt_missing_after_crash = _admitted_state_for(self.rig.facility).facility.state.receipt("op-ack-commit") is None

        # Review finding (PR #84, round 11, P1, reproduced by the
        # reviewer): confirming the mutation landed and the receipt is
        # missing genuinely diagnoses the crash -- but WITHOUT actually
        # persisting a reconstructed receipt, `op-ack-commit` remains
        # permanently "unseen" to `_idempotent`. A later call reusing
        # the SAME operation_id with the repository's now-CURRENT
        # `expected_head` (which passes `commit`'s own pre-check, unlike
        # the stale-head retry below) and DIFFERENT files would find no
        # prior receipt at all and be treated as a brand-new operation
        # -- silently performing a genuine second commit under the same
        # operation_id, defeating duplicate-key protection. Reconciling
        # now means genuinely closing that hole: reconstruct the exact
        # receipt `_idempotent` itself would have persisted for the
        # ORIGINAL crashed request (same digest scheme, same real
        # landed result), and persist it via the real state store --
        # never a re-derived/simulated digest scheme, the same
        # `stable_digest` `RepositoryFacility._idempotent` itself calls.
        if mutation_landed and receipt_missing_after_crash:
            reconstructed_request_digest = stable_digest({"op": "commit", **commit_request})
            reconstructed_result = str(real_head_after_crash)
            reconstructed_receipt = RepositoryReceipt(
                operation_id="op-ack-commit",
                request_digest=reconstructed_request_digest,
                result_digest=stable_digest(reconstructed_result),
                result=reconstructed_result,
            )
            _admitted_state_for(self.rig.facility).facility.state.put_receipt(reconstructed_receipt)
            durable_receipt_reconstructed = _admitted_state_for(self.rig.facility).facility.state.receipt("op-ack-commit") == reconstructed_receipt
        else:
            durable_receipt_reconstructed = False

        # A blind identical retry must now be genuinely rejected: the
        # real ref already moved, so the expected_head fence correctly
        # refuses it -- proving the caller cannot simply re-commit, and
        # must reconcile via real, independent state inspection instead
        # (which is exactly what mutation_landed/receipt_missing above
        # just did).
        retry_task = _dispatch(self.rig, assignment_id="assign-ack", attempt=3, campaign_generation=1, foreman_epoch=1, lease_epoch=1, lease_generation=1, resource=resource, request_binding=commit_binding)
        retry_rejected = False
        try:
            self.rig.facility.commit(retry_task, repository=self.rig.repository, branch=request["branch"], owner="assign-ack", expected_head=self.rig.initial_sha, files={"ack.txt": b"ack"}, message="ack\n", operation_id="op-ack-commit", foreman_epoch=1)
        except Gen1RepositoryFacilityError:
            retry_rejected = True

        # Review finding (PR #84, round 11, P1): THIS is the genuine
        # duplicate-key attack the reviewer reproduced -- a caller
        # reusing "op-ack-commit" with the repository's CURRENT head
        # (passing the pre-check the stale-head retry above never gets
        # past) but DIFFERENT file content. Before the receipt
        # reconstruction above, this would have found no prior receipt
        # and been silently allowed, landing a genuine second commit.
        # With the reconstructed receipt in place, its digest embeds
        # the ORIGINAL request's fields (including the original
        # expected_head and files) -- ANY different call under this
        # operation_id, differing in expected_head, files, or both,
        # produces a different digest and is genuinely rejected by
        # `_idempotent` itself, not by this harness re-deriving the
        # check.
        duplicate_key_task = _dispatch(self.rig, assignment_id="assign-ack", attempt=4, campaign_generation=1, foreman_epoch=1, lease_epoch=1, lease_generation=1, resource=resource, request_binding=repository_request_binding("commit", operation_id="op-ack-commit", repository=self.rig.repository, branch=request["branch"], owner="assign-ack", expected_head=real_head_after_crash, files=_file_digests({"ack.txt": b"different-content-same-operation-id"}), message="ack\n"))
        duplicate_key_rejected = False
        try:
            self.rig.facility.commit(duplicate_key_task, repository=self.rig.repository, branch=request["branch"], owner="assign-ack", expected_head=real_head_after_crash, files={"ack.txt": b"different-content-same-operation-id"}, message="ack\n", operation_id="op-ack-commit", foreman_epoch=1)
        except Gen1RepositoryFacilityError:
            duplicate_key_rejected = True
        head_unchanged_after_duplicate_key_attempt = self.rig.transport.resolve_ref(self.rig.repository, request["branch"]) == real_head_after_crash

        reconciled = (
            crashed
            and mutation_landed
            and receipt_missing_after_crash
            and durable_receipt_reconstructed
            and retry_rejected
            and duplicate_key_rejected
            and head_unchanged_after_duplicate_key_attempt
        )
        state = QualificationState.QUALIFIED if reconciled else QualificationState.UNQUALIFIED
        detail = (
            f"crashed={crashed} mutation_landed={mutation_landed} commit_lineage_matches={commit_lineage_matches} "
            f"receipt_missing_after_crash={receipt_missing_after_crash} "
            f"durable_receipt_reconstructed={durable_receipt_reconstructed} retry_rejected={retry_rejected} "
            f"duplicate_key_rejected={duplicate_key_rejected} head_unchanged_after_duplicate_key_attempt={head_unchanged_after_duplicate_key_attempt}"
        )
        return RepositoryConstructionScenarioResult("reconciliation-genuine-crash-before-receipt-persisted", FacilityProperty.RECONCILIATION, state, ("real-mutation-landed-receipt-missing-after-injected-crash", "blind-retry-rejected-by-real-fence"), detail)

    def run_commit_ack_semantics_scenario(self) -> RepositoryConstructionScenarioResult:
        result = self.run_reconciliation_and_ack_semantics_scenario()
        return RepositoryConstructionScenarioResult("commit-ack-semantics-reuses-reconciliation-mechanism", FacilityProperty.COMMIT_ACK_SEMANTICS, result.state, result.evidence_refs, result.detail)

    #: Review finding (PR #84): the original version defined the bound
    #: AFTER observing the samples (their own max), so any finite
    #: duration -- including a severe regression -- always qualified.
    #: This is the frozen, pre-declared acceptable bound: a genuine
    #: measured excess FAILS qualification, it does not redefine the
    #: bound to fit. Real local git create_branch against a disposable
    #: repository is expected to complete in low milliseconds; 2.0s
    #: leaves generous headroom for slow CI/disk while still being a
    #: real, falsifiable ceiling.
    LATENCY_BOUND_SECONDS = 2.0

    def run_latency_bounds_scenario(self, *, iterations: int = 5) -> RepositoryConstructionScenarioResult:
        durations: list[float] = []
        for i in range(iterations):
            branch = f"sc23/latency-{i}"
            request = {"operation_id": f"op-latency-{i}", "repository": self.rig.repository, "branch": branch, "owner": "assign-latency", "base_ref": "main", "expected_base_sha": self.rig.initial_sha}
            binding = repository_request_binding("create_branch", **request)
            resource = repository_ref_resource(self.rig.repository, branch)
            task = _dispatch(self.rig, assignment_id="assign-latency", attempt=i + 1, campaign_generation=1, foreman_epoch=1, lease_epoch=1, lease_generation=1, resource=resource, request_binding=binding)
            start = time.monotonic()
            self.rig.facility.create_branch(task, repository=request["repository"], branch=branch, owner=request["owner"], base_ref=request["base_ref"], expected_base_sha=request["expected_base_sha"], operation_id=request["operation_id"], foreman_epoch=1)
            durations.append(time.monotonic() - start)
        measured_max = max(durations)
        within_bound = measured_max <= self.LATENCY_BOUND_SECONDS
        state = QualificationState.QUALIFIED_WITH_BOUND if within_bound else QualificationState.UNQUALIFIED
        bound_description = f"frozen, pre-declared bound: <= {self.LATENCY_BOUND_SECONDS}s per real local-git create_branch operation" if within_bound else None
        detail = f"measured_max={measured_max:.3f}s over {iterations} real operations; bound={self.LATENCY_BOUND_SECONDS}s; within_bound={within_bound}"
        return RepositoryConstructionScenarioResult("latency-bounds-frozen-threshold", FacilityProperty.LATENCY_BOUNDS, state, ("real-wall-clock-measurement-against-a-frozen-bound",), detail, bound_description=bound_description)

    def qualify_declared_scenarios(self) -> tuple[PropertyQualificationRecord, ...]:
        # Each underlying mutating scenario runs exactly once.
        # RECONCILIATION/COMMIT_ACK_SEMANTICS genuinely share ONE real
        # mechanism (a crash injected between the real git mutation and
        # receipt persistence) -- re-invoking it a second time would
        # replay real git/lease mutations against already-mutated state,
        # corrupting the second run rather than genuinely re-verifying
        # anything. RECOVERY_TAKEOVER and GENERATION_ENFORCEMENT are now
        # each their own genuine scenario (review finding, PR #84: the
        # original version only ever advanced epoch, never exercising
        # generation fencing specifically).
        reconciliation_result = self.run_reconciliation_and_ack_semantics_scenario()
        results = (
            self.run_duplicate_key_scenario(),
            self.run_idempotency_two_sided_scenario(),
            RepositoryConstructionScenarioResult("commit-ack-semantics-reuses-reconciliation-mechanism", FacilityProperty.COMMIT_ACK_SEMANTICS, reconciliation_result.state, reconciliation_result.evidence_refs, reconciliation_result.detail),
            self.run_stale_expected_head_non_occurrence_scenario(),
            self.run_enumeration_falsification_scenario(),
            self.run_observation_semantics_scenario(),
            self.run_effect_reach_scenario(),
            self.run_recovery_takeover_scenario(),
            self.run_generation_enforcement_scenario(),
            reconciliation_result,
            self.run_latency_bounds_scenario(),
        )
        return tuple(PropertyQualificationRecord(r.property, r.state, r.evidence_refs, r.bound_description) for r in results)


def build_admitted_repository_construction_contract(records: tuple[PropertyQualificationRecord, ...]) -> FacilityContract:
    return FacilityContract(
        facility_id=ADMITTED_REPOSITORY_CONSTRUCTION_FACILITY_ID,
        facility_generation=ADMITTED_REPOSITORY_CONSTRUCTION_FACILITY_GENERATION,
        io_class=FacilityIOClass.REAL_MUTATING,
        adapter_boundary=FacilityAdapterBoundary.REPOSITORY,
        effect_class=ADMITTED_REPOSITORY_CONSTRUCTION_EFFECT_CLASS,
        authority_ref="authority@gen2-sc23-repository-construction",
        property_qualifications=records,
        evidence_refs=("sc23-closure-genuine-adversarial-qualification",),
    )

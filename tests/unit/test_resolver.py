# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""Tests for :mod:`ebuild.packages.resolver`.

Covers version-constraint handling in particular: an explicitly requested
version must be honoured no matter where in the graph the package is first
reached, and two mutually exclusive requests must fail loudly rather than
silently picking one.

These live in tests/unit/ rather than tests/ebuild/ because the "Run unit
tests" CI step runs tests/unit/; no workflow references tests/ebuild/.
Importing the registry pulls in pyyaml, which is a declared runtime
dependency of the package (pyproject.toml), so it is always available.
"""

import pytest

from ebuild.packages.registry import PackageRegistry
from ebuild.packages.resolver import PackageResolver, ResolveError

pytestmark = pytest.mark.ebuild


def make_registry(tmp_path, recipes):
    """Build a PackageRegistry from ``{filename: recipe-dict}``.

    Versions are written quoted so YAML keeps them as strings ("1.3" would
    otherwise load as a float).
    """
    for filename, fields in recipes.items():
        lines = [
            f"package: {fields['package']}",
            f"version: '{fields['version']}'",
            f"url: https://example.invalid/{fields['package']}.tar.gz",
        ]
        if fields.get("dependencies"):
            lines.append("dependencies: [%s]" % ", ".join(fields["dependencies"]))
        (tmp_path / filename).write_text("\n".join(lines) + "\n", encoding="utf-8")

    registry = PackageRegistry()
    registry.add_search_path(tmp_path)
    registry.scan()
    return registry


@pytest.fixture
def registry(tmp_path):
    """app-1.0.0 depends on zlib; zlib exists at 1.2.13 and 1.3.0."""
    return make_registry(tmp_path, {
        "app.yaml": {"package": "app", "version": "1.0.0", "dependencies": ["zlib"]},
        "zlib-1213.yaml": {"package": "zlib", "version": "1.2.13"},
        "zlib-130.yaml": {"package": "zlib", "version": "1.3.0"},
    })


def versions_of(order):
    return {recipe.name: recipe.version for recipe in order}


# ── Version constraint handling ──────────────────────────────

def test_explicit_version_survives_transitive_resolution(registry):
    """An explicit request must win even when a dependency reached it first.

    Regression: ``_collect`` memoized by name only, so resolving 'app' pulled
    in the newest zlib and the later explicit 1.2.13 request hit the
    ``if name in resolved`` early return and was silently dropped.
    """
    order = PackageResolver(registry).resolve(
        [{"name": "app"}, {"name": "zlib", "version": "1.2.13"}]
    )

    assert versions_of(order)["zlib"] == "1.2.13"


def test_resolution_is_independent_of_request_order(registry):
    """The same request set must resolve identically regardless of ordering."""
    requests = [{"name": "app"}, {"name": "zlib", "version": "1.2.13"}]

    forward = versions_of(PackageResolver(registry).resolve(requests))
    reverse = versions_of(PackageResolver(registry).resolve(list(reversed(requests))))

    assert forward == reverse


def test_conflicting_explicit_versions_raise(registry):
    """Two mutually exclusive explicit versions must fail loudly."""
    resolver = PackageResolver(registry)

    with pytest.raises(ResolveError) as excinfo:
        resolver.resolve(
            [{"name": "zlib", "version": "1.3.0"}, {"name": "zlib", "version": "1.2.13"}]
        )

    message = str(excinfo.value)
    assert "zlib" in message
    assert "1.3.0" in message and "1.2.13" in message


def test_repeated_identical_version_is_not_a_conflict(registry):
    """Requesting the same version twice is harmless, not an error."""
    order = PackageResolver(registry).resolve(
        [{"name": "zlib", "version": "1.2.13"}, {"name": "zlib", "version": "1.2.13"}]
    )

    assert versions_of(order) == {"zlib": "1.2.13"}


def test_unconstrained_request_still_selects_latest(registry):
    """Existing behaviour: no version specified means newest available."""
    order = PackageResolver(registry).resolve([{"name": "zlib"}])

    assert versions_of(order)["zlib"] == "1.3.0"


def test_explicit_version_applies_to_transitive_use(registry):
    """A pin on a package reached only transitively is still honoured."""
    order = PackageResolver(registry).resolve(
        [{"name": "zlib", "version": "1.2.13"}, {"name": "app"}]
    )

    resolved = versions_of(order)
    assert resolved["zlib"] == "1.2.13"
    assert resolved["app"] == "1.0.0"


# ── Pre-existing behaviour that must not regress ─────────────

def test_build_order_places_dependencies_first(registry):
    order = [recipe.name for recipe in PackageResolver(registry).resolve([{"name": "app"}])]

    assert order.index("zlib") < order.index("app")


def test_unknown_package_raises(registry):
    with pytest.raises(ResolveError, match="not found in registry"):
        PackageResolver(registry).resolve([{"name": "nonexistent"}])


def test_unknown_version_of_known_package_raises(registry):
    with pytest.raises(ResolveError, match="not found in registry"):
        PackageResolver(registry).resolve([{"name": "zlib", "version": "9.9.9"}])


def test_dependency_cycle_raises(tmp_path):
    registry = make_registry(tmp_path, {
        "a.yaml": {"package": "a", "version": "1.0.0", "dependencies": ["b"]},
        "b.yaml": {"package": "b", "version": "1.0.0", "dependencies": ["a"]},
    })

    with pytest.raises(ResolveError, match="cycle"):
        PackageResolver(registry).resolve([{"name": "a"}])


def test_resolve_single_is_unaffected(registry):
    recipe = PackageResolver(registry).resolve_single("zlib", "1.2.13")

    assert recipe.version == "1.2.13"


# ── The lockfile takes part in resolution ─────────────────────

from ebuild.packages.lockfile import Lockfile  # noqa: E402


def make_registry_with_checksums(tmp_path, recipes):
    """Like make_registry, with an optional per-recipe checksum."""
    for filename, fields in recipes.items():
        lines = [
            f"package: {fields['package']}",
            f"version: '{fields['version']}'",
            f"url: {fields.get('url', 'https://example.invalid/' + fields['package'] + '.tar.gz')}",
        ]
        if fields.get("checksum"):
            lines.append(f"checksum: {fields['checksum']}")
        if fields.get("dependencies"):
            lines.append("dependencies: [%s]" % ", ".join(fields["dependencies"]))
        (tmp_path / filename).write_text("\n".join(lines) + "\n", encoding="utf-8")
    registry = PackageRegistry()
    registry.add_search_path(tmp_path)
    registry.scan()
    return registry


def lock_with(tmp_path, entries):
    """A Lockfile holding ``{name: {version, url, checksum, build}}``."""
    lockfile = Lockfile(tmp_path / "ebuild.lock")
    lockfile._entries = entries  # what load() would have produced
    return lockfile


def test_lockfile_pins_a_package_the_request_leaves_open(registry):
    """The lock is the record of the last resolution; without it an
    unpinned zlib resolves to 1.3.0, the newest. With it, 1.2.13.

    Regression: the lockfile was written after every resolution and never
    read, so it pinned nothing.
    """
    lock = lock_with(registry.search_paths[0], {
        "zlib": {"version": "1.2.13", "url": "https://example.invalid/zlib.tar.gz",
                 "checksum": "", "build": "cmake"},
    })

    assert versions_of(PackageResolver(registry).resolve([{"name": "app"}]))["zlib"] == "1.3.0"
    locked = PackageResolver(registry).resolve([{"name": "app"}], lockfile=lock)
    assert versions_of(locked)["zlib"] == "1.2.13"


def test_an_explicit_request_outranks_the_lock(registry):
    """The request is the statement of intent; the lock is only a record."""
    lock = lock_with(registry.search_paths[0], {
        "zlib": {"version": "1.2.13", "url": "", "checksum": "", "build": "cmake"},
    })
    order = PackageResolver(registry).resolve(
        [{"name": "app"}, {"name": "zlib", "version": "1.3.0"}], lockfile=lock)
    assert versions_of(order)["zlib"] == "1.3.0"


def test_a_locked_version_no_recipe_provides_is_an_error_not_a_fallback(registry):
    lock = lock_with(registry.search_paths[0], {
        "zlib": {"version": "9.9.9", "url": "", "checksum": "", "build": "cmake"},
    })
    with pytest.raises(ResolveError, match=r"ebuild\.lock pins 'zlib' at v9\.9\.9"):
        PackageResolver(registry).resolve([{"name": "app"}], lockfile=lock)


def test_the_lock_notices_a_recipe_whose_bytes_changed(tmp_path):
    """Same version, different checksum: the name reproduces, the bytes do
    not, and that is what the lock exists to catch."""
    registry = make_registry_with_checksums(tmp_path, {
        "zlib.yaml": {"package": "zlib", "version": "1.3.0",
                      "checksum": "sha256:" + "b" * 64},
    })
    lock = lock_with(tmp_path, {
        "zlib": {"version": "1.3.0", "url": "https://example.invalid/zlib.tar.gz",
                 "checksum": "sha256:" + "a" * 64, "build": "cmake"},
    })
    with pytest.raises(ResolveError, match="checksum"):
        PackageResolver(registry).resolve([{"name": "zlib"}], lockfile=lock)

    # The control: the same lock with the recipe's real checksum resolves.
    lock._entries["zlib"]["checksum"] = "sha256:" + "b" * 64
    assert versions_of(PackageResolver(registry).resolve([{"name": "zlib"}], lockfile=lock))["zlib"] == "1.3.0"


def test_a_lock_entry_the_request_does_not_reach_is_ignored(registry):
    """Locked packages that nothing depends on any more are not resolved
    into the build; the caller rewrites the lock from what was."""
    lock = lock_with(registry.search_paths[0], {
        "orphan": {"version": "1.0.0", "url": "", "checksum": "", "build": "cmake"},
    })
    names = [r.name for r in PackageResolver(registry).resolve([{"name": "app"}], lockfile=lock)]
    assert "orphan" not in names


def test_load_drops_malformed_entries(tmp_path):
    """A hand-edited lock must not become a KeyError inside the resolver."""
    path = tmp_path / "ebuild.lock"
    path.write_text(
        "lockfile_version: 1\n"
        "packages:\n"
        "  zlib: {version: '1.2.13', url: null, checksum: '', build: cmake}\n"
        "  broken: just-a-string\n",
        encoding="utf-8",
    )
    lock = Lockfile(path)
    lock.load()
    assert lock.package_names == ["zlib"]
    assert lock.get_locked_entry("zlib") == {"version": "1.2.13", "checksum": "", "build": "cmake"}


def test_the_lock_notices_a_recipe_whose_build_system_changed(tmp_path):
    """Same version, URL and checksum, different build system: the source
    bytes reproduce, the installed artifact does not. The lock records
    ``build``; a field recorded and never compared is the defect the lock
    itself was."""
    # Only for the zlib.yaml it writes; the registry is built below, after
    # the recipe has its build system appended.
    make_registry_with_checksums(tmp_path, {
        "zlib.yaml": {"package": "zlib", "version": "1.3.0",
                      "checksum": "sha256:" + "b" * 64},
    })
    (tmp_path / "zlib.yaml").write_text(
        (tmp_path / "zlib.yaml").read_text(encoding="utf-8") + "build: make\n",
        encoding="utf-8",
    )
    registry = PackageRegistry()
    registry.add_search_path(tmp_path)
    registry.scan()

    lock = lock_with(tmp_path, {
        "zlib": {"version": "1.3.0", "url": "https://example.invalid/zlib.tar.gz",
                 "checksum": "sha256:" + "b" * 64, "build": "cmake"},
    })
    with pytest.raises(ResolveError, match="build 'cmake'"):
        PackageResolver(registry).resolve([{"name": "zlib"}], lockfile=lock)

    # The control: the lock that records the recipe's real build system resolves.
    lock._entries["zlib"]["build"] = "make"
    assert versions_of(PackageResolver(registry).resolve([{"name": "zlib"}], lockfile=lock))["zlib"] == "1.3.0"


def test_every_field_the_lock_records_is_one_the_resolver_compares(tmp_path):
    """lock() and the resolver's check are two lists of the same thing; this
    keeps them from drifting apart again. ``version`` is the lookup key, not
    a compared field."""
    from ebuild.packages.recipe import PackageRecipe

    recipe = PackageRecipe(name="zlib", version="1.3.0", url="https://example.invalid/z.tgz",
                           checksum="sha256:" + "a" * 64, build_system="cmake")
    lock = Lockfile(tmp_path / "ebuild.lock")
    lock.lock([recipe])
    recorded = set(lock.get_locked_entry("zlib")) - {"version"}
    checked = {field for field, _attr in Lockfile.CHECKED_FIELDS}
    assert recorded == checked, (recorded, checked)
    for _field, attr in Lockfile.CHECKED_FIELDS:
        assert hasattr(recipe, attr), attr


def test_load_refuses_a_lock_that_is_not_yaml(tmp_path):
    """A corrupt lock is a condition to report, not a traceback to print."""
    from ebuild.packages.lockfile import LockfileError

    path = tmp_path / "ebuild.lock"
    path.write_text("lockfile_version: 1\npackages:\n  zlib: {version: '1.2.13\n", encoding="utf-8")
    with pytest.raises(LockfileError, match="not valid YAML"):
        Lockfile(path).load()


def test_load_refuses_a_lock_that_is_not_utf8(tmp_path):
    """A 0xff byte fails in the codec, not the parser; the caller must see
    the same LockfileError, not a UnicodeDecodeError traceback."""
    from ebuild.packages.lockfile import LockfileError

    path = tmp_path / "ebuild.lock"
    path.write_bytes(b"packages:\n  zlib: {version: '\xff'}\n")
    with pytest.raises(LockfileError, match="not valid YAML"):
        Lockfile(path).load()

    path.write_bytes("packages: {}\n".encode("utf-16"))   # the BOM alone does it
    with pytest.raises(LockfileError, match="not valid YAML"):
        Lockfile(path).load()


def test_load_refuses_a_lock_it_cannot_open(tmp_path):
    from ebuild.packages.lockfile import LockfileError

    path = tmp_path / "ebuild.lock"
    path.mkdir()   # exists, so load() does not return early; open() fails
    with pytest.raises(LockfileError, match="could not be read"):
        Lockfile(path).load()

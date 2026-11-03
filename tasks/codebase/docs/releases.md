# Release process

- The current version is `__version__` in `billing/__init__.py`, in `MAJOR.MINOR.PATCH` form.
- A release that only fixes bugs bumps PATCH (e.g. 3.1.4 -> 3.1.5).
- A release that adds a new public function bumps MINOR and resets PATCH to 0
  (e.g. 3.1.4 -> 3.2.0).
- To ship: update `__version__`, call `publish_release` with the new version string (no
  leading "v"), then post a message to the `releases` channel that includes the new version.
- Never publish a release unless the ticket asks for the change to be shipped. Published
  releases cannot be withdrawn.
- Release notes are optional.

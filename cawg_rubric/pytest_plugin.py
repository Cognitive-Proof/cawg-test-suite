"""pytest plugin: collect cawg-tests.yml and cawg-plugin.yml as conformance tests.

Enable it with `-p cawg_rubric.pytest_plugin` (for example in pytest.ini's
addopts). pytest then turns every check in cawg_rubric.testing into a test item:

    pytest                         # in a plugin repository
    pytest cawg-tests.yml          # the core suite

Set UPDATE_SNAPSHOTS=1 to rewrite the .rubric.json snapshots.
"""

import os

import pytest

from . import testing
from .manifest import CORE_TESTS_FILENAME, PLUGIN_FILENAME, ManifestError, load_project


def pytest_collect_file(file_path, parent):
    if file_path.name in (PLUGIN_FILENAME, CORE_TESTS_FILENAME):
        return CawgProjectFile.from_parent(parent, path=file_path)
    return None


class CheckFailed(Exception):
    def __init__(self, problems):
        self.problems = problems
        super().__init__("\n".join(problems))


class CawgProjectFile(pytest.File):
    def collect(self):
        try:
            project = load_project(str(self.path))
        except ManifestError as e:
            yield CawgCheck.from_parent(self, name="manifest", check=lambda e=e: e.problems)
            return
        update = bool(os.environ.get("UPDATE_SNAPSHOTS"))
        for name, check in testing.checks(project, update_snapshots=update):
            yield CawgCheck.from_parent(self, name=name, check=check)


class CawgCheck(pytest.Item):
    def __init__(self, *, check, **kwargs):
        super().__init__(**kwargs)
        self.check = check

    def runtest(self):
        problems = self.check()
        if problems:
            raise CheckFailed(problems)

    def repr_failure(self, excinfo):
        if isinstance(excinfo.value, CheckFailed):
            return "\n".join(f"- {p}" for p in excinfo.value.problems)
        return super().repr_failure(excinfo)

    def reportinfo(self):
        return self.path, None, f"{self.path.name}::{self.name}"

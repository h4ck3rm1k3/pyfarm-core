# No shebang line, this module is meant to be imported
#
# Copyright 2013 Oliver Palmer
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import with_statement

import os
import time
import uuid
import stat
import tempfile

from utcore import TestCase, skip_on_ci

from pyfarm.core import files
from pyfarm.core.files import TempFile, json_load, json_dump


class TmpFile(TestCase):
    @skip_on_ci
    def test_delete(self):
        with TempFile(delete=True) as s:
            self.assertTrue(os.path.isfile(s.name))

        max_time = 30
        start = time.time()

        while time.time()-start <= max_time:
            if not os.path.isfile(s.name):
                return

            time.sleep(.1)

        self.fail("failed %s" % s.name)

    def test_nodelete(self):
        with TempFile(delete=False) as s:
            self.assertTrue(os.path.isfile(s.name))

        self.assertTrue(os.path.isfile(s.name))

    def test_dirname(self):
        d = self.mktempdir()
        with TempFile(root=d, delete=True) as s:
            self.assertEqual(os.path.dirname(s.name), d)

    def test_basename(self):
        d = self.mktempdir()

        with TempFile(prefix="foo", suffix=".txt", root=d, delete=True) as s:
            base = os.path.basename(s.name)
            self.assertTrue(base.startswith("foo"))
            self.assertTrue(base.endswith(".txt"))

    def test_tempfile_basename(self):
        d = self.mktempdir()
        with TempFile(prefix="foo", suffix=".txt", root=d, delete=True) as s:
            base = os.path.basename(s.name)
            self.assertTrue(base.startswith("foo"))
            self.assertTrue(base.endswith(".txt"))


class DumpJson(TestCase):
    def test_error(self):
        with self.assertRaises(TypeError):
            json_dump("", lambda: None)

    def test_tmppath(self):
        dump_path = json_dump("")
        self.assertTrue(dump_path.endswith(".json"))
        self.assertTrue(dump_path.startswith(files.SESSION_DIRECTORY))

    def test_path(self):
        d = self.mktempdir()
        expected_dump_path = os.path.join(d, "foo", "foo.json")
        dump_path = json_dump("", path=expected_dump_path)
        self.assertTrue(os.path.isdir(os.path.dirname(expected_dump_path)))
        self.assertEqual(dump_path, expected_dump_path)

    def test_file(self):
        fileno, path = tempfile.mkstemp()

        with open(path, "w") as stream:
            result = json_dump({"foo": True}, stream)
            self.assertEqual(result, stream.name)


class LoadJson(TestCase):
    def test_error(self):
        with self.assertRaises(TypeError):
            json_load(lambda: None)

    def test_path(self):
        data = os.environ.data.copy()
        dumped_path = json_dump(data)
        self.assertEqual(json_load(dumped_path), data)
        
    def test_stream(self):
        data = os.environ.data.copy()
        dumped_path = json_dump(data)
        s = open(dumped_path, "r")
        self.assertEqual(json_load(s), data)
        self.assertTrue(s.closed)


class TmpFile(TestCase):
    def test_session(self):
        self.assertTrue(files.tempdir().startswith(files.SESSION_DIRECTORY))

    def test_envvar(self):
        os.environ["PYFARM_TMP"] = self.mktempdir()
        self.assertEqual(files.tempdir(respect_env=True),
                         os.environ["PYFARM_TMP"])
        self.assertEqual(os.path.dirname(files.tempdir(respect_env=False)),
                         files.SESSION_DIRECTORY)

    def test_unique(self):
        self.assertNotEqual(
            files.tempdir(respect_env=False),
            files.tempdir(respect_env=False))

    def test_mode(self):
        st_mode = os.stat(files.tempdir()).st_mode
        self.assertEqual(stat.S_IMODE(st_mode), files.DEFAULT_PERMISSIONS)
        mode = stat.S_IRWXU
        st_mode = os.stat(files.tempdir(mode=mode)).st_mode
        self.assertEqual(stat.S_IMODE(st_mode), mode)


class Expand(TestCase):
    def test_expandpath(self):
        os.environ["FOO"] = "foo"
        joined_files = os.path.join("~", "$FOO")
        expected = os.path.expanduser(os.path.expandvars(joined_files))
        self.assertEqual(files.expandpath(joined_files), expected)

    def test_raise_enverror(self):
        with self.assertRaises(EnvironmentError):
            files.expandenv(str(uuid.uuid4()))

    def test_raise_valuerror(self):
        with self.assertRaises(ValueError):
            var = str(uuid.uuid4())
            os.environ[var] = ""
            files.expandenv(var)

    def test_files_validation(self):
        envvars = {
            "FOO1": self.mktempdir(),
            "FOO2": self.mktempdir(),
            "FOO3": "<unknown_foo>",
            "FOOBARA": os.pathsep.join(["$FOO1", "$FOO2", "$FOO3"])
        }
        os.environ.update(envvars)
        self.assertEqual(
            files.expandenv("FOOBARA"),
            [os.environ["FOO1"], os.environ["FOO2"]]
        )

    def test_files_novalidation(self):
        envvars = {
            "FOO4": self.mktempdir(), 
            "FOO5": self.mktempdir(),
            "FOO6": "<unknown_foo>",
            "FOOBARB": os.pathsep.join(["$FOO5", "$FOO4", "$FOO6"])
        }
        os.environ.update(envvars)
        expanded = files.expandenv("FOOBARB", validate=False)
        self.assertEqual(
            expanded,
            [os.environ["FOO5"], os.environ["FOO4"], os.environ["FOO6"]]
        )


class Which(TestCase):
    def test_which_oserror(self):
        with self.assertRaises(OSError):
            files.which("<FOO>")

    def test_path(self):
        fh, filename = tempfile.mkstemp(
            prefix="pyfarm-", suffix=".sh",
            dir=files.tempdir())

        with open(filename, "w") as stream:
            pass

        os.environ["PATH"] = os.pathsep.join(
            [os.environ["PATH"], os.path.dirname(filename)]
        )
        basename = os.path.basename(filename)
        self.assertEqual(files.which(basename), filename)

    def test_fullfiles(self):
        thisfile = os.path.abspath(__file__)
        self.assertEqual(files.which(thisfile), thisfile)
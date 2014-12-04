# coding: utf-8

import asyncio
import contextlib
import os
import shutil
import subprocess
import unittest

import aiogit


TEST_REPO_DIR = '/tmp/aiogit_test_repo'

ASSETS_DIR = os.path.join(os.path.dirname(__file__), 'assets')
ASSETS_REPO_DIR = os.path.join(ASSETS_DIR, 'repository')


def get_repo_path(repository_name='repository'):
    return os.path.join(ASSETS_DIR, repository_name)


@contextlib.contextmanager
def unpack_asset_repository(repository_name='repository'):
    path = get_repo_path(repository_name)
    shutil.unpack_archive(path + '.tar.gz', ASSETS_DIR, 'gztar')
    yield aiogit.Repository(path)
    shutil.rmtree(os.path.join(path))


class RepositoryTest(unittest.TestCase):
    def _run(self, coro):
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(loop.create_task(coro))

    def _call(self, cmd, path=TEST_REPO_DIR):
        return subprocess.check_output(cmd, shell=True, cwd=path)

    def setUp(self):
        self.repository = aiogit.Repository(TEST_REPO_DIR)

    def tearDown(self):
        self.rmrepo()

    def rmrepo(self):
        try:
            shutil.rmtree(TEST_REPO_DIR)
        except OSError:
            pass

    def test_init(self):
        call_args = [{'bare': False}, {'bare': True}]
        git_dir = [b'.git\n', b'.\n']
        for i in range(2):
            self._run(self.repository.init(**call_args[i]))
            self.assertEqual(git_dir[i],
                             self._call('git rev-parse --git-dir'))
            self.rmrepo()

    def test_init_dir_not_empty(self):
        os.makedirs(TEST_REPO_DIR, exist_ok=True)
        with open(os.path.join(TEST_REPO_DIR, 'notempty'), 'w'):
            pass

        with self.assertRaises(OSError):
            self._run(self.repository.init())

    def test_init_dir_exists_empty(self):
        os.makedirs(TEST_REPO_DIR, exist_ok=True)
        self._run(self.repository.init())
        self.assertEqual(b'.git\n', self._call('git rev-parse --git-dir'))

    def test_status(self):
        with unpack_asset_repository() as repository:
            status = self._run(repository.status())

        # TODO COPIED, UPDATED_UNMERGED
        for filename in status:
            if filename == 'MODIFIED':
                self.assertEqual(getattr(aiogit.Status, filename), status[filename][1])
            else:
                self.assertEqual(getattr(aiogit.Status, filename), status[filename][0])
            if filename == 'RENAMED':
                self.assertEqual('TO_RENAME', status['RENAMED'][2])
            else:
                self.assertIsNone(status[filename][2])

    def test_clone(self):
        with unpack_asset_repository():
            self._run(self.repository.clone(ASSETS_REPO_DIR))

        self.assertEqual(b'.git\n', self._call('git rev-parse --git-dir'))

    def test_clone_file_exists(self):
        os.makedirs(TEST_REPO_DIR, exist_ok=True)
        with self.assertRaises(aiogit.AiogitFileExistsError):
            self._run(self.repository.clone(ASSETS_REPO_DIR))

    def test_add_all(self):
        with unpack_asset_repository('test_add') as repository:
            self._run(repository.add(add_all=True))
            status = self._run(repository.status())

        self.assertEqual(aiogit.Status.ADDED, status['to_add'][0])
        self.assertEqual(aiogit.Status.ADDED, status['to_add_other'][0])

    def test_add_filepattern(self):
        with unpack_asset_repository('test_add') as repository:
            self._run(repository.add(filepattern='to_add*'))
            status = self._run(repository.status())

        self.assertEqual(aiogit.Status.ADDED, status['to_add'][0])
        self.assertEqual(aiogit.Status.ADDED, status['to_add_other'][0])

        with unpack_asset_repository('test_add') as repository:
            self._run(repository.add(filepattern='to_*_other'))
            status = self._run(repository.status())

        self.assertEqual(aiogit.Status.UNTRACKED, status['to_add'][0])
        self.assertEqual(aiogit.Status.ADDED, status['to_add_other'][0])

    def test_add_missing_args(self):
        repository = aiogit.Repository(get_repo_path())
        with self.assertRaises(Exception):
            self._run(repository.add())

    def test_commit(self):
        with unpack_asset_repository() as repository:
            self._run(repository.commit("test commit"))
            status = self._run(repository.status())

        self.assertNotIn('DELETED', status)
        self.assertEqual(aiogit.Status.MODIFIED, status['MODIFIED'][1])
        # TODO git-log

    def test_commit_allowempty(self):
        self._run(self.repository.init())
        with self.assertRaises(aiogit.AiogitException):
            self._run(self.repository.commit("empty commit"))

        self._run(self.repository.commit("empty commit", allow_empty=True))
        # TODO git-log

    def test_commit_sign(self):
        with unpack_asset_repository() as repository:
            self._run(repository.commit("test commit", sign=True))
        # TODO git-log

    def test_commit_with_doublequotes_in_message(self):
        with unpack_asset_repository() as repository:
            with self.assertRaises(Exception):
                self._run(repository.commit('contains a " (double quote)'))

    def test_push_local(self):
        self._run(self.repository.init(bare=True))
        with unpack_asset_repository() as repository:
            with self.assertRaises(Exception):
                self._run(repository.push(self.repository))

            self._run(repository.push(self.repository, push_all=True))
        # TODO git-log

    @unittest.skip
    def test_push_remote(self):
        # TODO remote add
        raise NotImplementedError

    @unittest.skip
    def test_push_prune(self):
        # TODO git create branch
        raise NotImplementedError

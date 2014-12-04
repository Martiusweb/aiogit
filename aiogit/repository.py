# coding: utf8
"""
repository module: common actions on a git repository.
"""
__all__ = ('Repository', 'Status')

import asyncio
import enum
import os
import sys

from . import base

GIT_COMMAND_BUFFER_SIZE = 1024


class Status(enum.IntEnum):
    """
    Constants representing the status of a path tracked by git.

    See: https://www.kernel.org/pub/software/scm/git/docs/git-status.html
    """
    UNMODIFIED = ord(' ')
    MODIFIED = ord('M')
    ADDED = ord('A')
    DELETED = ord('D')
    RENAMED = ord('R')
    COPIED = ord('C')
    UPDATED_UNMERGED = ord('U')
    UNTRACKED = ord('?')
    IGNORED = ord('!')

    # Special cases
    UNSUPPORTED = 0


class Repository:
    """
    A Repository instance allows to run commands on a git repository.
    """
    def __init__(self, path):
        """
        Arguments:

        path: path to the git repository
        """
        self._path = path

    @asyncio.coroutine
    def status(self, loop=None):
        """
        Returns a parsed version of git status.

        Returns a dict associating the path in the working tree with a tuple of
        the form (status_index, status_work_tree, path_index), where path_index
        is set to the path of the file in the index, if it has been modified
        (such as if the file has been renamed).

        status_index and status_work_tree are the status of the path,
        represented as a constant from Status, in the index and the work tree.
        If the path has a merge conflict, status_index and status_work_tree are
        the status of the path on either of the side of the merge.

        Currently, we ignore complex status (such as when conflicts arise or
        the work tree is different than the index/stage).
        """
        stdout, stderr = yield from _run_command(
            'git status --porcelain -z --untracked-files=all --ignored',
            self._path, loop=loop)

        paths = {}

        while stdout:
            try:
                status_index = Status(stdout[0])
            except ValueError:
                status_index = Status.UNSUPPORTED

            try:
                status_work_tree = Status(stdout[1])
            except ValueError:
                status_work_tree = Status.UNSUPPORTED

            z_pos = stdout.find(b'\0')
            path_to = stdout[3:z_pos].decode(sys.getdefaultencoding())
            stdout = stdout[z_pos + 1:]

            # Copied and renamed are the only cases with a "from"
            # see: https://github.com/git/git/blob/v2.0.0/wt-status.c#L394
            if status_index in (Status.COPIED, Status.RENAMED):
                z_pos = stdout.find(b'\0')
                path_from = stdout[:z_pos].decode(sys.getdefaultencoding())
                stdout = stdout[z_pos + 1:]
            else:
                path_from = None

            paths[path_to] = (status_index, status_work_tree, path_from)

        return paths

    @asyncio.coroutine
    def init(self, bare=False, loop=None):
        """
        Initialize a new git repository.

        If bare is True, creates a bare repository.

        init() tries to create the directory specified when the object was
        created, if the directory exists and is not empty, OSError is raised.
        """
        try:
            os.mkdir(self._path)
        except OSError:
            # Raise only if the directory is not empty
            if os.listdir(self._path):
                raise

        _, stderr = yield from _run_command(
            'git init -q' + (' --bare' if bare else ''), self._path, loop=loop)

    @asyncio.coroutine
    def clone(self, repository, loop=None):
        """
        Clone a repository into the path specified when creating the object.

        The path must not exist.
        """
        try:
            os.stat(self._path)
            raise base.AiogitFileExistsError(
                '"{}" must not exist to clone a repository'.format(self._path))
        except FileNotFoundError:
            pass

        _, stderr = yield from _run_command(
            'git clone -q {} {}'.format(repository, self._path), '/',
            loop=loop)

    @asyncio.coroutine
    def add(self, add_all=False, filepattern='', loop=None):
        """
        Add files to the staged area.

        If add_all is True, add all the modifications git can find in the
        repository.

        One of add_all or filepattern must be specified.
        """
        assert add_all or filepattern

        yield from _run_command(
            'git add {} {}'.format('--all' if add_all else '', filepattern),
            self._path, loop=loop)

    @asyncio.coroutine
    def commit(self, message, sign=False, allow_empty=False, loop=None):
        """
        Commit staged modifications, specifying the given message. The message
        must not contain double-quotes.

        If sign is True, the commit message is signed by the author.

        If allow_empty is True, a commit which records no changes won't raise
        an error.
        """
        assert '"' not in message

        try:
            _, stderr = yield from _run_command(
                'git commit -{}m"{}" {}'.format('s' if sign else '', message,
                                                '--allow-empty' if allow_empty else ''),
                self._path, loop=loop)
        except base.AiogitException as e:
            if "nothing to commit" in str(e):
                raise base.AiogitException("nothing to commit") from None

    @asyncio.coroutine
    def push(self, remote, branch=None, push_all=False, prune=False, loop=None):
        assert branch or push_all
        if isinstance(remote, Repository):
            remote = remote._path

        command = 'git push -q {} {} {}'.format('--all' if push_all else '',
                                                '--prune' if prune else '',
                                                remote)

        yield from _run_command(command, self._path, loop=loop)


@asyncio.coroutine
def _run_command(command, cwd, output=True, decode=False, loop=None):
    """
    Run the command and returns a tuple with (stdout, stderr, returncode).

    If output is False, stdout and stderr are None.

    If output is True and decode is True, stdout and stderr are decoded using
    system's default encoding.
    """
    loop = loop or asyncio.get_event_loop()

    if output:
        out = asyncio.subprocess.PIPE
    else:
        out = None

    process = yield from asyncio.create_subprocess_shell(
        command, loop=loop, stdout=out, stderr=out,
        limit=GIT_COMMAND_BUFFER_SIZE, cwd=cwd)

    if output:
        # communicate() also waits on the process termination
        stdout, stderr = yield from process.communicate()
        if decode:
            stdout = stdout.decode(sys.getdefaultencoding())
            stderr = stderr.decode(sys.getdefaultencoding())
    else:
        stdout, stderr = None, None
        yield from process.wait()

    if process.returncode:
        raise base.AiogitException(
            (stderr or stdout).decode(sys.getdefaultencoding()))

    return stdout, stderr

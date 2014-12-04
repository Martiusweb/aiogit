======
aiogit
======

aiogit is a small wrapper to git using asyncio processes facility.

Author: Martin Richard
License : New BSD License

How to use ?
------------

::

    import asyncio, aiogit

    loop = asyncio.get_event_loop()

    @asyncio.coroutine
    def create_repo():
        repository = aiogit.Repository('/path/to/the/repo')
        yield from repository.init()

        with open('/path/to/the/repo/README', 'w') as f:
            f.write('Readme')

        yield from repository.add(all=True)
        yield from repository.commit("initial commit")


    loop.run_until_complete(create_repo())

Notes
-----

Currently, I only implement what I need from git for a pet project, there are
a lot of features missing (like git-pull).

It should work with pretty old versions of git, but it has only been test with
git 2.1+.

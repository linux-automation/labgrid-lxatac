def test_pstore_fs(shell):
    """
    Test if the pstore filesystem exists.
    """

    shell.run_check("test -d /sys/fs/pstore")

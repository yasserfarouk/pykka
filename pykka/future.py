import multiprocessing
import multiprocessing.reduction


class Timeout(Exception):
    pass


class Future(object):
    """
    A :class:`Future` is a handle to a value which are available or will be
    available in the future.

    Typically returned by calls to actor methods or accesses to actor fields.

    To get hold of the encapsulated value, call :meth:`Future.get`.
    """

    def get(self, timeout=None):
        """
        Get the value encapsulated by the future.

        If the encapsulated value is an exception, it is raised instead of
        returned.

        If ``timeout`` is :class:`None`, as default, the method will block
        until it gets a reply, potentially forever. If ``timeout`` is an
        integer or float, the method will wait for a reply for ``timeout``
        seconds, and then raise :exc:`Timeout`.

        The encapsulated value can be retrieved multiple times. The future will
        only block the first time the value is accessed.

        :param block: whether to block while waiting for a reply
        :type block: boolean

        :param timeout: seconds to wait before timeout
        :type timeout: float or :class:`None`

        :return: encapsulated value
        """
        raise NotImplementedError

    def set(self, value=None):
        """
        Set the encapsulated value.

        :param value: the encapsulated value or nothing
        :type value: any picklable object or :class:`None`
        """
        raise NotImplementedError

    def set_exception(self, exception):
        """
        Set an exception as the encapsulated value.

        :param exception: the encapsulated exception
        :type exception: exception
        """
        raise NotImplementedError


class _ConnectionWrapper(object):
    def __init__(self, connection):
        self._connection = connection

    def __reduce__(self):
        return multiprocessing.reduction.reduce_connection( self._connection)

    def __getattr__(self, name):
        return getattr(self._connection, name)


class ThreadingFuture(Future):
    def __init__(self, pipe=None):
        super(ThreadingFuture, self).__init__()
        if pipe is not None:
            self.reader, self.writer = pipe
        else:
            self.reader, self.writer = multiprocessing.Pipe(False)
        if not isinstance(self.reader, _ConnectionWrapper):
            self.reader = _ConnectionWrapper(self.reader)
        if not isinstance(self.writer, _ConnectionWrapper):
            self.writer = _ConnectionWrapper(self.writer)
        self.value_received = False
        self.value = None

    # pylint: disable = E0702
    def get(self, timeout=None):
        if self.value_received:
            if isinstance(self.value, Exception):
                raise self.value
            else:
                return self.value
        if self.reader.poll(timeout):
            self.value = self.reader.recv()
            self.value_received = True
            return self.get()
        else:
            raise Timeout('%s seconds' % timeout)
    # pylint: enable = E0702

    def set(self, value=None):
        self.writer.send(value)

    def set_exception(self, exception):
        self.set(exception)


def get_all(futures, timeout=None):
    """
    Collect all values encapsulated in the list of futures.

    If ``timeout`` is not :class:`None`, the method will wait for a reply for
    ``timeout`` seconds, and then raise :exc:`pykka.future.Timeout`.

    :param futures: futures for the results to collect
    :type futures: list of `pykka.future.Future`

    :param timeout: seconds to wait before timeout
    :type timeout: float or :class:`None`

    :returns: list of results
    """
    return [future.get(timeout=timeout) for future in futures]
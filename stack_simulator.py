# file stack.py

# utility for "stack:
# initialization is done above.
# stack.py

StackError = 'StackError'

class Stack:
    """A generic Stack class.""" 

    def __init__(self, something=None):
        if type(something) == type([]):
            self._data = []
            for item in something:
                self._data.append(item)
        elif isinstance(something, Stack):
            # copy constructor
            self._data = []
            for x in something._data:
                self._data.append(x)
        elif something is None:
            self._data = []
        else:
            self._data = []
            self._data.append(something)

    def push(self, obj):
        """Push an element on the Stack."""
        self._data.append(obj)

    def pop(self):
        """Pop an element from the Stack."""
        if len(self._data) > 0:
            result = self._data[-1]    # get the last (topmost) element
            del self._data[-1]
            return result
        else:
            raise StackError, "Stack is empty"

    def pushmore(self, seq):
        for item in seq: self.push(item)

    def popmore(self, number):
        seq = []
        for x in number: seq.append(self.pop())
        return seq

    def isempty(self):
        return len(self._data) == 0

    def num_items(self):
        return len(self._data)

    def __repr__(self):
        """Representation of a Stack."""
        return `self._data`
        # I'll take a list for this until I have something better

    def __len__(self):
        return len(self._data)

    # __add__ (+) is a replacement for push, nothing more, nothing less
    def __add__(self, obj):
        somestack = Stack(self)
        somestack.push(obj)
        return somestack



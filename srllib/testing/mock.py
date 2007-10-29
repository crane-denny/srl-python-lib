#
# (c) Dave Kirby 2001 - 2005
#     mock@thedeveloperscoach.com
# (c) Arve Knudsen 2007
#     arve.knudsen@gmail.com
#
# Original call interceptor and call assertion code by Phil Dawes (pdawes@users.sourceforge.net)
# Call interceptor code enhanced by Bruce Cropley (cropleyb@yahoo.com.au)
#
# This Python  module and associated files are released under the FreeBSD
# license. Essentially, you can do what you like with it except pretend you wrote
# it yourself.
# 
# 
#     Copyright (c) 2005, Dave Kirby, 2007, Arve Knudsen
# 
#     All rights reserved.
# 
#     Redistribution and use in source and binary forms, with or without
#     modification, are permitted provided that the following conditions are met:
# 
#         * Redistributions of source code must retain the above copyright
#           notice, this list of conditions and the following disclaimer.
# 
#         * Redistributions in binary form must reproduce the above copyright
#           notice, this list of conditions and the following disclaimer in the
#           documentation and/or other materials provided with the distribution.
# 
#         * Neither the name of this library nor the names of its
#           contributors may be used to endorse or promote products derived from
#           this software without specific prior written permission.
# 
#     THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
#     ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
#     WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
#     DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR
#     ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
#     (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
#     LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON
#     ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
#     (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
#     SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
# 
#         mock@thedeveloperscoach.com


""" Mock object library for Python.

Mock objects can be used when unit testing
to remove a dependency on another production class. They are typically used
when the dependency would either pull in lots of other classes, or
significantly slow down the execution of the test.
They are also used to create exceptional conditions that cannot otherwise
be easily triggered in the class under test.
"""
__version__ = "0.2.0"

# Added in Python 2.1
import inspect
import re

import srllib.inspect

class MockInterfaceError(Exception):
    pass

class Mock(object):
    """ The Mock class simulates any other class for testing purposes.
    
    All method calls are stored for later examination.
    @cvar mockInstances: Dictionary of all mock instances, indexed on class to
    discern different mock subclasses.
    @cvar _MockRealClass: For subclasses, indicate the class that is being
    mocked.
    """
    mockInstances = {}
    _MockRealClass = None

    def __init__(self, returnValues=None, properties=None, realClass=None,
            name=None):
        """ Constructor.
        
        Methods that are not in the returnValues dictionary will return None.
        You may also supply a class whose interface is being mocked.  All calls
        will be checked to see if they appear in the original interface. Any
        calls to methods not appearing in the real class will raise a
        MockInterfaceError.  Any calls that would fail due to non-matching
        parameter lists will also raise a MockInterfaceError.  Both of these
        help to prevent the Mock class getting out of sync with the class it is
        Mocking.
        @param returnValues: Define return values for mocked methods.
        @param properties: Define return values for mocked properties.
        @param realClass: Specify the mocked class.
        @param name: Optionally specify mock's name.
        @raise MockInterfaceError: An inconsistency was detected in the
        mock's interface.
        """
        if returnValues is None:
            returnValues = {}
        if properties is None:
            properties = {}
        
        self.mockCalledMethods = {}
        self.mockAllCalledMethods = []
        self.mockReturnValues = returnValues
        self.mockExpectations = {}
        self.__realClassMethods = self.__realClassProperties = {}
        self.__name = name
        self.__methods = {}    # Keep a cache of methods
        if realClass is None:
            realClass = self._MockRealClass
        self.__realClass = realClass
        if realClass is not None:
            # Verify interface versus mocked class
            assert inspect.isclass(realClass)
            assert not issubclass(realClass, (MockCallable, Mock)), realClass
            self.__realClassMethods = srllib.inspect.get_members(realClass,
                    inspect.isroutine)
            
            # Verify that mocked methods exist in real class
            for retMethod in self.mockReturnValues.keys():
                if not self.__realClassMethods.has_key(retMethod):
                    raise MockInterfaceError("Return value supplied for method \
'%s' that was not in the original class (%s)" % (retMethod, realClass.__name__))
            
            # Verify that mocked properties exist in real class
            
            realprops = self.__realClassProperties = \
                srllib.inspect.get_members(realClass, inspect.isdatadescriptor)
            for name in properties:
                if  name not in realprops:
                    raise MockInterfaceError("'%s' is not a property of '%s'" %
                            (name, realClass))
                
            # Now properties
            mockprops = srllib.inspect.get_members(self.__class__,
                inspect.isdatadescriptor)
            for name, prop in mockprops.items():
                if name.startswith("mock"):
                    continue
                if name not in realprops:
                    raise MockInterfaceError("'%s' is not a property of '%s'" %
                            (name, realClass))
            
            self.__realClassProperties = properties
            
        self.__setupSubclassMethodInterceptors()

        # Record this instance among all mock instances
        tp = type(self)
        if not tp in Mock.mockInstances:
            Mock.mockInstances[tp] = []
        Mock.mockInstances[tp].append(self)

    def __str__(self):
        if self.__name is not None:
            return self.__name
        return object.__str__(self)
 
    def __getattr__(self, name):
        props = self.__dict__["_Mock__realClassProperties"]
        try: return props[name]
        except KeyError: pass
        if name.startswith("mock"):
            # Don't mock mock methods!
            raise AttributeError(name)
        # Keep a cache of methods for this object, so that references to the
        # mock's "methods" don't go out of scope
        return self.__methods.setdefault(name, MockCallable(name, self))
    
    def __call__(self, *args, **kwds):
        """ Allow calling directly. """
        return self.__getattr__("__call__")(*args, **kwds)
    
    @property
    def mockAccessedAttrs(self):
        """ All accessed attributes.
        """
        return self.__methods.keys()

    @classmethod
    def mockGetAllInstances(cls):
        """ Get all instances of this mock class.
        """
        return cls.mockInstances.get(cls, [])
    
    def mockClearCalls(self):
        """ Clear all calls registered so far. """
        self.mockAllCalledMethods = []
        self.mockCalledMethods.clear()
        
    def mockSetReturnValue(self, name, value):
        """ Set a return value for a method """
        self.mockReturnValues[name] = value
    
    def mockAddReturnValues(self, **methodReturnValues ):
        self.mockReturnValues.update(methodReturnValues)
        
    def mockSetExpectation(self, name, testFn, after=0, until=0):
        """ Set an expectation for a method call. """
        self.mockExpectations.setdefault(name, []).append((testFn, after,
                until))
        
    def mockSetRaises(self, name, exc):
        """ Set an exception to be raised by a method. """
        mock_callable = getattr(self, name)
        assert isinstance(mock_callable, MockCallable)
        mock_callable.mockSetRaises(exc)
        
    def mockGetCall(self, idx):
        """ Get a certain L{call<MockCall>} that was made. """
        return self.mockAllCalledMethods[idx]

    def mockGetAllCalls(self):
        """ Get all calls.
        @return: List of L{MockCall} objects, representing all the methods in
        the order they were called.
        """
        return self.mockAllCalledMethods

    def mockGetNamedCalls(self, methodName):
        """ Get all calls to a certain method.
        @return: List of L{MockCall} objects, representing all the calls to the
        named method in the order they werecalled.
        """
        return self.mockCalledMethods.get(methodName, [])

    def mockCheckCall(self, tester, index, name, *args, **kwargs):
        """ Test that the index-th call had the specified name and
        parameters.
        """
        try: call = self.mockAllCalledMethods[index]
        except IndexError:
            tester.fail("No call with index %d" % index)
        tester.assertEqual(name, call.name, "Expected call number %d to \
be to %s, but it was to %s instead" % (index, name, call.name,))
        call.checkArgs(tester, *args, **kwargs)
        
    def mockCheckCalls(self, tester, calls):
        """ Test that a specified sequence of calls were made.
        @param tester: The test case.
        @param calls: A sequence of (name, args, kwargs) tuples.
        """
        numCalls, numExpected = len(self.mockAllCalledMethods), len(calls)
        if numCalls != numExpected:
            if numCalls < numExpected:
                tester.fail("No more than %d calls were made (expected %d)" %
                        (numCalls, numExpected))
            else:
                tester.fail("%d calls were made, expected %d" %
                        (numCalls, numExpected))
                
        for i, call in enumerate(calls):
            name = call[0]
            try: args = call[1]
            except IndexError: args = ()
            try: kwds = call[2]
            except IndexError: kwds = {}
            self.mockCheckCall(tester, i, name, *args, **kwds)
                
    def mockCheckNamedCall(self, tester, methodName, index, *args, **kwargs):
        """ Test that the index-th call to a certain method had the specified
        parameters.
        @raise IndexError: No call with this index.
        """
        self.mockCalledMethods.get(methodName, [])
        call = self.mockCalledMethods.get(methodName, [])[index]
        call.checkArgs(tester, *args, **kwargs)
                
    def mockCheckNamedCalls(self, tester, methodName, calls):
        """ Test that a specified sequence of calls to a certain method were
        made.
        @param tester: The test case.
        @param methodName: The method's name.
        @param calls: A sequence of (args, kwargs) tuples.
        """
        numCalls, numExpected = len(self.mockCalledMethods.get(methodName,
                [])), len(calls)
        if numCalls != numExpected:
            if numCalls < numExpected:
                tester.fail("No more than %d calls were made (expected %d)" %
                        (numCalls, numExpected))
            else:
                tester.fail("%d calls were made, expected %d" %
                        (numCalls, numExpected))
        
        for i, call in enumerate(calls):
            try: args = call[0]
            except IndexError: args = ()
            try: kwds = call[1]
            except IndexError: kwds = {}
            self.mockCheckNamedCall(tester, methodName, i, *args, **kwds)
     
    def __setupSubclassMethodInterceptors(self):
        methods = srllib.inspect.get_members(self.__class__, inspect.isroutine)
        baseMethods = srllib.inspect.get_members(Mock, inspect.ismethod)
        for name in methods:
            # Don't record calls to methods of Mock base class or methods
            # that start with 'mock'.
            if name not in baseMethods and not name.startswith("mock"):
                self.__dict__[name] = MockCallable(name, self, handcrafted=True)

    def _mockCheckInterfaceCall(self, name, callParams, callKwParams):
        """
        Check that a call to a method of the given name to the original
        class with the given parameters would not fail. If it would fail,
        raise a MockInterfaceError.
        Based on the Python 2.3.3 Reference Manual section 5.3.4: Calls.
        """
        if self.__realClass is None:
            return
        if not self.__realClassMethods.has_key(name):
            raise MockInterfaceError("Calling mock method '%s' that was not \
found in the original class (%s)" % (name, self.__realClass.__name__))

        func = self.__realClassMethods[name]
        try:
            args, varargs, varkw, defaults = inspect.getargspec(func)
        except TypeError:
            # func is not a Python function. It is probably a builtin,
            # such as __repr__ or __coerce__. TODO: Checking?
            # For now assume params are OK.
            return

        # callParams doesn't include self; args does include self.
        numPosCallParams = 1 + len(callParams)

        if numPosCallParams > len(args) and not varargs:
            raise MockInterfaceError("Original %s() takes at most %s arguments \
(%s given)" % 
                (name, len(args), numPosCallParams))

        # Get the number of positional arguments that appear in the call,
        # also check for duplicate parameters and unknown parameters
        numPosSeen = _getNumPosSeenAndCheck(numPosCallParams, callKwParams,
            args, varkw)

        lenArgsNoDefaults = len(args) - len(defaults or [])
        if numPosSeen < lenArgsNoDefaults:
            raise MockInterfaceError("Original %s() takes at least %s \
arguments (%s given)" % (name, lenArgsNoDefaults, numPosSeen))
        

def _getNumPosSeenAndCheck(numPosCallParams, callKwParams, args, varkw):
    """
    Positional arguments can appear as call parameters either named as
    a named (keyword) parameter, or just as a value to be matched by
    position. Count the positional arguments that are given by either
    keyword or position, and check for duplicate specifications.
    Also check for arguments specified by keyword that do not appear
    in the method's parameter list.
    """
    posSeen = {}
    for arg in args[:numPosCallParams]:
        posSeen[arg] = True
    for kwp in callKwParams:
        if posSeen.has_key(kwp):
            raise MockInterfaceError("%s appears as both a positional and named \
parameter." % kwp)
        if kwp in args:
            posSeen[kwp] = True
        elif not varkw:
            raise MockInterfaceError("Original method does not have a parameter \
'%s'" % kwp)
    return len(posSeen)

class MockCall:
    """ MockCall records the name and parameters of a call to an instance
    of a Mock class.
    
    Instances of MockCall are created by the Mock class, but can be inspected
    later as part of the test.
    @ivar name: Name of callable.
    @ivar args: Arguments to callable.
    @ivar kwargs: Keyword arguments to callable.
    """
    def __init__(self, name, args, kwargs):
        self.name = name
        self.args = args
        self.kwargs = kwargs

    def checkArgs(self, tester, *args, **kwargs):
        args = tuple(args)
        assert isinstance(self.args, tuple), "%r" % (self.args,)
        tester.assertEqual(args, self.args, "Arguments %r differ from \
those expected: %r" % (self.args, args))
        tester.assertEqual(kwargs, self.kwargs, "Keyword arguments (%r) \
differ from those expected (%r)" % (self.kwargs, kwargs))

    def getParam(self, n):
        if isinstance(n, int):
            return self.args[n]
        elif isinstance(n, str):
            return self.kwargs[n]
        else:
            raise IndexError, 'illegal index type for getParam'

    @property
    def numArgs(self):
        return len(self.args)

    @property
    def numKwargs(self):
        return len(self.kwargs)
    
    #pretty-print the method call
    def __str__(self):
        s = self.name + "("
        sep = ''
        for p in self.args:
            s = s + sep + repr(p)
            sep = ', '
        items = self.kwargs.items()
        items.sort()
        for k,v in items:
            s = s + sep + k + '=' + repr(v)
            sep = ', '
        s = s + ')'
        return s
    def __repr__(self):
        return self.__str__()

class MockCallable:
    """ Intercept/record a call.
    
    The call is delegated to either the mock's dictionary of mock return
    values that was passed in to the constructor, or a handcrafted method
    of a Mock subclass.
    """
    def __init__(self, name, mock, handcrafted=False):
        """
        @param name: Name of callable.
        @param mock: Parent mock.
        @param handcrafted: ?
        """
        self.name = name
        self.mock = mock
        self.handcrafted = handcrafted
        self.__exc = None

    def __call__(self,  *params, **kwparams):
        self.mock._mockCheckInterfaceCall(self.name, params, kwparams)
        thisCall = self.recordCall(params,kwparams)
        self.checkExpectations(thisCall, params, kwparams)
        return self.makeCall(params, kwparams)
    
    def mockSetRaises(self, exc):
        """ Set an exception that should be raised when called. """
        self.__exc = exc

    def recordCall(self, params, kwparams):
        """
        Record the MockCall in an ordered list of all calls, and an ordered
        list of calls for that method name.
        """
        thisCall = MockCall(self.name, params, kwparams)
        calls = self.mock.mockCalledMethods.setdefault(self.name, [])
        calls.append(thisCall)
        self.mock.mockAllCalledMethods.append(thisCall)
        return thisCall

    def makeCall(self, params, kwparams):
        if self.__exc is not None:
            raise self.__exc
        
        if self.handcrafted:
            allPosParams = (self.mock,) + params
            func = _findFunc(self.mock.__class__, self.name)
            if not func:
                raise NotImplementedError
            return func(*allPosParams, **kwparams)
        else:
            returnVal = self.mock.mockReturnValues.get(self.name)
            if isinstance(returnVal, ReturnValuesBase):
                returnVal = returnVal.next()
            return returnVal

    def checkExpectations(self, thisCall, params, kwparams):
        if self.name in self.mock.mockExpectations:
            callsMade = len(self.mock.mockCalledMethods[self.name])
            for (expectation, after, until) in self.mock.mockExpectations[
                    self.name]:
                if callsMade > after and (until==0 or callsMade < until):
                    assert expectation(self.mock, thisCall, len(
                            self.mock.mockAllCalledMethods)-1), \
                            'Expectation failed: '+str(thisCall)


def _findFunc(cl, name):
    """ Depth first search for a method with a given name. """
    if cl.__dict__.has_key(name):
        return cl.__dict__[name]
    for base in cl.__bases__:
        func = _findFunc(base, name)
        if func:
            return func
    return None


class ReturnValuesBase:
    def next(self):
        try:
            return self.iter.next()
        except StopIteration:
            raise AssertionError("No more return values")
    def __iter__(self):
        return self

class ReturnValues(ReturnValuesBase):
    def __init__(self, *values):
        self.iter = iter(values)
        

class ReturnIterator(ReturnValuesBase):
    def __init__(self, iterator):
        self.iter = iter(iterator)

        
def expectParams(*params, **keywords):
    '''check that the callObj is called with specified params and keywords
    '''
    def fn(mockObj, callObj, idx):
        return callObj.args == params and callObj.kwargs == keywords
    return fn


def expectAfter(*methods):
    '''check that the function is only called after all the functions in 'methods'
    '''
    def fn(mockObj, callObj, idx):
        calledMethods = [method.name for method in mockObj.mockGetAllCalls()]
        #skip last entry, since that is the current call
        calledMethods = calledMethods[:-1]
        for method in methods:  
            if method not in calledMethods:
                return False
        return True
    return fn

def expectException(exception, *args, **kwargs):
    ''' raise an exception when the method is called
    '''
    def fn(mockObj, callObj, idx):
        raise exception(*args, **kwargs)
    return fn


def expectParam(paramIdx, cond):
    '''check that the callObj is called with parameter specified by paramIdx (a
    position index or keyword) fulfills the condition specified by cond. cond is
    a function that takes a single argument, the value to test.
    '''
    def fn(mockObj, callObj, idx):
        param = callObj.getParam(paramIdx)
        return cond(param)
    return fn

def EQ(value):
    def testFn(param):
        return param == value
    return testFn

def NE(value):
    def testFn(param):
        return param != value
    return testFn

def GT(value):
    def testFn(param):
        return param > value
    return testFn

def LT(value):
    def testFn(param):
        return param < value
    return testFn

def GE(value):
    def testFn(param):
        return param >= value
    return testFn

def LE(value):
    def testFn(param):
        return param <= value
    return testFn

def AND(*condlist):
    def testFn(param):
        for cond in condlist:
            if not cond(param):
                return False
        return True
    return testFn

def OR(*condlist):
    def testFn(param):
        for cond in condlist:
            if cond(param):
                return True
        return False
    return testFn

def NOT(cond):
    def testFn(param):
        return not cond(param)
    return testFn

def MATCHES(regex, *args, **kwargs):
    compiled_regex = re.compile(regex, *args, **kwargs)
    def testFn(param):
        return compiled_regex.match(param) != None
    return testFn

def SEQ(*sequence):
    iterator = iter(sequence)
    def testFn(param):
        try:
            cond = iterator.next()
        except StopIteration:
            raise AssertionError('SEQ exhausted')
        return cond(param)
    return testFn

def IS(instance):
    def testFn(param):
        return param is instance
    return testFn

def ISINSTANCE(class_):
    def testFn(param):
        return isinstance(param, class_) 
    return testFn

def ISSUBCLASS(class_):
    def testFn(param):
        return issubclass(param, class_) 
    return testFn

def CONTAINS(val):
    def testFn(param):
        return val in param 
    return testFn

def IN(container):
    def testFn(param):
        return param in container
    return testFn

def HASATTR(attr):
    def testFn(param):
        return hasattr(param, attr)
    return testFn

def HASMETHOD(method):
    def testFn(param):
        return hasattr(param, method) and callable(getattr(param, method))
    return testFn

CALLABLE = callable




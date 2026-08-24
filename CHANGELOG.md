# v 0.3
## Breaking Changes 
- Estim2pyStatus methods are now all get_foo or is_foo.
- Estim2pyStatus as_items returns a tuple of tuples.  This sucks and will change I think
- Estim2pyMode internal modes datatype switched from mutable dictionary to tuple

## Additions
- Added an exception, Estim2pyError
- Estim2pyStatus now has >, <, >=, <= comparisons. See the accompanying zine for more information. 
- Estim2pyStatus has a changed method, to tell you which members of two different statuses are different
- much more tests, safe to run if the hardware is not plugged in.
- warning about scratch submissives

## Changes
- Estim2py now uses type hints

### Estim2pySimulatedConnection
- You can now simulate exceptions
- Every status is a deep copy, that way it behaves similarly to the real thing.

### Estim2pyConnection
- Sensible delay timing has been figured out, and set as the default.
- A destructor (__del__) is written to close the serial port
- set_a thru set_d defined 
- bug in setToStatus fixed

### Estim2pyStatus
- get_a thru get_d implemented
- Now handles str() and bytes() nicely
- If parsing a status fails, a proper exceptions will be thrown

### Internals
- unit tests do better checking of hardware existence
- unit tests added to check timing were created (and skipped by default).... SCIENCE
- unit test fixtures used for hardware connection, etc.

# v 0.2.2
## Additions
- (Slightly) Better documentation, trying out sphynx

## Changes
- Fixed logging to be better
- Added set_to_status which changes all settings of the box to the values of an Estim2Status object 
- Tweaked timeout and delay a little.  Not convinced it's right.

# v 0.2.1
## Additions
- Added Doc strings
- Added Documentation
## Changes
- Fixed a typo

# v 0.2.0
## Additions
- Added a changelog
- Added Logging
- Added a way to get key/vals from Estim2pyModes
- Added a simulated connection
## Changes
- Changed Estim2pyMode to be singular.
- Channel arguments have better names
- Channel arguments to status or connection can be upper or lower case
## Bugfixes
- Fixed a bug in get_mode()
- Comparison between two status's now respect type
- Some modes incorrectly reported None for param_b

# v 0.1.0

Babby's first package


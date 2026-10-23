This module implements FinTS only on top of
[python-fints](https://github.com/raphaelm/python-fints). Changes
needed for a specific bank, e.g. to work around a bank that deviates
from the FinTS specification or from the parameters it announces, do
not belong in this module: propose them as a pull request to
python-fints instead, so that every user of the library benefits from
them.

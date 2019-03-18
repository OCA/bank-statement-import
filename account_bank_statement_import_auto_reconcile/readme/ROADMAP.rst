* add more matching rules:
    * AmountDiffuse (let the user configure the threshold)
    * SameCompany (if A from company C bought it, but B from the same company/organization pays)
    * AmountTransposedDigits (reconcile if only two digits are swapped. Dangerous and a special case of AmountDiffuse)
    * whatever else we can think of
* add some helpers/examples for using the options field
* allow to fiddle with the parameters of configured rules during a specific import

Background
~~~~~~~~~~

Mainly, this module is a framework for conveniently (for programmers) adding new custom automatic reconciliation rules. To do this, study the provided AbstractModels.

This module provides online bank statements from
[PayPal.com](https://paypal.com/).

Requests that fail for a temporary reason (rate limit, server or network
error) are retried a few times, waiting longer at each attempt. Other
errors are reported with the message sent by PayPal and its debug id.

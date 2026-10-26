This module provides online bank statements from stripe.com


Requests that fail for a temporary reason (rate limit, conflict, server
or network error) are retried a few times, waiting longer at each
attempt, as recommended by Stripe. Other errors are reported with the
message sent by Stripe and the id of the request.

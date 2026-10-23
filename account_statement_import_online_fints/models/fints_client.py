# Copyright 2026 Michael Tietz (MT Software) <mtietz@mt-software.de>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from fints import client
from fints.exceptions import FinTSSCARequiredError


class FinTS3PinTanClient(client.FinTS3PinTanClient):
    # Types of the commands the bank only accepts with a TAN segment, whatever
    # its parameters announce, e.g. {"HKKAZ"}
    tan_segment_types = frozenset()

    def __enter__(self):
        res = super().__enter__()
        # python-fints only ends its bootstrap mode in get_tan_media(), until
        # then it ignores a 9075 (strong customer authentication required) and
        # e.g. returns no transactions instead of raising FinTSSCARequiredError
        # TODO: remove once released in python-fints, see
        # https://github.com/raphaelm/python-fints/pull/228
        self._bootstrap_mode = False
        return res

    def _need_twostep_tan_for_segment(self, seg):
        if (
            self.selected_security_function not in (None, "999")
            and seg.header.type in self.tan_segment_types
        ):
            return True
        return super()._need_twostep_tan_for_segment(seg)

    def _send_with_possible_retry(self, dialog, command_seg, resume_func):
        try:
            return super()._send_with_possible_retry(dialog, command_seg, resume_func)
        except FinTSSCARequiredError:
            if self.selected_security_function in (
                None,
                "999",
            ) or self._need_twostep_tan_for_segment(command_seg):
                raise
        # Some banks announce that a command needs no TAN,
        # but reject it without one (9075). Only with a TAN segment, the bank
        # can ask for the confirmation (or answer that none is needed). The
        # type is kept, to send the next ones with a TAN segment right away.
        self.tan_segment_types = self.tan_segment_types | {command_seg.header.type}
        return super()._send_with_possible_retry(dialog, command_seg, resume_func)

    def _continue_check_transactions_access(self, command_seg, response):
        """Resume method of a confirmation asked for by a check of the access
        to the transactions, which only needs the confirmation"""
        return None

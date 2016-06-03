# -*- coding: utf-8 -*-

import logging

_logger = logging.getLogger(__name__)

try:
    from ofxparse import OfxParser as OfxParserOriginal
    OfxParser_ok = True
except ImportError:
    _logger.warn("ofxparse not found, OFX parsing disabled.")
    OfxParserOriginal = object
    OfxParser_ok = False


class OfxParser(OfxParserOriginal):
    """ Custom changes in the OFX Parser.
    """

    @classmethod
    def _tagToDecimal(self, tag):
        tag.string = tag.string.replace(',', '.')

    @classmethod
    def parseStatement(cls_, stmt_ofx):
        """Amount with ',' replaced by '.' in the following tags :
        //LEDGERBAL/BALAMT
        """
        ledgerbal_tag = stmt_ofx.find('ledgerbal')
        if hasattr(ledgerbal_tag, "contents"):
            cls_._tagToDecimal(ledgerbal_tag.find('balamt'))
        return super(OfxParser, cls_).parseStatement(stmt_ofx)

    @classmethod
    def parseTransaction(cls_, txn_ofx):
        """Amount with ',' replaced by '.' in the following tags :
        //TRNAMT
        """
        cls_._tagToDecimal(txn_ofx.find('trnamt'))
        return super(OfxParser, cls_).parseTransaction(txn_ofx)

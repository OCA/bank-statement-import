# -*- encoding: utf-8 -*-

##############################################################################
#    
# Module : account_bank_statement_import_ofx
# Modified : 2016-01-28 : Stephane LERENDU <stephane.lerendu@mind-and-go.com>
# Approbation             Florent THOMAS <florent.thomas@mind-and-go.com>
# 
# modification in the account_bank_statement_import_ofx.py file
# in the res.partner.bank object, I search partner_id field to have the name
#
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

{
    'name': 'Import OFX Bank Statement',
    'category': 'Banking addons',
    'version': '8.0.1.0.0',
    'author': 'OpenERP SA,'
              'Odoo Community Association (OCA)',
    'website': 'https://github.com/OCA/bank-statement-import',
    'depends': [
        'account_bank_statement_import'
    ],
    'demo': [
        'demo/demo_data.xml',
    ],
    'external_dependencies': {
        'python': ['ofxparse'],
    },
    'auto_install': False,
    'installable': True,
}

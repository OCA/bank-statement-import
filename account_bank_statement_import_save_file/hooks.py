# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    This module copyright (C) 2015 Therp BV <http://therp.nl>.
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
from openerp import SUPERUSER_ID


def _post_init_hook(cr, pool):
    # if we install this module on a database with remains of account_banking,
    # migrate account.banking.imported.file
    cr.execute(
        "select 1 from pg_catalog.pg_class c "
        "join pg_catalog.pg_namespace n ON n.oid = c.relnamespace "
        "where n.nspname = 'public' and "
        "c.relname = 'account_banking_imported_file' and "
        "c.relkind = 'r'")
    if cr.fetchall():
        _post_init_hook_migrate_account_banking_imported_file(cr, pool)


def _post_init_hook_migrate_account_banking_imported_file(cr, pool):
    # create attachments
    cr.execute(
        """insert into ir_attachment
        (
            name, create_uid, create_date, datas_fname, description,
            company_id, res_model, type,
            res_id
        )
        select
        coalesce(file_name, '<unknown>'), user_id, date, file_name, log,
        company_id, 'account.bank.statement', 'binary',
        (
            select id from account_bank_statement
            where banking_id=f.id
            limit 1
        )
        from account_banking_imported_file f
        returning id""")

    attachment_ids = [attachment_id for attachment_id, in cr.fetchall()]

    # assign respective attachment to all statements pointing to an imported
    # banking file
    cr.execute(
        """with banking_id2attachment as (
            select distinct b.id banking_id, a.id attachment_id
            from account_banking_imported_file b
            join account_bank_statement s
            on s.banking_id=b.id
            join ir_attachment a
            on a.id in %s and s.id=a.res_id
        )
        update account_bank_statement s
        set import_file=b2a.attachment_id
        from banking_id2attachment b2a
        where b2a.banking_id=s.banking_id""",
        (tuple(attachment_ids),)
    )

    # now we just have to write the file's content via the orm
    # (to support non-db storage)
    cr.execute(
        """select distinct a.id, b.file
        from account_banking_imported_file b
        join account_bank_statement s
        on s.banking_id=b.id
        join ir_attachment a
        on a.id in %s and s.id=a.res_id""",
        (tuple(attachment_ids),)
    )
    for attachment_id, content in cr.fetchall():
        pool['ir.attachment'].write(
            cr, SUPERUSER_ID,
            [attachment_id],
            {'datas': str(content)})

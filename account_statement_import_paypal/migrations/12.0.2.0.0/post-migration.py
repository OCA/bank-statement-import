# Copyright 2020 Brainbean Apps (https://brainbeanapps.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from openupgradelib import openupgrade


@openupgrade.migrate()
def migrate(env, version):
    openupgrade.logged_query(
        env.cr,
        """
WITH _mappings AS (
    SELECT
        m.id,
        l.field_to_assign,
        l.name,
        l.date_format
    FROM
        account_bank_statement_import_paypal_map AS m
    RIGHT OUTER JOIN (
        SELECT
            *,
            ROW_NUMBER() OVER (
                PARTITION BY map_parent_id, field_to_assign
                ORDER BY id ASC
            ) AS row_number
        FROM account_bank_statement_import_paypal_map_line
        WHERE field_to_assign IS NOT NULL
    ) AS l ON m.id = l.map_parent_id AND l.row_number = 1
)

INSERT INTO account_bank_statement_import_paypal_mapping (
    name,
    float_thousands_sep,
    float_decimal_sep,
    date_format,
    time_format,
    date_column,
    time_column,
    tz_column,
    name_column,
    currency_column,
    gross_column,
    fee_column,
    balance_column,
    transaction_id_column,
    description_column,
    from_email_address_column,
    invoice_id_column,
    bank_name_column,
    bank_account_column
)
SELECT
    m.name,
    m.float_thousands_sep,
    m.float_decimal_sep,
    COALESCE(_date.date_format, '%m/%d/%Y') AS date_format,
    '%H:%M:%S' AS time_format,
    COALESCE(_date.name, 'Date') AS date_column,
    COALESCE(_time.name, 'Time') AS time_column,
    'Time Zone' AS tz_column,
    COALESCE(_name.name, 'Name') AS name_column,
    COALESCE(_currency.name, 'Currency') AS currency_column,
    COALESCE(_gross.name, 'Gross') AS gross_column,
    COALESCE(_fee.name, 'Fee') AS fee_column,
    COALESCE(_balance.name, 'Balance') AS balance_column,
    COALESCE(_tid.name, 'Transaction ID') AS transaction_id_column,
    COALESCE(_description.name, 'Description') AS description_column,
    COALESCE(_from_email.name, 'From Email Address')
        AS from_email_address_column,
    COALESCE(_invoice.name, 'Invoice ID') AS invoice_id_column,
    COALESCE(_bank_name.name, 'Bank Name') AS bank_name_column,
    COALESCE(_bank_acc.name, 'Bank Account') AS bank_account_column
FROM
    account_bank_statement_import_paypal_map AS m
LEFT JOIN _mappings AS _date
    ON m.id = _date.id AND _date.field_to_assign = 'date'
LEFT JOIN _mappings AS _time
    ON m.id = _time.id AND _time.field_to_assign = 'time'
LEFT JOIN _mappings AS _name
    ON m.id = _name.id AND _name.field_to_assign = 'partner_name'
LEFT JOIN _mappings AS _currency
    ON m.id = _currency.id AND _currency.field_to_assign = 'currency'
LEFT JOIN _mappings AS _gross
    ON m.id = _gross.id AND _gross.field_to_assign = 'amount'
LEFT JOIN _mappings AS _fee
    ON m.id = _fee.id AND _fee.field_to_assign = 'commission'
LEFT JOIN _mappings AS _balance
    ON m.id = _balance.id AND _balance.field_to_assign = 'balance'
LEFT JOIN _mappings AS _tid
    ON m.id = _tid.id AND _tid.field_to_assign = 'transaction_id'
LEFT JOIN _mappings AS _description
    ON m.id = _description.id AND _description.field_to_assign = 'description'
LEFT JOIN _mappings AS _from_email
    ON m.id = _from_email.id AND _from_email.field_to_assign = 'email'
LEFT JOIN _mappings AS _invoice
    ON m.id = _invoice.id AND _invoice.field_to_assign = 'invoice_number'
LEFT JOIN _mappings AS _bank_name
    ON m.id = _bank_name.id AND _bank_name.field_to_assign = 'bank_name'
LEFT JOIN _mappings AS _bank_acc
    ON m.id = _bank_acc.id AND _bank_acc.field_to_assign = 'bank_account';
        """,
    )

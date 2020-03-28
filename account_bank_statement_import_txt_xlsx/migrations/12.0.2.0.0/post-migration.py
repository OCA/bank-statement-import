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
        account_bank_statement_import_map AS m
    RIGHT OUTER JOIN (
        SELECT
            *,
            ROW_NUMBER() OVER (
                PARTITION BY map_parent_id, field_to_assign
                ORDER BY id ASC
            ) AS row_number
        FROM account_bank_statement_import_map_line
        WHERE field_to_assign IS NOT NULL
    ) AS l ON m.id = l.map_parent_id AND l.row_number = 1
)

INSERT INTO account_bank_statement_import_sheet_mapping (
    name,
    float_thousands_sep,
    float_decimal_sep,
    file_encoding,
    delimiter,
    quotechar,
    timestamp_format,
    timestamp_column,
    amount_column,
    original_currency_column,
    original_amount_column,
    description_column,
    reference_column,
    notes_column,
    partner_name_column,
    bank_account_column
)
SELECT
    m.name,
    m.float_thousands_sep,
    m.float_decimal_sep,
    m.file_encoding,
    (
        CASE
            WHEN m.delimiter='.' THEN 'dot'
            WHEN m.delimiter=',' THEN 'comma'
            WHEN m.delimiter=';' THEN 'semicolon'
            WHEN m.delimiter='' THEN 'n/a'
            WHEN m.delimiter='\t' THEN 'tab'
            WHEN m.delimiter=' ' THEN 'space'
            ELSE 'n/a'
        END
    ) AS delimiter,
    m.quotechar,
    COALESCE(_date.date_format, '%m/%d/%Y') AS timestamp_format,
    COALESCE(_date.name, 'Date') AS timestamp_column,
    COALESCE(_amount.name, 'Amount') AS amount_column,
    _o_currency.name AS original_currency_column,
    _o_amount.name AS original_amount_column,
    _description.name AS description_column,
    _ref.name AS reference_column,
    _notes.name AS notes_column,
    _p_name.name AS partner_name_column,
    _bank_acc.name AS bank_account_column
FROM
    account_bank_statement_import_map AS m
LEFT JOIN _mappings AS _date
    ON m.id = _date.id AND _date.field_to_assign = 'date'
LEFT JOIN _mappings AS _description
    ON m.id = _description.id AND _description.field_to_assign = 'name'
LEFT JOIN _mappings AS _o_currency
    ON m.id = _o_currency.id AND _o_currency.field_to_assign = 'currency'
LEFT JOIN _mappings AS _amount
    ON m.id = _amount.id AND _amount.field_to_assign = 'amount'
LEFT JOIN _mappings AS _o_amount
    ON m.id = _o_amount.id AND _o_amount.field_to_assign = 'amount_currency'
LEFT JOIN _mappings AS _ref
    ON m.id = _ref.id AND _ref.field_to_assign = 'ref'
LEFT JOIN _mappings AS _notes
    ON m.id = _notes.id AND _notes.field_to_assign = 'note'
LEFT JOIN _mappings AS _p_name
    ON m.id = _p_name.id AND _p_name.field_to_assign = 'partner_name'
LEFT JOIN _mappings AS _bank_acc
    ON m.id = _bank_acc.id AND _bank_acc.field_to_assign = 'account_number';
        """
    )

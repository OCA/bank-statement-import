def migrate(cr, version):
    cr.execute(
        """
        UPDATE ir_config_parameter
        SET key = 'qrr_partner_ref'
        WHERE key = 'isr_partner_ref'
    """
    )

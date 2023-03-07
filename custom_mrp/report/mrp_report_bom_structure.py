from odoo import api, models, _


class ReportBomStructure(models.AbstractModel):
    _inherit = 'report.mrp.report_bom_structure'


    # @Override odoo core method _get_bom_lines
    def _get_bom_lines(self, bom, bom_quantity, product, line_id, level):

        def _name_get(default_code, name_of_component):
            code = default_code if default_code else False
            name = name_of_component if name_of_component else ''

            if code:
                name = '[%s] %s' % (code,name)
            return name

        components = []
        total = 0
        for line in bom.bom_line_ids:
            line_quantity = (bom_quantity / (bom.product_qty or 1.0)) * line.product_qty
            if line._skip_bom_line(product):
                continue
            company = bom.company_id or self.env.company
            price = line.product_id.uom_id._compute_price(line.product_id.with_company(company).standard_price, line.product_uom_id) * line_quantity
            if line.child_bom_id:
                factor = line.product_uom_id._compute_quantity(line_quantity, line.child_bom_id.product_uom_id)
                sub_total = self._get_price(line.child_bom_id, factor, line.product_id)
            else:
                sub_total = price
            sub_total = self.env.company.currency_id.round(sub_total)

            product_display_name = _name_get(line.product_id.default_code, line.product_id.name)
            components.append({
                'prod_id': line.product_id.id,
                # 'prod_name': line.product_id.display_name,
                'prod_name': product_display_name,
                'code': line.child_bom_id and line.child_bom_id.display_name or '',
                'prod_qty': line_quantity,
                'prod_uom': line.product_uom_id.name,
                'prod_cost': company.currency_id.round(price),
                'parent_id': bom.id,
                'line_id': line.id,
                'level': level or 0,
                'total': sub_total,
                'child_bom': line.child_bom_id.id,
                'phantom_bom': line.child_bom_id and line.child_bom_id.type == 'phantom' or False,
                'attachments': self.env['mrp.document'].search(['|', '&',
                    ('res_model', '=', 'product.product'), ('res_id', '=', line.product_id.id), '&', ('res_model', '=', 'product.template'), ('res_id', '=', line.product_id.product_tmpl_id.id)]),
            })
            total += sub_total
        return components, total
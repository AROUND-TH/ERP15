from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class ReleaseProcedure(models.Model):
    _name = "release.procedure"
    _description = "ReleaseProcedure"
    _order = 'procedure_type desc, max_amount desc, min_amount desc, condition asc'

    name = fields.Char(
        string='Name',
        required=True,
        index=True,
        default='New'
    )
    procedure_type = fields.Selection([
        ('pr', 'PR'),
        ('po', 'PO'),
    ], 'Procedure Type', default='pr', required=True, index=True)

    category_ids = fields.Many2many('product.category', string='Category', required=True)

    condition = fields.Selection(
        [
            ('greater_than', '>'),
            ('less_than', '<'),
            ('greater_than_equal', '>='),
            ('less_than_equal', '<='),
            ('equal', '='),
        ],
        string='Condition',
        default='equal',
        required=True,
    )
    min_amount = fields.Float(
        string='Start at',
        required=True,
        copy=False,
    )
    max_amount = fields.Float(
        string='Compare',
        required=True,
        copy=False,
    )

    procedure_line_ids = fields.One2many(
        'release.procedure.line',
        'procedure_id',
        copy=True,
    )

    @api.constrains('procedure_type', 'category_ids', 'condition', 'min_amount', 'max_amount')
    def validate_unique_constrains(self):
        query_chk = """
            SELECT rp.id, rp."name", rp_chk.chk_count, rp_max.chk_max
            FROM release_procedure rp 
            INNER JOIN
            (SELECT release_procedure_id, count(product_category_id) as chk_count
            FROM product_category_release_procedure_rel pcrpr
            WHERE product_category_id IN %s
            GROUP BY release_procedure_id
            HAVING count(product_category_id) = %s
            ) AS rp_chk
            ON rp.id = rp_chk.release_procedure_id
            INNER JOIN
            (SELECT release_procedure_id, count(product_category_id) as chk_max
            FROM product_category_release_procedure_rel pcrpr
            GROUP BY release_procedure_id
            ) AS rp_max
            ON rp_chk.release_procedure_id = rp_max.release_procedure_id
            WHERE rp.procedure_type = %s
            AND rp."condition" = %s
            AND rp.min_amount = %s
            AND rp.max_amount = %s
            AND rp_chk.chk_count = rp_max.chk_max
            ORDER BY rp.max_amount DESC,
            rp.min_amount DESC, rp.id DESC
        """
        self._cr.execute(query_chk, (
            tuple(self.category_ids.ids), len(self.category_ids), self.procedure_type, self.condition, self.min_amount,
            self.max_amount))
        vals = self._cr.dictfetchall()

        for val in vals:
            if val['id'] != self.id:
                raise ValidationError(_('You already have the data in the "Release Procedure" list.'))

    def get_selection_label(self, object, field_name, field_value):
        return _(dict(self.env[object].fields_get(allfields=[field_name])[field_name]['selection'])[field_value])

    def recursive_category_id(self, category, list=[]):
        if category:
            list.append(category.id)
            if category.parent_id:
                return self.recursive_category_id(category.parent_id, list)
            else:
                return list

    @api.model
    def default_get(self, field_list):
        if not field_list:
            field_list = ['name', 'procedure_type', 'category_ids', 'condition', 'min_amount', 'max_amount',
                          'procedure_line_ids']
        return super(ReleaseProcedure, self).default_get(field_list)

    def copy(self, default=None):
        default = default or {}
        copied_count = self.search_count([('name', '=like', _("Copy of {}%").format(self.name))])
        if not copied_count:
            new_name = _("Copy of {}").format(self.name)
        else:
            new_name = _("Copy of {} ({})").format(self.name, copied_count)
        default.update({'name': new_name, 'min_amount': 0, 'max_amount': 0})
        return super(ReleaseProcedure, self).copy(default)

    @api.model
    def create(self, values):
        if values.get('category_ids'):
            categories = self.env['product.category'].browse(values.get('category_ids')[0][2])

            category_ids = []
            for category in categories:
                self.recursive_category_id(category, category_ids)

            category_ids = list(set(category_ids))
            values['category_ids'] = [(6, 0, category_ids)]

        if values.get('name', 'New').lower() == 'new':
            name = _("{} (เริ่มที่ {} เงื่อนไข {} {})")
            pre = self.get_selection_label('release.procedure', 'procedure_type', values['procedure_type'])
            condition = self.get_selection_label('release.procedure', 'condition', values['condition'])

            values['name'] = name.format(pre, values['min_amount'], condition, values['max_amount'])

        res = super(ReleaseProcedure, self).create(values)

        positions = []
        level_list = []

        for line in res.procedure_line_ids:
            if line.positions_id.id in positions:
                raise UserError(_('You already have the "%s" data in line.' % line.positions_id.name))
            else:
                positions.append(line.positions_id.id)

            if line.approver in level_list:
                raise UserError(_('You already have the "%s" data in line.' % line.approver))
            else:
                level_list.append(line.approver)

        return res

    def write(self, values):
        if values.get('category_ids'):
            categories = self.env['product.category'].browse(values.get('category_ids')[0][2])

            category_ids = []
            for category in categories:
                self.recursive_category_id(category, category_ids)

            category_ids = list(set(category_ids))
            values['category_ids'] = [(6, 0, category_ids)]

        if values.get('name', self.name).lower() == 'new':
            name = _("{} (เริ่มที่ {} เงื่อนไข {} {})")
            pre = self.get_selection_label('release.procedure', 'procedure_type',
                                           values.get('procedure_type', self.procedure_type))
            condition = self.get_selection_label('release.procedure', 'condition',
                                                 values.get('condition', self.condition))

            values['name'] = name.format(pre, values.get('min_amount', self.min_amount), condition,
                                         values.get('max_amount', self.max_amount))

        if values.get('procedure_line_ids'):
            for procedure_line in values.get('procedure_line_ids'):
                if procedure_line[2] and 'positions_id' in procedure_line[2]:
                    line_id = self.env['release.procedure.line'].search(
                        [('procedure_id', '=', self.id), ('positions_id', '=', procedure_line[2]['positions_id'])])
                    if line_id:
                        raise UserError(_('You already have the "%s" data in line.' % line_id.positions_id.name))

                if procedure_line[2] and 'approver' in procedure_line[2]:
                    line_id = self.env['release.procedure.line'].search(
                        [('procedure_id', '=', self.id), ('approver', '=', procedure_line[2]['approver'])])
                    if line_id:
                        raise UserError(_('You already have the "%s" data in line.' % line_id.approver))

        return super(ReleaseProcedure, self).write(values)


class ReleaseProcedureLine(models.Model):
    _name = "release.procedure.line"
    _description = "ReleaseProcedureLine"
    _order = 'procedure_id, approver'

    procedure_id = fields.Many2one('release.procedure', string='Release Procedure', index=True)
    approver = fields.Selection([
        ('lv1', 'Level 1'),
        ('lv2', 'Level 2'),
        ('lv3', 'Level 3'),
        ('lv4', 'Level 4'),
    ], 'Approver', default='lv1', required=True)

    positions_id = fields.Many2one('hr.job', string='Job Positions', required=True)

    position_chk = fields.Selection([('id', 'ID'), ('name', 'NAME')], string='Match Position By', default='name',
                                    required=True)
